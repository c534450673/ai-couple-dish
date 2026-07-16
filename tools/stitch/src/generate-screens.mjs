import { performance } from "node:perf_hooks";
import { logEvent } from "./logger.mjs";
import { SCREEN_SPECS, getScreenPrompt } from "./prompts.mjs";

async function withRetry(
  operation,
  { maxAttempts, sleep, onRetry, onFailure }
) {
  let lastError;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return { value: await operation(attempt), attempt };
    } catch (error) {
      lastError = error;
      if (error?.recoverable !== true || attempt >= maxAttempts) {
        await onFailure(error, attempt);
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
    maxAttempts = 3,
    write
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
      }, write);
      continue;
    }

    const started = performance.now();
    const { value: generated, attempt } = await withRetry(
      async attempt => {
        logEvent("stitch.screen.generate", {
          result: "started",
          projectId: state.projectId,
          screenId: screen.id,
          screenTitle: screen.title,
          deviceType: screen.deviceType,
          attempt
        }, write);
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
          }, write);
        },
        async onFailure(error, failedAttempt) {
          logEvent("stitch.screen.generate", {
            result: "error",
            projectId: state.projectId,
            screenId: screen.id,
            screenTitle: screen.title,
            deviceType: screen.deviceType,
            attempt: failedAttempt,
            maxAttempts,
            stage: "generate",
            errorName: error?.name || "Error",
            errorMessage: error?.message || String(error),
            durationMs: Math.round(performance.now() - started)
          }, write);
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
    try {
      await checkpoint(state);
    } catch (error) {
      logEvent("stitch.screen.generate", {
        result: "error",
        projectId: state.projectId,
        screenId: screen.id,
        screenTitle: screen.title,
        deviceType: screen.deviceType,
        attempt,
        maxAttempts,
        stage: "checkpoint",
        errorName: error?.name || "Error",
        errorMessage: error?.message || String(error),
        durationMs: Math.round(performance.now() - started)
      }, write);
      throw error;
    }
    logEvent("stitch.screen.generate", {
      result: "ok",
      projectId: state.projectId,
      screenId: screen.id,
      screenTitle: screen.title,
      deviceType: screen.deviceType,
      remoteScreenId: generated.screenId,
      durationMs: Math.round(performance.now() - started)
    }, write);
  }

  return state;
}
