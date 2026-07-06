# AI Agent 设计规格

> 日期：2026-07-06  
> 状态：已实现

## 目标

为 ai-couple-dish 提供全局 AI 助手，覆盖菜单、菜谱、情侣模块，支持：

- 流式聊天（SSE 打字效果）
- 语音输入（Web Speech API）
- 写操作预览确认
- 表单页 AI 帮填

## 架构

- **后端**：`KimiClient` → `AiAgentService`（Tool Calling 循环）→ 现有 Service
- **前端**：浮动按钮 + `AiChatDrawer`（fetch SSE + 语音识别）
- **配置**：`AI_BASE_URL` / `AI_API_KEY` / `AI_MODEL` 环境变量

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/chat/stream` | SSE 流式聊天 |
| POST | `/api/ai/chat/confirm` | 确认写操作 |
| POST | `/api/ai/chat/reject` | 取消写操作 |
| POST | `/api/ai/generate` | 表单 AI 帮填 |

## Tools

查询：`list_menus`, `search_menus`, `get_menu_stats`, `get_couple_info`, `get_couple_home`, `list_recipes`, `search_recipes`, `recommend_dish`

写操作（需确认）：`add_menu`, `create_recipe`
