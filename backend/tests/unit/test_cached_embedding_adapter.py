"""specs/027-pgvector-embedding-store — `CachedEmbeddingAdapter` real-DB coverage.

`RecurrenceReader` itself is untouched by this feature (research.md Decision 2 — a
decorator adapter, not a new port); its own existing test suite is the non-regression
proof for User Story 3. This file covers the one genuinely new piece of logic: cache
hit/miss/model-scoping in `CachedEmbeddingAdapter` itself, against a real Postgres with
the pgvector extension installed.
"""

from uuid import uuid4

from app.db import async_session_factory
from app.readers.adapters.pgvector_embedding_cache import CachedEmbeddingAdapter
from app.readers.application.ports import EmbeddingPort

# embedding_cache.embedding is vector(1536) — matching OpenAIEmbeddingAdapter.MODEL_ID's
# real output dimension (data-model.md); every fixture vector must be the real width or
# Postgres rejects the insert ("expected 1536 dimensions, not N").
_DIMENSIONS = 1536


def _fixture_vector(fill: float) -> list[float]:
    return [fill] * _DIMENSIONS


class _CountingEmbeddingPort(EmbeddingPort):
    def __init__(self, vector: list[float] | None = None) -> None:
        self.calls: list[str] = []
        self._vector = vector or _fixture_vector(0.1)

    async def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return self._vector


async def test_repeated_content_is_embedded_only_once():
    model = f"test-model-{uuid4().hex[:8]}"
    fake = _CountingEmbeddingPort(_fixture_vector(0.5))
    text_content = f"ticket title {uuid4().hex[:8]}"

    async with async_session_factory() as session:
        cache = CachedEmbeddingAdapter(session, model, fake)
        first = await cache.embed(text_content)
        second = await cache.embed(text_content)

    assert fake.calls == [text_content]  # the delegate was called exactly once
    assert first == second == _fixture_vector(0.5)


async def test_different_content_each_costs_one_call():
    model = f"test-model-{uuid4().hex[:8]}"
    fake = _CountingEmbeddingPort()
    text_a = f"title a {uuid4().hex[:8]}"
    text_b = f"title b {uuid4().hex[:8]}"

    async with async_session_factory() as session:
        cache = CachedEmbeddingAdapter(session, model, fake)
        await cache.embed(text_a)
        await cache.embed(text_b)
        await cache.embed(text_a)
        await cache.embed(text_b)

    assert sorted(fake.calls) == sorted([text_a, text_b])


async def test_a_model_change_never_reuses_another_models_cached_vector():
    text_content = f"shared title {uuid4().hex[:8]}"
    model_a = f"model-a-{uuid4().hex[:8]}"
    model_b = f"model-b-{uuid4().hex[:8]}"
    fake_a = _CountingEmbeddingPort(_fixture_vector(1.0))
    fake_b = _CountingEmbeddingPort(_fixture_vector(2.0))

    async with async_session_factory() as session:
        cache_a = CachedEmbeddingAdapter(session, model_a, fake_a)
        cache_b = CachedEmbeddingAdapter(session, model_b, fake_b)
        result_a = await cache_a.embed(text_content)
        result_b = await cache_b.embed(text_content)

    assert fake_a.calls == [text_content]
    assert fake_b.calls == [text_content]  # model B never reused model A's cache hit
    assert result_a == _fixture_vector(1.0)
    assert result_b == _fixture_vector(2.0)


async def test_a_delegate_failure_on_a_genuine_miss_propagates_and_caches_nothing():
    model = f"test-model-{uuid4().hex[:8]}"
    text_content = f"unembeddable title {uuid4().hex[:8]}"

    class _FailingEmbeddingPort(EmbeddingPort):
        async def embed(self, text: str) -> list[float]:
            raise ValueError("OPENAI_API_KEY is not configured")

    async with async_session_factory() as session:
        cache = CachedEmbeddingAdapter(session, model, _FailingEmbeddingPort())
        raised = False
        try:
            await cache.embed(text_content)
        except ValueError:
            raised = True
        assert raised

        # No partial cache write from the failed attempt — a retry with a working
        # delegate must still call it, not silently return nothing/garbage.
        fake = _CountingEmbeddingPort(_fixture_vector(9.0))
        cache_retry = CachedEmbeddingAdapter(session, model, fake)
        result = await cache_retry.embed(text_content)

    assert fake.calls == [text_content]
    assert result == _fixture_vector(9.0)
