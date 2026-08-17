"""REQ-M1-06 — an unmet cadence produces an `absence` event; a just-satisfied one
produces none. Uses the seeded weekly `recurring_sync` commitment
(data-base/11-seed-data.sql). `last_contact_at()` is deliberately global (across the
whole ledger, not scoped to this commitment) and `EventRepositoryPort.append` requires
appends in global `occurred_at` order (tests/conftest.py's `ledger_floor` docstring) —
so both tests pin `as_of` to a random far-future point *anchored to the ledger's
current floor*, not to "now" directly, so a prior run's far-future data (this file's
own past runs included, since events can never be deleted) never un-satisfies what
should be a comfortably-overdue window.
"""

import uuid
from datetime import datetime, timedelta

from app.config import settings
from app.db import async_session_factory
from app.ingestion.adapters.encryption import BucketedFernetEncryption
from app.ingestion.adapters.key_store import FileKeyStore
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyCollectorRunRepository,
    SqlAlchemyCommitmentLookup,
    SqlAlchemyEventRepository,
)
from app.ingestion.application.ports import NewEvent
from app.ingestion.application.use_cases import DetectAbsenceUseCase
from tests.conftest import ledger_floor


async def _far_future_as_of(session) -> datetime:
    floor = await ledger_floor(session)
    return floor + timedelta(days=2000 + (uuid.uuid4().int % 2000))


async def test_unmet_cadence_appends_absence_event():
    # The real, persistent deployment key store (see test_replay.py's identical
    # note) — cheap to keep consistent even though absence-event bodies aren't
    # decrypted by anything today.
    key_store = FileKeyStore(settings.data_keys_dir)
    encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)

    async with async_session_factory() as setup_session:
        as_of = await _far_future_as_of(setup_session)

    async with async_session_factory() as session:
        use_case = DetectAbsenceUseCase(
            commitments=SqlAlchemyCommitmentLookup(session),
            collector_runs=SqlAlchemyCollectorRunRepository(session),
            events=SqlAlchemyEventRepository(session),
            encryption=encryption,
            key_store=key_store,
        )
        appended = await use_case.execute(as_of=as_of)

    assert len(appended) >= 1


async def test_just_satisfied_cadence_appends_nothing(make_envelope):
    key_store = FileKeyStore(settings.data_keys_dir)
    encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)

    async with async_session_factory() as session:
        as_of = await _far_future_as_of(session)
        envelope_id = await make_envelope(as_of)
        events = SqlAlchemyEventRepository(session)
        await events.append(
            NewEvent(envelope_id=envelope_id, event_type="message", occurred_at=as_of),
            data_key_ref="test-key",
        )

        use_case = DetectAbsenceUseCase(
            commitments=SqlAlchemyCommitmentLookup(session),
            collector_runs=SqlAlchemyCollectorRunRepository(session),
            events=events,
            encryption=encryption,
            key_store=key_store,
        )
        appended = await use_case.execute(as_of=as_of)

    assert appended == []
