import datetime as dt
from typing import Any, Dict, Optional

import httpx

from app.http_client import request_with_retries


class SupabaseClient:
    def __init__(self, base_url: str, api_key: str, timeout: float, retries: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.retries = retries
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, str]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        url = f"{self.base_url}/rest/v1/{path.lstrip('/')}"
        merged_headers = self._headers()
        if headers:
            merged_headers.update(headers)
        response = await request_with_retries(
            self._client,
            method,
            url,
            self.retries,
            params=params,
            json=json,
            headers=merged_headers,
        )
        response.raise_for_status()
        if response.content:
            return response.json()
        return None

    async def upsert_dedupe(
        self, dedupe_key: str, chat_id: str, normalized_text: str, expires_at: dt.datetime
    ) -> None:
        payload = {
            "dedupe_key": dedupe_key,
            "chat_id": chat_id,
            "normalized_text": normalized_text,
            "expires_at": expires_at.isoformat(),
        }
        await self._request(
            "POST",
            "dedupe_cache",
            params={"on_conflict": "dedupe_key"},
            json=[payload],
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )

    async def is_deduped(self, dedupe_key: str, now: dt.datetime) -> bool:
        params = {
            "dedupe_key": f"eq.{dedupe_key}",
            "expires_at": f"gt.{now.isoformat()}",
            "select": "dedupe_key,expires_at",
        }
        data = await self._request("GET", "dedupe_cache", params=params)
        return bool(data)

    async def log_event(self, event: Dict[str, Any]) -> None:
        await self._request(
            "POST",
            "event_logs",
            json=[event],
            headers={"Prefer": "return=minimal"},
        )
