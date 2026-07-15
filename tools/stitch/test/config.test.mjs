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

test("logEvent redacts normalized sensitive field names recursively", () => {
  const lines = [];
  logEvent(
    "stitch.health",
    {
      STITCH_API_KEY: "environment-key",
      stitchApiKey: "camel-case-key",
      nested: {
        refreshToken: "refresh-token",
        authorization: "Bearer credential",
        clientSecret: "client-secret",
        screenId: "screen-2"
      }
    },
    line => lines.push(line)
  );

  const output = JSON.parse(lines[0]);
  assert.equal(output.STITCH_API_KEY, "[REDACTED]");
  assert.equal(output.stitchApiKey, "[REDACTED]");
  assert.equal(output.nested.refreshToken, "[REDACTED]");
  assert.equal(output.nested.authorization, "[REDACTED]");
  assert.equal(output.nested.clientSecret, "[REDACTED]");
  assert.equal(output.nested.screenId, "screen-2");
});

test("logEvent emits stable protected metadata defaults", () => {
  const lines = [];
  logEvent(undefined, {}, line => lines.push(line));

  const output = JSON.parse(lines[0]);
  assert.match(output.timestamp, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
  assert.equal(output.event, "unknown");
  assert.equal(output.result, "unknown");
  assert.equal(output.durationMs, 0);
});

test("logEvent keeps protected metadata after context fields", () => {
  const lines = [];
  logEvent(
    "stitch.health",
    {
      timestamp: "spoofed-timestamp",
      event: "spoofed-event",
      result: "ok",
      durationMs: 37,
      screenId: "screen-3"
    },
    line => lines.push(line)
  );

  const output = JSON.parse(lines[0]);
  assert.notEqual(output.timestamp, "spoofed-timestamp");
  assert.equal(output.event, "stitch.health");
  assert.equal(output.result, "ok");
  assert.equal(output.durationMs, 37);
  assert.equal(output.screenId, "screen-3");
});
