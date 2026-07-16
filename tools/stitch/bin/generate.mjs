import { performance } from "node:perf_hooks";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createStitchSdk } from "../src/client.mjs";
import { readStitchConfig } from "../src/config.mjs";
import { generateHomeDesign } from "../src/generate-home.mjs";
import { generateRemainingScreens } from "../src/generate-screens.mjs";
import { logEvent } from "../src/logger.mjs";
import {
  readGenerationState,
  writeGenerationState
} from "../src/state-store.mjs";

const DEFAULT_STATE_PATH = fileURLToPath(
  new URL(
    "../../../docs/design/stitch/couple-cosmos/generation-state.json",
    import.meta.url
  )
);
const STITCH_TRANSPORT_ERROR_PREFIX = "Stitch Transport Error:";

export async function runStitchGenerate(dependencies = {}) {
  const {
    readConfig = readStitchConfig,
    createSdk = createStitchSdk,
    readState = readGenerationState,
    writeState = writeGenerationState,
    generateHome = generateHomeDesign,
    generateScreens = generateRemainingScreens,
    statePath = DEFAULT_STATE_PATH,
    write = line => process.stderr.write(line + String.fromCharCode(10))
  } = dependencies;
  const started = performance.now();
  const originalConsoleError = console.error;
  let client;
  let sdk;
  let state;
  let failure;
  let isClosing = false;

  console.error = (...args) => {
    if (
      isClosing &&
      args.length === 2 &&
      args[0] === STITCH_TRANSPORT_ERROR_PREFIX &&
      args[1]?.name === "AbortError"
    ) {
      return;
    }
    failure ??= {
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
    const config = readConfig();
    ({ sdk, client } = createSdk(config));
    state = await readState(statePath);

    const homeAction =
      state.projectId && state.screens["home-base"]
        ? "skip"
        : state.projectId
          ? "resume"
          : "create";
    const homeStarted = performance.now();
    logEvent(
      "stitch.home.generate",
      {
        result: "started",
        action: homeAction,
        projectId: state.projectId,
        projectTitle: state.projectTitle,
        screenId: "home"
      },
      write
    );
    state = await generateHome(sdk, state);
    logEvent(
      "stitch.home.generate",
      {
        result: "ok",
        action: homeAction,
        projectId: state.projectId,
        projectTitle: state.projectTitle,
        screenId: "home",
        remoteScreenId: state.screens["home-base"]?.screenId,
        durationMs: Math.round(performance.now() - homeStarted)
      },
      write
    );

    await writeState(statePath, state);
    state = await generateScreens(sdk, state, {
      async checkpoint(nextState) {
        await writeState(statePath, nextState);
      }
    });
  } catch (error) {
    failure ??= error;
  } finally {
    if (client) {
      isClosing = true;
      try {
        await client.close();
      } catch (error) {
        failure ??= error;
      }
      await new Promise(resolveImmediate => setImmediate(resolveImmediate));
      isClosing = false;
    }
    console.error = originalConsoleError;
  }

  const durationMs = Math.round(performance.now() - started);
  if (failure) {
    logEvent(
      "stitch.generate",
      {
        result: "error",
        durationMs,
        projectId: state?.projectId,
        projectTitle: state?.projectTitle,
        errorName: failure?.name || "Error",
        errorMessage: failure?.message || String(failure)
      },
      write
    );
    return 1;
  }

  logEvent(
    "stitch.generate",
    {
      result: "ok",
      durationMs,
      projectId: state.projectId,
      projectTitle: state.projectTitle,
      screenCount: Object.keys(state.screens).length
    },
    write
  );
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await runStitchGenerate();
}
