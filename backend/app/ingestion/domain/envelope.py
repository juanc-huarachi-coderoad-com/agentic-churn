"""The `Envelope` value object (REQ-M1-10) — the normalized shape a `Collector` hands
to the ledger, before it becomes a `raw_envelopes` row. Pure data + idempotency-key
derivation; no I/O.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def idempotency_key(source_type: str, source_native_id: str) -> str:
    """`hash(source_type, source_native_id)` (REQ-M1-03) — deterministic, so running a
    collector twice over an overlapping window collides on this key rather than
    duplicating events."""
    return hashlib.sha256(f"{source_type}:{source_native_id}".encode()).hexdigest()


@dataclass(frozen=True)
class Envelope:
    source_type: str
    source_native_id: str
    occurred_at: datetime
    identity_status: str  # "resolved" | "unresolved"
    resolved_stakeholder_id: str | None
    redacted_fields: list[str]
    payload_text: str
    """Plaintext, human-readable form of the raw signal — encrypted just before
    persistence (RunCollectorUseCase), never stored as-is."""
    structured_payload: dict[str, Any] = field(default_factory=dict)
    """Non-body structured fields (ticket number/state, usage delta, etc.) — mirrors
    events.structured_payload (data-base/03-schema-ledger.md)."""

    @property
    def idempotency_key(self) -> str:
        return idempotency_key(self.source_type, self.source_native_id)
