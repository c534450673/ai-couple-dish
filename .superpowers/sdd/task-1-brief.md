### Task 1: 建立隔离的 Stitch 工具与密钥安全边界

**Files:**
- Create: tools/stitch/package.json
- Create: tools/stitch/package-lock.json
- Create: tools/stitch/src/config.mjs
- Create: tools/stitch/src/logger.mjs
- Create: tools/stitch/test/config.test.mjs

**Interfaces:**
- Produces: readStitchConfig(env) -> { apiKey: string, host: string }
- Produces: publicConfig(config) -> { hasApiKey: boolean, host: string }
- Produces: logEvent(event, fields, write) -> void
- Consumes: process.env.STITCH_API_KEY and optional process.env.STITCH_HOST

- [ ] **Step 1: 写密钥与日志脱敏失败测试**

Create tools/stitch/test/config.test.mjs:

~~~javascript
import assert from "node:assert/strict";
import test from "node:test";
import { readStitchConfig, publicConfig } from "../src/config.mjs";
import { logEvent } from "../src/logger.mjs";

test("readStitchConfig rejects a missing API key", () => {
  assert.throws(
    () => readStitchConfig({}),
    /STITCH_API_KEY must be provided through the process environment/
  );
});

test("publicConfig never returns the API key", () => {
  const config = readStitchConfig({
    STITCH_API_KEY: "secret-value",
    STITCH_HOST: "https://stitch.googleapis.com/mcp"
  });

  assert.deepEqual(publicConfig(config), {
    hasApiKey: true,
    host: "https://stitch.googleapis.com/mcp"
  });
});

test("logEvent redacts key and token fields recursively", () => {
  const lines = [];
  logEvent(
    "stitch.health",
    {
      result: "ok",
      apiKey: "secret-value",
      nested: { accessToken: "token-value", screenId: "screen-1" }
    },
    line => lines.push(line)
  );

  assert.equal(lines.length, 1);
  assert.equal(lines[0].includes("secret-value"), false);
  assert.equal(lines[0].includes("token-value"), false);
  assert.equal(lines[0].includes("screen-1"), true);
});
~~~

- [ ] **Step 2: 运行测试并验证因模块不存在而失败**

Run:

~~~bash
cd tools/stitch
node --test test/config.test.mjs
~~~

Expected: FAIL，错误包含 ERR_MODULE_NOT_FOUND。

- [ ] **Step 3: 创建固定依赖和安全配置实现**

Create tools/stitch/package.json:

~~~json
{
  "name": "@ai-couple-dish/stitch-design",
  "private": true,
  "type": "module",
  "engines": {
    "node": ">=20"
  },
  "scripts": {
    "test": "node --test test/*.test.mjs"
  },
  "dependencies": {
    "@google/stitch-sdk": "0.3.5"
  }
}
~~~

Create tools/stitch/src/config.mjs:

~~~javascript
const DEFAULT_HOST = "https://stitch.googleapis.com/mcp";

export function readStitchConfig(env = process.env) {
  const apiKey = String(env.STITCH_API_KEY || "").trim();
  if (!apiKey) {
    throw new Error(
      "STITCH_API_KEY must be provided through the process environment"
    );
  }

  return Object.freeze({
    apiKey,
    host: String(env.STITCH_HOST || DEFAULT_HOST).trim()
  });
}

export function publicConfig(config) {
  return Object.freeze({
    hasApiKey: Boolean(config.apiKey),
    host: config.host
  });
}
~~~

Create tools/stitch/src/logger.mjs:

~~~javascript
const SENSITIVE_NAMES = new Set([
  "apikey",
  "api_key",
  "token",
  "accesstoken",
  "access_token",
  "authorization"
]);

function sanitize(value, key = "") {
  const normalizedKey = key.toLowerCase();
  if (SENSITIVE_NAMES.has(normalizedKey)) {
    return "[REDACTED]";
  }
  if (Array.isArray(value)) {
    return value.map(item => sanitize(item));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([name, item]) => [name, sanitize(item, name)])
    );
  }
  return value;
}

export function logEvent(
  event,
  fields = {},
  write = line => process.stderr.write(line + String.fromCharCode(10))
) {
  write(
    JSON.stringify({
      timestamp: new Date().toISOString(),
      event,
      ...sanitize(fields)
    })
  );
}
~~~

- [ ] **Step 4: 安装依赖并运行安全测试**

Run:

~~~bash
cd tools/stitch
npm install
npm test
~~~

Expected: package-lock.json 生成，3 tests PASS，安装版本为 @google/stitch-sdk@0.3.5。

- [ ] **Step 5: 提交隔离工具基础**

Run:

~~~bash
git add tools/stitch/package.json tools/stitch/package-lock.json tools/stitch/src/config.mjs tools/stitch/src/logger.mjs tools/stitch/test/config.test.mjs
git commit -m "build: 建立安全的Stitch设计工具"
~~~
