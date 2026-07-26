import asyncio
import io
import os
import re
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import uvicorn
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import Connection, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from structlog.testing import capture_logs

os.environ.setdefault("DB_PASSWORD", "db-secret")
os.environ.setdefault("JWT_SECRET", "x" * 64)

from app.core.config import Settings
from app.db.models import (
    Anniversary,
    CoupleMenu,
    Feed,
    FoodNote,
    PosterTemplate,
    User,
    UserPoster,
)
from app.db.session import get_session
from app.main import create_app
from app.redis.client import RedisClient
from app.services import poster as poster_service
from app.services import poster_renderer

SECRET = "p" * 64
POSTER_LOG_FIELDS = {
    "requestId",
    "module",
    "operation",
    "result",
    "durationMs",
    "errorCode",
    "event",
    "log_level",
}


def _reset_schema(connection: Connection) -> None:
    table_names = inspect(connection).get_table_names()
    quote = connection.dialect.identifier_preparer.quote
    connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
    try:
        for table_name in table_names:
            connection.exec_driver_sql(f"DROP TABLE {quote(table_name)}")
    finally:
        connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")


def _schema_statements() -> list[str]:
    schema_path = Path(__file__).parents[2] / "src" / "test" / "resources" / "schema-test.sql"
    source = schema_path.read_text(encoding="utf-8")
    mysql_source = re.sub(r"CREATE (UNIQUE )?INDEX IF NOT EXISTS", r"CREATE \1INDEX", source)
    return [statement.strip() for statement in mysql_source.split(";") if statement.strip()]


@pytest.fixture
async def mysql_poster_engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(mysql_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_reset_schema)
            for statement in _schema_statements():
                await connection.exec_driver_sql(statement)
        yield engine
    finally:
        await engine.dispose()


@asynccontextmanager
async def _running_uvicorn(app) -> AsyncIterator[str]:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = int(listener.getsockname()[1])
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        lifespan="off",
        access_log=False,
        log_config=None,
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        for _ in range(100):
            if server.started:
                break
            if task.done():
                await task
            await asyncio.sleep(0.02)
        assert server.started
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, timeout=10)
        listener.close()


async def _login(client: AsyncClient, code: str, nickname: str) -> dict[str, str]:
    response = await client.post("/api/user/login", json={"code": code, "nickName": nickname})
    assert response.json()["code"] == 200
    return {"Authorization": f"Bearer {response.json()['data']['token']}"}


async def _bind(client: AsyncClient, first: dict[str, str], second: dict[str, str]) -> None:
    code = (await client.post("/api/couple/generateCode", headers=first)).json()["data"]
    response = await client.post("/api/couple/bind", headers=second, json={"coupleCode": code})
    assert response.json()["code"] == 200


def _matching_files(root: Path, pattern: str) -> set[Path]:
    return set(root.rglob(pattern))


@pytest.mark.integration
async def test_poster_real_mysql_redis_filesystem_and_tcp_pixels(
    mysql_poster_engine: AsyncEngine,
    redis_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = RedisClient(redis_url)
    await redis.connect()
    session_factory = async_sessionmaker(mysql_poster_engine, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DB_PASSWORD="db-secret",  # noqa: S106
        JWT_SECRET=SECRET,
        FILE_UPLOAD_PATH=str(tmp_path),
        FILE_BASE_URL="/api/uploads",
        FILE_PUBLIC_PATH="/api/uploads",
        POSTER_RENDER_CONCURRENCY=2,
    )  # noqa: S106
    app = create_app(settings)
    app.state.redis = redis

    async def session_override() -> AsyncIterator[object]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    current_year = datetime.now(ZoneInfo("Asia/Shanghai")).year
    sentinel_title = "POSTER_PRIVATE_TITLE_SENTINEL"
    absolute_path_sentinel = str(await asyncio.to_thread(tmp_path.resolve))

    try:
        with capture_logs() as logs:
            async with _running_uvicorn(app) as base_url:
                async with AsyncClient(base_url=base_url, timeout=30) as client:
                    assert (await client.get("/api/poster/templates")).status_code == 401
                    first = await _login(client, "POSTER_OPENID_SENTINEL_ONE", "海报甲")
                    partner = await _login(client, "POSTER_OPENID_SENTINEL_TWO", "海报乙")
                    outsider = await _login(client, "POSTER_OPENID_SENTINEL_THREE", "海报丙")
                    outsider_partner = await _login(client, "POSTER_OPENID_SENTINEL_FOUR", "海报丁")
                    await _bind(client, first, partner)
                    await _bind(client, outsider, outsider_partner)

                    async with session_factory() as session:
                        users = (
                            (await session.execute(select(User).order_by(User.id.asc())))
                            .scalars()
                            .all()
                        )
                        first_user, partner_user, outsider_user, _ = users
                        assert first_user.couple_id is not None
                        assert outsider_user.couple_id != first_user.couple_id
                        templates = [
                            PosterTemplate(
                                template_code=f"poster-{poster_type}",
                                template_name=f"{poster_type}模板",
                                template_type=poster_type,
                                template_config=(
                                    '{"background":"#101525","surface":"#1A2034",'
                                    '"primary":"#FFB2B7","secondary":"#54E8D3",'
                                    '"text":"#F7F7FB"}'
                                ),
                                is_active=1,
                                create_time=datetime.now(),
                            )
                            for poster_type in ("anniversary", "feed", "map", "annual")
                        ]
                        inactive = PosterTemplate(
                            template_code="poster-inactive",
                            template_name="禁用模板",
                            template_type="annual",
                            template_config="{}",
                            is_active=0,
                            create_time=datetime.now(),
                        )
                        session.add_all([*templates, inactive])
                        await session.flush()
                        anniversary = Anniversary(
                            couple_id=first_user.couple_id,
                            creator_id=first_user.id,
                            name="相恋纪念日",
                            anniversary_date=date(current_year, 7, 26),
                            anniversary_type=2,
                            is_deleted=0,
                        )
                        feed = Feed(
                            couple_id=first_user.couple_id,
                            sender_id=first_user.id,
                            receiver_id=partner_user.id,
                            feed_type="dessert",
                            content="公开投喂文案",
                            message="一起吃甜品",
                            status=1,
                            expire_time=datetime.now() + timedelta(days=1),
                            create_time=datetime(current_year, 6, 1, 10, 0),
                        )
                        menu = CoupleMenu(
                            couple_id=first_user.couple_id,
                            creator_id=first_user.id,
                            restaurant_name="星河餐厅",
                            location="滨江路",
                            status=1,
                            is_favorite=1,
                            is_deleted=0,
                            eaten_date=date(current_year, 5, 2),
                        )
                        note = FoodNote(
                            couple_id=first_user.couple_id,
                            author_id=first_user.id,
                            title="年度记录",
                            content="不应进入海报正文的私密内容",
                            is_deleted=0,
                            create_time=datetime(current_year, 4, 1, 9, 0),
                        )
                        session.add_all([anniversary, feed, menu, note])
                        await session.commit()
                        template_ids = {item.template_type: item.id for item in templates}
                        inactive_id = inactive.id
                        anniversary_id = anniversary.id
                        feed_id = feed.id
                        menu_id = menu.id
                        first_user_id = first_user.id

                    source = tmp_path / "user" / str(first_user_id) / "source.png"
                    source.parent.mkdir(parents=True)
                    Image.new("RGB", (640, 400), "#54E8D3").save(source)
                    source_url = f"/api/uploads/user/{first_user_id}/source.png"

                    template_response = await client.get("/api/poster/templates", headers=first)
                    assert template_response.json()["code"] == 200
                    assert [item["id"] for item in template_response.json()["data"]] == list(
                        template_ids.values()
                    )
                    filtered = await client.get(
                        "/api/poster/templates",
                        headers=first,
                        params={"posterType": "annual"},
                    )
                    assert [item["templateType"] for item in filtered.json()["data"]] == ["annual"]
                    assert (
                        await client.post("/api/poster/generate", headers=first, json={})
                    ).json()["code"] == 9001
                    assert (
                        await client.post(
                            "/api/poster/generate",
                            headers=first,
                            json={
                                "posterType": "annual",
                                "templateId": template_ids["map"],
                            },
                        )
                    ).json()["code"] == 9001
                    assert (
                        await client.post(
                            "/api/poster/generate",
                            headers=first,
                            json={"templateId": inactive_id},
                        )
                    ).json()["code"] == 8902
                    assert (
                        await client.get("/api/poster/list", headers=first, params={"limit": 101})
                    ).json()["code"] == 9001

                    requests = [
                        {
                            "templateId": template_ids["anniversary"],
                            "relatedId": anniversary_id,
                            "customData": {
                                "title": sentinel_title,
                                "imageUrl": source_url,
                                "unknown": "accepted",
                            },
                        },
                        {"posterType": "feed", "relatedId": feed_id},
                        {
                            "posterType": "map",
                            "templateId": template_ids["map"],
                            "relatedId": menu_id,
                        },
                        {
                            "posterType": "annual",
                            "templateId": template_ids["annual"],
                            "relatedId": current_year,
                        },
                    ]
                    generated: list[dict[str, object]] = []
                    for payload in requests:
                        response = await client.post(
                            "/api/poster/generate", headers=first, json=payload
                        )
                        assert response.status_code == 200
                        assert response.json()["code"] == 200
                        assert response.json()["message"] == "海报生成成功"
                        generated.append(response.json()["data"])

                    assert [item["posterType"] for item in generated] == [
                        "anniversary",
                        "feed",
                        "map",
                        "annual",
                    ]
                    assert generated[0]["templateId"] == template_ids["anniversary"]
                    assert generated[1]["templateId"] == template_ids["feed"]
                    for item in generated:
                        download = await client.get(str(item["posterUrl"]))
                        assert download.status_code == 200
                        assert download.headers["content-type"] == "image/png"
                        assert download.headers["x-content-type-options"] == "nosniff"
                        assert download.content.startswith(b"\x89PNG\r\n\x1a\n")
                        with Image.open(io.BytesIO(download.content)) as image:
                            image.load()
                            assert image.format == "PNG"
                            assert image.size == (1080, 1440)
                            assert image.mode == "RGB"
                            assert len(image.getcolors(maxcolors=2_000_000) or []) > 100
                    annual_png = await client.get(str(generated[3]["posterUrl"]))
                    with Image.open(io.BytesIO(annual_png.content)) as image:
                        assert image.getpixel((10, 10)) == (16, 21, 37)
                        assert image.getpixel((80, 600)) == (26, 32, 52)

                    first_id = int(generated[0]["id"])
                    assert (
                        await client.get(f"/api/poster/detail/{first_id}", headers=outsider)
                    ).json()["code"] == 8903
                    assert (
                        await client.get(f"/api/poster/share/{first_id}", headers=outsider)
                    ).json()["code"] == 8903
                    assert (
                        await client.delete(f"/api/poster/delete/{first_id}", headers=outsider)
                    ).json()["code"] == 8903
                    own_list = await client.get("/api/poster/list", headers=first)
                    assert [item["id"] for item in own_list.json()["data"]] == sorted(
                        [int(item["id"]) for item in generated], reverse=True
                    )
                    assert (await client.get("/api/poster/list", headers=outsider)).json()[
                        "data"
                    ] == []

                    concurrent = await asyncio.gather(
                        *[
                            client.post(
                                "/api/poster/generate",
                                headers=first,
                                json={"posterType": "annual", "relatedId": current_year},
                            )
                            for _ in range(2)
                        ]
                    )
                    concurrent_data = [response.json()["data"] for response in concurrent]
                    assert concurrent_data[0]["id"] != concurrent_data[1]["id"]
                    assert concurrent_data[0]["posterUrl"] != concurrent_data[1]["posterUrl"]
                    concurrent_downloads = await asyncio.gather(
                        *[client.get(str(item["posterUrl"])) for item in concurrent_data]
                    )
                    assert all(response.status_code == 200 for response in concurrent_downloads)
                    assert not await asyncio.to_thread(_matching_files, tmp_path, "*.tmp")

                    deleted_url = str(generated[0]["posterUrl"])
                    assert (
                        await client.delete(f"/api/poster/delete/{first_id}", headers=first)
                    ).json()["code"] == 200
                    assert (await client.get(deleted_url)).status_code == 404
                    assert (
                        await client.delete(f"/api/poster/delete/{first_id}", headers=first)
                    ).json()["code"] == 200
                    assert (
                        await client.get(f"/api/poster/detail/{first_id}", headers=first)
                    ).json()["code"] == 8901

                    async with session_factory() as session:
                        before_count = int(
                            await session.scalar(select(func.count()).select_from(UserPoster)) or 0
                        )
                    before_files = await asyncio.to_thread(_matching_files, tmp_path, "*.png")
                    with monkeypatch.context() as patch:

                        def render_failure(**_kwargs):
                            raise poster_renderer.PosterRenderError

                        patch.setattr(poster_renderer, "render_and_publish", render_failure)
                        failed_render = await client.post(
                            "/api/poster/generate",
                            headers=first,
                            json={"posterType": "annual"},
                        )
                    assert failed_render.json()["code"] == 9002
                    async with session_factory() as session:
                        assert (
                            int(
                                await session.scalar(select(func.count()).select_from(UserPoster))
                                or 0
                            )
                            == before_count
                        )
                    assert (
                        await asyncio.to_thread(_matching_files, tmp_path, "*.png") == before_files
                    )

                    with monkeypatch.context() as patch:

                        async def db_failure(_session, _item) -> None:
                            raise RuntimeError("POSTER_DB_EXCEPTION_SENTINEL")

                        patch.setattr(poster_service, "_commit_generated_poster", db_failure)
                        failed_db = await client.post(
                            "/api/poster/generate",
                            headers=first,
                            json={"posterType": "annual"},
                        )
                    assert failed_db.status_code == 500
                    assert failed_db.json()["code"] == 500
                    assert (
                        await asyncio.to_thread(_matching_files, tmp_path, "*.png") == before_files
                    )

                    retry_poster = (
                        await client.post(
                            "/api/poster/generate",
                            headers=first,
                            json={"posterType": "annual"},
                        )
                    ).json()["data"]
                    retry_id = int(retry_poster["id"])
                    retry_url = str(retry_poster["posterUrl"])
                    with monkeypatch.context() as patch:

                        def unlink_failure(**_kwargs):
                            raise OSError("POSTER_UNLINK_EXCEPTION_SENTINEL")

                        patch.setattr(poster_renderer, "unlink_published_poster", unlink_failure)
                        failed_unlink = await client.delete(
                            f"/api/poster/delete/{retry_id}", headers=first
                        )
                    assert failed_unlink.json()["code"] == 9002
                    async with session_factory() as session:
                        row = await session.get(UserPoster, retry_id)
                        assert row is not None and row.is_deleted == 1
                    assert (await client.get(retry_url)).status_code == 200
                    assert (
                        await client.delete(f"/api/poster/delete/{retry_id}", headers=first)
                    ).json()["code"] == 200
                    assert (await client.get(retry_url)).status_code == 404

        poster_logs = [entry for entry in logs if entry.get("module") == "poster"]
        assert poster_logs
        assert all(set(entry) <= POSTER_LOG_FIELDS for entry in poster_logs)
        logged = str(poster_logs)
        for secret in (
            sentinel_title,
            "POSTER_OPENID_SENTINEL",
            "海报甲",
            "公开投喂文案",
            "POSTER_DB_EXCEPTION_SENTINEL",
            "POSTER_UNLINK_EXCEPTION_SENTINEL",
            absolute_path_sentinel,
            "/api/uploads/poster/",
        ):
            assert secret not in logged
    finally:
        await redis.close()
