"""Provider configuration request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderKeyIn(BaseModel):
    api_key: str = Field(min_length=8, max_length=500)


class EnabledModelsIn(BaseModel):
    enabled_models: list[str] = Field(default_factory=list, max_length=500)


class ProviderConfigOut(BaseModel):
    provider: str
    configured: bool
    key_hint: str | None = None
    enabled_models: list[str]
    is_enabled: bool


class TestConnectionOut(BaseModel):
    ok: bool
    models: list[str] = Field(default_factory=list)
    category: str | None = None
    message: str | None = None
