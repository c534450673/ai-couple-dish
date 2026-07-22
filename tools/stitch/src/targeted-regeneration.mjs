import { performance } from "node:perf_hooks";
import { logEvent } from "./logger.mjs";
import {
  PROJECT_SCREEN_LIMIT,
  effectiveProjectId,
  ensureProjectRegistry
} from "./project-shards.mjs";
import {
  SCREEN_SPECS,
  TARGETED_REGENERATION_LOCAL_IDS,
  getRegenerationPrompt
} from "./prompts.mjs";

function screenTitleFor(localId) {
  const screenId = localId === "home-base" ? "home" : localId;
  return SCREEN_SPECS.find(screen => screen.id === screenId)?.title || localId;
}

function countProjectReferences(state, projectId) {
  return Object.values(state.screens || {}).filter(
    reference => effectiveProjectId(state, reference) === projectId
  ).length;
}

function isOwnedByProject(state, localId, projectId) {
  return effectiveProjectId(state, state.screens?.[localId]) === projectId;
}

function sanitizeErrorMessage(error, prompt = "") {
  const message = error?.message || String(error);
  return message
    .replaceAll(prompt, "[REDACTED_PROMPT]")
    .replace(/((?:https?:\/\/[^\s?]+|\/[^\s?]+))\?[^\s]*/gi, "$1")
    .replace(/\bauthorization\s*:\s*bearer\s+[^\s,;]+/gi, "Authorization: Bearer [REDACTED]")
    .replace(/\b(api[_-]?key|token|secret)\s*([=:])\s*[^\s,&;]+/gi, "$1$2[REDACTED]");
}

function validateMaxAttempts(maxAttempts) {
  if (!Number.isInteger(maxAttempts) || maxAttempts < 1) {
    throw new Error("maxAttempts must be a positive integer");
  }
}

function logLifecycle({
  write,
  result,
  projectId,
  localId,
  screenTitle,
  attempt,
  stage,
  started,
  error,
  prompt,
  delayMs
}) {
  logEvent("stitch.screen.regenerate", {
    result,
    projectId,
    localId,
    screenTitle,
    attempt,
    stage,
    durationMs: Math.round(performance.now() - started),
    ...(delayMs === undefined ? {} : { delayMs }),
    ...(error ? {
      errorName: error?.name || "Error",
      errorMessage: sanitizeErrorMessage(error, prompt)
    } : {})
  }, write);
}

export function validateRegenerationTargets(localIds, state) {
  if (!Array.isArray(localIds) || localIds.length === 0) {
    throw new Error("Targeted regeneration requires at least one local id");
  }
  if (new Set(localIds).size !== localIds.length) {
    throw new Error("Duplicate targeted regeneration local ids are not allowed");
  }
  for (const localId of localIds) {
    if (!TARGETED_REGENERATION_LOCAL_IDS.includes(localId)) {
      throw new Error(`Unknown targeted regeneration local id: ${localId}`);
    }
  }

  const registered = ensureProjectRegistry(state);
  const project = registered.projects?.[2];
  if (!project?.projectId) {
    throw new Error("Targeted regeneration requires the third Stitch project");
  }

  const pending = localIds.filter(
    localId => !isOwnedByProject(registered, localId, project.projectId)
  );
  const requiredCapacity = countProjectReferences(registered, project.projectId) + pending.length;
  if (requiredCapacity > PROJECT_SCREEN_LIMIT) {
    throw new Error(
      `Third Stitch project capacity exceeded: ${requiredCapacity}/${PROJECT_SCREEN_LIMIT}`
    );
  }

  return { localIds: [...localIds], projectId: project.projectId };
}

export async function regenerateScreens(
  sdk,
  initialState,
  localIds,
  {
    checkpoint,
    sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds)),
    maxAttempts = 3,
    write
  } = {}
) {
  validateMaxAttempts(maxAttempts);
  let state = ensureProjectRegistry(initialState);
  const targets = validateRegenerationTargets(localIds, state);
  const projectId = targets.projectId;

  for (const localId of targets.localIds) {
    if (isOwnedByProject(state, localId, projectId)) {
      continue;
    }

    const screenTitle = screenTitleFor(localId);
    const prompt = getRegenerationPrompt(localId);
    const started = performance.now();
    const project = sdk.project(projectId);
    let generated;
    let successfulAttempt;

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      logLifecycle({
        write, result: "started", projectId, localId, screenTitle, attempt,
        stage: "generate", started
      });
      try {
        generated = await project.generate(prompt, "MOBILE");
        successfulAttempt = attempt;
        break;
      } catch (error) {
        if (error?.recoverable !== true || attempt === maxAttempts) {
          logLifecycle({
            write, result: "error", projectId, localId, screenTitle, attempt,
            stage: "generate", started, error, prompt
          });
          throw error;
        }
        const delayMs = 1000 * attempt;
        logLifecycle({
          write, result: "retry", projectId, localId, screenTitle, attempt,
          stage: "generate", started, error, prompt, delayMs
        });
        await sleep(delayMs);
      }
    }

    if (typeof generated?.screenId !== "string" || !generated.screenId.trim()) {
      const error = new Error(
        `Expected generated screen ${localId} to include a non-empty screenId`
      );
      logLifecycle({
        write, result: "error", projectId, localId, screenTitle,
        attempt: successfulAttempt, stage: "response", started, error, prompt
      });
      throw error;
    }

    const nextState = {
      ...state,
      screens: {
        ...state.screens,
        [localId]: {
          screenId: generated.screenId,
          kind: "base",
          projectId
        }
      }
    };
    try {
      await checkpoint(nextState);
    } catch (error) {
      logLifecycle({
        write, result: "error", projectId, localId, screenTitle,
        attempt: successfulAttempt, stage: "checkpoint", started, error, prompt
      });
      throw error;
    }
    state = nextState;
    logLifecycle({
      write, result: "ok", projectId, localId, screenTitle,
      attempt: successfulAttempt, stage: "checkpoint", started
    });
  }

  return state;
}
