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

    # True only for `SimulatedCollector` (specs/019-meeting-audio-ingestion,
    # found necessary while implementing `AudioCollector` — a real gap in the
    # original plan for that feature, not a design anticipated up front).
    # `SimulatedCollector` is one Python object standing in for every Phase 1
    # source at once, with no per-source "is this one connected" signal of
    # its own — that ambiguity is exactly why `RunCollectorUseCase` treats
    # the three MVP source types as unconditionally expected regardless of
    # what a given run's fixture actually contains. A dedicated,
    # single-purpose collector (`AudioCollector`, `source_type="transcripts"`)
    # has no such ambiguity: its own declared `source_type` is always what's
    # expected, simply because it was the collector asked to run, never
    # inferred from a fixture's contents. Leave this `False` for any new
    # dedicated collector — `True` would make `RunCollectorUseCase` phantom-
    # expect gmail/zendesk/warehouse from a collector that never touches them.
    mvp_sources_always_expected: bool = False

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
