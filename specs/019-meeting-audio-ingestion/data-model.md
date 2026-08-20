# Phase 1 Data Model: Meeting Audio Ingestion

One new table. Zero changes to any existing table's shape — `sources`, `collector_runs`,
`coverage_reports`, `raw_envelopes`, and `events` already have every column this feature needs
(`source_type` already has a `'transcripts'` value, `collector_trigger` already has `'poll'` and
`'manual'`; `data-base/10-ddl-appendix.md:45-74`). The new table's "who did this" column is a
real `users.id` foreign key, per the constitution's Ownership columns rule.

## New: `meeting_series_consent` (User Story 2, FR-004/FR-005)

One row per consent decision (grant or revoke) for one recurring meeting series — insert-only,
so "current status" is always the latest row per `series_id`, never an edited field
(`research.md` Decision 4).

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `series_id` | TEXT NOT NULL | Matches `events.structured_payload->>'series_id'` for `event_type = 'meeting'` rows — the same identifier `SqlAlchemyMeetingTranscriptRepository` already reads (`backend/app/readers/adapters/sqlalchemy_repository.py:336`) |
| `status` | ENUM(`granted`,`revoked`) NOT NULL | |
| `all_parties_confirmed` | BOOLEAN NOT NULL | The CS lead's explicit attestation that every participant in the series consented, not just the client-side sponsor — a `granted` row with this `false` is rejected at the application boundary (FR-005 requires *all-party* consent, not partial) |
| `documented_by_user_id` | UUID NOT NULL, FK → `users.id` | Ownership column, per constitution. Restricted at the application boundary to `role = cs_lead` (FR-016) |
| `documented_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| `note` | TEXT NULL | Free-text context (e.g. how consent was obtained) — never parsed or relied on programmatically |

**Validation rules:** A `granted` row requires `all_parties_confirmed = true`. `series_id` is
never empty. Insert-only — matches every other audit-shaped table in this schema
(`collector_runs`, `retention_job_runs`, `finding_type_config_changes`).

**Relationships:** No FK to `events`/`raw_envelopes` — consent gates *future* collection by
`series_id` string match, the same loose coupling `structured_payload->>'series_id'` already
has to everything else; a consent decision is not "about" any single event.

**Query pattern:** "is `series_id` currently consented?" = `SELECT status FROM
meeting_series_consent WHERE series_id = :series_id ORDER BY documented_at DESC LIMIT 1` =
`'granted'`. Exposed through a new `MeetingSeriesConsentRepositoryPort.is_active(series_id) ->
bool` (`backend/app/ingestion/application/ports.py`), called by both `AudioCollector.fetch()`
and (after `research.md` Decision 3's migration) `SimulatedCollector.fetch()`.

## Reused, unchanged: `sources` / `collector_runs` / `coverage_reports`

Satisfies the spec's "Collection Cycle" key entity without a new table. A scheduled or manual
audio-collection run is one more `collector_runs` row (`trigger = 'poll'` or `'manual'`,
`source_id` pointing at the `transcripts` row in `sources`) exactly like every existing
collector run; `coverage_reports.gap_reason`/`sources_read` already carry the "what failed and
why" detail FR-013/FR-014 require, once `research.md` Decision 5's `fetch()` failure handling
lands. No new "audio collection run" entity is introduced — it would duplicate what these three
tables already do for every other source.

## Reused, unchanged: `events` / meeting transcript evidence

`AudioCollector`'s output becomes an `event_type = 'meeting'` row through the exact same
`_event_type_for_source("transcripts") -> "meeting"` mapping and `structured_payload` shape
(`participant`, `series_id`) `SimulatedCollector`'s calendar branch already produces
(`research.md` Decision 2). `MeetingTranscriptInfo`, `MeetingReader`, and the `meeting_commitment`
finding type (`backend/app/readers/application/meeting_reader.py`) are unmodified.

## Not a database entity: the transcribed-audio in-memory buffer

The downloaded audio bytes and the transcription-service response never reach a repository or a
table — `AudioCollector.fetch()` holds them only in memory (or an ephemeral temp file) for the
duration of one item's download-transcribe-discard sequence (`research.md` Decision 8). There is
nothing to model here precisely because FR-008 requires nothing to persist.

## Migration

`backend/migrations/versions/0006_meeting_series_consent.py` — the next sequential migration
after `0005_ask_queries_response_mode.py`. Adds `meeting_series_consent` and its `status` enum
only; no change to any existing table or enum.
