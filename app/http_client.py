import asyncio
from typing import Iterable, Optional

import httpx


DEFAULT_RETRY_STATUSES = {429, 500, 502, 503, 504}


async def request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    retries: int,
    retry_statuses: Optional[Iterable[int]] = None,
    **kwargs,
) -> httpx.Response:
    statuses = set(retry_statuses or DEFAULT_RETRY_STATUSES)
    last_exc: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code not in statuses:
                return response
            last_exc = httpx.HTTPStatusError(
                f"Retryable status code {response.status_code}",
                request=response.request,
                response=response,
            )
        except httpx.RequestError as exc:
            last_exc = exc

        if attempt < retries:
            await asyncio.sleep(0.5 * (2 ** attempt))

    if last_exc:
        raise last_exc
    raise RuntimeError("request_with_retries failed without exception")
