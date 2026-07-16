import assert from "node:assert/strict";
import test from "node:test";
import { generateHomeDesign } from "../src/generate-home.mjs";
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
  assert.equal(result.screens["home-base"].screenId, "home-base-id");
  assert.equal(result.screens["home-emotion"].screenId, "home-emotion-id");
  assert.equal(calls[0].options.variantCount, 3);
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
