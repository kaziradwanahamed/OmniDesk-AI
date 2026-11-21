"""Structured JSON logging with a secret-redaction filter.

The redaction filter strips common credential shapes (Authorization / Bearer
tokens, API keys, cookies) from every emitted log record, so provider API keys,
session cookies, and authorization headers never reach the logs. This satisfies
the blueprint's "secret-redacting logger" and "Log Redaction Filter"
requirements (Chapters 8 and 24).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

REDACTED = "***REDACTED***"

# Key/value shapes: keep the leading label (group 1), redact the secret (group 2).
_PAIR_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*)(\S+)"),
    re.compile(r"(?i)(x-api-key\s*[:=]\s*)(\S+)"),
    re.compile(r"(?i)(cookie\s*[:=]\s*)([^\s;]+)"),
    re.compile(r"(?i)(bearer\s+)(\S+)"),
    re.compile(r"(?i)(\"?api[_-]?key\"?\s*[:=]\s*\"?)([A-Za-z0-9._\-]{6,})"),
]

# Standalone secret shapes.
_TOKEN_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9._\-]{8,}"),      # OpenAI-style keys
    re.compile(r"AIza[A-Za-z0-9._\-]{10,}"),     # Google API key style
]

# Credentials embedded in connection URLs / DSNs, e.g. postgres://user:pass@host
# (these can surface in tracebacks logged via logger.exception).
_URL_CREDENTIALS = re.compile(
    r"\b([a-zA-Z][a-zA-Z0-9+.\-]*://)[^:/?#\s@]+:[^@/?#\s]+@"
)


def redact(text: str) -> str:
    """Return ``text`` with recognizable secrets replaced by a placeholder."""
    if not text:
        return text
    out = text
    for pat in _PAIR_PATTERNS:
        out = pat.sub(lambda m: f"{m.group(1)}{REDACTED}", out)
    for pat in _TOKEN_PATTERNS:
        out = pat.sub(REDACTED, out)
    out = _URL_CREDENTIALS.sub(lambda m: f"{m.group(1)}***:***@", out)
    return out


class RedactionFilter(logging.Filter):
    """Redacts secrets from the log message template and its string args."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                redact(a) if isinstance(a, str) else a for a in record.args
            )
        return True


class JsonFormatter(logging.Formatter):
    """Minimal structured JSON log formatter (also redacts, belt-and-suspenders)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }
        if record.exc_info:
            payload["exc"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON formatter + redaction filter on the root and uvicorn loggers."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # Route uvicorn's loggers through the same redacting handler.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = [handler]
        lg.propagate = False
        lg.setLevel(level.upper())
