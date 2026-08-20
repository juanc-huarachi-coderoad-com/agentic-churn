"""Shared meeting-transcript `Envelope` building — extracted from
`SimulatedCollector` (specs/019-meeting-audio-ingestion, research.md
Decision 2) so the new `AudioCollector` reuses the exact same shape rather
than a second, drift-prone implementation. Nothing about the `Envelope`
downstream consumers see changes: same `source_type="transcripts"`, same
`structured_payload` keys — `_event_type_for_source`,
`SqlAlchemyMeetingTranscriptRepository`, and `MeetingReader` all require zero
changes regardless of which collector produced the envelope.

`source_type="transcripts"` (the enum value), not `"calendar"` — `sources.
source_type` is looked up as a singleton per value (`get_or_create_source`),
and `"calendar"` is already claimed by `DetectAbsenceUseCase.
ABSENCE_SOURCE_TYPE` for its internally-generated absence events.
`source_type` (data-base/10-ddl-appendix.md's enum) deliberately carries both
`calendar` and `transcripts` as distinct values for exactly this reason.
"""

from datetime import datetime

from app.ingestion.domain.envelope import Envelope

MEETING_SOURCE_TYPE = "transcripts"
MEETING_SOURCE_DISPLAY_NAME = "Meridian — Calendar/transcripts"


def build_meeting_envelope(
    *,
    source_native_id: str,
    occurred_at: datetime,
    transcript: str,
    attendee: str,
    series_id: str,
    consent_documented: bool,
) -> Envelope:
    """`consent_documented` is descriptive metadata only (what the caller
    believes to be true) — it is never the enforcement point. Collection-time
    consent enforcement lives in each collector's `fetch()`, against the real
    `meeting_series_consent` audit table (research.md Decision 3), before an
    item ever reaches this function."""
    return Envelope(
        source_type=MEETING_SOURCE_TYPE,
        source_native_id=source_native_id,
        occurred_at=occurred_at,
        identity_status="unresolved",
        resolved_stakeholder_id=None,
        redacted_fields=[],
        payload_text=transcript,
        structured_payload={
            "participant": attendee,
            "series_id": series_id,
            "consent_documented": consent_documented,
        },
    )
