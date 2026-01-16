import json
import logging
import time
from typing import Any, Dict


logger = logging.getLogger("bridge")


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format="%(message)s")


def log_structured(level: int, message: str, **fields: Any) -> None:
    payload: Dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "message": message,
    }
    payload.update(fields)
    logger.log(level, json.dumps(payload, ensure_ascii=True))
