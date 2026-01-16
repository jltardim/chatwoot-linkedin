import json
import re
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl

import httpx

from app.http_client import request_with_retries
from app.models import ParsedUnipileEvent


def _unwrap_body_string(raw: str) -> str:
    out = raw.strip()
    if out.startswith('"') and out.endswith('"'):
        out = out[1:-1]
    out = re.sub(r"^\s*\{\s*\"\{", "{", out)
    out = re.sub(r"\}\"\s*\}\s*$", "}", out)
    out = out.replace('\\"', '"')
    return out.strip()


def _fix_known_breaks(raw: str) -> str:
    s = raw
    s = re.sub(
        r'"provider_chat_id"\s*:\s*"([^"]+)"\s*:\s*"([^"]*)"\s*,',
        lambda m: f'"provider_chat_id":"{m.group(1)}{m.group(2)}",',
        s,
    )
    s = re.sub(
        r'"occupation"\s*:\s*"([^"]*?)"\s*:\s*""\s*,\s*"([^"]*?)"\s*,',
        lambda m: f'"occupation":"{m.group(1)}{m.group(2)}",',
        s,
    )
    return s


def _safe_json_parse(raw: str) -> Optional[Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _regex_pick(raw: str, key: str) -> Optional[str]:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"]*)"', raw, re.IGNORECASE)
    if not match:
        return None
    value = match.group(1)
    return value


def _regex_pick_bool(raw: str, key: str) -> Optional[bool]:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*(true|false|1|0)', raw, re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).lower()
    return value in {"true", "1"}


def _unescape_message(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return value.replace("\\n", "\n").replace("\\\"", '"')


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return None


def _extract_from_payload(payload: Dict[str, Any], parsed: Dict[str, Any], parse_mode: str) -> ParsedUnipileEvent:
    attendees = payload.get("attendees") or []
    attendee_name = None
    attendee_id = None
    if isinstance(attendees, list) and attendees:
        attendee = attendees[0] or {}
        attendee_name = attendee.get("attendee_name")
        attendee_id = attendee.get("attendee_id")

    message = payload.get("message")
    if isinstance(message, str):
        message = _unescape_message(message)

    timestamp = payload.get("timestamp")
    if timestamp is None and isinstance(parsed, dict):
        timestamp = parsed.get("timestamp")

    return ParsedUnipileEvent(
        chat_id=payload.get("chat_id"),
        message=message,
        is_sender=_coerce_bool(payload.get("is_sender")),
        attendee_name=attendee_name,
        attendee_id=attendee_id,
        message_id=payload.get("message_id"),
        provider_message_id=payload.get("provider_message_id"),
        event=parsed.get("event") if isinstance(parsed, dict) else None,
        timestamp=timestamp,
        parse_mode=parse_mode,
        raw=parsed,
    )


def _fallback_extract(raw: str) -> ParsedUnipileEvent:
    attendee_name = _regex_pick(raw, "attendee_name")
    attendee_id = _regex_pick(raw, "attendee_id")

    message = _regex_pick(raw, "message")
    message = _unescape_message(message)

    return ParsedUnipileEvent(
        chat_id=_regex_pick(raw, "chat_id"),
        message=message,
        is_sender=_regex_pick_bool(raw, "is_sender"),
        attendee_name=attendee_name,
        attendee_id=attendee_id,
        message_id=_regex_pick(raw, "message_id"),
        provider_message_id=_regex_pick(raw, "provider_message_id"),
        event=_regex_pick(raw, "event"),
        timestamp=_regex_pick(raw, "timestamp"),
        parse_mode="regex_fallback",
        raw=raw[:1000],
    )


def parse_unipile_webhook(body: bytes, content_type: Optional[str]) -> ParsedUnipileEvent:
    raw = body.decode("utf-8", errors="replace").strip()
    candidates = []

    if raw:
        candidates.append(raw)

    if raw:
        pairs = parse_qsl(raw, keep_blank_values=True)
        for key, value in pairs:
            key = key.strip()
            value = value.strip()
            if key.startswith("{"):
                candidates.append(key)
            if value.startswith("{"):
                candidates.append(value)

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unwrapped = _unwrap_body_string(candidate)
        parsed = _safe_json_parse(unwrapped)
        parse_mode = "json"
        if parsed is None:
            fixed = _fix_known_breaks(unwrapped)
            parsed = _safe_json_parse(fixed)
            parse_mode = "json_fixed"

        if isinstance(parsed, dict):
            payload = parsed.get("data") if isinstance(parsed.get("data"), dict) else parsed
            return _extract_from_payload(payload, parsed, parse_mode)

    return _fallback_extract(raw)


class UnipileClient:
    def __init__(self, base_url: str, api_key: str, timeout: float, retries: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.retries = retries
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        url = f"{self.base_url}/chats/{chat_id}/messages"
        headers = {
            "X-API-KEY": self.api_key,
            "accept": "application/json",
        }
        response = await request_with_retries(
            self._client,
            "POST",
            url,
            self.retries,
            headers=headers,
            files={"text": (None, text)},
        )
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}
