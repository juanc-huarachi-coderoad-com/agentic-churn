"""Real-DB: `RunRetentionUseCase` actually shreds, is idempotent, and records
failures (specs/011-production-hardening, User Story 1 — FR-001/002/003/004a).
"""

from datetime import UTC, datetime

from cryptography.fernet import Fernet
from sqlalchemy import text

from app.config import settings
from app.db import async_session_factory, engine, shredder_session_factory
from app.ingestion.adapters.key_store import FileKeyStore
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyEventRepository,
    SqlAlchemyRetentionJobRepository,
)
from app.ingestion.application.ports import KeyStorePort, NewEvent
from app.ingestion.application.use_cases import RunRetentionUseCase

_AGED_BUCKET = "2020-01-01"  # decades past any retention window


class _FailOnSecondDestroy(KeyStorePort):
    """Wraps a real `FileKeyStore`, raising on its second `destroy()` call —
    simulates the retention job crashing partway through a multi-bucket run
    (FR-004a)."""

    def __init__(self, delegate: KeyStorePort) -> None:
        self._delegate = delegate
        self._destroy_calls = 0

    def current_bucket_id(self) -> str:
        return self._delegate.current_bucket_id()

    def resolve(self, bucket_id: str) -> Fernet:
        return self._delegate.resolve(bucket_id)

    def list_active_buckets(self) -> list[str]:
        return self._delegate.list_active_buckets()

    def destroy(self, bucket_id: str) -> None:
        self._destroy_calls += 1
        if self._destroy_calls == 2:
            raise RuntimeError("simulated failure mid-run")
        self._delegate.destroy(bucket_id)


async def _run(key_store: KeyStorePort):
    async with (
        async_session_factory() as session,
        shredder_session_factory() as shredder_session,
    ):
        use_case = RunRetentionUseCase(
            key_store=key_store,
            retention_repo=SqlAlchemyRetentionJobRepository(session, shredder_session),
            retention_window_days=settings.retention_window_days,
        )
        return await use_case.execute()


async def test_retention_job_shreds_an_aged_bucket_and_is_idempotent(tmp_path, make_envelope):
    key_store = FileKeyStore(str(tmp_path))
    fernet = key_store.resolve(_AGED_BUCKET)
    ciphertext = fernet.encrypt(b"a message that should be shredded")

    envelope_id = await make_envelope()
    async with async_session_factory() as session:
        events = SqlAlchemyEventRepository(session)
        event_id = await events.append(
            NewEvent(
                envelope_id=envelope_id,
                event_type="message",
                occurred_at=datetime.now(UTC),
                body_encrypted=ciphertext,
            ),
            data_key_ref=_AGED_BUCKET,
        )

    result = await _run(key_store)
    assert result.status == "succeeded"
    assert result.buckets_evaluated >= 1
    assert result.buckets_shredded >= 1
    assert _AGED_BUCKET not in key_store.list_active_buckets()

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT body_encrypted FROM events WHERE id = :id"), {"id": event_id}
            )
        ).one()
    assert row.body_encrypted is None

    async with engine.begin() as conn:
        run_row = (
            await conn.execute(
                text(
                    "SELECT status, buckets_shredded FROM retention_job_runs "
                    "ORDER BY started_at DESC LIMIT 1"
                )
            )
        ).one()
    assert run_row.status == "succeeded"

    # Idempotent re-run (FR-003): the bucket is already gone, so this run
    # evaluates whatever buckets remain (possibly zero) and shreds none of
    # them again — no error either way.
    second = await _run(key_store)
    assert second.status == "succeeded"


async def test_retention_job_records_a_failed_run_and_leaves_earlier_shreds_intact(tmp_path):
    key_store = FileKeyStore(str(tmp_path))
    key_store.resolve("2020-01-01")
    key_store.resolve("2020-01-02")
    key_store.resolve("2020-01-03")

    failing_store = _FailOnSecondDestroy(key_store)
    try:
        await _run(failing_store)
        raise AssertionError("expected RuntimeError to propagate")
    except RuntimeError:
        pass

    async with engine.begin() as conn:
        run_row = (
            await conn.execute(
                text(
                    "SELECT status, error_detail, buckets_evaluated, buckets_shredded "
                    "FROM retention_job_runs ORDER BY started_at DESC LIMIT 1"
                )
            )
        ).one()
    assert run_row.status == "failed"
    assert run_row.error_detail is not None
    assert "simulated failure" in run_row.error_detail
    # The first bucket's destroy() succeeded before the second one raised —
    # that work is not rolled back (FR-003: a partial run is always safe to
    # resume, not atomic-or-nothing).
    assert run_row.buckets_shredded == 1
