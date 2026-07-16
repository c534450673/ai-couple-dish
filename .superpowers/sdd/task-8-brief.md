### Task 8: 执行真实 Stitch 生成、视觉复核与工作包验收

> Controller resolution: 真实 Google/Stitch 流量必须经已验证的本机 Mihomo/Clash 代理 `127.0.0.1:7897`，使用 Node `undici` ProxyAgent preload；密钥只能通过 PTY `read -s` 注入当前子进程，不能出现在 shell 命令、环境文件、日志或报告。当前基线已有 113+项测试，“17 tests PASS”是过时计数。真实 export 前必须先本地检查 generation-state 的 projectId 和精确 20 个安全 local ID，拒绝绝对/`..`/额外键，再运行 export；这是 Task 6 localId Minor 在真实写文件前的 controller gate。首页三个真实变体的最终选择不得默认：Controller 先完成视觉复核、展示并给出推荐，然后由用户明确选择 `home-emotion|home-food|home-memory`；选择前不提交 Task 8 资产。

**Files:**
- Generate: docs/design/stitch/couple-cosmos/generation-state.json
- Generate: docs/design/stitch/couple-cosmos/manifest.json
- Generate: docs/design/stitch/couple-cosmos/screenshots/*
- Generate: docs/design/stitch/couple-cosmos/html/*
- Modify: docs/design/stitch/couple-cosmos/README.md

**Interfaces:**
- Consumes: 用户提供的 STITCH_API_KEY，仅存在于当前执行进程。
- Produces: 至少 20 个导出屏幕：首页基础稿、三个首页变体、其余 16 个页面/状态稿。
- Produces: 用户最终选择的首页变体 ID 和视觉复核记录。

- [ ] **Step 1: 在不打印密钥的情况下确认环境**

Run:

~~~bash
cd tools/stitch
node -e 'if (!process.env.STITCH_API_KEY) process.exit(1)'
~~~

Expected: exit 0，无标准输出。

- [ ] **Step 2: 运行完整单元测试和 SDK 健康检查**

Run:

~~~bash
cd tools/stitch
npm ci
npm test
npm run stitch:health
~~~

Expected: 17 tests PASS；健康检查 result 为 ok；日志中不含密钥。

- [ ] **Step 3: 生成项目、首页变体和全部页面**

Run:

~~~bash
cd tools/stitch
npm run stitch:generate
~~~

Expected: result 为 ok，screenCount 为 20；中断后再次运行会跳过 generation-state.json 中已完成屏幕。

- [ ] **Step 4: 导出并验证所有设计资产**

Run:

~~~bash
cd tools/stitch
npm run stitch:export
npm run stitch:verify
~~~

Expected: manifest.json 包含 20 项；每项 HTML 与截图文件存在且 SHA-256 匹配；无密钥泄漏。

- [ ] **Step 5: 逐页进行视觉复核**

Review checklist:

- 使用本地图片查看器检查 login、bind、home-emotion、home-food、home-memory、menu-list、recipe-detail、feed、memories、map、ai-chat、settings 和 system-states。
- 确认所有页面使用 Couple Cosmos 令牌而非玫瑰奶油令牌。
- 确认中文文本没有乱码或溢出。
- 确认 375px、390px、430px 布局说明完整。
- 确认六类系统状态和 reduced-motion 说明存在。
- 确认表单、危险操作和 AI 写操作具备明确确认与错误恢复。

After the user selects one variant, set SELECTED_HOME_VARIANT to exactly home-emotion, home-food or home-memory, then run:

~~~bash
cd tools/stitch
case "$SELECTED_HOME_VARIANT" in
  home-emotion|home-food|home-memory) ;;
  *) exit 1 ;;
esac
node - "$SELECTED_HOME_VARIANT" <<'NODE'
import { readFileSync, writeFileSync } from "node:fs";
const file = "../../docs/design/stitch/couple-cosmos/README.md";
const selected = process.argv[2];
const content = readFileSync(file, "utf8");
writeFileSync(
  file,
  content.replace(
    /Selected home variant: (none|home-emotion|home-food|home-memory)/,
    "Selected home variant: " + selected
  )
);
NODE
~~~

Expected: 视觉复核记录没有未解决的阻断项；README.md 记录一个且仅一个已批准首页变体。

- [ ] **Step 6: 运行提交前检查**

Run:

~~~bash
cd tools/stitch
npm test
npm run stitch:verify
cd ../..
git diff --check
~~~

Expected: tests PASS，验证 result 为 ok，git diff --check 无输出。

- [ ] **Step 7: 运行 GitNexus 变更检测并提交设计产物**

Run GitNexus:

~~~text
gitnexus_detect_changes({scope: "all"})
~~~

Expected: 只影响 tools/stitch、docs/design/stitch 和本计划预期文件，不影响业务执行流程。

Run:

~~~bash
git add tools/stitch docs/design/stitch/couple-cosmos
git commit -m "design: 生成双人宇宙全页面设计"
~~~

## Work Package Completion Gate

完成本计划必须同时满足：

- @google/stitch-sdk 锁定为 0.3.5。
- 单元测试全部通过。
- Stitch 健康检查成功且日志无密钥。
- 20 个页面/变体均有截图和 HTML。
- manifest 文件和 SHA-256 校验通过。
- 用户已复核首页三个真实变体并选定最终版本。
- Stitch 项目 ID、屏幕 ID 和导出文件可追溯。
- 未修改 frontend-h5 和后端业务代码。
- GitNexus 检测没有非预期执行流影响。

通过此门槛后，下一份独立计划为 FastAPI 后端合同与迁移计划。
