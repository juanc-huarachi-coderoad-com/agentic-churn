"""Domain entities for M4 (feedback memory) — pure data, no I/O.
See `specs/010-feedback-memory/data-model.md`.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FindingPatternComponents:
    reader_type: str
    finding_type: str


@dataclass(frozen=True)
class DampingWeight:
    pattern_signature: str
    weight: float
    false_alarm_count: int
    resolved_count: int
    correct_count: int
    disclosure_text: str | None
    last_updated_at: datetime
