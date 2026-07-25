from importlib import import_module
from pathlib import Path


def test_python_runtime_and_required_modules() -> None:
    import sys

    assert sys.version_info[:2] == (3, 12)
    for module in ("fastapi", "pydantic", "sqlalchemy", "redis", "structlog"):
        assert import_module(module)


def test_lockfile_is_committed() -> None:
    assert (Path(__file__).parents[1] / "uv.lock").is_file()
