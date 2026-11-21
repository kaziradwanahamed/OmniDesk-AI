"""Shared conservative token estimator.

A deliberately provider-agnostic estimate (``ceil(len(text) / 3.5)`` plus a fixed
per-message overhead). It is always labeled as an estimate in the UI and is never
presented as a billed token count. Extracted here so both the ContextBuilder and
the summarization service can use it without an import cycle.
"""

from __future__ import annotations

import math

_CHARS_PER_TOKEN = 3.5
_PER_MESSAGE_OVERHEAD = 4


def estimate_tokens(text: str) -> int:
    """Conservative token estimate: ceil(len(text) / 3.5)."""
    if not text:
        return 0
    return math.ceil(len(text) / _CHARS_PER_TOKEN)


def estimate_message_tokens(content: str) -> int:
    """Per-message estimate: content estimate + a fixed per-message overhead."""
    return estimate_tokens(content) + _PER_MESSAGE_OVERHEAD


def chars_for_tokens(max_tokens: int) -> int:
    """Approximate character budget for a token budget (for truncation)."""
    return int(max_tokens * _CHARS_PER_TOKEN)
