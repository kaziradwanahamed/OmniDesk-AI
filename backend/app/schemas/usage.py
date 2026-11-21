"""Usage ledger response schemas (verified provider metadata only)."""

from __future__ import annotations

from pydantic import BaseModel


class UsageByModel(BaseModel):
    provider: str
    model_id: str | None = None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    request_count: int


class UsageSummaryOut(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    by_model: list[UsageByModel]
