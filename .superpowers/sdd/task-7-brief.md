### Task 7: 校验页面覆盖、文件哈希和密钥泄漏

> Controller resolution: 校验器必须真正消费 `generation-state.json`，并将 state、manifest 与预期 20 个 local ID 做精确集合与字段交叉校验：缺失、额外、重复 localId，projectId/screenId/kind 不一致均必须失败。manifest 中截图/HTML 路径必须是安全的预期相对路径，拒绝绝对路径、`..` 逃逸及与 localId 不匹配的文件名。密钥扫描范围包含 manifest buffer、generation-state buffer 及所有引用截图/HTML，不得在错误中回显 forbidden value。`bin/verify.mjs` 必须导出可注入的 `runStitchVerify`、使用 `import.meta.url` 定位输出根，并对每屏和最终结果输出详细结构化 JSON 日志。当前基线已有 74+项测试，“17 tests PASS”为过时计数。
> 为了使 brief 中“篡改 HTML 为 secret-value 时报密钥泄漏”的指定验收可成立，对已读 buffer 的 forbidden-value 扫描必须先于哈希比对；同一文件同时泄漏且哈希不匹配时，优先报 `Forbidden secret value found`。

**Files:**
- Modify: tools/stitch/package.json
- Create: tools/stitch/src/verifier.mjs
- Create: tools/stitch/bin/verify.mjs
- Create: tools/stitch/test/verifier.test.mjs

**Interfaces:**
- Produces: verifyDesignExport(root, expectedIds, forbiddenValues) -> Promise<{ screenCount: number }>
- Consumes: manifest.json, generation-state.json, screenshots/*, html/*

- [ ] **Step 1: 写缺页、哈希错误和密钥泄漏失败测试**

Create tools/stitch/test/verifier.test.mjs:

~~~javascript
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { verifyDesignExport } from "../src/verifier.mjs";

function hash(value) {
  return createHash("sha256").update(value).digest("hex");
}

async function fixture() {
  const root = await mkdtemp(join(tmpdir(), "stitch-verify-"));
  await mkdir(join(root, "screenshots"));
  await mkdir(join(root, "html"));
  await writeFile(join(root, "screenshots", "login.png"), "image");
  await writeFile(join(root, "html", "login.html"), "html");
  await writeFile(
    join(root, "manifest.json"),
    JSON.stringify({
      version: 1,
      projectId: "project-1",
      screens: [{
        localId: "login",
        projectId: "project-1",
        screenId: "screen-1",
        kind: "base",
        screenshot: "screenshots/login.png",
        screenshotSha256: hash("image"),
        html: "html/login.html",
        htmlSha256: hash("html"),
        exportedAt: "2026-07-15T00:00:00.000Z"
      }]
    })
  );
  return root;
}

test("verifyDesignExport accepts complete matching files", async () => {
  const root = await fixture();
  assert.deepEqual(
    await verifyDesignExport(root, ["login"], ["secret-value"]),
    { screenCount: 1 }
  );
});

test("verifyDesignExport rejects a missing required screen", async () => {
  const root = await fixture();
  await assert.rejects(
    () => verifyDesignExport(root, ["login", "bind"], []),
    /Missing exported screens: bind/
  );
});

test("verifyDesignExport rejects leaked secrets", async () => {
  const root = await fixture();
  await writeFile(join(root, "html", "login.html"), "secret-value");
  await assert.rejects(
    () => verifyDesignExport(root, ["login"], ["secret-value"]),
    /Forbidden secret value found/
  );
});
~~~

- [ ] **Step 2: 运行测试并验证校验模块不存在**

Run:

~~~bash
cd tools/stitch
node --test test/verifier.test.mjs
~~~

Expected: FAIL，错误包含 ERR_MODULE_NOT_FOUND。

- [ ] **Step 3: 实现覆盖率、哈希和泄漏校验**

Create tools/stitch/src/verifier.mjs:

~~~javascript
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

function hash(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

export async function verifyDesignExport(
  root,
  expectedIds,
  forbiddenValues = []
) {
  const manifestBuffer = await readFile(join(root, "manifest.json"));
  const manifest = JSON.parse(manifestBuffer.toString("utf8"));
  const exportedIds = manifest.screens.map(screen => screen.localId);
  const missing = expectedIds.filter(id => !exportedIds.includes(id));
  if (missing.length > 0) {
    throw new Error("Missing exported screens: " + missing.join(", "));
  }

  for (const screen of manifest.screens) {
    const screenshot = await readFile(join(root, screen.screenshot));
    const html = await readFile(join(root, screen.html));
    if (hash(screenshot) !== screen.screenshotSha256) {
      throw new Error("Screenshot hash mismatch: " + screen.localId);
    }
    if (hash(html) !== screen.htmlSha256) {
      throw new Error("HTML hash mismatch: " + screen.localId);
    }
    const searchable = Buffer.concat([screenshot, html, manifestBuffer]);
    for (const forbidden of forbiddenValues.filter(Boolean)) {
      if (searchable.includes(Buffer.from(forbidden))) {
        throw new Error("Forbidden secret value found: " + screen.localId);
      }
    }
  }

  return { screenCount: manifest.screens.length };
}
~~~

Create tools/stitch/bin/verify.mjs:

~~~javascript
import { resolve } from "node:path";
import { SCREEN_SPECS } from "../src/prompts.mjs";
import { verifyDesignExport } from "../src/verifier.mjs";
import { logEvent } from "../src/logger.mjs";

const expectedIds = [
  "home-base",
  "home-emotion",
  "home-food",
  "home-memory",
  ...SCREEN_SPECS.filter(screen => screen.id !== "home").map(screen => screen.id)
];
const root = resolve("../../docs/design/stitch/couple-cosmos");

try {
  const result = await verifyDesignExport(
    root,
    expectedIds,
    [process.env.STITCH_API_KEY, process.env.STITCH_ACCESS_TOKEN]
  );
  logEvent("stitch.verify", { result: "ok", ...result });
} catch (error) {
  logEvent("stitch.verify", {
    result: "error",
    errorName: error.name,
    errorMessage: error.message
  });
  process.exitCode = 1;
}
~~~

Add the verification command:

~~~bash
cd tools/stitch
npm pkg set 'scripts.stitch:verify=node bin/verify.mjs'
~~~

- [ ] **Step 4: 运行校验测试**

Run:

~~~bash
cd tools/stitch
npm test
~~~

Expected: 17 tests PASS。

- [ ] **Step 5: 提交校验器**

Run:

~~~bash
git add tools/stitch/package.json tools/stitch/src/verifier.mjs tools/stitch/bin/verify.mjs tools/stitch/test/verifier.test.mjs
git commit -m "test: 校验Stitch页面与导出哈希"
~~~
