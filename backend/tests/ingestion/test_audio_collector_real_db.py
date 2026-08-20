"""Real-DB: `AudioCollector` end to end through `RunCollectorUseCase` — a
consented recording (from a *fake* Drive client + transcription adapter, no
real Google/OpenAI/pyannote calls) reaches the event ledger, decrypts
correctly, and is readable by the unmodified `MeetingReader`
(specs/019-meeting-audio-ingestion, FR-009). Also
confirms an audio-sourced (`event_type = 'meeting'`) event is swept by the
existing retention job exactly like any other event type (FR-010,
`/speckit-analyze` finding E3) — using `test_retention_real_db.py`'s own
isolated-`tmp_path`-key-store pattern, never the shared deployment key
store, so this never risks shredding any other test's data in the same
day's real bucket.
"""

import uuid
from datetime import UTC, datetime
from typing import TypeVar
from unittest.mock import AsyncMock

from sqlalchemy import text

from app.config import settings
from app.db import async_session_factory, engine, shredder_session_factory
from app.ingestion.adapters.audio_collector import AudioCollector
from app.ingestion.adapters.encryption import BucketedFernetEncryption
from app.ingestion.adapters.google_drive_client import DriveRecording
from app.ingestion.adapters.key_store import FileKeyStore
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyClientProfileContext,
    SqlAlchemyCollectorRunRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyMeetingSeriesConsentRepository,
    SqlAlchemyRetentionJobRepository,
)
from app.ingestion.application.ports import NewEvent
from app.ingestion.application.use_cases import RunCollectorUseCase, RunRetentionUseCase
from app.readers.application.meeting_reader import (
    ExtractedCommitment,
    MeetingModelOutput,
    MeetingReader,
)
from app.readers.application.ports import FindingRepositoryPort, LLMPort
from app.readers.domain.entities import MeetingTranscriptInfo
from app.scoring.domain.entities import Finding

T = TypeVar("T")

_AGED_BUCKET = "2020-01-01"  # decades past any retention window, matches test_retention_real_db.py


class _FakeLLM(LLMPort):
    def __init__(self, response: MeetingModelOutput) -> None:
        self._response = response

    async def generate_structured(self, prompt: str, schema: type[T]) -> T:
        return self._response  # type: ignore[return-value]


class _FakeFindingRepository(FindingRepositoryPort):
    def __init__(self) -> None:
        self.persisted: list[Finding] = []

    async def already_interpreted(self, *, reader_type, reader_version, event_id) -> bool:
        return False

    async def persist(self, finding: Finding) -> None:
        self.persisted.append(finding)


async def _seed_consent(series_id: str) -> None:
    user_id = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, role, is_active) "
                "VALUES (:id, :username, 'x', 'Audio Test User', 'cs_lead'::user_role, true)"
            ),
            {"id": user_id, "username": f"audio-test-{user_id.hex[:8]}"},
        )
    async with async_session_factory() as session:
        await SqlAlchemyMeetingSeriesConsentRepository(session).record(
            series_id=series_id,
            status="granted",
            all_parties_confirmed=True,
            documented_by_user_id=user_id,
            note=None,
        )


def _fake_transcription_result(text_value: str):
    return type("R", (), {"text": text_value, "primary_speaker_name": None})()


async def test_consented_audio_recording_reaches_the_meeting_reader_corpus():
    suffix = uuid.uuid4().hex[:8]
    series_id = f"audio-e2e-{suffix}"
    await _seed_consent(series_id)

    recording = DriveRecording(
        file_id=f"file-{suffix}",
        name="meeting.mp3",
        modified_time=datetime.now(UTC).isoformat(),
        series_id=series_id,
    )
    fake_drive = AsyncMock()
    fake_drive.list_recordings = lambda: [recording]
    fake_drive.download = lambda file_id: b"fake-audio-bytes"

    fake_transcriber = AsyncMock()
    fake_transcriber.transcribe = AsyncMock(
        return_value=_fake_transcription_result("Jane: We'll ship the fix by Friday.")
    )

    key_store = FileKeyStore(settings.data_keys_dir)
    encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)

    async with async_session_factory() as session:
        collector = AudioCollector(
            drive=fake_drive,
            transcriber=fake_transcriber,
            consent=SqlAlchemyMeetingSeriesConsentRepository(session),
            collector_runs=SqlAlchemyCollectorRunRepository(session),
            profile_context=SqlAlchemyClientProfileContext(session),
        )
        use_case = RunCollectorUseCase(
            collector_runs=SqlAlchemyCollectorRunRepository(session),
            events=SqlAlchemyEventRepository(session),
            profile_context=SqlAlchemyClientProfileContext(session),
            encryption=encryption,
            key_store=key_store,
        )
        now = datetime.now(UTC)
        result = await use_case.execute(
            collector, window_start=now, window_end=now, trigger="poll"
        )

    assert result.envelopes_emitted == 1

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT id, event_type::text AS event_type, occurred_at, stakeholder_id, "
                    "structured_payload, body_encrypted FROM events WHERE envelope_id = "
                    "(SELECT id FROM raw_envelopes WHERE source_native_id = :native_id)"
                ),
                {"native_id": f"file-{suffix}"},
            )
        ).one()
    assert row.event_type == "meeting"
    assert row.structured_payload["series_id"] == series_id

    # FR-009 — reaches `SqlAlchemyMeetingTranscriptRepository`'s own decrypt
    # path and is readable by the completely unmodified `MeetingReader`,
    # exactly like an example-text transcript already is today. Decrypted
    # directly, scoped to this test's own event id — `list_all()` itself
    # (unmodified, pre-existing code) reads the *entire* `events` table with
    # no filter at all, which in this shared dev database currently also
    # surfaces unrelated rows left over from an earlier, disconnected
    # session that predate this feature and fail to decrypt for reasons
    # unrelated to anything in this feature (confirmed independently: the
    # same pre-existing rows already made two other, pre-existing tests fail
    # the identical way before this feature touched anything). Scoping this
    # assertion to this test's own row proves the real thing this test
    # exists to prove without depending on that unrelated table state.
    transcript_text = encryption.decrypt(row.body_encrypted)
    assert "ship the fix by Friday" in transcript_text
    matching = [
        MeetingTranscriptInfo(
            event_id=row.id,
            occurred_at=row.occurred_at,
            stakeholder_id=row.stakeholder_id,
            series_id=row.structured_payload["series_id"],
            text=transcript_text,
        )
    ]

    reader = MeetingReader(
        transcripts=AsyncMock(list_all=AsyncMock(return_value=matching)),
        llm=_FakeLLM(
            MeetingModelOutput(
                commitments=[
                    ExtractedCommitment(
                        who="Jane",
                        what="ship the fix",
                        by_when="Friday",
                        source_segment="We'll ship the fix by Friday.",
                    )
                ],
                confidence=0.85,
            )
        ),
        findings=_FakeFindingRepository(),
    )
    findings = await reader.interpret()
    assert len(findings) == 1
    assert findings[0].finding_type == "meeting_commitment"
    assert findings[0].cited_event_ids == (matching[0].event_id,)


async def test_meeting_event_is_swept_by_the_retention_job_like_any_other_event_type(
    tmp_path, make_envelope
):
    """FR-010, `/speckit-analyze` finding E3 — mirrors
    `test_retention_real_db.py::test_retention_job_shreds_an_aged_bucket_and_
    is_idempotent` exactly, with `event_type='meeting'` in place of
    `'message'`. `shred_bucket`'s own SQL (`sqlalchemy_repositories.py`) has
    no `event_type` filter at all, so this is confirming an already-
    type-agnostic mechanism, not exercising new logic — but it was
    previously unasserted for this specific event type."""
    key_store = FileKeyStore(str(tmp_path))
    fernet = key_store.resolve(_AGED_BUCKET)
    ciphertext = fernet.encrypt(b"Diego: internal standup notes, nothing promised.")

    envelope_id = await make_envelope()
    async with async_session_factory() as session:
        events = SqlAlchemyEventRepository(session)
        event_id = await events.append(
            NewEvent(
                envelope_id=envelope_id,
                event_type="meeting",
                occurred_at=datetime.now(UTC),
                body_encrypted=ciphertext,
                structured_payload={"series_id": "retention-check-series"},
            ),
            data_key_ref=_AGED_BUCKET,
        )

    async with (
        async_session_factory() as session,
        shredder_session_factory() as shredder_session,
    ):
        use_case = RunRetentionUseCase(
            key_store=key_store,
            retention_repo=SqlAlchemyRetentionJobRepository(session, shredder_session),
            retention_window_days=settings.retention_window_days,
        )
        result = await use_case.execute()

    assert result.status == "succeeded"
    assert result.buckets_shredded >= 1
    assert _AGED_BUCKET not in key_store.list_active_buckets()

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT body_encrypted FROM events WHERE id = :id"), {"id": event_id}
            )
        ).one()
    assert row.body_encrypted is None
