import { getScreenPrompt, HOME_VARIANT_PROMPT } from "./prompts.mjs";

const VARIANT_KEYS = ["home-emotion", "home-food", "home-memory"];

export async function generateHomeDesign(sdk, state) {
  if (state.projectId && state.screens["home-base"]) {
    return state;
  }

  const project = state.projectId
    ? sdk.project(state.projectId)
    : await sdk.createProject(state.projectTitle);
  const base = await project.generate(getScreenPrompt("home"), "MOBILE");
  const variants = await base.variants(
    HOME_VARIANT_PROMPT,
    {
      variantCount: 3,
      creativeRange: "EXPLORE",
      aspects: ["LAYOUT", "COLOR_SCHEME", "IMAGES", "TEXT_CONTENT"]
    },
    "MOBILE"
  );
  if (!Array.isArray(variants)) {
    throw new Error("Expected home variants to be an array");
  }
  if (variants.length !== VARIANT_KEYS.length) {
    throw new Error(
      `Expected ${VARIANT_KEYS.length} home variants, received ${variants.length}`
    );
  }
  if (
    !variants.every(
      (screen) =>
        typeof screen?.screenId === "string" && screen.screenId.trim().length > 0
    )
  ) {
    throw new Error(
      "Expected every home variant to include a non-empty screenId"
    );
  }

  const screens = {
    ...state.screens,
    "home-base": { screenId: base.screenId, kind: "base" }
  };
  for (const [index, screen] of variants.entries()) {
    screens[VARIANT_KEYS[index]] = {
      screenId: screen.screenId,
      kind: "variant"
    };
  }

  return {
    ...state,
    projectId: project.projectId,
    screens
  };
}
