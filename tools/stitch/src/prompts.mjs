const BASE_PROMPT = [
  "Design a production-grade mobile H5 screen for AI Couple Dish.",
  "Brand direction: Couple Cosmos, a private food universe shared by two partners.",
  "Use deep midnight navy and purple-black gradients, coral #FF5D73, electric mint #54E8D3, star gold #FFC857, translucent glass cards and cinematic food photography.",
  "Use modern Chinese typography, 24px primary card radius and 28px sheet radius.",
  "Maintain WCAG-readable contrast and touch targets of at least 44px.",
  "Motion notes must include reduced-motion behavior and must never hide business meaning.",
  "Target mobile widths 375px, 390px and 430px.",
  "All visible product copy must be Simplified Chinese."
];

const NORMAL_SCREEN_GUARDRAILS = [
  "Create exactly one complete, actionable normal-state business screen; make that normal state visually dominant.",
  "Do not create a state guide, component sheet, debug gallery, developer-facing design notes, or vertically stacked page variants.",
  "Loading, empty data, failure, unauthorized, and unbound-couple cases may only be brief design notes and must never replace the normal-state page body.",
  "Do not visibly render DEBUG, UI STATES, implementation notes, or design instructions."
];

const PRODUCT_NAVIGATION_GUARDRAIL =
  "When bottom navigation is present, use exactly these Simplified Chinese labels: 星球、菜单、投喂、回忆、我们.";

const SYSTEM_STATES_GUARDRAILS = [
  "This is the only screen permitted to be a full global status-component sheet.",
  "Cover skeleton, empty data, network failure, unauthorized, unbound couple, offline draft, Toast, Modal, and reduced-motion variants across the whole product.",
  "Do not turn it into an AI-chef-only state page."
];

const specs = [
  ["login", "登录与注册", [
    "Show two luminous planets gradually approaching above a secure phone and password form.",
    "Include login/register mode, password visibility, inline validation, loading button, privacy links and redirect recovery."
  ]],
  ["bind", "情侣绑定", [
    "Make 邀请 TA and 输入情侣码 the two primary normal-state workflows, with an immediately usable invitation code and code-entry form.",
    "Show code expiry progress, copy, share, regenerate and a celebratory avatar-orbit merge state."
  ]],
  ["home", "星球首页", [
    "Show the shared-couple normal state with partner avatar orbit, love-day counter, mood and online presence.",
    "Use a dynamic Bento Grid for anniversary, wish, feed, recipe, recent restaurant and Tonight We Eat."
  ]],
  ["menu-list", "我们的美食库", [
    "Combine restaurant, recipe and map tabs with search and filters.",
    "Use image-first cards for want-to-go, visited, recommended and favorites."
  ]],
  ["menu-detail", "餐厅详情", [
    "Make the normal restaurant-detail workflow actionable with a shared hero food image, status, location, price, tags, partner activity and edit actions.",
    "Include like, favorite, map and create-memory actions."
  ]],
  ["recipe-list", "共同菜谱列表", [
    "Make browsing the shared recipe library the normal workflow, with want-to-cook, cooked, mine and partner filters.",
    "Include difficulty, cooking time, ingredients and inventory match."
  ]],
  ["recipe-detail", "菜谱详情", [
    "Show hero image, ingredients, numbered cooking steps, serving adjustment and shared completion state.",
    "Include add-to-shopping-list and AI adaptation actions."
  ]],
  ["recipe-editor", "菜谱与餐厅编辑器", [
    "Make creating or editing one recipe or restaurant the normal workflow with a progressive form, image upload, draft status and leave confirmation.",
    "Show field errors beside fields and preserve entered content after upload or network errors."
  ]],
  ["feed", "情侣投喂", [
    "Make sending one food invitation the normal workflow with a central press-and-hold feed action, food, time, message and surprise mode.",
    "Show accept, reject, alternative proposal, countdown and completion celebration."
  ]],
  ["memories", "双人回忆时间轴", [
    "Combine anniversaries, wishes, notes and footprints in a filterable timeline.",
    "Use orbit countdowns, illuminated completed wishes and year grouping."
  ]],
  ["note-editor", "美食笔记编辑", [
    "Make composing one shared food note the normal workflow with photos, text, location, linked restaurant, linked recipe and local draft.",
    "Include upload progress, retry and privacy explanation."
  ]],
  ["map", "共同足迹地图", [
    "Make exploring shared food footprints the normal workflow with a dark cosmic map, clustered food locations and a draggable memory card.",
    "Include list/map switch, nearby filter, location permission and offline state."
  ]],
  ["ai-chat", "AI 美食星球", [
    "Make one normal AI meal-planning conversation the dominant workflow, showing a luminous assistant planet, real Chinese conversation messages, streaming answer trail and quick prompts.",
    "Any write tool must show a write-action confirmation preview, data source explanation, confirm and reject actions."
  ]],
  ["settings", "我们与设置", [
    "Show couple profile, relationship stage, shared metrics, privacy, theme, files, password, unbind and logout.",
    "Dangerous actions require clear consequence copy and dual confirmation."
  ]],
  ["notification-center", "情侣通知中心", [
    "Make reviewing actionable shared notifications the normal workflow; group feed, wish, anniversary, task and system notifications.",
    "Show unread state, bulk read, notification settings and failure recovery."
  ]],
  ["legal-privacy", "隐私与数据权利", [
    "Present privacy policy, terms, third-party services, data export, account deletion and couple-data ownership.",
    "Use readable long-form layout with a persistent section navigator."
  ]],
  ["system-states", "全局状态组件", [
    "Create the full global status component sheet for skeleton, empty, network error, unauthorized, unbound couple, offline draft, toast, modal and reduced-motion variants.",
    "Include exact spacing, icon and button hierarchy."
  ]]
];

export const SCREEN_SPECS = Object.freeze(
  specs.map(([id, title, requirements]) =>
    Object.freeze({
      id,
      title,
      deviceType: "MOBILE",
      requirements: Object.freeze(requirements)
    })
  )
);

export const HOME_VARIANT_PROMPT = [
  "Generate three materially different Couple Cosmos home-screen variants.",
  "Vary layout and information hierarchy, not only color.",
  "Keep the partner orbit, Tonight We Eat action and five-tab navigation.",
  "Variant one prioritizes emotional status, variant two prioritizes food decisions, and variant three prioritizes shared memories.",
  "All variants must retain accessibility and reduced-motion notes."
].join(" ");

export const TARGETED_REGENERATION_LOCAL_IDS = Object.freeze([
  "home-base", "bind", "menu-detail", "recipe-list", "recipe-editor",
  "feed", "note-editor", "map", "ai-chat", "notification-center",
  "system-states"
]);

export function getScreenPrompt(screenId) {
  const screen = SCREEN_SPECS.find(item => item.id === screenId);
  if (!screen) {
    throw new Error("Unknown Stitch screen id: " + screenId);
  }
  const guardrails = screenId === "system-states"
    ? SYSTEM_STATES_GUARDRAILS
    : NORMAL_SCREEN_GUARDRAILS;
  const navigation = screenId === "login" ? [] : [PRODUCT_NAVIGATION_GUARDRAIL];
  return [...BASE_PROMPT, ...guardrails, ...navigation, ...screen.requirements].join(" ");
}

export function getRegenerationPrompt(localId) {
  if (!TARGETED_REGENERATION_LOCAL_IDS.includes(localId)) {
    throw new Error("Unknown targeted regeneration local id: " + localId);
  }
  return getScreenPrompt(localId === "home-base" ? "home" : localId);
}
