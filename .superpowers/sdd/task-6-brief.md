### Task 6: 导出 HTML、截图和 SHA-256 manifest

> Controller resolution: Task 6 先以 fake SDK/fetch 实现并验证导出器；`docs/design/stitch/couple-cosmos/` 中的真实 manifest、HTML 和截图由 Task 8 在真实 generation-state 产生后执行本命令生成，不得在本任务伪造远程资产。`bin/export.mjs` 必须像 Task 3/5 一样使用 cwd 无关的 `import.meta.url` 路径和单行结构化 CLI 错误边界，精准处理 SDK close AbortError；不得照抄下方 try 外初始化示例。当前基线已有 56+项测试，“14 tests PASS”是过时计数，验收以新鲜全量全绿为准。导出过程必须通过 `logEvent` 提供每屏开始/成功/失败及最终汇总的详细非敏感 JSON 日志。

**Files:**
- Modify: tools/stitch/package.json
- Create: tools/stitch/src/exporter.mjs
- Create: tools/stitch/bin/export.mjs
- Create: tools/stitch/test/exporter.test.mjs
- Generate: docs/design/stitch/couple-cosmos/manifest.json
- Generate: docs/design/stitch/couple-cosmos/screenshots/*
- Generate: docs/design/stitch/couple-cosmos/html/*

**Interfaces:**
- Produces: downloadArtifact(url, outputPath, fetchImpl) -> Promise<{ sha256, bytes }>
- Produces: exportDesignProject(sdk, state, outputRoot, fetchImpl) -> Promise<Manifest>
- Manifest entry: { localId, projectId, screenId, kind, screenshot, screenshotSha256, html, htmlSha256, exportedAt }

- [ ] **Step 1: 写下载与 manifest 失败测试**

Create tools/stitch/test/exporter.test.mjs:

~~~javascript
import assert from "node:assert/strict";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { exportDesignProject } from "../src/exporter.mjs";

test("exportDesignProject writes screenshot, html and hashes", async () => {
  const root = await mkdtemp(join(tmpdir(), "stitch-export-"));
  const sdk = {
    project(projectId) {
      assert.equal(projectId, "project-1");
      return {
        async getScreen(screenId) {
          assert.equal(screenId, "screen-1");
          return {
            async getImage() {
              return "https://assets.example/image";
            },
            async getHtml() {
              return "https://assets.example/html";
            }
          };
        }
      };
    }
  };
  const fetchImpl = async url => ({
    ok: true,
    status: 200,
    async arrayBuffer() {
      return Buffer.from(url.endsWith("image") ? "image-bytes" : "html-bytes");
    }
  });
  const state = {
    projectId: "project-1",
    projectTitle: "AI Couple Dish - Couple Cosmos",
    screens: {
      login: { screenId: "screen-1", kind: "base" }
    }
  };

  const manifest = await exportDesignProject(sdk, state, root, fetchImpl);
  assert.equal(manifest.version, 1);
  assert.equal(manifest.screens.length, 1);
  assert.equal(
    await readFile(join(root, "screenshots", "login.png"), "utf8"),
    "image-bytes"
  );
  assert.equal(
    await readFile(join(root, "html", "login.html"), "utf8"),
    "html-bytes"
  );
  assert.equal(manifest.screens[0].screenshotSha256.length, 64);
});
~~~

- [ ] **Step 2: 运行测试并验证导出模块不存在**

Run:

~~~bash
cd tools/stitch
node --test test/exporter.test.mjs
~~~

Expected: FAIL，错误包含 ERR_MODULE_NOT_FOUND。

- [ ] **Step 3: 实现安全下载、哈希和原子 manifest**

Create tools/stitch/src/exporter.mjs:

~~~javascript
import { createHash } from "node:crypto";
import { mkdir, rename, writeFile } from "node:fs/promises";
import { join } from "node:path";

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

export async function exportDesignProject(
  sdk,
  state,
  outputRoot,
  fetchImpl = fetch
) {
  const screenshotRoot = join(outputRoot, "screenshots");
  const htmlRoot = join(outputRoot, "html");
  await mkdir(screenshotRoot, { recursive: true });
  await mkdir(htmlRoot, { recursive: true });

  const project = sdk.project(state.projectId);
  const screens = [];
  for (const [localId, reference] of Object.entries(state.screens)) {
    const screen = await project.getScreen(reference.screenId);
    const screenshot = "screenshots/" + localId + ".png";
    const html = "html/" + localId + ".html";
    const imageResult = await downloadArtifact(
      await screen.getImage(),
      join(outputRoot, screenshot),
      fetchImpl
    );
    const htmlResult = await downloadArtifact(
      await screen.getHtml(),
      join(outputRoot, html),
      fetchImpl
    );
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
  const destination = join(outputRoot, "manifest.json");
  await writeFile(
    temporary,
    JSON.stringify(manifest, null, 2) + String.fromCharCode(10)
  );
  await rename(temporary, destination);
  return manifest;
}
~~~

Create tools/stitch/bin/export.mjs:

~~~javascript
import { resolve } from "node:path";
import { performance } from "node:perf_hooks";
import { readStitchConfig } from "../src/config.mjs";
import { createStitchSdk } from "../src/client.mjs";
import { readGenerationState } from "../src/state-store.mjs";
import { exportDesignProject } from "../src/exporter.mjs";
import { logEvent } from "../src/logger.mjs";

const root = resolve("../../docs/design/stitch/couple-cosmos");
const state = await readGenerationState(resolve(root, "generation-state.json"));
if (!state.projectId) {
  throw new Error("Run npm run stitch:generate before export");
}
const started = performance.now();
const config = readStitchConfig();
const { sdk, client } = createStitchSdk(config);

try {
  const manifest = await exportDesignProject(sdk, state, root);
  logEvent("stitch.export", {
    result: "ok",
    projectId: manifest.projectId,
    screenCount: manifest.screens.length,
    durationMs: Math.round(performance.now() - started)
  });
} catch (error) {
  logEvent("stitch.export", {
    result: "error",
    errorName: error.name,
    errorMessage: error.message,
    durationMs: Math.round(performance.now() - started)
  });
  process.exitCode = 1;
} finally {
  await client.close();
}
~~~

Add the export command:

~~~bash
cd tools/stitch
npm pkg set 'scripts.stitch:export=node bin/export.mjs'
~~~

- [ ] **Step 4: 运行导出测试**

Run:

~~~bash
cd tools/stitch
npm test
~~~

Expected: 14 tests PASS。

- [ ] **Step 5: 提交导出器代码**

Run:

~~~bash
git add tools/stitch/package.json tools/stitch/src/exporter.mjs tools/stitch/bin/export.mjs tools/stitch/test/exporter.test.mjs
git commit -m "design: 增加Stitch设计资产导出"
~~~
