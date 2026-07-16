import { createHash } from "node:crypto";
import { mkdir, rename, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { performance } from "node:perf_hooks";
import { logEvent } from "./logger.mjs";

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
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

async function exportArtifact({
  projectId,
  localId,
  reference,
  artifact,
  outputRoot,
  fetchImpl,
  getUrl,
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
    const result = await downloadArtifact(
      await getUrl(),
      join(outputRoot, artifact),
      fetchImpl
    );
    logEvent(
      "stitch.export.screen",
      {
        result: "ok",
        ...context,
        bytes: result.bytes,
        hash: result.sha256,
        durationMs: Math.round(performance.now() - started)
      },
      write
    );
    return result;
  } catch (error) {
    const details = toErrorDetails(error);
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
  write = line => process.stderr.write(line + String.fromCharCode(10))
) {
  await mkdir(join(outputRoot, "screenshots"), { recursive: true });
  await mkdir(join(outputRoot, "html"), { recursive: true });

  const project = sdk.project(state.projectId);
  const screens = [];
  for (const [localId, reference] of Object.entries(state.screens)) {
    let screen;
    const screenshot = "screenshots/" + localId + ".png";
    const html = "html/" + localId + ".html";
    const imageResult = await exportArtifact({
      projectId: state.projectId,
      localId,
      reference,
      artifact: screenshot,
      outputRoot,
      fetchImpl,
      async getUrl() {
        screen = await project.getScreen(reference.screenId);
        return screen.getImage();
      },
      write
    });
    const htmlResult = await exportArtifact({
      projectId: state.projectId,
      localId,
      reference,
      artifact: html,
      outputRoot,
      fetchImpl,
      getUrl: () => screen.getHtml(),
      write
    });
    screens.push({
      localId,
      projectId: state.projectId,
      screenId: reference.screenId,
      kind: reference.kind,
      screenshot,
      screenshotSha256: imageResult.sha256,
      html,
      htmlSha256: htmlResult.sha256,
      exportedAt: new Date().toISOString()
    });
  }

  const manifest = { version: 1, projectId: state.projectId, screens };
  const temporary = join(outputRoot, "manifest.json.tmp");
  await writeFile(temporary, JSON.stringify(manifest, null, 2) + "\n");
  await rename(temporary, join(outputRoot, "manifest.json"));
  return manifest;
}
