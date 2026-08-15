"""`OpenAIEmbeddingAdapter` — implements `EmbeddingPort` via `text-embedding-3-
small` (`architecture/03-technology-stack.md`). The only file in this module
that imports `openai` (`.importlinter`'s `readers-application-purity` contract).
"""

from openai import AsyncOpenAI

from app.readers.application.ports import EmbeddingPort

_MODEL = "text-embedding-3-small"


class OpenAIEmbeddingAdapter(EmbeddingPort):
    """Deliberately doesn't validate `api_key` at construction time (unlike a
    typical fail-fast adapter): `RunReadersUseCase` only isolates a failure
    raised from within `Reader.interpret()` (FR-014a), so an eager `__init__`
    raise would crash the whole run instead of being caught and reported as
    Recurrence's own isolated failure (`spec.md`'s Edge Cases — "isolated to
    Recurrence alone")."""

    def __init__(self, api_key: str) -> None:
        # The client itself isn't built here — `AsyncOpenAI(api_key="")` raises
        # immediately (an empty string isn't treated as "provide one later"),
        # which would defeat the deferred-validation point above just as surely
        # as an eager check would. Built lazily on first `embed()` call instead,
        # once `_api_key` has already been confirmed non-empty.
        self._api_key = api_key
        self._client: AsyncOpenAI | None = None

    async def embed(self, text: str) -> list[float]:
        if not self._api_key:
            raise ValueError(
                "OPENAI_API_KEY is not configured — the Recurrence reader fails "
                "honestly rather than silently skipping (spec.md's Edge Cases)"
            )
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._api_key)
        response = await self._client.embeddings.create(model=_MODEL, input=text)
        return response.data[0].embedding
