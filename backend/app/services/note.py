import html
import json
from time import perf_counter
from typing import cast

import structlog
from fastapi import Request
from sqlalchemy import delete, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Anniversary, FoodNote, NoteLike, User
from app.schemas.business import NoteRequest, NoteUpdateRequest

logger = structlog.get_logger()


def _log_fields(
    request: Request, operation: str, result: str, started: float, error_code: str = "NONE"
) -> dict[str, object]:
    return {
        "requestId": request.state.request_id,
        "module": "note",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _user(session: AsyncSession, user_id: int) -> User:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        raise BusinessError(1001, "用户不存在")
    return user


async def _couple_id(session: AsyncSession, user_id: int) -> int:
    user = await _user(session, user_id)
    if user.couple_id is None:
        raise BusinessError(2006, "未绑定情侣关系")
    return user.couple_id


async def _anniversary_for_couple(
    session: AsyncSession, couple_id: int, anniversary_id: int
) -> Anniversary:
    anniversary = await session.scalar(
        select(Anniversary).where(
            Anniversary.id == anniversary_id,
            Anniversary.couple_id == couple_id,
            Anniversary.is_deleted == 0,
        )
    )
    if anniversary is None:
        raise BusinessError(4001, "纪念日不存在")
    return anniversary


def _decode_urls(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in decoded] if isinstance(decoded, list) else []


def _encode_urls(value: list[str] | None) -> str | None:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) if value else None


async def _payload(session: AsyncSession, note: FoodNote, user_id: int) -> dict[str, object | None]:
    author = await session.scalar(select(User).where(User.id == note.author_id))
    anniversary = (
        await session.scalar(select(Anniversary).where(Anniversary.id == note.anniversary_id))
        if note.anniversary_id is not None
        else None
    )
    liked = await session.scalar(
        select(NoteLike.id).where(NoteLike.note_id == note.id, NoteLike.user_id == user_id)
    )
    return {
        "id": note.id,
        "coupleId": note.couple_id,
        "authorId": note.author_id,
        "authorName": author.nick_name if author else None,
        "authorAvatar": author.avatar_url if author else None,
        "title": note.title,
        "content": note.content,
        "location": note.location,
        "latitude": float(note.latitude) if note.latitude is not None else None,
        "longitude": float(note.longitude) if note.longitude is not None else None,
        "isAnniversaryLinked": bool(note.is_anniversary_linked),
        "anniversaryId": note.anniversary_id,
        "anniversaryName": anniversary.name if anniversary else None,
        "viewCount": note.view_count,
        "likeCount": note.like_count,
        "commentCount": note.comment_count,
        "photoUrls": _decode_urls(note.photo_urls),
        "createTime": note.create_time.isoformat() if note.create_time else None,
        "isLiked": liked is not None,
        "isAuthor": note.author_id == user_id,
    }


def _plain(value: str | None) -> str | None:
    return html.escape(value, quote=False) if value is not None else None


async def list_notes(
    request: Request,
    session: AsyncSession,
    user_id: int,
    anniversary_id: int | None = None,
) -> list[dict[str, object | None]]:
    started = perf_counter()
    couple_id = await _couple_id(session, user_id)
    conditions = [FoodNote.couple_id == couple_id, FoodNote.is_deleted == 0]
    if anniversary_id is not None:
        conditions.append(FoodNote.anniversary_id == anniversary_id)
    result = await session.execute(
        select(FoodNote)
        .where(*conditions)
        .order_by(FoodNote.create_time.desc(), FoodNote.id.desc())
    )
    items = [await _payload(session, note, user_id) for note in result.scalars().all()]
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "list", "success", started)
    )
    return items


async def detail(
    request: Request, session: AsyncSession, user_id: int, note_id: int
) -> dict[str, object | None]:
    started = perf_counter()
    couple_id = await _couple_id(session, user_id)
    note = await session.scalar(
        select(FoodNote).where(FoodNote.id == note_id, FoodNote.is_deleted == 0)
    )
    if note is None:
        raise BusinessError(4001, "笔记不存在")
    if note.couple_id != couple_id:
        raise BusinessError(4002, "无权查看此笔记")
    result = await _payload(session, note, user_id)
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "detail", "success", started)
    )
    return result


async def add(request: Request, session: AsyncSession, user_id: int, payload: NoteRequest) -> int:
    started = perf_counter()
    couple_id = await _couple_id(session, user_id)
    if payload.anniversary_id is not None:
        await _anniversary_for_couple(session, couple_id, payload.anniversary_id)
    note = FoodNote(
        couple_id=couple_id,
        author_id=user_id,
        title=_plain(payload.title) or "",
        content=_plain(payload.content) or "",
        location=_plain(payload.location),
        latitude=payload.latitude,
        longitude=payload.longitude,
        is_anniversary_linked=payload.is_anniversary_linked or 0,
        anniversary_id=payload.anniversary_id,
        view_count=0,
        like_count=0,
        comment_count=0,
        photo_urls=_encode_urls(payload.photo_urls),
        is_deleted=0,
    )
    session.add(note)
    await session.flush()
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "add", "success", started)
    )
    return note.id


async def _owned_note(session: AsyncSession, user_id: int, note_id: int) -> FoodNote:
    note = await session.scalar(
        select(FoodNote).where(FoodNote.id == note_id, FoodNote.is_deleted == 0)
    )
    if note is None:
        raise BusinessError(4001, "笔记不存在")
    if note.author_id != user_id:
        raise BusinessError(4002, "无权操作此笔记")
    return note


def _apply_payload(note: FoodNote, payload: NoteUpdateRequest) -> None:
    if "title" in payload.model_fields_set:
        note.title = _plain(payload.title) or note.title
    if "content" in payload.model_fields_set:
        note.content = _plain(payload.content) or note.content
    if "location" in payload.model_fields_set and payload.location is not None:
        note.location = _plain(payload.location)
    if "latitude" in payload.model_fields_set:
        note.latitude = payload.latitude
    if "longitude" in payload.model_fields_set:
        note.longitude = payload.longitude
    if payload.is_anniversary_linked is not None:
        note.is_anniversary_linked = payload.is_anniversary_linked
    if payload.anniversary_id is not None:
        note.anniversary_id = payload.anniversary_id
    if payload.photo_urls is not None:
        note.photo_urls = _encode_urls(payload.photo_urls)


async def update_note(
    request: Request,
    session: AsyncSession,
    user_id: int,
    note_id: int,
    payload: NoteUpdateRequest,
) -> None:
    started = perf_counter()
    note = await _owned_note(session, user_id, note_id)
    if payload.anniversary_id is not None:
        await _anniversary_for_couple(session, note.couple_id, payload.anniversary_id)
    _apply_payload(note, payload)
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "update", "success", started)
    )


async def delete_note(request: Request, session: AsyncSession, user_id: int, note_id: int) -> None:
    started = perf_counter()
    note = await _owned_note(session, user_id, note_id)
    note.is_deleted = 1
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "delete", "success", started)
    )


async def _accessible_note(session: AsyncSession, user_id: int, note_id: int) -> FoodNote:
    couple_id = await _couple_id(session, user_id)
    note = await session.scalar(
        select(FoodNote).where(
            FoodNote.id == note_id,
            FoodNote.couple_id == couple_id,
            FoodNote.is_deleted == 0,
        )
    )
    if note is None:
        raise BusinessError(4001, "笔记不存在")
    return note


async def like(request: Request, session: AsyncSession, user_id: int, note_id: int) -> None:
    started = perf_counter()
    note = await _accessible_note(session, user_id, note_id)
    session.add(NoteLike(note_id=note.id, user_id=user_id))
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        await logger.ainfo(
            "business_operation_completed",
            **_log_fields(request, "like", "idempotent", started, "ALREADY_LIKED"),
        )
        return
    await session.execute(
        update(FoodNote).where(FoodNote.id == note.id).values(like_count=FoodNote.like_count + 1)
    )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "like", "success", started)
    )


async def unlike(request: Request, session: AsyncSession, user_id: int, note_id: int) -> None:
    started = perf_counter()
    note = await _accessible_note(session, user_id, note_id)
    result = cast(
        CursorResult[object],
        await session.execute(
            delete(NoteLike).where(NoteLike.note_id == note.id, NoteLike.user_id == user_id)
        ),
    )
    if result.rowcount:
        await session.execute(
            update(FoodNote)
            .where(FoodNote.id == note.id, FoodNote.like_count > 0)
            .values(like_count=FoodNote.like_count - 1)
        )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed",
        **_log_fields(
            request,
            "unlike",
            "idempotent" if not result.rowcount else "success",
            started,
        ),
    )


async def comment(
    request: Request, session: AsyncSession, user_id: int, note_id: int, content: str
) -> None:
    started = perf_counter()
    note = await _accessible_note(session, user_id, note_id)
    if not content.strip():
        raise BusinessError(9001, "参数无效")
    await session.execute(
        update(FoodNote)
        .where(FoodNote.id == note.id)
        .values(comment_count=FoodNote.comment_count + 1)
    )
    await session.commit()
    await logger.ainfo(
        "business_operation_completed", **_log_fields(request, "comment", "success", started)
    )
