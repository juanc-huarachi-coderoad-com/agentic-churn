"""`AudioCollector` — the real, first external-API `Collector`
(specs/019-meeting-audio-ingestion). Invoked through its own, independent
`RunCollectorUseCase.execute(audio_collector, ...)` call (research.md
Decision 1), never merged with `SimulatedCollector`'s run.

`fetch()`, per Drive recording:
1. Checks the real consent audit table before downloading anything
   (structural gate, mirrors `SimulatedCollector`, research.md Decision 3) —
   a folder whose name matches no real series is simply never active either,
   so this single check also covers research.md Decision 11 without a
   second "known series" lookup.
2. Skips a recording whose `idempotency_key` already has a matching
   `raw_envelopes` row *before* downloading or transcribing it (research.md
   Decision 10 — the load-bearing fix for `/speckit-analyze` finding F1;
   `RunCollectorUseCase`'s own post-fetch dedup exists too, but only
   prevents a duplicate row, not the expensive work this check avoids).
3. Downloads, transcribes, and lets the in-memory audio bytes go out of
   scope once transcription completes or fails — never written to disk here
   (research.md Decision 8; the one real temp file in this pipeline,
   `pyannote_diarization.py`'s, deletes itself in its own `finally` block).
4. A per-item failure (corrupt audio, transcription error) is logged and
   skipped without aborting the cycle (FR-013).
5. A whole-connection failure (`GoogleDriveAuthenticationError`) is allowed
   to propagate out of `fetch()` — `RunCollectorUseCase.execute()`'s own
   try/except (research.md Decision 5) records it as an honest, visible
   coverage gap (FR-012/FR-014), not a crash.

`normalize()` reuses `build_meeting_envelope` (research.md Decision 2) —
zero changes anywhere downstream of `fetch()`/`normalize()` (FR-009).
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.ingestion.adapters.google_drive_client import GoogleDriveClient
from app.ingestion.adapters.meeting_envelope import build_meeting_envelope
from app.ingestion.adapters.whisper_transcription import WhisperTranscriptionAdapter
from app.ingestion.application.collector import Collector
from app.ingestion.application.ports import (
    ClientProfileContextPort,
    CollectorRunRepositoryPort,
    MeetingSeriesConsentRepositoryPort,
)
from app.ingestion.domain.envelope import Envelope, idempotency_key

logger = logging.getLogger(__name__)

# architecture/06-error-handling.md's "Meeting audio ingestion" resilience
# budget — a documented initial estimate, not yet live-tested against a
# real recording (this implementation environment has no real Drive/OpenAI/
# pyannote access); recalibrate once a real deployment has run this.
_PER_ITEM_TIMEOUT_SECONDS = 300.0


@dataclass
class AudioCollectionStats:
    """Per-`fetch()`-call counters, exposed via `last_run_stats` —
    `contracts/meeting-audio.md`'s refresh response needs this finer
    breakdown than `CollectorRunResult`'s `envelopes_emitted`/
    `duplicates_skipped` alone provide. A fresh `AudioCollector` is
    constructed per request/scheduled cycle (`audio_refresh_router.py`,
    `worker.py`), so this is never shared or stale across runs."""

    recordings_found: int = 0
    skipped_no_consent: int = 0
    already_processed: int = 0
    failed: int = 0
    transcribed: int = 0


class AudioCollector(Collector):
    source_type = "transcripts"
    # `mvp_sources_always_expected` stays at `Collector`'s own default
    # (`False`) — this is exactly the dedicated, single-purpose collector
    # case that flag exists to distinguish from `SimulatedCollector`.

    def __init__(
        self,
        drive: GoogleDriveClient,
        transcriber: WhisperTranscriptionAdapter,
        consent: MeetingSeriesConsentRepositoryPort,
        collector_runs: CollectorRunRepositoryPort,
        profile_context: ClientProfileContextPort,
    ) -> None:
        self._drive = drive
        self._transcriber = transcriber
        self._consent = consent
        self._collector_runs = collector_runs
        self._profile_context = profile_context
        self.last_run_stats = AudioCollectionStats()

    async def fetch(self, window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
        stats = AudioCollectionStats()
        self.last_run_stats = stats
        recordings = self._drive.list_recordings()  # GoogleDriveAuthenticationError propagates
        stats.recordings_found = len(recordings)
        profile = await self._profile_context.get_current()
        candidate_names = [s.name for s in profile.stakeholders if s.name]
        # Real identifier (an email/username `resolve_identity` can actually
        # match), keyed by the same display name the transcription adapter
        # matches against — `structured_payload["participant"]` needs an
        # exact-lookup identifier, never a display name (the mismatch this
        # dict exists to avoid: found during implementation, before it could
        # ship as a silent "every audio finding is unresolved" bug).
        identifier_by_name = {
            s.name: s.identifiers[0] for s in profile.stakeholders if s.name and s.identifiers
        }

        items: list[dict[str, Any]] = []
        for recording in recordings:
            if not await self._consent.is_active(recording.series_id):
                stats.skipped_no_consent += 1
                continue

            key = idempotency_key(self.source_type, recording.file_id)
            if await self._collector_runs.envelope_exists(key):
                stats.already_processed += 1
                continue

            try:
                audio_bytes = self._drive.download(recording.file_id)
                result = await asyncio.wait_for(
                    self._transcriber.transcribe(audio_bytes, recording.name, candidate_names),
                    timeout=_PER_ITEM_TIMEOUT_SECONDS,
                )
            except Exception:
                # Includes `asyncio.TimeoutError` (`architecture/06-error-
                # handling.md`'s "Meeting audio ingestion" budget) — bounds
                # the Whisper API call reliably (it has real `await` points
                # `wait_for` can act on); the diarization pass inside
                # `transcribe()` is a synchronous, CPU-bound `pyannote.audio`
                # call with no `await` point of its own, so a wait_for
                # around it can only report the timeout once that call
                # finally returns, not preempt it mid-call — a known,
                # documented limitation, not a false "hard ceiling" claim.
                stats.failed += 1
                logger.exception(
                    "meeting audio item failed, skipped (FR-013): series=%s file=%s",
                    recording.series_id,
                    recording.file_id,
                )
                continue

            if not result.text:
                continue  # no discernible speech — a normal, valid outcome (spec.md's Edge Cases)

            stats.transcribed += 1
            items.append(
                {
                    "source_native_id": recording.file_id,
                    "occurred_at": recording.modified_time,
                    "transcript": result.text,
                    "attendee": identifier_by_name.get(result.primary_speaker_name or "", ""),
                    "series_id": recording.series_id,
                    "consent_documented": True,
                }
            )
        return items

    def normalize(self, raw_item: dict[str, Any]) -> Envelope:
        return build_meeting_envelope(
            source_native_id=raw_item["source_native_id"],
            occurred_at=datetime.fromisoformat(raw_item["occurred_at"]),
            transcript=raw_item["transcript"],
            attendee=raw_item["attendee"],
            series_id=raw_item["series_id"],
            consent_documented=raw_item["consent_documented"],
        )
