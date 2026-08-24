"""`CachedEmbeddingAdapter` — implements `EmbeddingPort` by checking the
`embedding_cache` table (pgvector) before delegating to another `EmbeddingPort`
on a miss, then persisting the result. `RecurrenceReader` is unaware this exists
— it only ever calls `EmbeddingPort.embed()`, unchanged (specs/027-pgvector-
embedding-store, research.md Decision 2: a decorator adapter, not a new port).

Raw parameterized SQL, matching every other adapter in this codebase — no `pgvector`
Python package (research.md Decision 3). A `vector` column's text representation is
`[0.1,0.2,...]`; that's what's built on write and parsed on read.
"""

import hashlib

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.readers.application.ports import EmbeddingPort


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _to_vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(repr(v) for v in vector) + "]"


def _parse_vector_literal(literal: str) -> list[float]:
    return [float(v) for v in literal.strip("[]").split(",")]


class CachedEmbeddingAdapter(EmbeddingPort):
    def __init__(self, session: AsyncSession, model: str, wrapped: EmbeddingPort) -> None:
        self._session = session
        self._model = model
        self._wrapped = wrapped

    async def embed(self, text_content: str) -> list[float]:
        content_hash = _content_hash(text_content)
        row = (
            await self._session.execute(
                text(
                    "SELECT embedding::text AS embedding FROM embedding_cache "
                    "WHERE content_hash = :content_hash AND model = :model"
                ),
                {"content_hash": content_hash, "model": self._model},
            )
        ).one_or_none()
        if row is not None:
            return _parse_vector_literal(row.embedding)

        # A genuine miss whose delegate call fails (e.g. a missing API key) must
        # propagate unchanged — the reader's existing honest-failure behavior for
        # that content is preserved exactly (spec.md FR-007); no cache write on
        # failure, nothing partial ever gets stored.
        embedding = await self._wrapped.embed(text_content)

        await self._session.execute(
            text(
                "INSERT INTO embedding_cache (content_hash, model, embedding) "
                "VALUES (:content_hash, :model, CAST(:embedding AS vector)) "
                "ON CONFLICT (content_hash, model) DO NOTHING"
            ),
            {
                "content_hash": content_hash,
                "model": self._model,
                "embedding": _to_vector_literal(embedding),
            },
        )
        await self._session.commit()
        return embedding
