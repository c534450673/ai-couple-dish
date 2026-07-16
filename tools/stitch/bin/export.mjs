import { join } from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createStitchSdk } from "../src/client.mjs";
import { readStitchConfig } from "../src/config.mjs";
import { exportDesignProject } from "../src/exporter.mjs";
import { logEvent } from "../src/logger.mjs";
import { readGenerationState } from "../src/state-store.mjs";

const DEFAULT_OUTPUT_ROOT = fileURLToPath(
  new URL("../../../docs/design/stitch/couple-cosmos/", import.meta.url)
);
const DEFAULT_STATE_PATH = join(DEFAULT_OUTPUT_ROOT, "generation-state.json");
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
  const message = error?.message || String(error);
  return {
    name: error?.name || "Error",
    message: message.replace(/(https?:\/\/[^\s?]+)\?[^\s]*/g, "$1?[REDACTED]")
  };
}

function formatConsoleError(args) {
  return args
    .map(value => {
      if (typeof value === "string") {
        return toErrorDetails({ message: value }).message;
      }
      const details = toErrorDetails(value);
      return details.name + ": " + details.message;
    })
    .join(" ");
}

export async function runStitchExport(dependencies = {}) {
  const {
    readState = readGenerationState,
    readConfig = readStitchConfig,
    createSdk = createStitchSdk,
    exportProject = exportDesignProject,
    statePath = DEFAULT_STATE_PATH,
    outputRoot = DEFAULT_OUTPUT_ROOT,
    fetchImpl = fetch,
    write = line => process.stderr.write(line + String.fromCharCode(10))
  } = dependencies;
  const started = performance.now();
  const originalConsoleError = console.error;
  let client;
  let state;
  let manifest;
  let primaryError;
  let sdkConsoleError;
  let isClosing = false;

  console.error = (...args) => {
    if (isExpectedCloseAbortError(isClosing, args)) return;
    sdkConsoleError ??= {
      name: "StitchConsoleError",
      message: formatConsoleError(args)
    };
  };

  try {
    state = await readState(statePath);
    if (!state?.projectId) {
      throw new Error("Run npm run stitch:generate before export");
    }
    const config = readConfig();
    const created = createSdk(config);
    client = created.client;
    manifest = await exportProject(
      created.sdk,
      state,
      outputRoot,
      fetchImpl,
      write
    );
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
      "stitch.export",
      {
        result: "error",
        durationMs,
        projectId: state?.projectId,
        errorName: details.name,
        errorMessage: details.message,
        ...(sdkConsoleError ? { sdkConsoleError } : {})
      },
      write
    );
    return 1;
  }

  logEvent(
    "stitch.export",
    {
      result: "ok",
      durationMs,
      projectId: manifest.projectId,
      screenCount: manifest.screens.length
    },
    write
  );
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await runStitchExport();
}
