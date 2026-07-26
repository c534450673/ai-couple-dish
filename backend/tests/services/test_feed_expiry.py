from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.errors import BusinessError
from app.db.models import Feed
from app.services import feed


class FakeResult:
    def __init__(self, items: list[Feed]) -> None:
        self._items = items

    def scalars(self) -> "FakeResult":
        return self

    def all(self) -> list[Feed]:
        return self._items


class FakeSession:
    def __init__(self, items: list[Feed]) -> None:
        self.items = items
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, _statement: object) -> FakeResult:
        return FakeResult(self.items)

    def add(self, item: object) -> None:
        self.added.append(item)

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class RejectSession:
    def __init__(self, item: Feed) -> None:
        self.item = item
        self.added: list[object] = []
        self.commit_count = 0

    async def scalar(self, _statement: object) -> Feed:
        return self.item

    def add(self, value: object) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        self.commit_count += 1


async def test_expire_due_updates_only_expired_pending_feed_and_spring_notification() -> None:
    item = Feed(
        id=8,
        couple_id=1,
        sender_id=2,
        receiver_id=3,
        feed_type="meal",
        status=0,
        expire_time=datetime.now() - timedelta(seconds=1),
    )
    session = FakeSession([item])

    assert await feed.expire_due(session, "run") == 1
    notification = next(value for value in session.added if value is not item)
    assert item.status == 3
    assert (notification.user_id, notification.type, notification.title, notification.content) == (
        2,
        2,
        "⏰ 投喂已过期",
        "您发送的投喂已过期未被领取，下次记得提醒TA及时领取哦！",
    )
    assert (
        notification.related_id,
        notification.related_type,
        notification.sender_id,
        notification.is_read,
    ) == (8, "feed", None, 0)


@pytest.mark.parametrize("status", [1, 2, 3])
async def test_reject_does_not_overwrite_terminal_feed(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    now = datetime(2026, 7, 26, 12, 0, 0)
    item = Feed(
        id=9,
        couple_id=1,
        sender_id=2,
        receiver_id=3,
        feed_type="meal",
        status=status,
        expire_time=now + timedelta(hours=1),
    )
    session = RejectSession(item)
    request = SimpleNamespace(state=SimpleNamespace(request_id="reject-terminal"))
    monkeypatch.setattr(feed, "_business_now", lambda: now)
    monkeypatch.setattr(feed, "_user", AsyncMock(return_value=SimpleNamespace(id=3)))

    with pytest.raises(BusinessError) as error:
        await feed.reject(request, session, 3, 9, "changed-plan")

    assert error.value.code == 6003
    assert item.status == status
    assert session.added == []
    assert session.commit_count == 0


async def test_reject_expired_pending_feed_marks_expired_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 26, 12, 0, 0)
    item = Feed(
        id=10,
        couple_id=1,
        sender_id=2,
        receiver_id=3,
        feed_type="meal",
        status=0,
        expire_time=now - timedelta(seconds=1),
    )
    session = RejectSession(item)
    request = SimpleNamespace(state=SimpleNamespace(request_id="reject-expired"))
    monkeypatch.setattr(feed, "_business_now", lambda: now)
    monkeypatch.setattr(feed, "_user", AsyncMock(return_value=SimpleNamespace(id=3)))

    with pytest.raises(BusinessError) as error:
        await feed.reject(request, session, 3, 10, "changed-plan")

    assert error.value.code == 6003
    assert item.status == 3
    assert session.commit_count == 1
    notifications = [value for value in session.added if value is not item]
    assert len(notifications) == 1
    assert notifications[0].sender_id is None
