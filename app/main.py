import datetime as dt
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request

from app.chatwoot import ChatwootClient
from app.config import settings
from app.dedupe import MARKER, build_dedupe_key, has_marker, normalize_text, strip_marker
from app.logging_utils import configure_logging, log_structured
from app.supabase_client import SupabaseClient
from app.unipile import UnipileClient, parse_unipile_webhook


configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.chatwoot = ChatwootClient(
        base_url=settings.chatwoot_base_url,
        account_id=settings.chatwoot_account_id,
        inbox_id=settings.chatwoot_inbox_id,
        api_token=settings.chatwoot_api_token,
        timeout=settings.request_timeout_seconds,
        retries=settings.request_retries,
    )
    app.state.unipile = UnipileClient(
        base_url=settings.unipile_base_url,
        api_key=settings.unipile_api_key,
        timeout=settings.request_timeout_seconds,
        retries=settings.request_retries,
    )

    supabase: Optional[SupabaseClient] = None
    if settings.supabase_url and settings.supabase_key:
        supabase = SupabaseClient(
            base_url=settings.supabase_url,
            api_key=settings.supabase_key,
            timeout=settings.request_timeout_seconds,
            retries=settings.request_retries,
        )
    app.state.supabase = supabase
    yield
    await app.state.chatwoot.close()
    await app.state.unipile.close()
    if app.state.supabase:
        await app.state.supabase.close()


app = FastAPI(lifespan=lifespan)


def _get_header(request: Request, name: str) -> str:
    return request.headers.get(name) or ""


def _verify_webhook_secret(request: Request) -> None:
    if not settings.webhook_secret:
        return
    provided = _get_header(request, "X-Webhook-Secret")
    if provided != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="invalid webhook secret")


async def _log_event(app: FastAPI, event: Dict[str, Any]) -> None:
    log_structured(logging.INFO, "event", **event)
    supabase = app.state.supabase
    if not supabase:
        return
    try:
        await supabase.log_event(event)
    except Exception as exc:  # noqa: BLE001
        log_structured(logging.ERROR, "event_log_failed", error=str(exc))


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook/chatwoot")
async def webhook_chatwoot(request: Request) -> Dict[str, Any]:
    _verify_webhook_secret(request)
    signature = _get_header(request, "X-SIGNATURE")

    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        await _log_event(
            app,
            {
                "source": "chatwoot",
                "decision": "error",
                "error": f"invalid_json: {exc}",
                "payload": (await request.body()).decode("utf-8", errors="replace")[:1000],
                "signature": signature,
            },
        )
        raise HTTPException(status_code=400, detail="invalid json")

    event = payload.get("event")
    message_type = payload.get("message_type")
    content = payload.get("content") or ""

    if event != "message_created" or message_type != "outgoing":
        await _log_event(
            app,
            {
                "source": "chatwoot",
                "decision": "ignored_event",
                "payload": payload,
                "signature": signature,
            },
        )
        return {"status": "ignored"}

    if has_marker(content):
        await _log_event(
            app,
            {
                "source": "chatwoot",
                "decision": "ignored_marker",
                "payload": payload,
                "signature": signature,
            },
        )
        return {"status": "ignored_marker"}

    conversation = payload.get("conversation") or {}
    meta_sender = (conversation.get("meta") or {}).get("sender") or {}
    custom_attributes = meta_sender.get("custom_attributes") or {}
    chat_id = custom_attributes.get("chat_id")

    if not chat_id:
        await _log_event(
            app,
            {
                "source": "chatwoot",
                "decision": "error",
                "error": "missing_chat_id",
                "payload": payload,
                "signature": signature,
            },
        )
        return {"status": "missing_chat_id"}

    normalized_text = normalize_text(content)
    dedupe_key = build_dedupe_key(chat_id, normalized_text) if normalized_text else None

    now = dt.datetime.now(tz=dt.timezone.utc)
    if dedupe_key and app.state.supabase:
        try:
            await app.state.supabase.upsert_dedupe(
                dedupe_key,
                chat_id=chat_id,
                normalized_text=normalized_text,
                expires_at=now + dt.timedelta(seconds=settings.dedupe_ttl_seconds),
            )
        except Exception as exc:  # noqa: BLE001
            await _log_event(
                app,
                {
                    "source": "chatwoot",
                    "decision": "error",
                    "error": f"dedupe_upsert_failed: {exc}",
                    "chat_id": chat_id,
                    "dedupe_key": dedupe_key,
                    "normalized_text": normalized_text,
                    "payload": payload,
                    "signature": signature,
                },
            )

    try:
        text_to_send = strip_marker(content)
        response = await app.state.unipile.send_message(chat_id=chat_id, text=text_to_send)
        await _log_event(
            app,
            {
                "source": "chatwoot",
                "decision": "sent_to_unipile",
                "chat_id": chat_id,
                "dedupe_key": dedupe_key,
                "normalized_text": normalized_text,
                "payload": payload,
                "signature": signature,
                "response": response,
            },
        )
        return {"status": "sent"}
    except Exception as exc:  # noqa: BLE001
        await _log_event(
            app,
            {
                "source": "chatwoot",
                "decision": "error",
                "error": f"unipile_send_failed: {exc}",
                "chat_id": chat_id,
                "dedupe_key": dedupe_key,
                "normalized_text": normalized_text,
                "payload": payload,
                "signature": signature,
            },
        )
        return {"status": "error"}


@app.post("/webhook/unipile")
async def webhook_unipile(request: Request) -> Dict[str, Any]:
    _verify_webhook_secret(request)
    signature = _get_header(request, "X-SIGNATURE")

    body = await request.body()
    parsed = parse_unipile_webhook(body, request.headers.get("content-type"))

    chat_id = parsed.chat_id
    message = parsed.message or ""
    is_sender = parsed.is_sender

    if not chat_id:
        await _log_event(
            app,
            {
                "source": "unipile",
                "decision": "error",
                "error": "missing_chat_id",
                "payload": parsed.raw,
                "signature": signature,
                "parse_mode": parsed.parse_mode,
            },
        )
        return {"status": "missing_chat_id"}

    if is_sender is None:
        await _log_event(
            app,
            {
                "source": "unipile",
                "decision": "error",
                "error": "missing_is_sender",
                "chat_id": chat_id,
                "payload": parsed.raw,
                "signature": signature,
                "parse_mode": parsed.parse_mode,
            },
        )
        return {"status": "missing_is_sender"}

    normalized_text = None
    dedupe_key = None
    if is_sender:
        normalized_text = normalize_text(message)
        dedupe_key = build_dedupe_key(chat_id, normalized_text) if normalized_text else None

        if dedupe_key and app.state.supabase:
            try:
                deduped = await app.state.supabase.is_deduped(
                    dedupe_key, now=dt.datetime.now(tz=dt.timezone.utc)
                )
            except Exception as exc:  # noqa: BLE001
                deduped = False
                await _log_event(
                    app,
                    {
                        "source": "unipile",
                        "decision": "error",
                        "error": f"dedupe_check_failed: {exc}",
                        "chat_id": chat_id,
                        "dedupe_key": dedupe_key,
                        "normalized_text": normalized_text,
                        "payload": parsed.raw,
                        "signature": signature,
                        "parse_mode": parsed.parse_mode,
                    },
                )
        else:
            deduped = False

        if deduped:
            await _log_event(
                app,
                {
                    "source": "unipile",
                    "decision": "blocked_echo",
                    "chat_id": chat_id,
                    "dedupe_key": dedupe_key,
                    "normalized_text": normalized_text,
                    "payload": parsed.raw,
                    "signature": signature,
                    "parse_mode": parsed.parse_mode,
                },
            )
            return {"status": "blocked_echo"}

    attendee_id = parsed.attendee_id or chat_id
    attendee_name = parsed.attendee_name or attendee_id
    email = f"{attendee_id}@gmail.com"

    try:
        contact = await app.state.chatwoot.get_or_create_contact(
            name=attendee_name, email=email, chat_id=chat_id
        )
        conversation = await app.state.chatwoot.get_or_create_conversation(contact)
    except Exception as exc:  # noqa: BLE001
        await _log_event(
            app,
            {
                "source": "unipile",
                "decision": "error",
                "error": f"chatwoot_contact_failed: {exc}",
                "chat_id": chat_id,
                "dedupe_key": dedupe_key,
                "normalized_text": normalized_text,
                "payload": parsed.raw,
                "signature": signature,
                "parse_mode": parsed.parse_mode,
            },
        )
        return {"status": "error"}

    if not is_sender:
        try:
            result = await app.state.chatwoot.create_message(
                conversation_id=str(conversation.get("id")),
                message_type="incoming",
                content=message,
            )
            await _log_event(
                app,
                {
                    "source": "unipile",
                    "decision": "created_incoming",
                    "chat_id": chat_id,
                    "is_sender": is_sender,
                    "message_id": parsed.message_id,
                    "provider_message_id": parsed.provider_message_id,
                    "payload": parsed.raw,
                    "signature": signature,
                    "parse_mode": parsed.parse_mode,
                    "response": result,
                },
            )
            return {"status": "created_incoming"}
        except Exception as exc:  # noqa: BLE001
            await _log_event(
                app,
                {
                    "source": "unipile",
                    "decision": "error",
                    "error": f"chatwoot_incoming_failed: {exc}",
                    "chat_id": chat_id,
                    "payload": parsed.raw,
                    "signature": signature,
                    "parse_mode": parsed.parse_mode,
                },
            )
            return {"status": "error"}

    if normalized_text is None:
        normalized_text = normalize_text(message)
    if dedupe_key is None:
        dedupe_key = build_dedupe_key(chat_id, normalized_text) if normalized_text else None

    try:
        outgoing_content = f"{MARKER}{strip_marker(message)}"
        result = await app.state.chatwoot.create_message(
            conversation_id=str(conversation.get("id")),
            message_type="outgoing",
            content=outgoing_content,
        )
        await _log_event(
            app,
            {
                "source": "unipile",
                "decision": "created_outgoing",
                "chat_id": chat_id,
                "is_sender": is_sender,
                "message_id": parsed.message_id,
                "provider_message_id": parsed.provider_message_id,
                "dedupe_key": dedupe_key,
                "normalized_text": normalized_text,
                "payload": parsed.raw,
                "signature": signature,
                "parse_mode": parsed.parse_mode,
                "response": result,
            },
        )
        return {"status": "created_outgoing"}
    except Exception as exc:  # noqa: BLE001
        await _log_event(
            app,
            {
                "source": "unipile",
                "decision": "error",
                "error": f"chatwoot_outgoing_failed: {exc}",
                "chat_id": chat_id,
                "dedupe_key": dedupe_key,
                "normalized_text": normalized_text,
                "payload": parsed.raw,
                "signature": signature,
                "parse_mode": parsed.parse_mode,
            },
        )
        return {"status": "error"}
