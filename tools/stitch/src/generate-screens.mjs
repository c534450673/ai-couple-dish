import { performance } from "node:perf_hooks";
import { logEvent } from "./logger.mjs";
import { SCREEN_SPECS, getScreenPrompt } from "./prompts.mjs";

async function withRetry(operation, { maxAttempts, sleep, onRetry }) {
  let lastError;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await operation(attempt);
    } catch (error) {
      lastError = error;
      if (error?.recoverable !== true || attempt >= maxAttempts) {
        throw error;
      }
      const delayMs = 1000 * attempt;
      await onRetry(error, attempt, delayMs);
      await sleep(delayMs);
    }
  }
  throw lastError;
}

export async function generateRemainingScreens(
  sdk,
  initialState,
  {
    checkpoint,
    sleep = milliseconds =>
      new Promise(resolve => setTimeout(resolve, milliseconds)),
    maxAttempts = 3
  }
) {
  let state = initialState;
  const project = sdk.project(state.projectId);
  const remaining = SCREEN_SPECS.filter(screen => screen.id !== "home");

  for (const screen of remaining) {
    if (state.screens[screen.id]) {
      logEvent("stitch.screen.skip", {
        result: "ok",
        projectId: state.projectId,
        screenId: screen.id,
        screenTitle: screen.title,
        reason: "already-generated"
      });
      continue;
    }

    const started = performance.now();
    const generated = await withRetry(
      async attempt => {
        logEvent("stitch.screen.generate", {
          result: "started",
          projectId: state.projectId,
          screenId: screen.id,
          screenTitle: screen.title,
          deviceType: screen.deviceType,
          attempt
        });
        return project.generate(
          getScreenPrompt(screen.id),
          screen.deviceType
        );
      },
      {
        maxAttempts,
        sleep,
        async onRetry(error, attempt, delayMs) {
          logEvent("stitch.screen.retry", {
            result: "retry",
            projectId: state.projectId,
            screenId: screen.id,
            screenTitle: screen.title,
            deviceType: screen.deviceType,
            attempt,
            delayMs,
            errorName: error?.name || "Error",
            errorMessage: error?.message || String(error)
          });
        }
      }
    );
    if (
      typeof generated?.screenId !== "string" ||
      generated.screenId.trim().length === 0
    ) {
      throw new Error(
        `Expected generated screen ${screen.id} to include a non-empty screenId`
      );
    }

    state = {
      ...state,
      screens: {
        ...state.screens,
        [screen.id]: {
          screenId: generated.screenId,
          kind: "base"
        }
      }
    };
    await checkpoint(state);
    logEvent("stitch.screen.generate", {
      result: "ok",
      projectId: state.projectId,
      screenId: screen.id,
      screenTitle: screen.title,
      deviceType: screen.deviceType,
      remoteScreenId: generated.screenId,
      durationMs: Math.round(performance.now() - started)
    });
  }

  return state;
}
