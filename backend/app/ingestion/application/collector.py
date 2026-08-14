"""The `Collector` interface (REQ-M1-01) — Template Method: every source-specific
adapter (real or simulated) implements `fetch`/`normalize`/`resolve_identity`, and
shares the same `run()` orchestration a concrete `RunCollectorUseCase` drives.
`architecture/09-clean-architecture-and-patterns.md`'s pattern catalog entry.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.ingestion.domain.envelope import Envelope


class Collector(ABC):
    source_type: str

    @abstractmethod
    async def fetch(self, window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
        """Raw items from the source, in `occurred_at` order — callers append to the
        ledger in the order `fetch()` yields, and the hash chain requires that order to
        be chronological (EventRepositoryPort.append's docstring)."""
        ...

    @abstractmethod
    def normalize(self, raw_item: dict[str, Any]) -> Envelope:
        """Raw item -> the standard `Envelope` shape (REQ-M1-10) — before identity
        resolution, which `RunCollectorUseCase` performs separately (it needs the
        current client profile, which a normalizer has no business depending on:
        REQ-M1-P3)."""
        ...
