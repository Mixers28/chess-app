from __future__ import annotations

import contextvars
import json
import logging
import sys
from typing import Any

# Bound per-request by RequestIDMiddleware; surfaces in every log line.
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


class JsonFormatter(logging.Formatter):
    """Minimal structured JSON formatter with request-id correlation."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        # Structured extras attached via logger.info(..., extra={"extra": {...}}).
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Uvicorn's access logger is noisy and duplicates our request logs.
    logging.getLogger("uvicorn.access").handlers = []


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
