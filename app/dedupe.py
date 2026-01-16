import hashlib
import re


OLD_MARKER = "\u200BLI_ECHO\u200B"
MARKER = "\u2063\u2063\u2063"
MARKERS = (OLD_MARKER, MARKER)
_SPACE_RE = re.compile(r"\s+")


def strip_marker(text: str) -> str:
    if not text:
        return ""
    cleaned = text
    for marker in MARKERS:
        cleaned = cleaned.replace(marker, "")
    return cleaned


def has_marker(text: str) -> bool:
    if not text:
        return False
    return any(marker in text for marker in MARKERS)


def normalize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = strip_marker(text)
    cleaned = _SPACE_RE.sub(" ", cleaned.strip())
    return cleaned


def build_dedupe_key(chat_id: str, normalized_text: str) -> str:
    digest = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    return f"{chat_id}|{digest}"
