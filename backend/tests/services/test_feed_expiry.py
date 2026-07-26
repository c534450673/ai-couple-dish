from datetime import datetime, timedelta

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
