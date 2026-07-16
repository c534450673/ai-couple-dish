import { performance } from "node:perf_hooks";
import { fileURLToPath, pathToFileURL } from "node:url";
import { logEvent } from "../src/logger.mjs";
import { SCREEN_SPECS } from "../src/prompts.mjs";
import { verifyDesignExport } from "../src/verifier.mjs";

const DEFAULT_OUTPUT_ROOT = fileURLToPath(
  new URL("../../../docs/design/stitch/couple-cosmos/", import.meta.url)
);
const DEFAULT_EXPECTED_IDS = Object.freeze([
  "home-base",
  "home-emotion",
  "home-food",
  "home-memory",
  ...SCREEN_SPECS.filter(screen => screen.id !== "home").map(screen => screen.id)
]);

export async function runStitchVerify(dependencies = {}) {
  const {
    verify = verifyDesignExport,
    outputRoot = DEFAULT_OUTPUT_ROOT,
    expectedIds = DEFAULT_EXPECTED_IDS,
    env = process.env,
    write = line => process.stderr.write(line + String.fromCharCode(10))
  } = dependencies;
  const started = performance.now();
  const forbiddenValues = [env.STITCH_API_KEY, env.STITCH_ACCESS_TOKEN];

  try {
    const result = await verify(
      outputRoot,
      expectedIds,
      forbiddenValues,
      write
    );
    logEvent(
      "stitch.verify",
      {
        result: "ok",
        screenCount: result.screenCount,
        durationMs: Math.round(performance.now() - started)
      },
      write
    );
    return 0;
  } catch (error) {
    let errorMessage = error?.message || String(error);
    for (const forbidden of forbiddenValues.filter(Boolean)) {
      errorMessage = errorMessage.replaceAll(String(forbidden), "[REDACTED]");
    }
    logEvent(
      "stitch.verify",
      {
        result: "error",
        durationMs: Math.round(performance.now() - started),
        errorName: error?.name || "Error",
        errorMessage
      },
      write
    );
    return 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await runStitchVerify();
}
