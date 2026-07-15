import assert from "node:assert/strict";
import test from "node:test";
import {
  SCREEN_SPECS,
  getScreenPrompt,
  HOME_VARIANT_PROMPT
} from "../src/prompts.mjs";

const REQUIRED_IDS = [
  "login",
  "bind",
  "home",
  "menu-list",
  "menu-detail",
  "recipe-list",
  "recipe-detail",
  "recipe-editor",
  "feed",
  "memories",
  "note-editor",
  "map",
  "ai-chat",
  "settings",
  "notification-center",
  "legal-privacy",
  "system-states"
];

test("screen catalog contains every approved screen exactly once", () => {
  const ids = SCREEN_SPECS.map(item => item.id);
  assert.deepEqual(ids.toSorted(), REQUIRED_IDS.toSorted());
  assert.equal(new Set(ids).size, ids.length);
});

test("every screen prompt contains visual tokens and system states", () => {
  for (const screen of SCREEN_SPECS) {
    const prompt = getScreenPrompt(screen.id);
    assert.match(prompt, /Couple Cosmos/);
    assert.match(prompt, /#FF5D73/);
    assert.match(prompt, /#54E8D3/);
    assert.match(prompt, /loading/);
    assert.match(prompt, /empty/);
    assert.match(prompt, /error/);
    assert.equal(screen.deviceType, "MOBILE");
  }
});

test("home variant prompt requests three materially different layouts", () => {
  assert.match(HOME_VARIANT_PROMPT, /three/);
  assert.match(HOME_VARIANT_PROMPT, /layout/);
  assert.match(HOME_VARIANT_PROMPT, /information hierarchy/);
});
