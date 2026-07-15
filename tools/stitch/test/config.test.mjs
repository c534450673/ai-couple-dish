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
