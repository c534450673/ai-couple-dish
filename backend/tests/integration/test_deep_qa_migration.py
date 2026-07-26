import asyncio
import os
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import Connection, inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from structlog.testing import capture_logs

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.auth import create_access_token, decode_access_token
from app.core.config import Settings
from app.db.models import CoupleQaProgress, DeepQaAnswer
from app.db.session import get_session
from app.main import create_app
from app.redis.client import RedisClient
from app.redis.keys import logout_blacklist_key

SECRET = "q" * 64
TOKEN_EXPIRATION_MS = 300_000


def _reset_schema(connection: Connection) -> None:
    quote = connection.dialect.identifier_preparer.quote
    connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
    try:
        for table_name in inspect(connection).get_table_names():
            connection.exec_driver_sql(f"DROP TABLE {quote(table_name)}")
    finally:
        connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")


def _schema_statements() -> list[str]:
    path = Path(__file__).parents[2] / "src" / "test" / "resources" / "schema-test.sql"
    source = path.read_text()
    mysql_source = re.sub(r"CREATE (UNIQUE )?INDEX IF NOT EXISTS", r"CREATE \1INDEX", source)
    return [statement.strip() for statement in mysql_source.split(";") if statement.strip()]


@pytest.fixture
async def mysql_deep_qa_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(mysql_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_reset_schema)
            for statement in _schema_statements():
                await connection.exec_driver_sql(statement)
        yield engine
    finally:
        await engine.dispose()


def _settings() -> Settings:
    return Settings(_env_file=None, DB_PASSWORD="db-secret", JWT_SECRET=SECRET)  # noqa: S106


def _token(user_id: int, *, expiration_ms: int = TOKEN_EXPIRATION_MS) -> str:
    return create_access_token(user_id, SECRET, expiration_ms=expiration_ms)


def _headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user_id)}"}


async def _rows(engine: AsyncEngine, statement: str, **params: Any) -> list[dict[str, Any]]:
    async with engine.connect() as connection:
        result = await connection.execute(text(statement), params)
        return [dict(row) for row in result.mappings().all()]


async def _execute(engine: AsyncEngine, statement: str, **params: Any) -> None:
    async with engine.begin() as connection:
        await connection.execute(text(statement), params)


async def _seed(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO t_user
                    (id, openid, nick_name, avatar_url, couple_id, status, is_deleted)
                VALUES
                    (101, 'qa-a-one', 'qa-private-name-one',
                     'https://avatar.invalid/qa-private-one', 11, 1, 0),
                    (102, 'qa-a-two', 'qa-private-name-two',
                     'https://avatar.invalid/qa-private-two', 11, 1, 0),
                    (201, 'qa-b-one', 'qa-b-one-name', NULL, 22, 1, 0),
                    (202, 'qa-b-two', 'qa-b-two-name', NULL, 22, 1, 0),
                    (301, 'qa-unbound', NULL, NULL, NULL, 1, 0),
                    (401, 'qa-forged', NULL, NULL, 33, 1, 0),
                    (402, 'qa-real-33-one', NULL, NULL, 33, 1, 0),
                    (403, 'qa-real-33-two', NULL, NULL, 33, 1, 0),
                    (601, 'qa-inactive-one', NULL, NULL, 66, 1, 0),
                    (602, 'qa-inactive-two', NULL, NULL, 66, 1, 0)
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_couple (id, couple_code, user_1_id, user_2_id, status)
                VALUES
                    (11, 'QA-PRIVATE-CODE-A', 101, 102, 1),
                    (22, 'QA-PRIVATE-CODE-B', 201, 202, 1),
                    (33, 'QA-PRIVATE-CODE-FORGED', 402, 403, 1),
                    (66, 'QA-PRIVATE-CODE-INACTIVE', 601, 602, 2)
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO t_deep_question
                    (id, week_number, question_text, question_type, options,
                     category, sort_order, is_active)
                VALUES
                    (1, 1, 'qa-private-question-one', 'open', NULL,
                     'relationship', 10, 1),
                    (2, 1, 'qa-private-question-choice', 'choice',
                     '["qa-private-option-alpha", "qa-private-option-beta"]',
                     'future', 20, 1),
                    (3, 1, 'qa-private-question-inactive', 'open', NULL,
                     'values', 15, 0),
                    (4, 2, 'qa-private-question-malformed', 'choice',
                     '["qa-private-broken"', 'values', 10, 1),
                    (5, 2, 'qa-private-question-non-string', 'choice',
                     '["qa-private-valid", 7]', 'dreams', 20, 1),
                    (6, 3, 'qa-private-question-null-options', 'open', NULL,
                     'unknown-category', 10, 1)
                """
            )
        )


@dataclass(frozen=True)
class DeepQaContext:
    client: AsyncClient
    engine: AsyncEngine
    redis: RedisClient
    auth: dict[int, dict[str, str]]


@pytest.fixture
async def deep_qa_context(
    mysql_deep_qa_engine: AsyncEngine, redis_url: str
) -> AsyncIterator[DeepQaContext]:
    await _seed(mysql_deep_qa_engine)
    redis = RedisClient(redis_url)
    await redis.connect()
    await redis.raw.flushdb()
    factory = async_sessionmaker(mysql_deep_qa_engine, expire_on_commit=False)
    app = create_app(_settings())
    app.state.redis = redis

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as client:
            yield DeepQaContext(
                client=client,
                engine=mysql_deep_qa_engine,
                redis=redis,
                auth={
                    user_id: _headers(user_id)
                    for user_id in (101, 102, 201, 202, 301, 401, 601, 999)
                },
            )
    finally:
        await redis.close()


def _payload(response: Response, *, status: int = 200) -> dict[str, Any]:
    assert response.status_code == status, response.text
    value = cast(dict[str, Any], response.json())
    assert set(value) == {"code", "message", "data"}
    return value


async def _submit(context: DeepQaContext, user_id: int, question_id: int, answer: str) -> Response:
    return await context.client.post(
        "/api/deepQa/submit",
        headers=context.auth[user_id],
        json={"questionId": question_id, "answerText": answer},
    )


async def _reset_a(context: DeepQaContext, *, week: int = 1, question: int = 1) -> None:
    await _execute(
        context.engine,
        "DELETE FROM t_deep_qa_answer WHERE couple_id = 11; "
        "UPDATE t_couple_qa_progress SET current_week = :week, current_question = :question, "
        "total_completed = 0 WHERE couple_id = 11",
        week=week,
        question=question,
    )


@pytest.mark.integration
async def test_auth_failures_and_blacklist_do_not_mutate_deep_qa_state(
    deep_qa_context: DeepQaContext,
) -> None:
    context = deep_qa_context
    valid_token = _token(101)
    claims = decode_access_token(valid_token, SECRET)
    await context.redis.raw.setex(logout_blacklist_key(claims.jti), 300, "1")
    requests = [
        context.client.get("/api/deepQa/current"),
        context.client.get(
            "/api/deepQa/current", headers={"Authorization": "Bearer malformed.jwt.value"}
        ),
        context.client.get(
            "/api/deepQa/current",
            headers={"Authorization": f"Bearer {_token(101, expiration_ms=-1)}"},
        ),
        context.client.get(
            "/api/deepQa/current", headers={"Authorization": f"Bearer {valid_token}"}
        ),
    ]
    responses = await asyncio.gather(*requests)
    assert all(response.status_code == 401 for response in responses)
    assert all(response.json()["code"] == 401 for response in responses)
    assert await _rows(context.engine, "SELECT id FROM t_couple_qa_progress") == []
    assert await _rows(context.engine, "SELECT id FROM t_deep_qa_answer") == []


@pytest.mark.integration
async def test_current_concurrency_week_options_context_and_redacted_logs(
    deep_qa_context: DeepQaContext,
) -> None:
    context = deep_qa_context
    await _execute(
        context.engine,
        """
        INSERT INTO t_deep_qa_answer
            (couple_id, question_id, user_id, answer_text, is_revealed, reveal_time)
        VALUES (22, 1, 201, 'qa-private-foreign-answer-one', 1, NOW()),
               (22, 1, 202, 'qa-private-foreign-answer-two', 1, NOW())
        """,
    )
    with capture_logs() as logs:
        current_responses = await asyncio.gather(
            *[
                context.client.get("/api/deepQa/current", headers=context.auth[101])
                for _ in range(6)
            ]
        )
        week_one = _payload(
            await context.client.get("/api/deepQa/week/1", headers=context.auth[101])
        )["data"]
        week_two = _payload(
            await context.client.get("/api/deepQa/week/2", headers=context.auth[101])
        )["data"]
        empty_week = _payload(
            await context.client.get("/api/deepQa/week/99", headers=context.auth[101])
        )["data"]
    assert all(_payload(response)["data"]["id"] == 1 for response in current_responses)
    assert await _rows(
        context.engine,
        "SELECT couple_id, current_week, current_question, total_completed "
        "FROM t_couple_qa_progress",
    ) == [{"couple_id": 11, "current_week": 1, "current_question": 1, "total_completed": 0}]
    assert [item["id"] for item in week_one] == [1, 2]
    assert week_one[0]["options"] == []
    assert week_one[1]["options"] == ["qa-private-option-alpha", "qa-private-option-beta"]
    assert [item["options"] for item in week_two] == [[], []]
    assert empty_week == []
    assert all(item["myAnswer"] is None and item["partnerAnswer"] is None for item in week_one)
    deep_logs = [entry for entry in logs if entry.get("module") == "deep_qa"]
    assert deep_logs
    assert all(
        {"requestId", "module", "operation", "result", "durationMs", "errorCode"} <= set(entry)
        for entry in deep_logs
    )
    serialized_logs = str(logs)
    for private_value in (
        "qa-private-question-one",
        "qa-private-question-malformed",
        "qa-private-option-alpha",
        "qa-private-name-one",
        "https://avatar.invalid/qa-private-one",
        "qa-private-foreign-answer-one",
        "QA-PRIVATE-CODE-A",
        context.auth[101]["Authorization"],
    ):
        assert private_value not in serialized_logs

    week_only_context = await _rows(
        context.engine, "SELECT couple_id FROM t_couple_qa_progress ORDER BY couple_id"
    )
    assert week_only_context == [{"couple_id": 11}]
    for user_id, code in ((999, 1001), (301, 2006), (401, 2006), (601, 2006)):
        response = await context.client.get("/api/deepQa/week/1", headers=context.auth[user_id])
        assert _payload(response)["code"] == code


@pytest.mark.integration
async def test_submit_privacy_reveal_idempotency_progress_and_history(
    deep_qa_context: DeepQaContext,
) -> None:
    context = deep_qa_context
    assert (
        _payload(await context.client.get("/api/deepQa/current", headers=context.auth[101]))[
            "data"
        ]["id"]
        == 1
    )
    first_answer = "qa-private-answer-one"
    second_answer = "qa-private-answer-two"
    first_submit = _payload(await _submit(context, 101, 1, f"  {first_answer}  "))
    assert first_submit == {"code": 200, "message": "答案提交成功", "data": None}
    assert await _rows(
        context.engine,
        "SELECT answer_text, is_revealed FROM t_deep_qa_answer WHERE couple_id = 11",
    ) == [{"answer_text": first_answer, "is_revealed": 0}]
    assert _payload(await context.client.get("/api/deepQa/progress", headers=context.auth[101]))[
        "data"
    ] == {"currentWeek": 1, "currentQuestion": 1, "totalCompleted": 0, "totalQuestions": 5}

    mine = _payload(await context.client.get("/api/deepQa/current", headers=context.auth[101]))[
        "data"
    ]
    partner = _payload(await context.client.get("/api/deepQa/current", headers=context.auth[102]))[
        "data"
    ]
    assert mine["myAnswer"]["answerText"] == first_answer
    assert mine["partnerAnswer"] is None and mine["isRevealed"] is False
    assert partner["myAnswer"] is None and partner["partnerAnswer"] is None
    assert first_answer not in str(partner)

    duplicate = _payload(await _submit(context, 101, 1, "must-not-overwrite"))
    assert (duplicate["code"], duplicate["message"]) == (9001, "该问题已回答过")
    assert _payload(await _submit(context, 102, 1, second_answer))["code"] == 200
    before_reveal = _payload(
        await context.client.get("/api/deepQa/current", headers=context.auth[101])
    )["data"]
    assert before_reveal["partnerAnswer"] is None and before_reveal["isRevealed"] is False

    revealed = _payload(
        await context.client.post("/api/deepQa/reveal/1", headers=context.auth[101])
    )["data"]
    assert revealed["myAnswer"]["answerText"] == first_answer
    assert revealed["partnerAnswer"]["answerText"] == second_answer
    assert revealed["isRevealed"] is True
    reveal_rows = await _rows(
        context.engine,
        "SELECT user_id, is_revealed, reveal_time FROM t_deep_qa_answer "
        "WHERE couple_id = 11 ORDER BY user_id",
    )
    assert [row["is_revealed"] for row in reveal_rows] == [1, 1]
    assert reveal_rows[0]["reveal_time"] == reveal_rows[1]["reveal_time"]
    progress = await _rows(
        context.engine,
        "SELECT current_week, current_question, total_completed "
        "FROM t_couple_qa_progress WHERE couple_id = 11",
    )
    assert progress == [{"current_week": 1, "current_question": 2, "total_completed": 1}]

    repeated = await asyncio.gather(
        *[
            context.client.post(
                "/api/deepQa/reveal/1", headers=context.auth[101 if index % 2 == 0 else 102]
            )
            for index in range(6)
        ]
    )
    assert all(_payload(response)["code"] == 200 for response in repeated)
    assert (
        await _rows(
            context.engine,
            "SELECT current_week, current_question, total_completed "
            "FROM t_couple_qa_progress WHERE couple_id = 11",
        )
        == progress
    )
    assert await _rows(
        context.engine,
        "SELECT reveal_time FROM t_deep_qa_answer WHERE couple_id = 11 ORDER BY user_id",
    ) == [
        {"reveal_time": reveal_rows[0]["reveal_time"]},
        {"reveal_time": reveal_rows[0]["reveal_time"]},
    ]
    history_a = _payload(
        await context.client.get("/api/deepQa/history", headers=context.auth[101])
    )["data"]
    history_b = _payload(
        await context.client.get("/api/deepQa/history", headers=context.auth[102])
    )["data"]
    assert len(history_a) == len(history_b) == 1
    assert history_a[0]["myAnswer"]["answerText"] == first_answer
    assert history_b[0]["myAnswer"]["answerText"] == second_answer
    assert (
        _payload(await context.client.get("/api/deepQa/current", headers=context.auth[101]))[
            "data"
        ]["id"]
        == 2
    )


@pytest.mark.integration
async def test_submit_and_skip_are_serialized_under_concurrency(
    deep_qa_context: DeepQaContext,
) -> None:
    context = deep_qa_context
    await context.client.get("/api/deepQa/current", headers=context.auth[101])
    same_user = await asyncio.gather(
        *[_submit(context, 101, 1, f"qa-concurrent-answer-{index}") for index in range(10)]
    )
    codes = [_payload(response)["code"] for response in same_user]
    assert codes.count(200) == 1 and codes.count(9001) == 9
    assert await _rows(
        context.engine,
        "SELECT COUNT(*) AS count FROM t_deep_qa_answer WHERE couple_id = 11",
    ) == [{"count": 1}]

    await _reset_a(context)
    both = await asyncio.gather(
        _submit(context, 101, 1, "qa-simultaneous-one"),
        _submit(context, 102, 1, "qa-simultaneous-two"),
    )
    assert [_payload(response)["code"] for response in both].count(200) == 2
    assert await _rows(
        context.engine,
        "SELECT user_id FROM t_deep_qa_answer WHERE couple_id = 11 ORDER BY user_id",
    ) == [{"user_id": 101}, {"user_id": 102}]
    assert await _rows(
        context.engine,
        "SELECT current_week, current_question, total_completed "
        "FROM t_couple_qa_progress WHERE couple_id = 11",
    ) == [{"current_week": 1, "current_question": 1, "total_completed": 0}]

    await _reset_a(context)
    submit_response, skip_response = await asyncio.gather(
        _submit(context, 101, 1, "qa-submit-versus-skip"),
        context.client.post("/api/deepQa/skip", headers=context.auth[102]),
    )
    submit_code = _payload(submit_response)["code"]
    skip_code = _payload(skip_response)["code"]
    assert sorted((submit_code, skip_code)) == [200, 9001]
    answer_count = (
        await _rows(
            context.engine, "SELECT COUNT(*) AS count FROM t_deep_qa_answer WHERE couple_id = 11"
        )
    )[0]["count"]
    progress = (
        await _rows(
            context.engine,
            "SELECT current_question, total_completed "
            "FROM t_couple_qa_progress WHERE couple_id = 11",
        )
    )[0]
    assert (answer_count, progress["current_question"]) in {(1, 1), (0, 2)}
    assert progress["total_completed"] == 0
    if answer_count == 1:
        blocked = _payload(await context.client.post("/api/deepQa/skip", headers=context.auth[102]))
        assert (blocked["code"], blocked["message"]) == (
            9001,
            "当前问题已有回答，不能跳过",
        )


@pytest.mark.integration
async def test_reveal_requires_both_answers_and_crosses_week_and_terminal_boundaries(
    deep_qa_context: DeepQaContext,
) -> None:
    context = deep_qa_context
    await context.client.get("/api/deepQa/current", headers=context.auth[101])
    await _submit(context, 101, 1, "qa-only-one-answer")
    rejected = _payload(
        await context.client.post("/api/deepQa/reveal/1", headers=context.auth[101])
    )
    assert (rejected["code"], rejected["message"]) == (9001, "双方都回答后才能揭晓")
    assert await _rows(
        context.engine,
        "SELECT is_revealed, reveal_time FROM t_deep_qa_answer WHERE couple_id = 11",
    ) == [{"is_revealed": 0, "reveal_time": None}]
    missing = _payload(
        await context.client.post("/api/deepQa/reveal/999", headers=context.auth[101])
    )
    assert (missing["code"], missing["message"]) == (9001, "问题不存在")

    await _reset_a(context, question=2)
    await _submit(context, 101, 2, "qa-week-edge-one")
    await _submit(context, 102, 2, "qa-week-edge-two")
    assert (
        _payload(await context.client.post("/api/deepQa/reveal/2", headers=context.auth[101]))[
            "code"
        ]
        == 200
    )
    assert await _rows(
        context.engine,
        "SELECT current_week, current_question, total_completed "
        "FROM t_couple_qa_progress WHERE couple_id = 11",
    ) == [{"current_week": 2, "current_question": 1, "total_completed": 1}]

    await _reset_a(context, week=3)
    await _submit(context, 101, 6, "qa-terminal-one")
    await _submit(context, 102, 6, "qa-terminal-two")
    await context.client.post("/api/deepQa/reveal/6", headers=context.auth[101])
    terminal = _payload(
        await context.client.get("/api/deepQa/progress", headers=context.auth[102])
    )["data"]
    assert terminal == {
        "currentWeek": 4,
        "currentQuestion": 1,
        "totalCompleted": 1,
        "totalQuestions": 5,
    }
    assert (
        _payload(await context.client.get("/api/deepQa/current", headers=context.auth[101]))["data"]
        is None
    )
    before = await _rows(
        context.engine,
        "SELECT current_week, current_question, total_completed "
        "FROM t_couple_qa_progress WHERE couple_id = 11",
    )
    assert (
        _payload(await context.client.post("/api/deepQa/skip", headers=context.auth[101]))["code"]
        == 200
    )
    assert (
        await _rows(
            context.engine,
            "SELECT current_week, current_question, total_completed "
            "FROM t_couple_qa_progress WHERE couple_id = 11",
        )
        == before
    )


@pytest.mark.integration
async def test_skip_traverses_active_questions_without_incrementing_completed(
    deep_qa_context: DeepQaContext,
) -> None:
    context = deep_qa_context
    await context.client.get("/api/deepQa/progress", headers=context.auth[101])
    expected = [(1, 2), (2, 1), (2, 2), (3, 1), (4, 1)]
    for week, question in expected:
        response = _payload(
            await context.client.post("/api/deepQa/skip", headers=context.auth[101])
        )
        assert response == {"code": 200, "message": "操作成功", "data": None}
        row = (
            await _rows(
                context.engine,
                "SELECT current_week, current_question, total_completed "
                "FROM t_couple_qa_progress WHERE couple_id = 11",
            )
        )[0]
        assert (row["current_week"], row["current_question"]) == (week, question)
        assert row["total_completed"] == 0
    assert await _rows(context.engine, "SELECT id FROM t_deep_qa_answer WHERE couple_id = 11") == []


@pytest.mark.integration
async def test_history_is_unique_limited_ordered_and_couple_scoped(
    deep_qa_context: DeepQaContext,
) -> None:
    context = deep_qa_context
    await _execute(
        context.engine,
        """
        INSERT INTO t_deep_qa_answer
            (couple_id, question_id, user_id, answer_text, is_revealed, reveal_time)
        VALUES
            (11, 1, 101, 'qa-history-a1', 1, '2026-07-20 10:00:00'),
            (11, 1, 102, 'qa-history-a2', 1, '2026-07-20 10:00:00'),
            (11, 2, 101, 'qa-history-b1', 1, '2026-07-21 10:00:00'),
            (11, 2, 102, 'qa-history-b2', 1, '2026-07-21 10:00:00'),
            (11, 4, 101, 'qa-history-c1', 1, '2026-07-21 10:00:00'),
            (11, 4, 102, 'qa-history-c2', 1, '2026-07-21 10:00:00'),
            (22, 1, 201, 'qa-history-foreign-one', 1, '2026-07-22 10:00:00'),
            (22, 1, 202, 'qa-history-foreign-two', 1, '2026-07-22 10:00:00')
        """,
    )
    assert await _rows(context.engine, "SELECT id FROM t_couple_qa_progress") == []
    limited = _payload(
        await context.client.get("/api/deepQa/history?limit=2", headers=context.auth[101])
    )["data"]
    assert [item["id"] for item in limited] == [4, 2]
    assert len({item["id"] for item in limited}) == 2
    assert limited[0]["myAnswer"]["answerText"] == "qa-history-c1"
    assert limited[0]["partnerAnswer"]["answerText"] == "qa-history-c2"
    assert "qa-history-foreign" not in str(limited)
    assert await _rows(context.engine, "SELECT id FROM t_couple_qa_progress") == []
    assert (
        len(
            _payload(
                await context.client.get("/api/deepQa/history?limit=100", headers=context.auth[102])
            )["data"]
        )
        == 3
    )


@pytest.mark.integration
async def test_empty_or_deactivated_current_question_has_defined_read_and_write_behavior(
    deep_qa_context: DeepQaContext,
) -> None:
    context = deep_qa_context
    await _execute(context.engine, "DELETE FROM t_deep_question")
    assert (
        _payload(await context.client.get("/api/deepQa/current", headers=context.auth[101]))["data"]
        is None
    )
    assert (
        _payload(await context.client.get("/api/deepQa/progress", headers=context.auth[101]))[
            "data"
        ]["totalQuestions"]
        == 0
    )
    assert await _rows(context.engine, "SELECT COUNT(*) AS count FROM t_deep_question") == [
        {"count": 0}
    ]

    await _execute(
        context.engine,
        "INSERT INTO t_deep_question "
        "(id, week_number, question_text, question_type, sort_order, is_active) "
        "VALUES (1, 1, 'qa-deactivated-question', 'open', 10, 0)",
    )
    assert (
        _payload(await context.client.get("/api/deepQa/current", headers=context.auth[101]))["data"]
        is None
    )
    invalid_submit = _payload(await _submit(context, 101, 1, "qa-must-not-persist"))
    invalid_skip = _payload(
        await context.client.post("/api/deepQa/skip", headers=context.auth[101])
    )
    assert (invalid_submit["code"], invalid_submit["message"]) == (
        9001,
        "当前问题无效，请刷新后重试",
    )
    assert (invalid_skip["code"], invalid_skip["message"]) == (
        9001,
        "当前问题无效，请刷新后重试",
    )
    assert await _rows(context.engine, "SELECT id FROM t_deep_qa_answer") == []


@pytest.mark.integration
async def test_transaction_failures_roll_back_submit_reveal_and_progress(
    deep_qa_context: DeepQaContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = deep_qa_context
    await context.client.get("/api/deepQa/current", headers=context.auth[101])
    original_flush = AsyncSession.flush

    async def fail_after_answer_flush(session: AsyncSession, objects: Any = None) -> None:
        has_answer = any(isinstance(item, DeepQaAnswer) for item in session.new)
        await original_flush(session, objects)
        if has_answer:
            raise RuntimeError("injected submit failure")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "flush", fail_after_answer_flush)
        failed_submit = await _submit(context, 101, 1, "qa-rollback-submit-answer")
    assert failed_submit.status_code == 500
    assert await _rows(context.engine, "SELECT id FROM t_deep_qa_answer WHERE couple_id = 11") == []
    assert await _rows(
        context.engine,
        "SELECT current_question, total_completed FROM t_couple_qa_progress WHERE couple_id = 11",
    ) == [{"current_question": 1, "total_completed": 0}]

    await _execute(
        context.engine,
        """
        INSERT INTO t_deep_qa_answer
            (couple_id, question_id, user_id, answer_text, is_revealed)
        VALUES (11, 1, 101, 'qa-rollback-reveal-one', 0),
               (11, 1, 102, 'qa-rollback-reveal-two', 0)
        """,
    )

    async def fail_after_reveal_flush(session: AsyncSession, objects: Any = None) -> None:
        has_revealed_answer = any(
            isinstance(item, DeepQaAnswer) and item.is_revealed == 1 for item in session.dirty
        )
        await original_flush(session, objects)
        if has_revealed_answer:
            raise RuntimeError("injected reveal failure")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "flush", fail_after_reveal_flush)
        failed_reveal = await context.client.post("/api/deepQa/reveal/1", headers=context.auth[101])
    assert failed_reveal.status_code == 500
    assert await _rows(
        context.engine,
        "SELECT is_revealed, reveal_time FROM t_deep_qa_answer "
        "WHERE couple_id = 11 ORDER BY user_id",
    ) == [
        {"is_revealed": 0, "reveal_time": None},
        {"is_revealed": 0, "reveal_time": None},
    ]

    async def fail_after_progress_flush(session: AsyncSession, objects: Any = None) -> None:
        has_progress = any(isinstance(item, CoupleQaProgress) for item in session.dirty)
        await original_flush(session, objects)
        if has_progress:
            raise RuntimeError("injected progress failure")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "flush", fail_after_progress_flush)
        failed_progress = await context.client.post(
            "/api/deepQa/reveal/1", headers=context.auth[101]
        )
    assert failed_progress.status_code == 500
    assert await _rows(
        context.engine,
        "SELECT is_revealed, reveal_time FROM t_deep_qa_answer "
        "WHERE couple_id = 11 ORDER BY user_id",
    ) == [
        {"is_revealed": 0, "reveal_time": None},
        {"is_revealed": 0, "reveal_time": None},
    ]
    assert await _rows(
        context.engine,
        "SELECT current_week, current_question, total_completed "
        "FROM t_couple_qa_progress WHERE couple_id = 11",
    ) == [{"current_week": 1, "current_question": 1, "total_completed": 0}]


@pytest.mark.integration
async def test_answer_length_boundaries_trim_and_non_current_rejection(
    deep_qa_context: DeepQaContext,
) -> None:
    context = deep_qa_context
    await context.client.get("/api/deepQa/current", headers=context.auth[101])
    assert _payload(await _submit(context, 101, 2, "qa-non-current"))["code"] == 9001
    assert _payload(await _submit(context, 101, 1, " 字 "))["code"] == 200
    assert await _rows(
        context.engine,
        "SELECT answer_text FROM t_deep_qa_answer WHERE couple_id = 11 AND user_id = 101",
    ) == [{"answer_text": "字"}]
    await _execute(context.engine, "DELETE FROM t_deep_qa_answer WHERE couple_id = 11")
    exact_limit = "界" * 5000
    assert _payload(await _submit(context, 101, 1, exact_limit))["code"] == 200
    row = await _rows(
        context.engine,
        "SELECT CHAR_LENGTH(answer_text) AS answer_length FROM t_deep_qa_answer "
        "WHERE couple_id = 11 AND user_id = 101",
    )
    assert row == [{"answer_length": 5000}]
