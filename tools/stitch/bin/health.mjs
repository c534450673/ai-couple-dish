import { performance } from "node:perf_hooks";
import { readStitchConfig, publicConfig } from "../src/config.mjs";
import { createStitchSdk, assertRequiredTools } from "../src/client.mjs";
import { logEvent } from "../src/logger.mjs";

const started = performance.now();
const config = readStitchConfig();
const { client } = createStitchSdk(config);

try {
  const tools = await assertRequiredTools(client);
  logEvent("stitch.health", {
    result: "ok",
    durationMs: Math.round(performance.now() - started),
    tools,
    config: publicConfig(config)
  });
} catch (error) {
  logEvent("stitch.health", {
    result: "error",
    durationMs: Math.round(performance.now() - started),
    errorName: error.name,
    errorMessage: error.message
  });
  process.exitCode = 1;
} finally {
  await client.close();
}
