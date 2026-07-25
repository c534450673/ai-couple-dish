import re
from pathlib import Path

ROOT = Path(__file__).parents[3]
TEXT_SUFFIXES = {".py", ".toml", ".json", ".md", ".yml", ".yaml", ".conf", ".sh"}
SCAN_ROOTS = (ROOT / "backend/app", ROOT / "backend/contracts", ROOT / "docs/runbooks")
EXPLICIT_ARTIFACTS = {
    ROOT / ".github/workflows/fastapi.yml",
    ROOT / "backend/scripts/verify_fastapi_foundation.sh",
    ROOT / "backend/Dockerfile.fastapi",
    ROOT / "README.md",
    ROOT / "docs/ENVIRONMENT.md",
}
PATTERNS = [
    re.compile(r"AQ\.[A-Za-z0-9_-]{20,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b1[3-9]\d{9}\b"),
]


def _scanned_artifacts() -> set[Path]:
    paths = set(EXPLICIT_ARTIFACTS)
    for root in SCAN_ROOTS:
        paths.update(
            path for path in root.rglob("*") if path.is_file() and path.suffix in TEXT_SUFFIXES
        )
    return paths


def test_fastapi_artifacts_contain_no_secret_or_real_phone() -> None:
    violations: list[str] = []
    for path in _scanned_artifacts():
        text = path.read_text(errors="ignore")
        if any(pattern.search(text) for pattern in PATTERNS):
            violations.append(str(path.relative_to(ROOT)))
    assert violations == []


def test_sensitive_scan_covers_fastapi_acceptance_files() -> None:
    assert EXPLICIT_ARTIFACTS <= _scanned_artifacts()


def test_fastapi_acceptance_artifacts_and_document_state_exist() -> None:
    required = (
        ROOT / ".github/workflows/fastapi.yml",
        ROOT / "backend/scripts/verify_fastapi_foundation.sh",
        ROOT / "docs/runbooks/fastapi-dual-stack.md",
    )
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    assert missing == []

    documents = (ROOT / "README.md", ROOT / "docs/ENVIRONMENT.md")
    text = "\n".join(path.read_text(errors="ignore") for path in documents)
    assert "FastAPI" in text
    assert "Spring" in text
    assert "193" in text
    assert "尚未" in text or "未" in text
