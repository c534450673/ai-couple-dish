import assert from "node:assert/strict";
import test from "node:test";
import {
  SCREEN_SPECS,
  getScreenPrompt,
  HOME_VARIANT_PROMPT,
  TARGETED_REGENERATION_LOCAL_IDS,
  getRegenerationPrompt
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

test("every screen prompt contains visual tokens and motion support", () => {
  for (const screen of SCREEN_SPECS) {
    const prompt = getScreenPrompt(screen.id);
    assert.match(prompt, /Couple Cosmos/);
    assert.match(prompt, /#FF5D73/);
    assert.match(prompt, /#54E8D3/);
    assert.match(prompt, /reduced-motion/);
    assert.equal(screen.deviceType, "MOBILE");
  }
});

test("home variant prompt requests three materially different layouts", () => {
  assert.match(HOME_VARIANT_PROMPT, /three/);
  assert.match(HOME_VARIANT_PROMPT, /layout/);
  assert.match(HOME_VARIANT_PROMPT, /information hierarchy/);
});

test("business prompts prioritize one normal page and fixed navigation", () => {
  for (const { id } of SCREEN_SPECS) {
    if (id === "login" || id === "system-states") continue;
    const prompt = getScreenPrompt(id);
    assert.match(prompt, /complete, actionable normal-state business screen/);
    assert.match(prompt, /Do not create a state guide/);
    assert.match(prompt, /星球、菜单、投喂、回忆、我们/);
  }
});

test("only system-states permits a full status component sheet", () => {
  assert.match(getScreenPrompt("system-states"), /only screen permitted/i);
  for (const { id } of SCREEN_SPECS) {
    if (id === "system-states") continue;
    assert.match(getScreenPrompt(id), /Do not create a state guide/);
    assert.doesNotMatch(getScreenPrompt(id), /only screen permitted/i);
  }
});

test("business prompts do not require complete state definitions", () => {
  for (const { id } of SCREEN_SPECS) {
    if (id === "system-states") continue;
    const prompt = getScreenPrompt(id);
    assert.doesNotMatch(
      prompt,
      /Define normal, loading, empty, error, unauthorized and unbound-couple states\./
    );
    assert.doesNotMatch(prompt, /(?:Define|Cover).*?(?:normal.*loading|loading.*empty).*?states/i);
  }
});

test("targeted regeneration has exactly the audited ids", () => {
  assert.deepEqual(TARGETED_REGENERATION_LOCAL_IDS, [
    "home-base", "bind", "menu-detail", "recipe-list", "recipe-editor",
    "feed", "note-editor", "map", "ai-chat", "notification-center",
    "system-states"
  ]);
  assert.equal(getRegenerationPrompt("home-base"), getScreenPrompt("home"));
  assert.throws(() => getRegenerationPrompt("home-emotion"), /Unknown targeted/);
  assert.throws(() => getRegenerationPrompt("login"), /Unknown targeted/);
});

test("binding and AI prompts require their primary workflows", () => {
  assert.match(getRegenerationPrompt("bind"), /邀请 TA/);
  assert.match(getRegenerationPrompt("bind"), /输入情侣码/);
  assert.match(getRegenerationPrompt("ai-chat"), /real Chinese conversation messages/);
  assert.match(getRegenerationPrompt("ai-chat"), /write-action confirmation preview/);
});
