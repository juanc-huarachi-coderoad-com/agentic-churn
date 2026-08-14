"""Pure hash-chain arithmetic (REQ-M2-08) — SHA-256 over an already-canonicalized,
pipe-delimited field string, matching data-base/10-ddl-appendix.md's `verify_hash_chain()`
exactly. No I/O here: assembling the canonical text for TIMESTAMPTZ/UUID/JSONB fields
requires Postgres's own `::text` casts to guarantee byte-for-byte agreement with that
function's independent recomputation (Postgres's text rendering of those types isn't
something a Python formatter can safely reproduce) — so that assembly step lives in the
adapter (sqlalchemy_repositories.py), which owns the DB round-trip; this module only
hashes an already-assembled canonical string.
"""

import hashlib

GENESIS_HASH = "0" * 64


def canonicalize(fields: list[str | None]) -> str:
    """Pipe-delimited, NULLs (None) as empty string — the exact serialization
    data-base/03-schema-ledger.md specifies."""
    return "|".join("" if f is None else f for f in fields)


def compute_hash(fields: list[str | None]) -> str:
    """`fields` is the full 11-field canonical list, prev_event_hash included as the
    last element — matching verify_hash_chain()'s single `digest(...)` call over one
    concatenated string, not a separate hash-of-hash step."""
    return hashlib.sha256(canonicalize(fields).encode()).hexdigest()
