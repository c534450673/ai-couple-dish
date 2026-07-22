import { createHash } from "node:crypto";
import { mkdir, mkdtemp, rename, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { performance } from "node:perf_hooks";
import { logEvent } from "./logger.mjs";
import { effectiveProjectId, projectRegistry } from "./project-shards.mjs";

const SCREENSHOT_FALLBACK_SOURCE = "screenshot-fallback";

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[character]);
}

function screenshotFallbackHtml(localId) {
  const safeLocalId = escapeHtml(localId);
  const safeScreenshotPathSegment = escapeHtml(encodeURIComponent(localId));
  const notice = escapeHtml(
    "仅视觉参考：Stitch 未提供可下载的 HTML，以下内容来自真实截图。"
  );
  return `<!doctype html>
<html lang="zh-CN" data-stitch-html-source="${SCREENSHOT_FALLBACK_SOURCE}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${safeLocalId} - ${notice}</title>
  <style>
    body { margin: 0; padding: 24px; background: #f5f5f5; color: #222; font-family: sans-serif; }
    main { max-width: 960px; margin: 0 auto; }
    .notice { margin: 0 0 16px; padding: 12px 16px; background: #fff4d6; border: 1px solid #e7c765; }
    img { display: block; max-width: 100%; height: auto; margin: 0 auto; }
  </style>
</head>
<body>
  <main>
    <p class="notice">${notice}</p>
    <img src="../screenshots/${safeScreenshotPathSegment}.png" alt="${safeLocalId} ${notice}">
  </main>
</body>
</html>
`;
}

export async function downloadArtifact(url, outputPath, fetchImpl = fetch) {
  const response = await fetchImpl(url, { redirect: "follow" });
  if (!response.ok) {
    throw new Error("Artifact download failed with HTTP " + response.status);
  }
  const buffer = Buffer.from(await response.arrayBuffer());
  await writeFile(outputPath, buffer);
  return { sha256: sha256(buffer), bytes: buffer.length };
}

function toErrorDetails(error) {
  const message = error?.message || String(error);
  return {
    name: error?.name || "Error",
    message: message.replace(/(https?:\/\/[^\s?]+)\?[^\s]*/g, "$1?[REDACTED]")
  };
}

function isTransientReadError(error, operation) {
  if (error?.recoverable === true) return true;
  const message = (error?.message || String(error)).toLowerCase();
  if (message.includes("service is currently unavailable")) return true;
  return (
    operation === "get_screen" &&
    message.includes("request contains an invalid argument")
  );
}

async function readWithRetry(
  operation,
  context,
  { maxAttempts, sleep, write }
) {
  const started = performance.now();
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      if (!isTransientReadError(error, context.operation) || attempt === maxAttempts) {
        throw error;
      }
      const delayMs = 1000 * attempt;
      const details = toErrorDetails(error);
      logEvent(
        "stitch.export.read",
        {
          result: "retry",
          ...context,
          attempt,
          delayMs,
          errorName: details.name,
          errorMessage: details.message,
          durationMs: Math.round(performance.now() - started)
        },
        write
      );
      await sleep(delayMs);
    }
  }
  throw new Error("Unreachable Stitch export read retry state");
}

function redactStagingPath(error, stagingRoot) {
  if (error && typeof error.message === "string") {
    error.message = error.message.replaceAll(stagingRoot, "[STAGING]");
  }
  return error;
}

async function exportArtifact({
  projectId,
  localId,
  reference,
  artifact,
  outputRoot,
  fetchImpl,
  getUrl,
  fallbackContent,
  write
}) {
  const started = performance.now();
  const context = {
    projectId,
    localId,
    screenId: reference.screenId,
    kind: reference.kind,
    artifact
  };
  logEvent("stitch.export.screen", { result: "started", ...context }, write);
  try {
    const url = await getUrl();
    const usesFallback =
      fallbackContent !== undefined &&
      (typeof url !== "string" || !url.trim());
    const artifactSource = usesFallback ? SCREENSHOT_FALLBACK_SOURCE : "stitch";
    let result;
    if (usesFallback) {
      const buffer = Buffer.from(fallbackContent, "utf8");
      await writeFile(join(outputRoot, artifact), buffer);
      result = { sha256: sha256(buffer), bytes: buffer.length };
    } else {
      result = await downloadArtifact(url, join(outputRoot, artifact), fetchImpl);
    }
    logEvent(
      "stitch.export.screen",
      {
        result: "ok",
        ...context,
        artifactSource,
        bytes: result.bytes,
        hash: result.sha256,
        durationMs: Math.round(performance.now() - started)
      },
      write
    );
    return { ...result, artifactSource };
  } catch (error) {
    const details = toErrorDetails(redactStagingPath(error, outputRoot));
    logEvent(
      "stitch.export.screen",
      {
        result: "error",
        ...context,
        errorName: details.name,
        errorMessage: details.message,
        durationMs: Math.round(performance.now() - started)
      },
      write
    );
    throw error;
  }
}

export async function exportDesignProject(
  sdk,
  state,
  outputRoot,
  fetchImpl = fetch,
  write = line => process.stderr.write(line + String.fromCharCode(10)),
  {
    maxReadAttempts = 3,
    sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds))
  } = {}
) {
  if (!Number.isInteger(maxReadAttempts) || maxReadAttempts < 1) {
    throw new Error("maxReadAttempts must be a positive integer");
  }
  await mkdir(outputRoot, { recursive: true });
  const stagingRoot = await mkdtemp(join(outputRoot, ".stitch-export-"));

  try {
    await mkdir(join(stagingRoot, "screenshots"));
    await mkdir(join(stagingRoot, "html"));
    const projectHandles = new Map();
    const projectScreenIndexes = new Map();
    function projectFor(projectId) {
      if (!projectHandles.has(projectId)) {
        projectHandles.set(projectId, sdk.project(projectId));
      }
      return projectHandles.get(projectId);
    }
    async function screenFor(projectId, screenId) {
      const project = projectFor(projectId);
      if (typeof project.screens === "function") {
        if (!projectScreenIndexes.has(projectId)) {
          const started = performance.now();
          logEvent(
            "stitch.export.project-screens",
            { result: "started", projectId },
            write
          );
          projectScreenIndexes.set(
            projectId,
            readWithRetry(
              () => project.screens(),
              { operation: "list_screens", projectId },
              { maxAttempts: maxReadAttempts, sleep, write }
            ).then(
              listedScreens => {
                const index = new Map(
                  listedScreens.map(screen => [screen.screenId, screen])
                );
                logEvent(
                  "stitch.export.project-screens",
                  {
                    result: "ok",
                    projectId,
                    screenCount: index.size,
                    durationMs: Math.round(performance.now() - started)
                  },
                  write
                );
                return index;
              },
              error => {
                const details = toErrorDetails(error);
                logEvent(
                  "stitch.export.project-screens",
                  {
                    result: "error",
                    projectId,
                    errorName: details.name,
                    errorMessage: details.message,
                    durationMs: Math.round(performance.now() - started)
                  },
                  write
                );
                throw error;
              }
            )
          );
        }
        const listedScreen = (await projectScreenIndexes.get(projectId)).get(
          screenId
        );
        if (listedScreen) return listedScreen;
      }
      return readWithRetry(
        () => project.getScreen(screenId),
        { operation: "get_screen", projectId, screenId },
        { maxAttempts: maxReadAttempts, sleep, write }
      );
    }
    const screens = [];
    for (const [localId, reference] of Object.entries(state.screens)) {
      const projectId = effectiveProjectId(state, reference);
      if (typeof projectId !== "string" || !projectId.trim()) {
        throw new Error("Expected every exported screen to have a projectId");
      }
      let screen;
      const screenshot = "screenshots/" + localId + ".png";
      const html = "html/" + localId + ".html";
      const imageResult = await exportArtifact({
        projectId,
        localId,
        reference,
        artifact: screenshot,
        outputRoot: stagingRoot,
        fetchImpl,
        async getUrl() {
          screen = await screenFor(projectId, reference.screenId);
          return screen.getImage();
        },
        write
      });
      const htmlResult = await exportArtifact({
        projectId,
        localId,
        reference,
        artifact: html,
        outputRoot: stagingRoot,
        fetchImpl,
        getUrl: () => screen.getHtml(),
        fallbackContent: screenshotFallbackHtml(localId),
        write
      });
      screens.push({
        localId,
        projectId,
        screenId: reference.screenId,
        kind: reference.kind,
        screenshot,
        screenshotSha256: imageResult.sha256,
        html,
        htmlSha256: htmlResult.sha256,
        htmlSource: htmlResult.artifactSource,
        exportedAt: new Date().toISOString()
      });
    }

    const manifest = {
      version: 1,
      projectId: state.projectId,
      projectIds: projectRegistry(state).map(project => project.projectId),
      screens
    };
    const stagedManifest = join(stagingRoot, "manifest.json");
    await writeFile(stagedManifest, JSON.stringify(manifest, null, 2) + "\n");
    await mkdir(join(outputRoot, "screenshots"), { recursive: true });
    await mkdir(join(outputRoot, "html"), { recursive: true });
    for (const screen of screens) {
      await rename(
        join(stagingRoot, screen.screenshot),
        join(outputRoot, screen.screenshot)
      );
      await rename(join(stagingRoot, screen.html), join(outputRoot, screen.html));
    }
    await rename(stagedManifest, join(outputRoot, "manifest.json"));
    return manifest;
  } catch (error) {
    throw redactStagingPath(error, stagingRoot);
  } finally {
    try {
      await rm(stagingRoot, { recursive: true, force: true });
    } catch (error) {
      throw redactStagingPath(error, stagingRoot);
    }
  }
}
