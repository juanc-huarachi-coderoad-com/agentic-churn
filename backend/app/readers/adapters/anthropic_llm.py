"""`AnthropicLLMAdapter` — implements `LLMPort` via the Anthropic Messages API's
native structured-output support (`client.messages.parse(output_format=...)`,
returning a `parsed_output` instance of the requested type — no forced tool
call involved, and no `tools` parameter is ever passed, structurally matching
REQ-M5-P2's zero-tools requirement). The only file in this module that imports
`anthropic` (`.importlinter`'s `readers-application-purity` contract).

Timeout/retry budget: 8s per attempt, 2 retries, 1s/2s backoff
(`architecture/06-error-handling.md`) — on exhaustion, the underlying error is
re-raised for the caller (a reader) to treat as an abstention, never a
quarantine (nothing was produced to quarantine).
"""

import asyncio
from typing import TypeVar

import anthropic

from app.readers.application.ports import LLMPort

T = TypeVar("T")

_MAX_TOKENS = 1024
_PER_ATTEMPT_TIMEOUT_SECONDS = 8.0
_RETRY_BACKOFFS_SECONDS = (1.0, 2.0)


class AnthropicLLMAdapter(LLMPort):
    """Deliberately doesn't validate `api_key` at construction time — mirrors
    `OpenAIEmbeddingAdapter`'s existing precedent (feature 005): `RunReadersUseCase`
    only isolates a failure raised from within `Reader.interpret()` (FR-014a),
    so an eager `__init__` raise would crash the whole run instead of being
    caught and reported as Tone/Intent's own isolated failure."""

    def __init__(self, api_key: str, model_id: str) -> None:
        self._api_key = api_key
        self._model_id = model_id
        self._client: anthropic.AsyncAnthropic | None = None

    async def generate_structured(self, prompt: str, schema: type[T]) -> T:
        if not self._api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not configured — Tone/Intent fail "
                "honestly rather than silently skipping (mirrors Recurrence's "
                "own OPENAI_API_KEY precedent, spec.md's Edge Cases)"
            )
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(
                api_key=self._api_key, timeout=_PER_ATTEMPT_TIMEOUT_SECONDS
            )

        attempts = 1 + len(_RETRY_BACKOFFS_SECONDS)
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                response = await self._client.messages.parse(
                    model=self._model_id,
                    max_tokens=_MAX_TOKENS,
                    messages=[{"role": "user", "content": prompt}],
                    output_format=schema,
                )
                parsed = response.parsed_output
                if parsed is None:
                    raise ValueError("Model response did not contain parseable structured output")
                return parsed
            except Exception as exc:  # noqa: BLE001 — genuinely any failure retries/exhausts the same way
                last_error = exc
                if attempt < len(_RETRY_BACKOFFS_SECONDS):
                    await asyncio.sleep(_RETRY_BACKOFFS_SECONDS[attempt])

        assert last_error is not None
        raise last_error
