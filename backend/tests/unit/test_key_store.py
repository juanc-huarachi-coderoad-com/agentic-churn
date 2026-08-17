"""Pure `FileKeyStore` behavior (specs/011-production-hardening, User Story 1) — no
DB, a fresh `tmp_path` directory per test."""

from datetime import UTC, datetime

import pytest
from cryptography.fernet import InvalidToken

from app.ingestion.adapters.key_store import FileKeyStore


def test_current_bucket_id_is_todays_date():
    store = FileKeyStore("/tmp/does-not-need-to-exist-yet")
    assert store.current_bucket_id() == datetime.now(UTC).date().isoformat()


def test_resolve_on_unseen_bucket_lazily_creates_a_key(tmp_path):
    store = FileKeyStore(str(tmp_path))
    assert store.list_active_buckets() == []
    key = store.resolve("2026-01-01")
    assert key is not None
    assert store.list_active_buckets() == ["2026-01-01"]


def test_resolve_on_a_known_bucket_returns_the_same_key_twice(tmp_path):
    store = FileKeyStore(str(tmp_path))
    first = store.resolve("2026-01-01")
    second = store.resolve("2026-01-01")
    # Same underlying key material — round-trips across both handles.
    ciphertext = first.encrypt(b"same key material")
    assert second.decrypt(ciphertext) == b"same key material"


def test_destroy_removes_the_bucket_and_a_later_resolve_creates_a_new_key(tmp_path):
    store = FileKeyStore(str(tmp_path))
    original = store.resolve("2026-01-01")
    ciphertext = original.encrypt(b"before destruction")

    store.destroy("2026-01-01")
    assert store.list_active_buckets() == []

    recreated = store.resolve("2026-01-01")
    assert store.list_active_buckets() == ["2026-01-01"]
    # Genuinely a new, different key — the old ciphertext no longer decrypts,
    # proving destruction is real, not cached (research.md Decision 1's
    # crypto-shredding guarantee at the unit level).
    with pytest.raises(InvalidToken):
        recreated.decrypt(ciphertext)


def test_destroy_on_an_unknown_bucket_is_not_an_error(tmp_path):
    store = FileKeyStore(str(tmp_path))
    store.destroy("2020-01-01")  # never created — must not raise
