import asyncio
import json
import secrets
import string
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Never
from zoneinfo import ZoneInfo

import structlog
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import (
    Anniversary,
    Couple,
    CoupleMenu,
    Feed,
    FoodNote,
    PosterTemplate,
    User,
    UserPoster,
)
from app.schemas.poster import PosterGenerateRequest
from app.services import poster_renderer

logger = structlog.get_logger()
POSTER_TYPES = {"anniversary", "feed", "map", "annual"}
POSTER_TYPE_NAMES = {
    "anniversary": "纪念日",
    "feed": "恋爱动态",
    "map": "足迹地图",
    "annual": "年度总结",
}
FEED_TYPE_NAMES = {
    "meal": "正餐",
    "dessert": "甜品",
    "snack": "小吃",
    "drink": "饮品",
}
IMAGE_REJECTION_ERROR_CODES = {
    "file": "IMAGE_CANDIDATE_FILE",
    "format": "IMAGE_CANDIDATE_FORMAT",
    "dimensions": "IMAGE_CANDIDATE_DIMENSIONS",
    "animated": "IMAGE_CANDIDATE_ANIMATED",
    "bomb": "IMAGE_CANDIDATE_BOMB",
    "decode": "IMAGE_CANDIDATE_DECODE",
}
INVITE_ALPHABET = string.ascii_uppercase + string.digits
SHANGHAI = ZoneInfo("Asia/Shanghai")
MAX_SIGNED_INT64 = 2**63 - 1


@dataclass(frozen=True)
class ValidatedGenerateInput:
    poster_type: str | None
    template_id: int | None
    related_id: int | None
    title: str | None
    subtitle: str | None
    image_url: str | None


@dataclass(frozen=True)
class CoupleContext:
    user: User
    partner: User
    couple: Couple


@dataclass(frozen=True)
class RenderContent:
    title: str
    subtitle: str
    metrics: tuple[tuple[str, str], ...]
    image_urls: tuple[str, ...] = ()


def _log_fields(
    request: Request,
    operation: str,
    result: str,
    started: float,
    error_code: str = "NONE",
) -> dict[str, object]:
    return {
        "requestId": getattr(request.state, "request_id", "unknown"),
        "module": "poster",
        "operation": operation,
        "result": result,
        "durationMs": max(0, round((perf_counter() - started) * 1000)),
        "errorCode": error_code,
    }


async def _log(
    event: str,
    request: Request,
    operation: str,
    result: str,
    started: float,
    error_code: str = "NONE",
) -> None:
    fields = _log_fields(request, operation, result, started, error_code)
    if result in {"failed", "rejected", "cleanup_failed"}:
        await logger.aerror(event, **fields)
    else:
        await logger.ainfo(event, **fields)


def _invalid() -> Never:
    raise BusinessError(9001, "参数无效")


def _validate_poster_type(poster_type: str | None) -> None:
    if poster_type is not None and poster_type not in POSTER_TYPES:
        _invalid()


def _validate_positive_int64(value: int | None) -> None:
    if value is not None and not 1 <= value <= MAX_SIGNED_INT64:
        _invalid()


def _validate_custom_structure(value: Any, *, depth: int = 0) -> int:
    if depth > 3:
        _invalid()
    if isinstance(value, dict):
        return len(value) + sum(
            _validate_custom_structure(item, depth=depth + 1) for item in value.values()
        )
    if isinstance(value, list):
        return sum(_validate_custom_structure(item, depth=depth + 1) for item in value)
    return 0


def validate_generate_input(
    payload: PosterGenerateRequest, *, current_year: int
) -> ValidatedGenerateInput:
    poster_type = payload.poster_type.strip() if payload.poster_type else None
    _validate_poster_type(poster_type)
    _validate_positive_int64(payload.template_id)
    if poster_type is None and payload.template_id is None:
        _invalid()
    _validate_positive_int64(payload.related_id)
    if poster_type == "annual" and payload.related_id is not None:
        if not 2000 <= payload.related_id <= current_year:
            _invalid()

    custom_data = payload.custom_data or {}
    try:
        encoded = json.dumps(custom_data, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        _invalid()
    if len(encoded.encode("utf-8")) > 8 * 1024:
        _invalid()
    if _validate_custom_structure(custom_data) > 32:
        _invalid()

    limits = {"title": 40, "subtitle": 80, "imageUrl": 512}
    known: dict[str, str | None] = {}
    for key, limit in limits.items():
        value = custom_data.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > limit):
            _invalid()
        known[key] = value
    return ValidatedGenerateInput(
        poster_type=poster_type,
        template_id=payload.template_id,
        related_id=payload.related_id,
        title=known["title"],
        subtitle=known["subtitle"],
        image_url=known["imageUrl"],
    )


def generate_invite_code() -> str:
    return "".join(secrets.choice(INVITE_ALPHABET) for _ in range(8))


def poster_dto(item: UserPoster, template_names: dict[int, str]) -> dict[str, object | None]:
    return {
        "id": item.id,
        "posterType": item.poster_type,
        "posterTypeName": POSTER_TYPE_NAMES.get(item.poster_type, item.poster_type),
        "templateId": item.template_id,
        "templateName": template_names.get(item.template_id),
        "posterUrl": item.poster_url,
        "inviteCode": item.invite_code,
        "createTime": item.create_time.isoformat(),
    }


def _template_dto(item: PosterTemplate) -> dict[str, object | None]:
    return {
        "id": item.id,
        "templateCode": item.template_code,
        "templateName": item.template_name,
        "templateType": item.template_type,
        "templateTypeName": POSTER_TYPE_NAMES.get(item.template_type, item.template_type),
        "templateConfig": item.template_config,
        "previewUrl": item.preview_url,
        "isActive": bool(item.is_active),
    }


async def _require_user(session: AsyncSession, user_id: int) -> User:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        raise BusinessError(1001, "用户不存在")
    return user


async def _require_couple_context(session: AsyncSession, user_id: int) -> CoupleContext:
    user = await _require_user(session, user_id)
    if user.couple_id is None:
        raise BusinessError(2006, "未绑定情侣关系")
    couple = await session.scalar(
        select(Couple).where(Couple.id == user.couple_id, Couple.status == 1)
    )
    if couple is None or user.id not in {couple.user1_id, couple.user2_id}:
        raise BusinessError(2006, "未绑定情侣关系")
    partner_id = couple.user2_id if user.id == couple.user1_id else couple.user1_id
    if partner_id is None:
        raise BusinessError(2006, "未绑定情侣关系")
    partner = await session.scalar(select(User).where(User.id == partner_id, User.is_deleted == 0))
    if partner is None or partner.couple_id != couple.id:
        raise BusinessError(2006, "未绑定情侣关系")
    return CoupleContext(user=user, partner=partner, couple=couple)


async def _template_names(session: AsyncSession, template_ids: set[int]) -> dict[int, str]:
    if not template_ids:
        return {}
    rows = await session.execute(
        select(PosterTemplate.id, PosterTemplate.template_name).where(
            PosterTemplate.id.in_(template_ids)
        )
    )
    return {int(template_id): str(name) for template_id, name in rows.all()}


async def get_templates(
    request: Request,
    session: AsyncSession,
    user_id: int,
    poster_type: str | None,
) -> list[dict[str, object | None]]:
    started = perf_counter()
    try:
        _validate_poster_type(poster_type)
        await _require_user(session, user_id)
        query = select(PosterTemplate).where(PosterTemplate.is_active == 1)
        if poster_type is not None:
            query = query.where(PosterTemplate.template_type == poster_type)
        result = await session.execute(query.order_by(PosterTemplate.id.asc()))
        payload = [_template_dto(item) for item in result.scalars().all()]
    except BusinessError as error:
        await _log(
            "poster_templates_failed", request, "templates", "rejected", started, str(error.code)
        )
        raise
    await _log("poster_templates_completed", request, "templates", "success", started)
    return payload


def _validate_list_filters(poster_type: str | None, limit: int) -> None:
    _validate_poster_type(poster_type)
    if not 1 <= limit <= 100:
        _invalid()


async def list_posters(
    request: Request,
    session: AsyncSession,
    user_id: int,
    poster_type: str | None,
    limit: int,
) -> list[dict[str, object | None]]:
    started = perf_counter()
    try:
        _validate_list_filters(poster_type, limit)
        await _require_user(session, user_id)
        query = select(UserPoster).where(UserPoster.user_id == user_id, UserPoster.is_deleted == 0)
        if poster_type is not None:
            query = query.where(UserPoster.poster_type == poster_type)
        result = await session.execute(
            query.order_by(UserPoster.create_time.desc(), UserPoster.id.desc()).limit(limit)
        )
        items = result.scalars().all()
        names = await _template_names(session, {item.template_id for item in items})
        payload = [poster_dto(item, names) for item in items]
    except BusinessError as error:
        await _log("poster_list_failed", request, "list", "rejected", started, str(error.code))
        raise
    await _log("poster_list_completed", request, "list", "success", started)
    return payload


async def _resolve_template(
    session: AsyncSession, validated: ValidatedGenerateInput, current_year: int
) -> tuple[PosterTemplate, poster_renderer.PosterPalette]:
    if validated.template_id is not None:
        template = await session.scalar(
            select(PosterTemplate).where(
                PosterTemplate.id == validated.template_id,
                PosterTemplate.is_active == 1,
            )
        )
    else:
        template = await session.scalar(
            select(PosterTemplate)
            .where(
                PosterTemplate.template_type == validated.poster_type,
                PosterTemplate.is_active == 1,
            )
            .order_by(PosterTemplate.id.asc())
            .limit(1)
        )
    if template is None or template.template_type not in POSTER_TYPES:
        raise BusinessError(8902, "海报模板不存在")
    if validated.poster_type is not None and validated.poster_type != template.template_type:
        raise BusinessError(9001, "参数无效")
    if template.template_type == "annual" and validated.related_id is not None:
        if not 2000 <= validated.related_id <= current_year:
            raise BusinessError(9001, "参数无效")
    try:
        palette = poster_renderer.parse_template_config(template.template_config)
    except poster_renderer.PosterTemplateConfigError as error:
        raise BusinessError(8902, "海报模板不存在") from error
    return template, palette


def _decode_urls(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return ()
    if not isinstance(decoded, list):
        return ()
    return tuple(item for item in decoded if isinstance(item, str))


def _next_occurrence(value: date, current: date) -> date:
    try:
        candidate = value.replace(year=current.year)
    except ValueError:
        candidate = date(current.year, 2, 28)
    if candidate < current:
        try:
            candidate = value.replace(year=current.year + 1)
        except ValueError:
            candidate = date(current.year + 1, 2, 28)
    return candidate


async def _anniversary_content(
    session: AsyncSession,
    context: CoupleContext,
    related_id: int | None,
    current: date,
) -> RenderContent:
    if related_id is not None:
        item = await session.scalar(
            select(Anniversary).where(
                Anniversary.id == related_id,
                Anniversary.couple_id == context.couple.id,
                Anniversary.is_deleted == 0,
            )
        )
        if item is None:
            owner_couple_id = await session.scalar(
                select(Anniversary.couple_id).where(Anniversary.id == related_id)
            )
            if owner_couple_id is None or int(owner_couple_id) == context.couple.id:
                raise BusinessError(8901, "海报不存在")
            raise BusinessError(8903, "无权操作此海报")
        event_name = item.name
        event_date = item.anniversary_date
    else:
        event_name = "相恋纪念日"
        event_date = context.couple.start_date or current
    start_date = context.couple.start_date or current
    together_days = max(0, (current - start_date).days)
    days_until = max(0, (_next_occurrence(event_date, current) - current).days)
    return RenderContent(
        title=event_name,
        subtitle=f"值得珍藏的日子 · {event_date.isoformat()}",
        metrics=(
            ("相恋天数", f"{together_days} 天"),
            ("纪念日期", event_date.isoformat()),
            ("距离下一次", f"{days_until} 天"),
        ),
    )


async def _feed_content(
    session: AsyncSession, context: CoupleContext, related_id: int | None
) -> RenderContent:
    if related_id is not None:
        item = await session.scalar(
            select(Feed).where(
                Feed.id == related_id,
                Feed.couple_id == context.couple.id,
                Feed.status == 1,
            )
        )
        if item is None:
            owner_couple_id = await session.scalar(
                select(Feed.couple_id).where(Feed.id == related_id)
            )
            if owner_couple_id is None or int(owner_couple_id) == context.couple.id:
                raise BusinessError(8901, "海报不存在")
            raise BusinessError(8903, "无权操作此海报")
    else:
        item = await session.scalar(
            select(Feed)
            .where(Feed.couple_id == context.couple.id, Feed.status == 1)
            .order_by(Feed.create_time.desc(), Feed.id.desc())
            .limit(1)
        )
    received = int(
        await session.scalar(
            select(func.count())
            .select_from(Feed)
            .where(Feed.couple_id == context.couple.id, Feed.status == 1)
        )
        or 0
    )
    if item is None:
        return RenderContent(
            title="甜蜜投喂",
            subtitle="尚无记录，期待下一份心意",
            metrics=(("投喂类型", "尚无"), ("已领取", "0 次"), ("甜蜜记录", "0 次")),
        )
    feed_type = FEED_TYPE_NAMES.get(item.feed_type, "美食")
    public_copy = poster_renderer.sanitize_text(
        item.content or item.message or "甜蜜投喂", max_chars=80
    )
    return RenderContent(
        title="甜蜜投喂时刻",
        subtitle=public_copy,
        metrics=(
            ("投喂类型", feed_type),
            ("已领取", f"{received} 次"),
            ("最近心意", "已收藏" if item.status == 1 else "待领取"),
        ),
        image_urls=_decode_urls(item.image_urls),
    )


async def _map_content(
    session: AsyncSession, context: CoupleContext, related_id: int | None
) -> RenderContent:
    if related_id is not None:
        item = await session.scalar(
            select(CoupleMenu).where(
                CoupleMenu.id == related_id,
                CoupleMenu.couple_id == context.couple.id,
                CoupleMenu.status == 1,
                CoupleMenu.is_deleted == 0,
            )
        )
        if item is None:
            owner_couple_id = await session.scalar(
                select(CoupleMenu.couple_id).where(CoupleMenu.id == related_id)
            )
            if owner_couple_id is None or int(owner_couple_id) == context.couple.id:
                raise BusinessError(8901, "海报不存在")
            raise BusinessError(8903, "无权操作此海报")
    else:
        item = await session.scalar(
            select(CoupleMenu)
            .where(
                CoupleMenu.couple_id == context.couple.id,
                CoupleMenu.status == 1,
                CoupleMenu.is_deleted == 0,
            )
            .order_by(CoupleMenu.eaten_date.desc(), CoupleMenu.id.desc())
            .limit(1)
        )
    visited = int(
        await session.scalar(
            select(func.count())
            .select_from(CoupleMenu)
            .where(
                CoupleMenu.couple_id == context.couple.id,
                CoupleMenu.status == 1,
                CoupleMenu.is_deleted == 0,
            )
        )
        or 0
    )
    favorites = int(
        await session.scalar(
            select(func.count())
            .select_from(CoupleMenu)
            .where(
                CoupleMenu.couple_id == context.couple.id,
                CoupleMenu.is_favorite == 1,
                CoupleMenu.is_deleted == 0,
            )
        )
        or 0
    )
    if item is None:
        return RenderContent(
            title="我们的足迹",
            subtitle="尚无记录，下一站由我们一起发现",
            metrics=(("已去过", "0 个地点"), ("已收藏", "0 个地点"), ("最近地点", "尚无")),
        )
    latest_place = item.restaurant_name or item.location or "已到访地点"
    return RenderContent(
        title=latest_place,
        subtitle=item.location or "一起走过的美食足迹",
        metrics=(
            ("已去过", f"{visited} 个地点"),
            ("已收藏", f"{favorites} 个地点"),
            ("最近地点", latest_place),
        ),
        image_urls=_decode_urls(item.photo_urls),
    )


async def _annual_content(
    session: AsyncSession,
    context: CoupleContext,
    related_id: int | None,
    current_year: int,
) -> RenderContent:
    year = related_id or current_year
    if not 2000 <= year <= current_year:
        raise BusinessError(9001, "参数无效")
    start = datetime(year, 1, 1)
    end = datetime(year + 1, 1, 1)
    start_date = date(year, 1, 1)
    end_date = date(year + 1, 1, 1)
    feed_count = int(
        await session.scalar(
            select(func.count())
            .select_from(Feed)
            .where(
                Feed.couple_id == context.couple.id,
                Feed.status == 1,
                Feed.create_time >= start,
                Feed.create_time < end,
            )
        )
        or 0
    )
    menu_count = int(
        await session.scalar(
            select(func.count())
            .select_from(CoupleMenu)
            .where(
                CoupleMenu.couple_id == context.couple.id,
                CoupleMenu.status == 1,
                CoupleMenu.is_deleted == 0,
                CoupleMenu.eaten_date >= start_date,
                CoupleMenu.eaten_date < end_date,
            )
        )
        or 0
    )
    note_count = int(
        await session.scalar(
            select(func.count())
            .select_from(FoodNote)
            .where(
                FoodNote.couple_id == context.couple.id,
                FoodNote.is_deleted == 0,
                FoodNote.create_time >= start,
                FoodNote.create_time < end,
            )
        )
        or 0
    )
    latest = await session.scalar(
        select(CoupleMenu)
        .where(
            CoupleMenu.couple_id == context.couple.id,
            CoupleMenu.status == 1,
            CoupleMenu.is_deleted == 0,
            CoupleMenu.eaten_date >= start_date,
            CoupleMenu.eaten_date < end_date,
        )
        .order_by(CoupleMenu.eaten_date.desc(), CoupleMenu.id.desc())
        .limit(1)
    )
    latest_place = latest.restaurant_name if latest is not None else "尚无记录"
    return RenderContent(
        title=f"我们的 {year}",
        subtitle=f"一起收藏的 {year} 年度回忆",
        metrics=(
            ("甜蜜投喂", f"{feed_count} 次"),
            ("到访地点", f"{menu_count} 个"),
            ("共同笔记", f"{note_count} 篇 · {latest_place}"),
        ),
        image_urls=_decode_urls(latest.photo_urls) if latest is not None else (),
    )


async def _render_content(
    session: AsyncSession,
    context: CoupleContext,
    poster_type: str,
    related_id: int | None,
    current: date,
) -> RenderContent:
    if poster_type == "anniversary":
        return await _anniversary_content(session, context, related_id, current)
    if poster_type == "feed":
        return await _feed_content(session, context, related_id)
    if poster_type == "map":
        return await _map_content(session, context, related_id)
    return await _annual_content(session, context, related_id, current.year)


async def _local_candidates(
    request: Request,
    context: CoupleContext,
    urls: tuple[str, ...],
    started: float,
) -> tuple[Path, ...]:
    settings = request.app.state.settings
    members = {context.user.id, context.partner.id}
    paths: list[Path] = []
    for url in urls:
        path = poster_renderer.resolve_local_image_candidate(
            upload_root=Path(settings.file_upload_path),
            file_base_url=settings.file_base_url,
            file_public_path=settings.file_public_path,
            candidate_url=url,
            member_ids=members,
        )
        if path is None:
            await _log(
                "poster_image_candidate_rejected",
                request,
                "generate.decode",
                "rejected",
                started,
                "IMAGE_CANDIDATE_REJECTED",
            )
        elif path not in paths:
            paths.append(path)
    return tuple(paths)


async def _log_decode_rejections(
    request: Request,
    reasons: tuple[str, ...],
    started: float,
) -> None:
    for reason in sorted(Counter(reasons)):
        error_code = IMAGE_REJECTION_ERROR_CODES.get(reason, "IMAGE_CANDIDATE_REJECTED")
        await _log(
            "poster_image_candidate_rejected",
            request,
            "generate.decode",
            "rejected",
            started,
            error_code,
        )


async def _commit_generated_poster(session: AsyncSession, item: UserPoster) -> None:
    session.add(item)
    await session.flush()
    await session.commit()


async def generate(
    request: Request,
    session: AsyncSession,
    user_id: int,
    payload: PosterGenerateRequest,
) -> dict[str, object | None]:
    started = perf_counter()
    await _log("poster_generation_started", request, "generate", "started", started)
    current = datetime.now(SHANGHAI)
    try:
        validated = validate_generate_input(payload, current_year=current.year)
        context = await _require_couple_context(session, user_id)
        template, palette = await _resolve_template(session, validated, current.year)
        content = await _render_content(
            session, context, template.template_type, validated.related_id, current.date()
        )
        candidate_urls = tuple(
            value
            for value in (
                validated.image_url,
                *content.image_urls,
                context.user.avatar_url,
                context.partner.avatar_url,
            )
            if value
        )
        candidates = await _local_candidates(request, context, candidate_urls, started)
        await _log("poster_source_resolved", request, "generate.resolve", "success", started)
    except BusinessError as error:
        await _log(
            "poster_generation_failed",
            request,
            "generate.validate",
            "rejected",
            started,
            str(error.code),
        )
        raise

    invite_code = generate_invite_code()
    render_payload = poster_renderer.PosterRenderPayload(
        poster_type=template.template_type,
        type_name=POSTER_TYPE_NAMES[template.template_type],
        title=validated.title or content.title,
        subtitle=validated.subtitle or content.subtitle,
        couple_name=context.couple.couple_nickname
        or f"{context.user.nick_name or 'TA'} & {context.partner.nick_name or 'TA'}",
        invite_code=invite_code,
        generated_date=current.date(),
        metrics=content.metrics,
        palette=palette,
        image_candidates=candidates,
    )
    settings = request.app.state.settings
    try:
        async with request.app.state.poster_render_semaphore:
            published = await asyncio.to_thread(
                poster_renderer.render_and_publish,
                upload_root=Path(settings.file_upload_path),
                file_base_url=settings.file_base_url,
                user_id=user_id,
                payload=render_payload,
            )
    except poster_renderer.PosterRenderError as error:
        await _log(
            "poster_generation_failed",
            request,
            "generate.render",
            "failed",
            started,
            "9002",
        )
        raise BusinessError(9002, "文件上传失败") from error
    await _log_decode_rejections(request, published.rejection_reasons, started)
    await _log("poster_render_completed", request, "generate.render", "success", started)
    await _log("poster_file_published", request, "generate.publish", "success", started)

    item = UserPoster(
        user_id=user_id,
        couple_id=context.couple.id,
        poster_type=template.template_type,
        template_id=template.id,
        poster_url=published.url,
        invite_code=invite_code,
        is_deleted=0,
        create_time=current.replace(tzinfo=None),
    )
    try:
        await _commit_generated_poster(session, item)
    except Exception as error:
        rollback_failed = False
        try:
            await session.rollback()
        except Exception:
            rollback_failed = True
        compensation_error: str | None = None
        try:
            compensation_state = await asyncio.to_thread(
                poster_renderer.unlink_published_poster,
                upload_root=Path(settings.file_upload_path),
                file_base_url=settings.file_base_url,
                file_public_path=settings.file_public_path,
                poster_url=published.url,
            )
        except Exception:
            compensation_error = "POSTER_COMPENSATION_FAILED"
        else:
            if compensation_state == "refused":
                compensation_error = "POSTER_COMPENSATION_REFUSED"
        if rollback_failed:
            await _log(
                "poster_rollback_failed",
                request,
                "generate.rollback",
                "cleanup_failed",
                started,
                "DATABASE_ROLLBACK_FAILED",
            )
        if compensation_error is not None:
            await _log(
                "poster_compensation_failed",
                request,
                "generate.compensate",
                "cleanup_failed",
                started,
                compensation_error,
            )
        await _log(
            "poster_generation_failed",
            request,
            "generate.db_commit",
            "failed",
            started,
            "DATABASE_COMMIT_FAILED",
        )
        raise BusinessError(500, "服务器内部错误，请稍后重试", http_status=500) from error
    await _log("poster_record_committed", request, "generate.db_commit", "success", started)
    return poster_dto(item, {template.id: template.template_name})


async def _owned_poster(
    session: AsyncSession, user_id: int, poster_id: int, *, include_deleted: bool
) -> UserPoster:
    _validate_positive_int64(poster_id)
    await _require_user(session, user_id)
    item = await session.scalar(select(UserPoster).where(UserPoster.id == poster_id))
    if item is None or (not include_deleted and item.is_deleted != 0):
        raise BusinessError(8901, "海报不存在")
    if item.user_id != user_id:
        raise BusinessError(8903, "无权操作此海报")
    return item


async def _detail(
    request: Request,
    session: AsyncSession,
    user_id: int,
    poster_id: int,
    operation: str,
) -> dict[str, object | None]:
    started = perf_counter()
    try:
        item = await _owned_poster(session, user_id, poster_id, include_deleted=False)
        names = await _template_names(session, {item.template_id})
    except BusinessError as error:
        await _log("poster_detail_failed", request, operation, "rejected", started, str(error.code))
        raise
    await _log("poster_detail_completed", request, operation, "success", started)
    return poster_dto(item, names)


async def detail(
    request: Request, session: AsyncSession, user_id: int, poster_id: int
) -> dict[str, object | None]:
    return await _detail(request, session, user_id, poster_id, "detail")


async def share(
    request: Request, session: AsyncSession, user_id: int, poster_id: int
) -> dict[str, object | None]:
    return await _detail(request, session, user_id, poster_id, "share")


async def delete(request: Request, session: AsyncSession, user_id: int, poster_id: int) -> None:
    started = perf_counter()
    try:
        _validate_positive_int64(poster_id)
        await _require_user(session, user_id)
        item = await session.scalar(
            select(UserPoster).where(UserPoster.id == poster_id).with_for_update()
        )
        if item is None:
            raise BusinessError(8901, "海报不存在")
        if item.user_id != user_id:
            raise BusinessError(8903, "无权操作此海报")
        if item.is_deleted == 0:
            item.is_deleted = 1
            try:
                await session.commit()
            except Exception as error:
                await session.rollback()
                await _log(
                    "poster_delete_failed",
                    request,
                    "delete.db_commit",
                    "failed",
                    started,
                    "DATABASE_COMMIT_FAILED",
                )
                raise BusinessError(500, "服务器内部错误，请稍后重试", http_status=500) from error
        settings = request.app.state.settings
        try:
            file_state = await asyncio.to_thread(
                poster_renderer.unlink_published_poster,
                upload_root=Path(settings.file_upload_path),
                file_base_url=settings.file_base_url,
                file_public_path=settings.file_public_path,
                poster_url=item.poster_url,
            )
        except OSError as error:
            await _log(
                "poster_delete_failed",
                request,
                "delete.unlink",
                "cleanup_failed",
                started,
                "9002",
            )
            raise BusinessError(9002, "文件上传失败") from error
    except BusinessError as error:
        if error.code not in {500, 9002}:
            await _log(
                "poster_delete_failed",
                request,
                "delete",
                "rejected",
                started,
                str(error.code),
            )
        raise
    await _log(
        "poster_delete_completed",
        request,
        "delete",
        "success" if file_state != "refused" else "refused",
        started,
        "NONE" if file_state != "refused" else "CLEANUP_REFUSED",
    )
