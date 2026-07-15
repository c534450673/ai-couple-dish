import assert from "node:assert/strict";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { assertRequiredTools } from "../src/client.mjs";
import {
  emptyGenerationState,
  readGenerationState,
  writeGenerationState
} from "../src/state-store.mjs";

test("assertRequiredTools accepts the Stitch generation tool set", async () => {
  const client = {
    async listTools() {
      return {
        tools: [
          { name: "create_project" },
          { name: "generate_screen_from_text" },
          { name: "get_screen" }
        ]
      };
    }
  };

  assert.deepEqual(await assertRequiredTools(client), [
    "create_project",
    "generate_screen_from_text",
    "get_screen"
  ]);
});

test("assertRequiredTools rejects a missing generation tool", async () => {
  const client = {
    async listTools() {
      return { tools: [{ name: "create_project" }] };
    }
  };

  await assert.rejects(
    () => assertRequiredTools(client),
    /Missing required Stitch tools/
  );
});

test("generation state persists with an atomic round trip", async () => {
  const root = await mkdtemp(join(tmpdir(), "stitch-state-"));
  const filePath = join(root, "generation-state.json");
  const state = {
    ...emptyGenerationState(),
    projectId: "project-1",
    screens: {
      login: { screenId: "screen-1", kind: "base" }
    }
  };

  await writeGenerationState(filePath, state);
  assert.deepEqual(await readGenerationState(filePath), state);
});
