# Implementation Plan: Meeting Audio Ingestion

**Branch**: `019-meeting-audio-ingestion` | **Date**: 2026-08-19 | **Revised**: 2026-08-20 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/019-meeting-audio-ingestion/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

**2026-08-20 revision**: the spec's audio source changed from Google Drive to local storage
(installation friction — Drive's OAuth/app-registration setup was too heavy for the demo). This
plan is rewritten accordingly: every Drive-specific design decision below is replaced with its
local-storage equivalent. See `research.md`'s Decision 12 for the consolidated rationale and
`git log` on this branch for the Drive-era implementation this replaces (`google_drive_client.py`,
`google_drive_token_store.py` — both slated for deletion by `/speckit-tasks`).

## Summary

Add the one real component the existing meeting-evidence pipeline has always been missing: a
new `Collector` (`AudioCollector`) that discovers recordings in a configured local storage
folder, transcribes them via OpenAI Whisper with speaker diarization, and emits the exact
same `Envelope` shape `SimulatedCollector`'s calendar branch already produces — so the existing
`MeetingReader`, `meeting_commitment` finding type, identity resolution, redaction, encryption,
evidence trace, and scoring arithmetic require zero changes. Two new things make that safe to
ship: an auditable, append-only `meeting_series_consent` table that structurally gates
collection (replacing the fixture-only boolean both the audio path and, per `research.md`
Decision 3, the existing demo path relied on), and two ways to trigger a cycle — a scheduled
`APScheduler` job (`worker.py`) and a CS-lead-only manual-refresh endpoint. An inaccessible
storage location or a failed transcription surfaces through the existing coverage/score-freeze
mechanism (`specs/004-score-engine` FR-011), via one small, additive extension to
`RunCollectorUseCase.execute()`'s failure handling (`research.md` Decision 5). Local storage
requires no external account, no OAuth grant, and no new secret — the CS lead drops a file into
an already-mounted folder (`research.md` Decision 12), which is the entire point of this
revision.

## Technical Context

**Language/Version**: Python 3.12 (backend, unchanged); TypeScript/React 18 (frontend, small
addition only — a consent-management control and a refresh button)

**Primary Dependencies**: FastAPI, SQLAlchemy (async) + asyncpg, APScheduler — all existing.
No new listing/download library — local storage discovery uses only the standard library
(`pathlib`), replacing the `google-api-python-client` + `google-auth` dependency the Drive-era
design needed (`research.md` Decision 12, both removed by `/speckit-tasks`). `openai` SDK is
already a dependency (`OpenAIEmbeddingAdapter`) and is reused for the Whisper transcription
call; `pyannoteai-sdk` (hosted diarization API, `research.md` Decision 7) is unaffected by this
revision — diarization operates on already-read audio bytes regardless of where they came from

**Storage**: PostgreSQL 16 (existing) — one new table, `meeting_series_consent`
(`data-model.md`); no change to any existing table's shape

**Testing**: pytest + `hypothesis` (existing pattern) — new unit tests for `AudioCollector`,
the consent gate, and `WhisperTranscriptionAdapter` with a real temporary directory (via
`tmp_path`, standard pytest fixture — simpler than the mocked-client pattern the Drive-era
design needed, since there is no external API surface left to fake for discovery/reads) and
mocked OpenAI/pyannote.ai clients (mirroring `OpenAIEmbeddingAdapter`'s deferred-client
pattern); a real-DB integration test extending
`tests/ingestion/test_post_mvp_sources_real_db.py`'s existing pattern

**Target Platform**: Linux server, Docker Compose, one stack per client deployment (unchanged)

**Project Type**: Web application (existing `backend/` + `frontend/` split) — this feature adds
backend-heavy; the frontend addition is a small consent control + refresh button, not a new
top-level feature area

**Performance Goals**: Not latency-critical — a background/on-demand batch job, not a
request-path component. SC-003's "under one minute, excluding transcription time" bounds only
the manual-refresh *request* overhead, not the transcription itself

**Constraints**: No audio persistence anywhere, at any point beyond the source folder itself
(FR-008/SC-004 — an in-memory/temp copy made during processing is discarded; the source
recording in the local storage folder is left untouched, exactly as the Drive-era design never
deleted anything from Drive either); consent must be checked at collection time on every cycle,
not cached as a one-time decision (FR-003); zero changes to `backend/app/scoring/` or
`backend/app/readers/` required or permitted; a single configured local storage directory per
deployment (Assumptions)

**Scale/Scope**: One deployment, one client, a handful of meeting series, on the order of a few
recordings per week — well within the existing 50k–200k events/year deployment scale
(`architecture/03-technology-stack.md`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **P1 (Evidence or it does not exist)** — PASS. Unaffected: `MeetingReader` already cites real
  `event_id`s; `AudioCollector` only changes how those `events` rows are produced, not the
  citation mechanism.

- **P2 (The model interprets, code calculates)** — PASS. All new adapter code (local storage
  client, Whisper adapter) lives in `backend/app/ingestion/adapters/` — nothing in
  `backend/app/scoring/` changes or gains an import. The static no-LLM-in-scoring CI check is
  unaffected because nothing in this feature touches that module.

- **P3 (Each component refuses to do the next one's job)** — PASS. `AudioCollector` fetches and
  transcribes; it does not decide what counts as a commitment (that stays `MeetingReader`'s job,
  unchanged) and does not decide consent policy (it only *checks* the consent gate a CS lead
  already decided). Matches `SimulatedCollector`'s existing precedent of a structural,
  no-judgment consent filter.

- **P4 (A human always sends)** — PASS, with one clarification: this feature calls an external
  processing API (Whisper) to transcribe audio the client already consented to have processed.
  That is not the "send" capability P4 prohibits (a draft or message going *to the client or a
  third party on the product's behalf*) — it is the same category of outbound API call the Tone,
  Intent, and Recurrence readers already make to Anthropic/OpenAI today, governed by the same
  AI-safety rules, not a new kind of capability.

- **P5 (Admit what we cannot see)** — PASS, contingent on `research.md` Decision 5 landing as
  designed: a local-storage-access or transcription failure must flow into the *same*
  `coverage_reports`/score-freeze mechanism every other source's failure already uses, not a
  bespoke, second reporting path. This is the one piece of this feature with real risk of
  quietly diverging from the constitution if implemented as a `worker.py`-only try/except
  instead — flagged explicitly in Complexity Tracking below.

- **P6 (Silence is a success state)** — PASS. No new UI surface manufactures concern; the
  consent control and refresh button are CS-lead-initiated actions, not passive alerts, and the
  degraded-source notice reuses the existing coverage-gap presentation rather than adding a new
  one.

- **P8 (Clean Architecture: the Dependency Rule is law)** — PASS by construction: new adapters
  (`local_storage_client.py`, `whisper_transcription.py`, `audio_collector.py`,
  `sqlalchemy_meeting_series_consent.py`) live in `backend/app/ingestion/adapters/`; the new
  port (`MeetingSeriesConsentRepositoryPort`) lives in `backend/app/ingestion/application/
  ports.py`; no domain code gains a framework or SDK import. `local_storage_client.py` imports
  only `pathlib`/`os` (standard library) — strictly simpler than the Drive-era adapter it
  replaces, which needed `google.*` imports fenced off. `/speckit-tasks` must add (or confirm)
  an import-linter contract restricting `openai`/`pyannoteai` imports to the adapters layer
  within `ingestion`, mirroring the existing `readers-application-purity` contract (the `google.*`
  restriction this contract previously needed is removed along with the dependency itself).

- **P9 (Test-first determinism)** — PASS. Golden-replay, decimal-reconciliation, and
  monotonicity tests are unaffected (this feature never touches `backend/app/ledger/` or
  `backend/app/scoring/`'s own logic). New behavior gets its own unit + integration tests per
  the Testing context above; `research.md` Decision 5's `RunCollectorUseCase` change is additive
  and every existing test involving it continues to pass unmodified (the new `try/except` only
  activates when `fetch()` raises, which no existing `Collector` implementation ever did before
  now).

- **P10 (Simplicity over speculative generality)** — PASS. No new "Collection Cycle" table
  (reuses `collector_runs`/`coverage_reports`, `data-model.md`); no plugin/discovery mechanism
  for meeting sources (still exactly one real audio source); consent modeled as one append-only
  table, not a mutable-plus-history pair.

- **AI safety rules (Development Workflow & Quality Gates)** — the Whisper transcription call
  itself is not a new instance of "a place this codebase generates prose as a decision artifact"
  (Rule 1's inventory: Narrator, Draft composer, Ask agent `text_only`/`hybrid`) — its output is
  raw transcribed speech, evidentiary data equivalent to an email body, not a model-generated
  claim requiring `fact_check()`. The *existing* `MeetingReader` LLM call that reads that
  transcript and extracts a structured commitment remains the one governed by Rules 1–5, and is
  completely unchanged by this feature. **Follow-up**: this feature's Whisper/diarization calls
  need their own resilience budget (timeout/retry) — local file reads themselves are effectively
  instantaneous and need no budget of their own, unlike the Drive-era design's network-bound
  listing/download calls — the constitution's existing "Resilience budgets"
  paragraph only enumerates LLM-call budgets today. `/speckit-tasks` should size one (consistent
  with the Tone/Intent/Meeting readers' 8s × 2 retries precedent, scaled for a
  file-length-dependent transcription call), and a follow-up constitution amendment — the same
  pattern features 011 and 014 both followed after implementation — should add it as a new row
  once the real number is known from testing, not guessed here.

No violation requires a rejected-simpler-alternative justification beyond the one already
argued in `research.md` Decision 5 (touching `RunCollectorUseCase`, shared core code) — carried
into Complexity Tracking below because it's the one change in this feature that isn't purely
additive-and-isolated.

## Project Structure

### Documentation (this feature)

```text
specs/019-meeting-audio-ingestion/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── meeting-audio.md # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── ingestion/
│   │   ├── adapters/
│   │   │   ├── simulated_collector.py         # existing — consent check migrated to the new port (Decision 3)
│   │   │   ├── meeting_envelope.py             # NEW — shared envelope-building, extracted (Decision 2)
│   │   │   ├── audio_collector.py              # NEW — Collector impl, source_type="transcripts"; depends on
│   │   │   │                                    #   CollectorRunRepositoryPort too (Decision 10 — pre-read
│   │   │   │                                    #   idempotency check, not just RunCollectorUseCase's post-fetch one)
│   │   │   ├── local_storage_client.py         # NEW (replaces google_drive_client.py) — folder listing +
│   │   │   │                                    #   file reads via pathlib only (Decision 12); no token/secret
│   │   │   ├── whisper_transcription.py        # NEW — mirrors OpenAIEmbeddingAdapter's pattern
│   │   │   └── sqlalchemy_repositories.py       # existing — + SqlAlchemyMeetingSeriesConsentRepository
│   │   ├── application/
│   │   │   ├── ports.py                         # existing — + MeetingSeriesConsentRepositoryPort
│   │   │   └── use_cases.py                     # existing — RunCollectorUseCase.execute() gets Decision 5's try/except
│   │   │                                     #   AND a caller-supplied `trigger` param (Decision 5's correction,
│   │   │                                     #   finding F2 — replaces the hard-coded "manual" literal)
│   │   └── domain/                              # unchanged
│   ├── config.py                                # existing — + audio_poll_interval_hours, meeting_audio_storage_path
│   │                                             #   (replaces the four google_drive_* settings — no secret/credential)
│   └── worker.py                                # existing — + _run_audio_collector job, "audio" in --run-once
├── migrations/versions/
│   └── 0006_meeting_series_consent.py           # NEW
└── tests/
    ├── ingestion/
    │   ├── test_audio_collector.py               # NEW — unit, tmp_path storage root + mocked Whisper
    │   ├── test_meeting_series_consent.py         # NEW — unit, the consent gate/port
    │   └── test_post_mvp_sources_real_db.py       # existing — consent seeding updated per Decision 3's compatibility note
    └── unit/
        └── test_simulated_collector.py            # existing — consent-gate assertions updated to use the new port

frontend/
└── src/
    └── coverage/                                # existing feature dir — consent status + refresh button added here,
                                                   # alongside the existing degraded-source presentation (no new top-level feature area)
```

**Structure Decision**: Existing `backend/app/ingestion/` module (Clean Architecture layers
already in place) gets new adapter and port files, no new module. Existing `backend/app/worker.py`
gets one new scheduled job, following its established `_run_*`/`--run-once` pattern exactly.
Frontend addition is scoped to the existing `coverage` feature directory rather than a new one —
consent status and source health are both "is this source okay" information the CS lead already
looks at in one place.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `RunCollectorUseCase.execute()` (shared, existing core code) gets a `try/except` around `collector.fetch()` (`research.md` Decision 5) | `AudioCollector` is the first `Collector` whose `fetch()` can genuinely raise (the configured local storage path missing, unmounted, or permission-denied) — FR-012/FR-014 require that failure to freeze the score via the *existing* coverage mechanism, and the only place that mechanism's bookkeeping (`collector_runs`, `coverage_reports`) lives today is inside `execute()` | Catching the exception only in `worker.py`'s new job wrapper and hand-writing an equivalent `collector_runs`/`coverage_reports` sequence there — rejected: duplicates `execute()`'s bookkeeping for one collector, and leaves the manual-refresh endpoint (which also calls `execute()` directly) without the same handling, silently reintroducing the exact crash-on-failure gap this row exists to close |
| `RunCollectorUseCase.execute()` gains a `trigger: str` parameter, replacing its hard-coded `"manual"` literal (`research.md` Decision 5's correction, `/speckit-analyze` finding F2) | The scheduled poll (`worker.py`) and the manual-refresh endpoint both call this same method and both need `collector_runs.trigger` to actually distinguish `'poll'` from `'manual'` — `contracts/meeting-audio.md` already documents that distinction as real. Without this, every scheduled poll would silently mislabel itself as manual, an operationally misleading audit trail rather than a functional break | Leaving `"manual"` hard-coded and accepting the mislabeling — rejected: it is not merely cosmetic, `collector_runs.trigger` is this schema's one durable record of *why* a collection run happened, and `ReplayUseCase.execute(*, trigger: str, ...)` already establishes the caller-supplied-trigger pattern this codebase uses elsewhere for the identical need, so following it is not a novel abstraction, just consistency |
| `AudioCollector`'s constructor depends on `CollectorRunRepositoryPort` directly, not only on the ports `Collector` implementations have needed so far (`research.md` Decision 10, `/speckit-analyze` finding F1) | `fetch()` must check `envelope_exists()` *before* downloading/transcribing, not only rely on `RunCollectorUseCase`'s existing post-fetch dedup — otherwise every scheduled poll re-transcribes every still-present recording, forever, violating FR-011 in real operation, not just its persistence-layer outcome | Tracking "already processed" file IDs in `AudioCollector`'s own local state instead — rejected: duplicates state the ledger already durably tracks, drifts across restarts, and breaks under two concurrent runs (a manual refresh racing a scheduled poll) — exactly the class of problem `envelope_exists()` already exists to solve once, centrally |
