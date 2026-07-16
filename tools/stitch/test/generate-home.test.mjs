import assert from "node:assert/strict";
import test from "node:test";
import { generateHomeDesign } from "../src/generate-home.mjs";
import { HOME_VARIANT_PROMPT } from "../src/prompts.mjs";
import { emptyGenerationState } from "../src/state-store.mjs";

test("generateHomeDesign creates a project, base screen and three variants", async () => {
  const calls = [];
  const baseScreen = {
    screenId: "home-base-id",
    async variants(prompt, options, deviceType) {
      calls.push({ prompt, options, deviceType });
      return [
        { screenId: "home-emotion-id" },
        { screenId: "home-food-id" },
        { screenId: "home-memory-id" }
      ];
    }
  };
  const sdk = {
    async createProject(title) {
      assert.equal(title, "AI Couple Dish - Couple Cosmos");
      return {
        projectId: "project-1",
        async generate(prompt, deviceType) {
          assert.match(prompt, /Couple Cosmos/);
          assert.equal(deviceType, "MOBILE");
          return baseScreen;
        }
      };
    }
  };

  const result = await generateHomeDesign(sdk, emptyGenerationState());

  assert.equal(result.projectId, "project-1");
  assert.deepEqual(result.screens, {
    "home-base": { screenId: "home-base-id", kind: "base" },
    "home-emotion": { screenId: "home-emotion-id", kind: "variant" },
    "home-food": { screenId: "home-food-id", kind: "variant" },
    "home-memory": { screenId: "home-memory-id", kind: "variant" }
  });
  assert.deepEqual(calls, [
    {
      prompt: HOME_VARIANT_PROMPT,
      options: {
        variantCount: 3,
        creativeRange: "EXPLORE",
        aspects: ["LAYOUT", "COLOR_SCHEME", "IMAGES", "TEXT_CONTENT"]
      },
      deviceType: "MOBILE"
    }
  ]);
});

test("generateHomeDesign resumes an existing project without creating another", async () => {
  let createCalls = 0;
  const baseScreen = {
    screenId: "home-base-id",
    async variants() {
      return [
        { screenId: "home-emotion-id" },
        { screenId: "home-food-id" },
        { screenId: "home-memory-id" }
      ];
    }
  };
  const project = {
    projectId: "project-1",
    async generate() {
      return baseScreen;
    }
  };
  const sdk = {
    async createProject() {
      createCalls += 1;
      return project;
    },
    project(projectId) {
      assert.equal(projectId, "project-1");
      return project;
    }
  };
  const state = {
    ...emptyGenerationState(),
    projectId: "project-1"
  };

  const result = await generateHomeDesign(sdk, state);
  assert.equal(createCalls, 0);
  assert.equal(result.projectId, "project-1");
});

test("generateHomeDesign returns a completed home state without calling the SDK", async () => {
  const sdk = {
    async createProject() {
      assert.fail("createProject must not be called");
    },
    project() {
      assert.fail("project must not be called");
    }
  };
  const state = {
    ...emptyGenerationState(),
    projectId: "project-1",
    screens: {
      "home-base": { screenId: "home-base-id", kind: "base" }
    }
  };

  const result = await generateHomeDesign(sdk, state);

  assert.strictEqual(result, state);
});

for (const variantCount of [2, 4]) {
  test(`generateHomeDesign rejects ${variantCount} home variants without changing state`, async () => {
    const variants = Array.from({ length: variantCount }, (_, index) => ({
      screenId: `variant-${index + 1}`
    }));
    const sdk = {
      async createProject() {
        return {
          projectId: "project-1",
          async generate() {
            return {
              screenId: "home-base-id",
              async variants() {
                return variants;
              }
            };
          }
        };
      }
    };
    const state = emptyGenerationState();
    const originalState = structuredClone(state);

    await assert.rejects(
      generateHomeDesign(sdk, state),
      new RegExp(`Expected 3 home variants, received ${variantCount}`)
    );
    assert.deepEqual(state, originalState);
    assert.equal(Object.hasOwn(state.screens, "undefined"), false);
  });
}
