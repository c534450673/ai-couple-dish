import { performance } from "node:perf_hooks";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createStitchSdk } from "../src/client.mjs";
import { readStitchConfig } from "../src/config.mjs";
import { logEvent } from "../src/logger.mjs";
import {
  readGenerationState,
  writeGenerationState
} from "../src/state-store.mjs";
import { regenerateScreens } from "../src/targeted-regeneration.mjs";

const DEFAULT_STATE_PATH = fileURLToPath(
  new URL(
    "../../../docs/design/stitch/couple-cosmos/generation-state.json",
    import.meta.url
  )
);
const STITCH_TRANSPORT_ERROR_PREFIX = "Stitch Transport Error:";

function sanitizeErrorMessage(error, config) {
  let message = error?.message || String(error);
  const secretValues = [
    config?.apiKey,
    process.env.STITCH_API_KEY,
    process.env.STITCH_ACCESS_TOKEN
  ]
    .filter(Boolean)
    .map(String)
    .sort((left, right) => right.length - left.length);
  for (const secret of secretValues) {
    message = message.replaceAll(secret, "[REDACTED]");
  }
  return message
    .replace(/((?:https?:\/\/[^\s?]+|\/[^\s?]+))\?[^\s]*/gi, "$1")
    .replace(
      /\bauthorization\s*[:=]\s*bearer\s+(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\s,;&]+)/gi,
      "Authorization: Bearer [REDACTED]"
    )
    .replace(
      /((?:")?(?:stitch_api_key|stitch_access_token|api[_-]?key|token|authorization|secret|prompt)(?:")?\s*[:=]\s*)"(?:\\.|[^"\\])*"/gi,
      '$1"[REDACTED]"'
    )
    .replace(
      /((?:')?(?:stitch_api_key|stitch_access_token|api[_-]?key|token|authorization|secret|prompt)(?:')?\s*[:=]\s*)'(?:\\.|[^'\\])*'/gi,
      "$1'[REDACTED]'"
    )
    .replace(
      /\b(stitch_api_key|stitch_access_token|api[_-]?key|token|authorization|secret)\s*[:=]\s*[^\s,;&]+/gi,
      "$1=[REDACTED]"
    )
    .replace(/\bprompt\s*[:=]\s*[^,;&]+/gi, "prompt=[REDACTED]");
}

export async function runStitchRegenerate(
  localIds = process.argv.slice(2),
  dependencies = {}
) {
  const {
    readConfig = readStitchConfig,
    createSdk = createStitchSdk,
    readState = readGenerationState,
    writeState = writeGenerationState,
    regenerate = regenerateScreens,
    statePath = DEFAULT_STATE_PATH,
    write = line => process.stderr.write(line + String.fromCharCode(10))
  } = dependencies;
  const started = performance.now();
  const originalConsoleError = console.error;
  let config;
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
    config = readConfig();
    ({ sdk, client } = createSdk(config));
    state = await readState(statePath);
    state = await regenerate(sdk, state, localIds, {
      write,
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
      await new Promise(resolveTimer => setTimeout(resolveTimer, 0));
      await new Promise(resolveImmediate => setImmediate(resolveImmediate));
      isClosing = false;
    }
    console.error = originalConsoleError;
  }

  const durationMs = Math.round(performance.now() - started);
  const context = {
    targetCount: localIds.length,
    projectId: state?.projectId ?? null,
    projectTitle: state?.projectTitle ?? null,
    durationMs
  };
  if (failure) {
    logEvent(
      "stitch.regenerate",
      {
        result: "error",
        ...context,
        errorName: failure?.name || "Error",
        errorMessage: sanitizeErrorMessage(failure, config)
      },
      write
    );
    return 1;
  }

  logEvent("stitch.regenerate", { result: "ok", ...context }, write);
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await runStitchRegenerate();
}
