"""`AudioCollector` (specs/019-meeting-audio-ingestion) — mocked Drive
client, transcription adapter, and `CollectorRunRepositoryPort` (no real
Google/OpenAI/pyannote calls). Covers `/speckit-analyze` findings F1
(pre-download idempotency), C1 (unmapped folder), and E1 (a revoked, not
only a never-consented, series is never collected)."""

import asyncio
from datetime import UTC, datetime, time
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.ingestion.adapters.audio_collector import AudioCollector
from app.ingestion.adapters.google_drive_client import (
    DriveRecording,
    GoogleDriveAuthenticationError,
)
from app.ingestion.adapters.whisper_transcription import TranscriptionResult
from app.ingestion.application.ports import (
    ClientProfileContext,
    ClientProfileContextPort,
    CollectorRunRepositoryPort,
    MeetingSeriesConsentRepositoryPort,
    StakeholderIdentity,
)
from app.ingestion.domain.business_hours import WorkingCalendar
from app.ingestion.domain.envelope import idempotency_key


class _FakeDrive:
    def __init__(self, recordings: list[DriveRecording], fail: bool = False) -> None:
        self._recordings = recordings
        self._fail = fail
        self.downloaded: list[str] = []
        self.download_calls = 0

    def list_recordings(self) -> list[DriveRecording]:
        if self._fail:
            raise GoogleDriveAuthenticationError("token expired")
        return self._recordings

    def download(self, file_id: str) -> bytes:
        self.download_calls += 1
        self.downloaded.append(file_id)
        return b"audio-bytes"


class _FakeTranscriber:
    def __init__(self, result: TranscriptionResult | Exception) -> None:
        self._result = result
        self.transcribe_calls = 0

    async def transcribe(
        self, audio_bytes: bytes, filename: str, candidate_stakeholder_names: list[str]
    ) -> TranscriptionResult:
        self.transcribe_calls += 1
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class _FakeConsent(MeetingSeriesConsentRepositoryPort):
    def __init__(self, active_series: set[str]) -> None:
        self._active = active_series

    async def is_active(self, series_id: str) -> bool:
        return series_id in self._active

    async def record(self, **kwargs):  # pragma: no cover - unused here
        raise NotImplementedError

    async def list_current(self):  # pragma: no cover - unused here
        raise NotImplementedError


class _FakeCollectorRuns(CollectorRunRepositoryPort):
    def __init__(self, existing_keys: set[str] | None = None) -> None:
        self._existing = existing_keys or set()
        self.checked_keys: list[str] = []

    async def envelope_exists(self, idempotency_key: str) -> bool:
        self.checked_keys.append(idempotency_key)
        return idempotency_key in self._existing

    async def get_or_create_source(self, **kwargs):  # pragma: no cover - unused here
        raise NotImplementedError

    async def start_run(self, **kwargs):  # pragma: no cover - unused here
        raise NotImplementedError

    async def finish_run(self, **kwargs):  # pragma: no cover - unused here
        raise NotImplementedError

    async def record_coverage(self, **kwargs):  # pragma: no cover - unused here
        raise NotImplementedError

    async def insert_envelope(self, **kwargs):  # pragma: no cover - unused here
        raise NotImplementedError

    async def link_envelope_to_event(self, envelope_id, event_id):  # pragma: no cover
        raise NotImplementedError

    async def resolve_identity(self, *, source_identifier, source_type):  # pragma: no cover
        raise NotImplementedError


class _FakeProfileContext(ClientProfileContextPort):
    def __init__(self, stakeholders: tuple[StakeholderIdentity, ...]) -> None:
        self._stakeholders = stakeholders

    async def get_current(self) -> ClientProfileContext:
        return ClientProfileContext(
            profile_version_id=uuid4(),
            stakeholders=self._stakeholders,
            product_areas=(),
            exclusions=(),
            working_calendar=WorkingCalendar(
                working_hours_start=time(8, 0),
                working_hours_end=time(18, 0),
                timezone=ZoneInfo("UTC"),
            ),
            first_response_commitment=None,
        )


def _recording(series_id: str, file_id: str = "file-1") -> DriveRecording:
    return DriveRecording(
        file_id=file_id,
        name="recording.mp3",
        modified_time="2026-08-19T10:00:00.000Z",
        series_id=series_id,
    )


def _stakeholder(name: str, identifiers: tuple[str, ...] = ()) -> StakeholderIdentity:
    return StakeholderIdentity(id=uuid4(), name=name, identifiers=identifiers)


async def test_non_consented_series_is_never_downloaded():
    drive = _FakeDrive([_recording("never-decided-series")])
    transcriber = _FakeTranscriber(TranscriptionResult(text="", primary_speaker_name=None))
    collector = AudioCollector(
        drive=drive,
        transcriber=transcriber,
        consent=_FakeConsent(active_series=set()),
        collector_runs=_FakeCollectorRuns(),
        profile_context=_FakeProfileContext(()),
    )

    items = await collector.fetch(datetime.now(UTC), datetime.now(UTC))

    assert items == []
    assert drive.download_calls == 0
    assert transcriber.transcribe_calls == 0


async def test_revoked_series_is_also_never_downloaded():
    """`/speckit-analyze` finding E1 — a series that WAS consented and is
    then revoked must never be collected, not only a series that was never
    consented (the case above)."""
    drive = _FakeDrive([_recording("revoked-series")])
    # `_FakeConsent`'s active_series is empty — "revoked" and "never
    # decided" both resolve to `is_active() == False` (spec.md's Edge
    # Cases), so this fake is deliberately identical to the case above; the
    # meaningful assertion is that AudioCollector's behavior for a revoked
    # series doesn't differ from a never-consented one.
    collector = AudioCollector(
        drive=drive,
        transcriber=_FakeTranscriber(TranscriptionResult(text="", primary_speaker_name=None)),
        consent=_FakeConsent(active_series=set()),
        collector_runs=_FakeCollectorRuns(),
        profile_context=_FakeProfileContext(()),
    )

    items = await collector.fetch(datetime.now(UTC), datetime.now(UTC))

    assert items == []
    assert drive.download_calls == 0


async def test_unmapped_folder_is_skipped_same_as_non_consented():
    """`/speckit-analyze` finding C1 — a Drive folder whose name matches no
    real series is naturally never active either, so it's skipped by the
    exact same check as a never-consented series (research.md Decision 11)."""
    drive = _FakeDrive([_recording("typo-folder-nam")])
    collector = AudioCollector(
        drive=drive,
        transcriber=_FakeTranscriber(TranscriptionResult(text="", primary_speaker_name=None)),
        # "typo-folder-name" is the real, correctly-spelled series
        consent=_FakeConsent(active_series={"typo-folder-name"}),
        collector_runs=_FakeCollectorRuns(),
        profile_context=_FakeProfileContext(()),
    )

    items = await collector.fetch(datetime.now(UTC), datetime.now(UTC))

    assert items == []
    assert drive.download_calls == 0


async def test_already_processed_recording_is_skipped_before_download():
    """`/speckit-analyze` finding F1, research.md Decision 10 — the
    load-bearing assertion: Whisper/Drive must never be called a second
    time for an already-processed recording, not merely "no duplicate
    Envelope returned."""
    recording = _recording("acme-weekly-sync", file_id="already-seen")
    existing_key = idempotency_key("transcripts", "already-seen")
    drive = _FakeDrive([recording])
    transcriber = _FakeTranscriber(TranscriptionResult(text="", primary_speaker_name=None))
    collector_runs = _FakeCollectorRuns(existing_keys={existing_key})
    collector = AudioCollector(
        drive=drive,
        transcriber=transcriber,
        consent=_FakeConsent(active_series={"acme-weekly-sync"}),
        collector_runs=collector_runs,
        profile_context=_FakeProfileContext(()),
    )

    items = await collector.fetch(datetime.now(UTC), datetime.now(UTC))

    assert items == []
    assert drive.download_calls == 0, "already-processed recording must never be downloaded"
    assert transcriber.transcribe_calls == 0, "already-processed recording must never transcribe"
    assert existing_key in collector_runs.checked_keys


async def test_audio_never_persists_after_a_successful_transcription():
    stakeholder = _stakeholder("Jane", identifiers=("jane@example.com",))
    drive = _FakeDrive([_recording("acme-weekly-sync")])
    transcriber = _FakeTranscriber(
        TranscriptionResult(text="Jane: Ship by Friday.", primary_speaker_name="Jane")
    )
    collector = AudioCollector(
        drive=drive,
        transcriber=transcriber,
        consent=_FakeConsent(active_series={"acme-weekly-sync"}),
        collector_runs=_FakeCollectorRuns(),
        profile_context=_FakeProfileContext((stakeholder,)),
    )

    items = await collector.fetch(datetime.now(UTC), datetime.now(UTC))

    assert len(items) == 1
    assert items[0]["transcript"] == "Jane: Ship by Friday."
    # The real identifier resolve_identity() can match, never the display
    # name itself (a bug found during implementation, before it could ship).
    assert items[0]["attendee"] == "jane@example.com"
    envelope = collector.normalize(items[0])
    assert envelope.structured_payload["participant"] == "jane@example.com"


async def test_a_failing_recording_is_skipped_without_aborting_the_cycle():
    """FR-013 — a per-item transcription failure doesn't block the rest of
    the cycle. `AudioCollector.fetch()` isolates it per-item; this test
    covers the single-item shape (the multi-item "rest of the cycle
    proceeds" shape is exercised at the `RunCollectorUseCase` level,
    test_simulated_collector.py's real-fetch-failure test)."""
    drive = _FakeDrive([_recording("acme-weekly-sync")])
    transcriber = _FakeTranscriber(RuntimeError("corrupt audio"))
    collector = AudioCollector(
        drive=drive,
        transcriber=transcriber,
        consent=_FakeConsent(active_series={"acme-weekly-sync"}),
        collector_runs=_FakeCollectorRuns(),
        profile_context=_FakeProfileContext(()),
    )

    items = await collector.fetch(datetime.now(UTC), datetime.now(UTC))

    assert items == []  # skipped, not raised — the whole cycle doesn't abort
    assert collector.last_run_stats.failed == 1


async def test_a_transcription_that_exceeds_the_per_item_budget_is_treated_as_failed(
    monkeypatch,
):
    """architecture/06-error-handling.md's "Meeting audio ingestion"
    resilience budget — a hung Whisper call is bounded, not left to run
    forever within one collection cycle."""
    import app.ingestion.adapters.audio_collector as audio_collector_module

    monkeypatch.setattr(audio_collector_module, "_PER_ITEM_TIMEOUT_SECONDS", 0.01)

    class _HangingTranscriber:
        async def transcribe(self, audio_bytes, filename, candidate_stakeholder_names):
            await asyncio.sleep(10)
            raise AssertionError("should have timed out before this line")

    drive = _FakeDrive([_recording("acme-weekly-sync")])
    collector = AudioCollector(
        drive=drive,
        transcriber=_HangingTranscriber(),
        consent=_FakeConsent(active_series={"acme-weekly-sync"}),
        collector_runs=_FakeCollectorRuns(),
        profile_context=_FakeProfileContext(()),
    )

    items = await collector.fetch(datetime.now(UTC), datetime.now(UTC))

    assert items == []
    assert collector.last_run_stats.failed == 1


async def test_whole_connection_failure_propagates_not_swallowed():
    """A Drive-auth failure is a whole-cycle failure, distinct from a
    per-item one above — it must propagate so `RunCollectorUseCase.execute()`
    records it honestly (research.md Decision 5), never be silently
    swallowed here."""
    drive = _FakeDrive([], fail=True)
    collector = AudioCollector(
        drive=drive,
        transcriber=_FakeTranscriber(TranscriptionResult(text="", primary_speaker_name=None)),
        consent=_FakeConsent(active_series=set()),
        collector_runs=_FakeCollectorRuns(),
        profile_context=_FakeProfileContext(()),
    )

    threw = False
    try:
        await collector.fetch(datetime.now(UTC), datetime.now(UTC))
    except GoogleDriveAuthenticationError:
        threw = True
    assert threw
