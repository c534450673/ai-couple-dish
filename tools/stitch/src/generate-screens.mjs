import { performance } from "node:perf_hooks";
import { logEvent } from "./logger.mjs";
import {
  PROJECT_SCREEN_LIMIT,
  effectiveProjectId,
  ensureProjectRegistry
} from "./project-shards.mjs";
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

function countScreens(state, projectId) {
  return Object.values(state.screens).filter(
    reference => effectiveProjectId(state, reference) === projectId
  ).length;
}

async function ensureWritableProject(sdk, state, checkpoint, write) {
  const active = state.projects.at(-1);
  if (active && countScreens(state, active.projectId) < PROJECT_SCREEN_LIMIT) {
    return { state, projectId: active.projectId };
  }

  const shardNumber = state.projects.length + 1;
  const title = `${state.projectTitle} - Part ${shardNumber}`;
  const currentScreenCount = active
    ? countScreens(state, active.projectId)
    : 0;
  const started = performance.now();
  logEvent("stitch.project.shard", {
    result: "started",
    shardNumber,
    title,
    currentScreenCount
  }, write);
  const project = await sdk.createProject(title);
  if (typeof project?.projectId !== "string" || !project.projectId.trim()) {
    throw new Error("Expected a non-empty Stitch shard projectId");
  }
  const next = {
    ...state,
    projects: [...state.projects, { projectId: project.projectId, title }]
  };
  await checkpoint(next);
  logEvent("stitch.project.shard", {
    result: "ok",
    shardNumber,
    projectId: project.projectId,
    title,
    durationMs: Math.round(performance.now() - started)
  }, write);
  return { state: next, projectId: project.projectId };
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
  let state = ensureProjectRegistry(initialState);
  const remaining = SCREEN_SPECS.filter(screen => screen.id !== "home");

  for (const screen of remaining) {
    if (state.screens[screen.id]) {
      logEvent("stitch.screen.skip", {
        result: "ok",
        projectId: effectiveProjectId(state, state.screens[screen.id]),
        screenId: screen.id,
        screenTitle: screen.title,
        reason: "already-generated"
      }, write);
      continue;
    }

    const writable = await ensureWritableProject(sdk, state, checkpoint, write);
    state = writable.state;
    const projectId = writable.projectId;
    const project = sdk.project(projectId);
    const started = performance.now();
    const { value: generated, attempt } = await withRetry(
      async attempt => {
        logEvent("stitch.screen.generate", {
          result: "started",
          projectId,
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
            projectId,
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
            projectId,
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
          kind: "base",
          projectId
        }
      }
    };
    try {
      await checkpoint(state);
    } catch (error) {
      logEvent("stitch.screen.generate", {
        result: "error",
        projectId,
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
      projectId,
      screenId: screen.id,
      screenTitle: screen.title,
      deviceType: screen.deviceType,
      remoteScreenId: generated.screenId,
      durationMs: Math.round(performance.now() - started)
    }, write);
  }

  return state;
}
