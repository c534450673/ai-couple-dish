from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any
from uuid import uuid4

import httpx
import structlog
from fastapi import Request
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import BusinessError
from app.schemas.business import (
    AiGenerateRequest,
    MenuRequest,
    RecipeRequest,
)
from app.services import couple as couple_service
from app.services import menu as menu_service
from app.services import recipe as recipe_service

logger = structlog.get_logger()
SESSION_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
MSG_PREFIX = "ai:session:msg:"
PENDING_PREFIX = "ai:session:pending:"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
PENDING_TTL_SECONDS = 30 * 60
SAFE_ERROR = "AI 服务暂时不可用，请稍后重试"


class AiGateway:
    """OpenAI 兼容网关客户端。请求体、密钥和响应原文不进入日志。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _endpoint(self) -> str:
        base = self.settings.ai_base_url.strip().rstrip("/")
        if not base or not self.settings.ai_api_key.get_secret_value().strip():
            raise BusinessError(9001, SAFE_ERROR)
        return f"{base}/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.ai_api_key.get_secret_value()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _body(
        self,
        messages: list[dict[str, Any]],
        *,
        stream: bool,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.settings.ai_model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        return body

    async def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        started = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.settings.ai_timeout_ms / 1000) as client:
                response = await client.post(
                    self._endpoint(),
                    headers=self._headers(),
                    json=self._body(messages, stream=False, tools=tools),
                )
            if response.status_code >= 400:
                raise BusinessError(9001, SAFE_ERROR)
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("invalid gateway response")
            await logger.ainfo(
                "ai_gateway_completed",
                module="ai",
                operation="complete",
                result="success",
                durationMs=round((perf_counter() - started) * 1000),
            )
            return data
        except BusinessError:
            raise
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as error:
            await logger.aerror(
                "ai_gateway_failed",
                module="ai",
                operation="complete",
                result="error",
                durationMs=round((perf_counter() - started) * 1000),
                errorCode=type(error).__name__,
            )
            raise BusinessError(9001, SAFE_ERROR) from error

    async def stream(self, messages: list[dict[str, Any]]) -> AsyncIterator[str]:
        started = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.settings.ai_timeout_ms / 1000) as client:
                async with client.stream(
                    "POST",
                    self._endpoint(),
                    headers={**self._headers(), "Accept": "text/event-stream"},
                    json=self._body(messages, stream=True),
                ) as response:
                    if response.status_code >= 400:
                        raise BusinessError(9001, SAFE_ERROR)
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            chunk = json.loads(raw)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content")
                        except (ValueError, TypeError, IndexError, AttributeError) as error:
                            raise BusinessError(9001, SAFE_ERROR) from error
                        if isinstance(token, str) and token:
                            yield token
            await logger.ainfo(
                "ai_gateway_completed",
                module="ai",
                operation="stream",
                result="success",
                durationMs=round((perf_counter() - started) * 1000),
            )
        except BusinessError:
            raise
        except (httpx.HTTPError, ValueError) as error:
            await logger.aerror(
                "ai_gateway_failed",
                module="ai",
                operation="stream",
                result="error",
                durationMs=round((perf_counter() - started) * 1000),
                errorCode=type(error).__name__,
            )
            raise BusinessError(9001, SAFE_ERROR) from error


class AiSessionStore:
    def __init__(self, request: Request) -> None:
        self.redis = request.app.state.redis.raw

    @staticmethod
    def resolve(user_id: int, session_id: str | None) -> str:
        if session_id is not None and session_id.strip():
            value = session_id.strip()
            if SESSION_PATTERN.fullmatch(value) is None:
                raise BusinessError(400, "会话标识无效")
            return value
        return f"u{user_id}-{uuid4().hex[:8]}"

    @staticmethod
    def _message_key(user_id: int, session_id: str) -> str:
        return f"{MSG_PREFIX}{user_id}:{session_id}"

    @staticmethod
    def _pending_key(user_id: int, session_id: str) -> str:
        return f"{PENDING_PREFIX}{user_id}:{session_id}"

    async def load_messages(
        self, user_id: int, session_id: str, max_history: int
    ) -> list[dict[str, Any]]:
        raw = await self.redis.get(self._message_key(user_id, session_id))
        if not raw:
            return [{"role": "system", "content": self.system_prompt()}]
        try:
            value = json.loads(raw)
            if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                return value
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        return [{"role": "system", "content": self.system_prompt()}]

    async def save_messages(
        self, user_id: int, session_id: str, messages: list[dict[str, Any]], max_history: int
    ) -> None:
        system = (
            messages[0]
            if messages and messages[0].get("role") == "system"
            else {"role": "system", "content": self.system_prompt()}
        )
        tail = messages[-max_history:]
        await self.redis.set(
            self._message_key(user_id, session_id),
            json.dumps([system, *tail], ensure_ascii=False, separators=(",", ":")),
            ex=SESSION_TTL_SECONDS,
        )

    async def get_pending(self, user_id: int, session_id: str) -> dict[str, Any] | None:
        raw = await self.redis.get(self._pending_key(user_id, session_id))
        if not raw:
            return None
        try:
            value = json.loads(raw)
            return value if isinstance(value, dict) else None
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    async def save_pending(self, user_id: int, session_id: str, action: dict[str, Any]) -> None:
        await self.redis.set(
            self._pending_key(user_id, session_id),
            json.dumps(action, ensure_ascii=False, separators=(",", ":")),
            ex=PENDING_TTL_SECONDS,
        )

    async def clear_pending(self, user_id: int, session_id: str) -> None:
        await self.redis.delete(self._pending_key(user_id, session_id))

    @staticmethod
    def system_prompt() -> str:
        return "你是情侣私密菜单 AI 助手，使用中文、语气温暖简洁；写操作只生成预览并等待确认。"


def _tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_menus",
                "description": "查询情侣菜单",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "integer"},
                        "keyword": {"type": "string"},
                        "page": {"type": "integer"},
                        "pageSize": {"type": "integer"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_menus",
                "description": "搜索情侣菜单",
                "parameters": {
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                    "required": ["keyword"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_menu_stats",
                "description": "获取菜单统计",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_couple_info",
                "description": "获取情侣关系",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_couple_home",
                "description": "获取情侣主页",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_recipes",
                "description": "获取情侣菜谱",
                "parameters": {
                    "type": "object",
                    "properties": {"page": {"type": "integer"}, "pageSize": {"type": "integer"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_recipes",
                "description": "搜索菜谱",
                "parameters": {
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                    "required": ["keyword"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_menu",
                "description": "添加菜单，需确认",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "restaurantName": {"type": "string"},
                        "dishName": {"type": "string"},
                        "dishCategory": {"type": "string"},
                        "price": {"type": "number"},
                        "location": {"type": "string"},
                        "note": {"type": "string"},
                        "rating": {"type": "integer"},
                        "status": {"type": "integer"},
                        "eatenDate": {"type": "string"},
                    },
                    "required": ["restaurantName"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_recipe",
                "description": "创建菜谱，需确认",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "difficulty": {"type": "string"},
                        "cookingTime": {"type": "integer"},
                        "servings": {"type": "integer"},
                        "ingredients": {"type": "array"},
                        "steps": {"type": "array"},
                        "publish": {"type": "boolean"},
                    },
                    "required": ["title"],
                },
            },
        },
    ]


async def _execute_tool(
    request: Request, session: AsyncSession, user_id: int, name: str, arguments: str
) -> tuple[str, dict[str, Any] | None]:
    try:
        args = json.loads(arguments) if arguments else {}
        if not isinstance(args, dict):
            raise ValueError("invalid arguments")
        if name == "add_menu":
            payload = {key: value for key, value in args.items() if value is not None}
            if not str(payload.get("restaurantName", "")).strip():
                raise BusinessError(400, "餐厅名称不能为空")
            action = {
                "actionId": uuid4().hex,
                "actionType": name,
                "title": "添加菜单",
                "summary": f"餐厅：{payload['restaurantName']}",
                "payload": payload,
            }
            return "已生成操作预览，等待用户确认。", action
        if name == "create_recipe":
            payload = {key: value for key, value in args.items() if value is not None}
            if not str(payload.get("title", "")).strip():
                raise BusinessError(400, "菜谱标题不能为空")
            action = {
                "actionId": uuid4().hex,
                "actionType": name,
                "title": "创建菜谱",
                "summary": f"菜谱：{payload['title']}",
                "payload": payload,
            }
            return "已生成操作预览，等待用户确认。", action
        result: Any
        if name in {"list_menus", "search_menus"}:
            result = await menu_service.list_menus(
                request,
                session,
                user_id,
                status=args.get("status"),
                keyword=args.get("keyword"),
                page=int(args.get("page", 1)),
                page_size=min(int(args.get("pageSize", 10)), 100),
            )
        elif name == "get_menu_stats":
            result = await menu_service.stats(request, session, user_id)
        elif name == "get_couple_info":
            result = await couple_service.get_info(session, user_id)
        elif name == "get_couple_home":
            result = await couple_service.get_home(session, user_id)
        elif name == "list_recipes":
            result = await recipe_service.couple_recipes(
                request,
                session,
                user_id,
                int(args.get("page", 1)),
                min(int(args.get("pageSize", 10)), 100),
            )
        elif name == "search_recipes":
            result = await recipe_service.search(
                request, session, user_id, str(args.get("keyword", "")), 1, 10
            )
        else:
            raise BusinessError(9003, "未知工具")
        return json.dumps(result, ensure_ascii=False, default=str), None
    except BusinessError as error:
        return json.dumps({"error": error.message}, ensure_ascii=False), None
    except (TypeError, ValueError, KeyError) as error:
        await logger.awarning(
            "ai_tool_rejected",
            module="ai",
            operation="tool",
            result="rejected",
            errorCode=type(error).__name__,
        )
        return json.dumps({"error": "工具参数无效"}, ensure_ascii=False), None


def gateway_for(request: Request) -> AiGateway:
    gateway = getattr(request.app.state, "ai_gateway", None)
    if gateway is None:
        gateway = AiGateway(request.app.state.settings)
        request.app.state.ai_gateway = gateway
    return gateway


async def chat_stream(
    request: Request, session: AsyncSession, user_id: int, message: str, session_id: str | None
) -> AsyncIterator[str]:
    store = AiSessionStore(request)
    sid = store.resolve(user_id, session_id)
    messages = await store.load_messages(user_id, sid, request.app.state.settings.ai_max_history)
    messages.append({"role": "user", "content": message})
    gateway = gateway_for(request)
    pending: dict[str, Any] | None = None
    for _ in range(request.app.state.settings.ai_max_tool_rounds):
        response = await gateway.complete(messages, _tools())
        choice = (response.get("choices") or [{}])[0]
        assistant = choice.get("message") or {}
        tool_calls = assistant.get("tool_calls") or []
        if not tool_calls:
            break
        messages.append(assistant)
        for call in tool_calls:
            function = call.get("function") or {}
            content, action = await _execute_tool(
                request,
                session,
                user_id,
                str(function.get("name", "")),
                str(function.get("arguments", "{}")),
            )
            if action:
                pending = action
                await store.save_pending(user_id, sid, action)
            messages.append(
                {"role": "tool", "tool_call_id": call.get("id", ""), "content": content}
            )
    if pending:
        yield _sse("pending_action", pending)
    full_reply: list[str] = []
    async for token in gateway.stream(messages):
        full_reply.append(token)
        yield _sse("token", token)
    messages.append({"role": "assistant", "content": "".join(full_reply)})
    await store.save_messages(user_id, sid, messages, request.app.state.settings.ai_max_history)
    yield _sse("session", sid)
    yield _sse("done", {})


def _sse(event: str, data: Any) -> str:
    return (
        f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"
    )


async def confirm(
    request: Request, session: AsyncSession, user_id: int, session_id: str
) -> dict[str, Any]:
    store = AiSessionStore(request)
    sid = store.resolve(user_id, session_id)
    action = await store.get_pending(user_id, sid)
    if action is None:
        raise BusinessError(9004, "没有待确认的操作")
    action_type = action.get("actionType")
    payload = action.get("payload") or {}
    try:
        if action_type == "add_menu":
            resource_id = await menu_service.add(
                request, session, user_id, MenuRequest.model_validate(payload)
            )
        elif action_type == "create_recipe":
            resource_id = await recipe_service.create(
                request, session, user_id, RecipeRequest.model_validate(payload)
            )
        else:
            raise BusinessError(9003, "不支持的确认操作")
    except ValidationError as error:
        raise BusinessError(400, "待确认操作参数无效") from error
    await store.clear_pending(user_id, sid)
    await logger.ainfo(
        "ai_action_confirmed",
        module="ai",
        operation="confirm",
        result="success",
        actionType=action_type,
    )
    return {"actionType": action_type, "resourceId": resource_id, "message": "操作已成功执行"}


async def reject(request: Request, user_id: int, session_id: str) -> None:
    store = AiSessionStore(request)
    await store.clear_pending(user_id, store.resolve(user_id, session_id))


async def generate(request: Request, user_id: int, payload: AiGenerateRequest) -> dict[str, Any]:
    type_name = payload.type.strip().lower()
    if type_name not in {"menu", "recipe"}:
        raise BusinessError(400, f"不支持的生成类型: {type_name}")
    system = (
        "你是菜单填写助手，只输出 JSON，字段 "
        "restaurantName,dishName,dishCategory,price,location,note,rating,status,eatenDate。"
        if type_name == "menu"
        else "你是菜谱填写助手，只输出 JSON，字段 "
        "title,description,difficulty,cookingTime,servings,ingredients,steps,publish。"
    )
    response = await gateway_for(request).complete(
        [{"role": "system", "content": system}, {"role": "user", "content": payload.prompt}]
    )
    content = str(((response.get("choices") or [{}])[0].get("message") or {}).get("content", ""))
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("not object")
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        await logger.awarning(
            "ai_generate_parse_failed",
            module="ai",
            operation="generate",
            result="rejected",
            errorCode=type(error).__name__,
        )
        raise BusinessError(9005, "AI 生成结果解析失败，请重试") from error
    return {"type": type_name, "data": data}
