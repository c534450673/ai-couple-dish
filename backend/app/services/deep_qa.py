"""情侣深度问答 FastAPI shadow 服务。"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Never

import structlog
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Couple, CoupleQaProgress, DeepQaAnswer, DeepQuestion, User

logger = structlog.get_logger()

_CATEGORY_NAMES = {
    "relationship": "感情",
    "future": "未来",
    "values": "价值观",
    "dreams": "梦想",
}


@dataclass(frozen=True)
class _CoupleContext:
    couple_id: int
    user_id: int
    user1_id: int
    user2_id: int

    @property
    def partner_id(self) -> int:
        return self.user2_id if self.user_id == self.user1_id else self.user1_id

    @property
    def member_ids(self) -> set[int]:
        return {self.user1_id, self.user2_id}


def _fields(
    request: Request,
    operation: str,
    result: str,
    started: float,
    error_code: str = "NONE",
) -> dict[str, object]:
    return {
        "requestId": getattr(request.state, "request_id", "unknown"),
        "module": "deep_qa",
        "operation": operation,
        "result": result,
        "durationMs": round((perf_counter() - started) * 1000),
        "errorCode": error_code,
    }


async def _completed(request: Request, operation: str, result: str, started: float) -> None:
    await logger.ainfo(
        "business_operation_completed",
        **_fields(request, operation, result, started),
    )


async def _reject(
    request: Request,
    session: AsyncSession,
    operation: str,
    started: float,
    code: int,
    message: str,
) -> Never:
    await session.rollback()
    await logger.awarning(
        "business_operation_rejected",
        **_fields(request, operation, "rejected", started, str(code)),
    )
    raise BusinessError(code, message)


async def _unexpected(
    request: Request,
    session: AsyncSession,
    operation: str,
    started: float,
    error: Exception,
) -> None:
    await session.rollback()
    await logger.aerror(
        "business_operation_failed",
        **_fields(request, operation, "error", started, type(error).__name__),
    )


async def _couple_context(
    request: Request,
    session: AsyncSession,
    user_id: int,
    operation: str,
    started: float,
    *,
    lock: bool,
) -> _CoupleContext:
    user = await session.scalar(select(User).where(User.id == user_id, User.is_deleted == 0))
    if user is None:
        await _reject(request, session, operation, started, 1001, "用户不存在")
    if user.couple_id is None:
        await _reject(request, session, operation, started, 2006, "未绑定情侣关系")
    statement = select(Couple).where(Couple.id == user.couple_id, Couple.status == 1)
    if lock:
        statement = statement.with_for_update()
    couple = await session.scalar(statement)
    if (
        couple is None
        or couple.user2_id is None
        or user.id not in {couple.user1_id, couple.user2_id}
    ):
        await _reject(request, session, operation, started, 2006, "未绑定情侣关系")
    return _CoupleContext(
        couple_id=couple.id,
        user_id=user.id,
        user1_id=couple.user1_id,
        user2_id=couple.user2_id,
    )


async def _get_or_create_progress(
    session: AsyncSession, couple_id: int
) -> tuple[CoupleQaProgress, bool]:
    progress = await session.scalar(
        select(CoupleQaProgress).where(CoupleQaProgress.couple_id == couple_id).with_for_update()
    )
    if progress is not None:
        return progress, False
    progress = CoupleQaProgress(
        couple_id=couple_id,
        current_week=1,
        current_question=1,
        total_completed=0,
    )
    session.add(progress)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        await session.scalar(select(Couple).where(Couple.id == couple_id).with_for_update())
        winner = await session.scalar(
            select(CoupleQaProgress)
            .where(CoupleQaProgress.couple_id == couple_id)
            .with_for_update()
        )
        if winner is None:
            raise
        return winner, False
    return progress, True


async def _current_question(
    session: AsyncSession, progress: CoupleQaProgress
) -> DeepQuestion | None:
    question: DeepQuestion | None = await session.scalar(
        select(DeepQuestion)
        .where(
            DeepQuestion.week_number == progress.current_week,
            DeepQuestion.is_active == 1,
        )
        .order_by(DeepQuestion.sort_order.asc(), DeepQuestion.id.asc())
        .offset(progress.current_question - 1)
        .limit(1)
    )
    return question


async def _advance_progress(session: AsyncSession, progress: CoupleQaProgress) -> None:
    next_in_week = await session.scalar(
        select(DeepQuestion.id)
        .where(
            DeepQuestion.week_number == progress.current_week,
            DeepQuestion.is_active == 1,
        )
        .order_by(DeepQuestion.sort_order.asc(), DeepQuestion.id.asc())
        .offset(progress.current_question)
        .limit(1)
    )
    if next_in_week is not None:
        progress.current_question += 1
        return
    next_week = await session.scalar(
        select(func.min(DeepQuestion.week_number)).where(
            DeepQuestion.week_number > progress.current_week,
            DeepQuestion.is_active == 1,
        )
    )
    if next_week is not None:
        progress.current_week = int(next_week)
        progress.current_question = 1
        return
    last_week = await session.scalar(
        select(func.max(DeepQuestion.week_number)).where(DeepQuestion.is_active == 1)
    )
    if last_week is not None:
        progress.current_week = int(last_week) + 1
        progress.current_question = 1


async def _is_terminal(session: AsyncSession, progress: CoupleQaProgress) -> bool:
    last_week = await session.scalar(
        select(func.max(DeepQuestion.week_number)).where(DeepQuestion.is_active == 1)
    )
    return (
        last_week is not None
        and progress.current_week == int(last_week) + 1
        and progress.current_question == 1
    )


async def _parse_options(request: Request, value: str | None) -> list[str]:
    if value is None or not value.strip():
        return []
    started = perf_counter()
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        parsed = None
    if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
        await logger.awarning(
            "deep_qa_options_rejected",
            **_fields(
                request,
                "parse_options",
                "rejected",
                started,
                "INVALID_QUESTION_OPTIONS",
            ),
        )
        return []
    return parsed


def _answer_payload(answer: DeepQaAnswer, user: User | None) -> dict[str, object | None]:
    return {
        "id": answer.id,
        "userId": answer.user_id,
        "userName": user.nick_name if user is not None else None,
        "userAvatar": user.avatar_url if user is not None else None,
        "answerText": answer.answer_text,
        "createTime": answer.create_time.isoformat() if answer.create_time else None,
    }


async def _question_payload(
    request: Request,
    session: AsyncSession,
    context: _CoupleContext,
    question: DeepQuestion,
) -> dict[str, object | None]:
    answers = list(
        (
            await session.scalars(
                select(DeepQaAnswer)
                .where(
                    DeepQaAnswer.couple_id == context.couple_id,
                    DeepQaAnswer.question_id == question.id,
                )
                .order_by(DeepQaAnswer.id.asc())
            )
        ).all()
    )
    user_rows: list[User] = []
    answer_user_ids = {answer.user_id for answer in answers}
    if answer_user_ids:
        user_rows = list(
            (await session.scalars(select(User).where(User.id.in_(answer_user_ids)))).all()
        )
    users = {user.id: user for user in user_rows}
    answer_by_user = {answer.user_id: answer for answer in answers}
    fully_revealed = (
        len(answers) == 2
        and set(answer_by_user) == context.member_ids
        and all(answer.is_revealed == 1 for answer in answers)
    )
    my_answer = answer_by_user.get(context.user_id)
    partner_answer = answer_by_user.get(context.partner_id) if fully_revealed else None
    return {
        "id": question.id,
        "weekNumber": question.week_number,
        "questionText": question.question_text,
        "questionType": question.question_type,
        "options": await _parse_options(request, question.options),
        "category": question.category,
        "categoryName": _CATEGORY_NAMES.get(question.category, question.category),
        "myAnswer": _answer_payload(my_answer, users.get(my_answer.user_id))
        if my_answer is not None
        else None,
        "partnerAnswer": _answer_payload(partner_answer, users.get(partner_answer.user_id))
        if partner_answer is not None
        else None,
        "isRevealed": fully_revealed,
        "progress": None,
    }


async def current(
    request: Request, session: AsyncSession, user_id: int
) -> dict[str, object | None] | None:
    started = perf_counter()
    operation = "current"
    try:
        context = await _couple_context(request, session, user_id, operation, started, lock=True)
        progress_row, created = await _get_or_create_progress(session, context.couple_id)
        question = await _current_question(session, progress_row)
        result = (
            await _question_payload(request, session, context, question)
            if question is not None
            else None
        )
        await session.commit()
    except BusinessError:
        raise
    except Exception as error:
        await _unexpected(request, session, operation, started, error)
        raise
    await _completed(request, operation, "created" if created else "success", started)
    return result


async def week(
    request: Request,
    session: AsyncSession,
    user_id: int,
    week_number: int,
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "week"
    try:
        context = await _couple_context(request, session, user_id, operation, started, lock=False)
        questions = list(
            (
                await session.scalars(
                    select(DeepQuestion)
                    .where(
                        DeepQuestion.week_number == week_number,
                        DeepQuestion.is_active == 1,
                    )
                    .order_by(DeepQuestion.sort_order.asc(), DeepQuestion.id.asc())
                )
            ).all()
        )
        result = [
            await _question_payload(request, session, context, question) for question in questions
        ]
    except BusinessError:
        raise
    except Exception as error:
        await _unexpected(request, session, operation, started, error)
        raise
    await _completed(request, operation, "success", started)
    return result


async def submit(
    request: Request,
    session: AsyncSession,
    user_id: int,
    question_id: int,
    answer_text: str,
) -> None:
    started = perf_counter()
    operation = "submit"
    try:
        context = await _couple_context(request, session, user_id, operation, started, lock=True)
        progress_row, _ = await _get_or_create_progress(session, context.couple_id)
        question = await _current_question(session, progress_row)
        if question is None or question.id != question_id:
            await _reject(
                request,
                session,
                operation,
                started,
                9001,
                "当前问题无效，请刷新后重试",
            )
        existing = await session.scalar(
            select(DeepQaAnswer.id)
            .where(
                DeepQaAnswer.couple_id == context.couple_id,
                DeepQaAnswer.question_id == question_id,
                DeepQaAnswer.user_id == context.user_id,
            )
            .with_for_update()
        )
        if existing is not None:
            await _reject(request, session, operation, started, 9001, "该问题已回答过")
        session.add(
            DeepQaAnswer(
                couple_id=context.couple_id,
                question_id=question_id,
                user_id=context.user_id,
                answer_text=answer_text,
                is_revealed=0,
            )
        )
        await session.flush()
        await session.commit()
    except BusinessError:
        raise
    except Exception as error:
        await _unexpected(request, session, operation, started, error)
        raise
    await _completed(request, operation, "success", started)


async def reveal(
    request: Request,
    session: AsyncSession,
    user_id: int,
    question_id: int,
) -> dict[str, object | None]:
    started = perf_counter()
    operation = "reveal"
    result_type = "success"
    try:
        context = await _couple_context(request, session, user_id, operation, started, lock=True)
        progress_row, _ = await _get_or_create_progress(session, context.couple_id)
        question = await session.scalar(select(DeepQuestion).where(DeepQuestion.id == question_id))
        if question is None:
            await _reject(request, session, operation, started, 9001, "问题不存在")
        answers = list(
            (
                await session.scalars(
                    select(DeepQaAnswer)
                    .where(
                        DeepQaAnswer.couple_id == context.couple_id,
                        DeepQaAnswer.question_id == question_id,
                    )
                    .order_by(DeepQaAnswer.user_id.asc(), DeepQaAnswer.id.asc())
                    .with_for_update()
                )
            ).all()
        )
        if len(answers) != 2 or {answer.user_id for answer in answers} != context.member_ids:
            await _reject(
                request,
                session,
                operation,
                started,
                9001,
                "双方都回答后才能揭晓",
            )
        if all(answer.is_revealed == 1 for answer in answers):
            result_type = "idempotent"
        else:
            reveal_time = datetime.now(UTC).replace(tzinfo=None)
            for answer in answers:
                answer.is_revealed = 1
                answer.reveal_time = reveal_time
            await session.flush()
            current_question = await _current_question(session, progress_row)
            if current_question is not None and current_question.id == question_id:
                await _advance_progress(session, progress_row)
                progress_row.total_completed += 1
                await session.flush()
        result = await _question_payload(request, session, context, question)
        await session.commit()
    except BusinessError:
        raise
    except Exception as error:
        await _unexpected(request, session, operation, started, error)
        raise
    await _completed(request, operation, result_type, started)
    return result


async def progress(request: Request, session: AsyncSession, user_id: int) -> dict[str, int]:
    started = perf_counter()
    operation = "progress"
    try:
        context = await _couple_context(request, session, user_id, operation, started, lock=True)
        progress_row, created = await _get_or_create_progress(session, context.couple_id)
        total_questions = int(
            (
                await session.scalar(
                    select(func.count(DeepQuestion.id)).where(DeepQuestion.is_active == 1)
                )
            )
            or 0
        )
        result = {
            "currentWeek": progress_row.current_week,
            "currentQuestion": progress_row.current_question,
            "totalCompleted": progress_row.total_completed,
            "totalQuestions": total_questions,
        }
        await session.commit()
    except BusinessError:
        raise
    except Exception as error:
        await _unexpected(request, session, operation, started, error)
        raise
    await _completed(request, operation, "created" if created else "success", started)
    return result


async def history(
    request: Request,
    session: AsyncSession,
    user_id: int,
    limit: int,
) -> list[dict[str, object | None]]:
    started = perf_counter()
    operation = "history"
    try:
        context = await _couple_context(request, session, user_id, operation, started, lock=False)
        reveal_order = func.max(DeepQaAnswer.reveal_time)
        rows = (
            await session.execute(
                select(DeepQaAnswer.question_id, reveal_order.label("last_reveal"))
                .where(
                    DeepQaAnswer.couple_id == context.couple_id,
                    DeepQaAnswer.is_revealed == 1,
                )
                .group_by(DeepQaAnswer.question_id)
                .order_by(reveal_order.desc(), DeepQaAnswer.question_id.desc())
                .limit(limit)
            )
        ).all()
        question_ids = [int(row.question_id) for row in rows]
        questions: dict[int, DeepQuestion] = {}
        if question_ids:
            question_rows = list(
                (
                    await session.scalars(
                        select(DeepQuestion).where(DeepQuestion.id.in_(question_ids))
                    )
                ).all()
            )
            questions = {question.id: question for question in question_rows}
        result = []
        for question_id in question_ids:
            question = questions.get(question_id)
            if question is None:
                continue
            payload = await _question_payload(request, session, context, question)
            if payload["isRevealed"]:
                result.append(payload)
    except BusinessError:
        raise
    except Exception as error:
        await _unexpected(request, session, operation, started, error)
        raise
    await _completed(request, operation, "success", started)
    return result


async def skip(request: Request, session: AsyncSession, user_id: int) -> None:
    started = perf_counter()
    operation = "skip"
    result_type = "success"
    try:
        context = await _couple_context(request, session, user_id, operation, started, lock=True)
        progress_row, _ = await _get_or_create_progress(session, context.couple_id)
        question = await _current_question(session, progress_row)
        if question is None:
            if await _is_terminal(session, progress_row):
                result_type = "idempotent"
                await session.commit()
            else:
                await _reject(
                    request,
                    session,
                    operation,
                    started,
                    9001,
                    "当前问题无效，请刷新后重试",
                )
        else:
            answer_exists = await session.scalar(
                select(DeepQaAnswer.id)
                .where(
                    DeepQaAnswer.couple_id == context.couple_id,
                    DeepQaAnswer.question_id == question.id,
                )
                .limit(1)
                .with_for_update()
            )
            if answer_exists is not None:
                await _reject(
                    request,
                    session,
                    operation,
                    started,
                    9001,
                    "当前问题已有回答，不能跳过",
                )
            await _advance_progress(session, progress_row)
            await session.commit()
    except BusinessError:
        raise
    except Exception as error:
        await _unexpected(request, session, operation, started, error)
        raise
    await _completed(request, operation, result_type, started)
