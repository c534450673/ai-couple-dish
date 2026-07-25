from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol

import pytest
from testcontainers.mysql import MySqlContainer
from testcontainers.redis import RedisContainer


class _Container(Protocol):
    def start(self) -> object: ...

    def stop(self) -> object: ...


@contextmanager
def _running_container[ContainerT: _Container](container: ContainerT) -> Iterator[ContainerT]:
    original_error: BaseException | None = None
    try:
        container.start()
        yield container
    except BaseException as error:
        original_error = error
        raise
    finally:
        try:
            container.stop()
        except Exception:
            if original_error is None:
                raise


@pytest.fixture(scope="session")
def mysql_url() -> Iterator[str]:
    with _running_container(MySqlContainer("mysql:8.0", dialect="asyncmy")) as container:
        url = container.get_connection_url()
        assert url.startswith("mysql+asyncmy://")
        yield url


@pytest.fixture(scope="session")
def redis_url() -> Iterator[str]:
    with _running_container(RedisContainer("redis:7-alpine")) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(container.port)
        yield f"redis://{host}:{port}/0"
