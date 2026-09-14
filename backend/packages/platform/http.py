from collections.abc import Mapping

import httpx


async def request_json(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 5.0,
    **kwargs: object,
) -> httpx.Response:
    request_headers = dict(headers or {})
    request_headers.setdefault("X-Request-ID", "")
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=timeout)) as client:
        return await client.request(method, url, headers=request_headers, **kwargs)
