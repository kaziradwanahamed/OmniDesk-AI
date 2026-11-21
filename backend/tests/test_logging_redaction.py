"""Security tests for the secret-redacting logger (Phase 1)."""

from __future__ import annotations

import json
import logging

from app.core.logging import REDACTED, JsonFormatter, RedactionFilter, redact


def test_redacts_authorization_bearer() -> None:
    out = redact("Authorization: Bearer sk-abcdefgh12345678")
    assert "sk-abcdefgh12345678" not in out
    assert REDACTED in out


def test_redacts_api_key_in_json() -> None:
    out = redact('{"api_key": "sk-abcdefgh12345678"}')
    assert "sk-abcdefgh12345678" not in out


def test_redacts_google_api_key() -> None:
    out = redact("using key AIzaSyA1234567890abcdefXYZ")
    assert "AIzaSyA1234567890abcdefXYZ" not in out


def test_redacts_cookie_header() -> None:
    out = redact("Cookie: session=supersecretvalue; other=1")
    assert "supersecretvalue" not in out


def test_redacts_url_credentials() -> None:
    out = redact("connect postgres://omnidesk:supersecret@db:5432/omnidesk failed")
    assert "supersecret" not in out
    # Host/scheme are preserved for debuggability.
    assert "db:5432" in out
    assert out.count("***:***@") == 1


def test_redaction_filter_mutates_record() -> None:
    f = RedactionFilter()
    record = logging.LogRecord(
        "t", logging.INFO, "p", 1,
        "Authorization: Bearer sk-abcdefgh12345678", None, None,
    )
    assert f.filter(record) is True
    assert "sk-abcdefgh12345678" not in record.getMessage()


def test_json_formatter_is_json_and_redacts() -> None:
    fmt = JsonFormatter()
    record = logging.LogRecord(
        "t", logging.INFO, "p", 1, "leaked sk-abcdefgh12345678", None, None,
    )
    data = json.loads(fmt.format(record))
    assert data["level"] == "INFO"
    assert "sk-abcdefgh12345678" not in data["message"]
