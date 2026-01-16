from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ParsedUnipileEvent:
    chat_id: Optional[str]
    message: Optional[str]
    is_sender: Optional[bool]
    attendee_name: Optional[str]
    attendee_id: Optional[str]
    message_id: Optional[str]
    provider_message_id: Optional[str]
    event: Optional[str]
    timestamp: Optional[str]
    parse_mode: str
    raw: Any
