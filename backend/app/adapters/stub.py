"""Deterministic stub echo adapter for verifying end-to-end persistence.

It performs no network calls and returns no fabricated usage (tokens are null).
Sending the exact content ``__fail__`` raises a ProviderError so the error /
history-preservation path can be tested.
"""

from __future__ import annotations

from app.adapters.base import (
    BaseProviderAdapter,
    NormalizedUsage,
    ProviderError,
    ProviderRequest,
    ProviderResponse,
)

STUB_MODEL_ID = "stub-echo"


class StubEchoAdapter(BaseProviderAdapter):
    provider_name = "stub"

    async def generate(
        self, req: ProviderRequest, api_key: str | None = None
    ) -> ProviderResponse:
        last_user = next(
            (m.content for m in reversed(req.messages) if m.role == "user"), ""
        )
        if last_user.strip() == "__fail__":
            raise ProviderError(
                "MODEL_UNAVAILABLE", "Simulated stub adapter failure."
            )
        reply = f"[stub-echo] You said: {last_user}"
        return ProviderResponse(
            provider="stub",
            model_id=STUB_MODEL_ID,
            content=reply,
            usage=NormalizedUsage(),  # no fabricated token counts
        )
