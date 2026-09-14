from collections.abc import Mapping
from typing import Any

import httpx


async def request_json(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout_seconds: float = 5.0,
    **kwargs: Any,
) -> httpx.Response:
    request_headers = dict(headers or {})
    request_headers.setdefault("X-Request-ID", "")
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_seconds, connect=timeout_seconds)
    ) as client:
        return await client.request(method, url, headers=request_headers, **kwargs)
