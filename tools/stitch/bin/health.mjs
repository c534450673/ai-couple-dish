import { performance } from "node:perf_hooks";
import { pathToFileURL } from "node:url";
import { readStitchConfig, publicConfig } from "../src/config.mjs";
import { createStitchSdk, assertRequiredTools } from "../src/client.mjs";
import { logEvent } from "../src/logger.mjs";

const STITCH_TRANSPORT_ERROR_PREFIX = "Stitch Transport Error:";

function isExpectedCloseAbortError(isClosing, args) {
  return (
    isClosing &&
    args.length === 2 &&
    args[0] === STITCH_TRANSPORT_ERROR_PREFIX &&
    args[1]?.name === "AbortError"
  );
}

function toErrorDetails(error) {
  return {
    name: error?.name || "Error",
    message: error?.message || String(error)
  };
}

export async function runStitchHealth(dependencies = {}) {
  const {
    readConfig = readStitchConfig,
    createSdk = createStitchSdk,
    assertTools = assertRequiredTools,
    write = line => process.stderr.write(line + String.fromCharCode(10))
  } = dependencies;
  const started = performance.now();
  const originalConsoleError = console.error;
  let client;
  let config;
  let tools;
  let primaryError;
  let sdkConsoleError;
  let isClosing = false;

  console.error = (...args) => {
    if (isExpectedCloseAbortError(isClosing, args)) return;
    sdkConsoleError ??= {
      name: "StitchConsoleError",
      message: args
        .map(value =>
          typeof value === "string"
            ? value
            : value?.message
              ? (value.name || "Error") + ": " + value.message
              : String(value)
        )
        .join(" ")
    };
  };

  try {
    config = readConfig();
    ({ client } = createSdk(config));
    tools = await assertTools(client);
  } catch (error) {
    primaryError = error;
  } finally {
    if (client) {
      isClosing = true;
      try {
        await client.close();
      } catch (error) {
        primaryError ??= error;
      }
      await new Promise(resolve => setImmediate(resolve));
      isClosing = false;
    }
    console.error = originalConsoleError;
  }

  const durationMs = Math.round(performance.now() - started);
  const error = primaryError ?? sdkConsoleError;
  if (error) {
    const details = toErrorDetails(error);
    logEvent(
      "stitch.health",
      {
        result: "error",
        durationMs,
        errorName: details.name,
        errorMessage: details.message,
        ...(sdkConsoleError ? { sdkConsoleError } : {})
      },
      write
    );
    return 1;
  }

  logEvent(
    "stitch.health",
    { result: "ok", durationMs, tools, config: publicConfig(config) },
    write
  );
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await runStitchHealth();
}
