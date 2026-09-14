"""数据库幂等记录读写。"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from services.dining.app.models import IdempotencyRecord


async def get_record(session: AsyncSession, user_id: int, key: str) -> dict[str, object] | None:
    row = await session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.user_id == user_id, IdempotencyRecord.idempotency_key == key
        )
    )
    if row is None:
        return None
    return cast(dict[str, object], json.loads(row.response_json))


async def run_once(
    session: AsyncSession,
    user_id: int,
    key: str | None,
    action: Callable[[], Awaitable[dict[str, object]]],
) -> dict[str, object]:
    if not key:
        return await action()

    record_statement = select(IdempotencyRecord).where(
        IdempotencyRecord.user_id == user_id, IdempotencyRecord.idempotency_key == key
    ).with_for_update()
    existing_row = await session.scalar(record_statement)
    if existing_row is not None:
        return cast(dict[str, object], json.loads(existing_row.response_json))

    # A missing idempotency row cannot itself be locked. Serialize first writers
    # on the stable user row, then re-check in the same transaction before action.
    await session.scalar(select(User.id).where(User.id == user_id).with_for_update())
    existing_row = await session.scalar(record_statement)
    if existing_row is not None:
        return cast(dict[str, object], json.loads(existing_row.response_json))

    response = await action()
    response_code = response.get("code")
    session.add(
        IdempotencyRecord(
            user_id=user_id,
            idempotency_key=key,
            response_code=response_code if isinstance(response_code, int) else 200,
            response_json=json.dumps(response, ensure_ascii=False, default=str),
        )
    )
    return response
