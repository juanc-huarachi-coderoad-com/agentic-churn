# Research: Meeting Audio Ingestion

Phase 0 output. Every decision below was checked against what the repository already does
(cited by file path), not assumed from the feature brief — the brief's claim that this closes
a single, narrow gap in an already-built pipeline holds, with one correction: the
"per-item consent flag" it describes isn't legacy scaffolding to delete, it's `demo/fixtures/
meridian-week.json`'s own `consent_documented` boolean, read directly by `SimulatedCollector.
fetch()` (`backend/app/ingestion/adapters/simulated_collector.py:171`). Decision 2 below
addresses that directly.

## Decision 1 — `AudioCollector` is a new, independent `Collector`, not a `SimulatedCollector` change

**Decision**: Add `backend/app/ingestion/adapters/audio_collector.py`, a new class implementing
the existing `Collector` ABC (`backend/app/ingestion/application/collector.py`), with
`source_type = "transcripts"`. It is invoked through its own, separate
`RunCollectorUseCase.execute(audio_collector, ...)` call — a second, independent collector run
alongside the existing `SimulatedCollector` run, never merged into it.

**Rationale**: `RunCollectorUseCase.execute()` already takes any `Collector` instance
(`use_cases.py:313`) — this is precisely the Open/Closed extension point Constitution P8/P10
describe ("a 9th reader is one new class, never an `if reader_type == ...` branch"). The
`source_type` enum already has `'transcripts'` as a value (`data-base/10-ddl-appendix.md:47`),
`collector_trigger` already has `'poll'` and `'manual'` (`:61`) — every schema seam this
feature needs already exists.

**Alternatives considered**: Extending `SimulatedCollector` itself to optionally fetch real
audio — rejected: it would conflate a fixture-file reader with a live external-API client
inside one class, breaking Single Responsibility and making the fixture path (still needed for
every other demo source) depend on Drive/Whisper credentials being configured at all.

## Decision 2 — the envelope-normalization shape is extracted and shared, not duplicated

**Decision**: `_normalize_calendar` and the `"transcripts"` entry in `_SOURCE_DISPLAY_NAMES`
(`simulated_collector.py:15-21,118-139`) move to a small shared module,
`backend/app/ingestion/adapters/meeting_envelope.py`, exporting a `build_meeting_envelope(...)`
function. Both `SimulatedCollector.normalize()` and the new `AudioCollector.normalize()` call
it. Nothing about the `Envelope` shape changes — same `source_type="transcripts"`, same
`structured_payload` keys (`participant`, `series_id`, `consent_documented`) — so
`_event_type_for_source`, `SqlAlchemyMeetingTranscriptRepository.list_all()`, and
`MeetingReader` (`backend/app/readers/application/meeting_reader.py`) require **zero** changes,
exactly as the spec's FR-009 requires.

**Rationale**: avoids two independent implementations of "how a meeting item becomes an
`Envelope`" silently drifting apart (P10). `consent_documented` stays in `structured_payload`
for now purely because nothing downstream reads it from there — it's informational, not the
enforcement point (Decision 3 covers enforcement).

**Alternatives considered**: Leaving `_normalize_calendar` private to `SimulatedCollector` and
duplicating an equivalent function for `AudioCollector` — rejected as exactly the kind of
drift-prone duplication P10 warns against, for a four-line function with real behavioral
consequences (get one field name wrong and `MeetingReader` silently sees nothing).

## Decision 3 — a real `meeting_series_consent` table replaces the fixture-boolean gate, for *both* collectors

**Decision**: New table `meeting_series_consent` (see `data-model.md`), a new
`MeetingSeriesConsentRepositoryPort.is_active(series_id) -> bool` (added to
`backend/app/ingestion/application/ports.py`), and a `SqlAlchemyMeetingSeriesConsentRepository`
adapter. `AudioCollector.fetch()` calls `is_active()` for every folder/series it discovers,
before downloading anything, and drops non-consented series the same way
`SimulatedCollector.fetch()` already drops them today (`simulated_collector.py:160-172`) —
**and `SimulatedCollector.fetch()` is changed to call the same port instead of reading
`item["consent_documented"]` off the fixture.**

**Rationale**: the feature brief's own compliance framing ("nada de recolectar sin
consentimiento documentado... regla dura") only holds if there is one real, auditable consent
mechanism — not one real table for the audio path and one trust-the-fixture boolean for the
demo path. Migrating `SimulatedCollector` too means the demo itself exercises the real
consent-then-collect flow end to end, which directly serves this feature's "should be on the
demo" requirement. `consent_documented` stays in the fixture JSON and in `structured_payload`
as descriptive metadata (what the fixture author intended), but is no longer what gates
collection.

**Compatibility note**: `tests/ingestion/test_post_mvp_sources_real_db.py::
test_unconsented_calendar_series_never_reaches_the_ledger` and
`test_consented_transcript_reaches_the_meeting_reader_corpus` currently pass *because* the
fixture's booleans happen to match the series names asserted on (`meridian-qbr` consented,
`meridian-standup` not). Once the gate moves to the DB table, these tests must seed
`meeting_series_consent` rows for those two series before running the collector — a task for
`/speckit-tasks`, flagged here so it isn't discovered as a surprise mid-implementation.

**Alternatives considered**: A second, audio-only consent check that leaves
`SimulatedCollector`'s fixture boolean untouched — rejected per the rationale above; it would
ship an auditable consent table that the product's own demo doesn't actually rely on, which
undercuts the compliance story this feature exists to deliver.

## Decision 4 — consent is append-only, current status is "latest row per series"

**Decision**: `meeting_series_consent` is insert-only. Granting consent inserts a
`status='granted'` row; revoking inserts a `status='revoked'` row for the same `series_id`.
"Active" means the most recent row (`documented_at`) for that `series_id` has
`status='granted'`.

**Rationale**: matches this codebase's existing append-only audit pattern
(`retention_job_runs`, `raw_envelopes` — `data-model.md`'s note in
specs/011-production-hardening, and P9's "quarantine is never silently repaired" philosophy)
and directly satisfies FR-004's "durable, append-only, queryable audit record" — an `UPDATE`ed
boolean column could not prove *when* a revocation happened or preserve the trail of a
grant-revoke-regrant history, which auditability requires.

**Alternatives considered**: A single mutable row per series with a `status` column updated in
place, plus a separate history table for the audit trail — rejected as two tables doing the
job one append-only table already does; classic P10 speculative generality.

## Decision 5 — `RunCollectorUseCase.execute()` gets one small, additive failure path for a real `fetch()` exception

**Decision**: `RunCollectorUseCase.execute()`'s call to `collector.fetch()` (`use_cases.py:321`)
is wrapped in a `try/except`. On a caught exception, the affected source is recorded exactly
the way the existing `fail_sources` test seam already records a simulated failure
(`collector_runs.error` set, `coverage_reports.gap_reason` includes it, `sources_read` does not
count it) — `fail_sources` becomes a thin wrapper over the same real code path, not a parallel
one.

**Rationale**: today, `fail_sources` is the *only* way a source is ever marked unreachable —
it's a test-injected frozenset, never something a real `fetch()` raising an exception produces;
an actual exception from `collector.fetch()` today propagates uncaught and crashes the whole
run before a single `collector_runs` row is even written. `SimulatedCollector.fetch()` never
raises (it reads a committed local file), so this gap has never mattered before now.
`AudioCollector.fetch()` is the first `Collector` whose `fetch()` can genuinely fail — an
invalid/expired Drive OAuth token, a network error, Drive API rate-limiting — and FR-012/FR-014
require that failure to be visible and to freeze the score via the *existing* coverage/degrade
mechanism (`specs/004-score-engine` FR-011), not a second, bespoke failure-reporting path
bolted on in `worker.py`. Routing the real failure through the same recording code the
simulated one already uses is the smallest change that makes both true at once.

**Blast-radius check**: this is an additive `try/except` around one call in a single method;
no existing call site's behavior changes when `fetch()` doesn't raise (every current test still
passes unmodified). It touches core, shared code, so it is called out explicitly here and in
`plan.md`'s Complexity Tracking rather than left implicit in a task description.

**Alternatives considered**: Catching the exception only in `worker.py`'s new
`_run_audio_collector()` wrapper and hand-writing an equivalent `collector_runs`/
`coverage_reports` sequence there — rejected: it would duplicate `execute()`'s bookkeeping
(source/run creation, coverage recording) a second time for exactly one collector, is exactly
the kind of drift P10 warns about, and — unlike Decision 5 — would leave the *manual refresh*
endpoint (which also calls `execute()` directly, not through `worker.py`) without the same
failure handling, silently reintroducing the crash.

**Correction (`/speckit-analyze` finding F2)**: `execute()` also hard-codes `trigger="manual"`
at its `start_run(...)` call (`use_cases.py:358`) — there is no `trigger` parameter on `execute()`
today, unlike `ReplayUseCase.execute(*, trigger: str, ...)`'s existing precedent
(`use_cases.py:173`), which already threads a caller-supplied trigger through to the same kind
of `start_run` call. Both the scheduled poll (Decision 9) and the manual-refresh endpoint call
this same method, and need `collector_runs.trigger` to actually read `'poll'` vs `'manual'` —
the whole reason `collector_trigger`'s enum has both values (Decision 1). This decision's scope
therefore grows by one parameter: add `trigger: str` to `execute()`'s signature, threaded to
`start_run(...)` in place of the literal `"manual"`, in the same touch to this method as the
`try/except` above — one small, additive signature change to shared code, not two separate
changes to the same method in two different features' worth of work.

## Decision 6 — Google Drive OAuth token is a per-deployment file secret, mirroring `FileKeyStore`

**Decision**: A one-time, out-of-band OAuth consent grant (run manually by whoever provisions a
deployment, not by the application at request time) produces a refresh token, stored at
`secrets/google-drive-token.json` — sibling to `secrets/data.key` and `secrets/data-keys/`,
same gitignored, per-deployment-secret directory. A small `GoogleDriveTokenStore` adapter
reads/refreshes it, mirroring `FileKeyStore`'s (`backend/app/ingestion/adapters/key_store.py`)
shape: a thin file-backed adapter behind a port, swappable for a Phase 2 secret manager without
touching application code — the same Phase 1/Phase 2 split `architecture/03-technology-stack.md`
already documents for encryption keys.

**Rationale**: matches the existing "one deployment = one client = one `.env` file" isolation
model (constitution, "Isolation model") and requires no new secret-management infrastructure —
consistent with P10 and with this being the feature's first real external-API integration
(`research.md`'s framing note, `spec.md` Assumptions).

**Alternatives considered**: Storing the refresh token in the database — rejected: every other
credential-shaped secret in this codebase (encryption keys, role passwords) lives in the file
system/`.env`, not the database, and a DB-stored OAuth secret would need its own encryption
story this feature doesn't otherwise need.

## Decision 7 — transcription: OpenAI Whisper for text, a lightweight diarization pass for speaker turns

**Decision**: `WhisperTranscriptionAdapter` (`backend/app/ingestion/adapters/whisper_transcription.py`)
mirrors `OpenAIEmbeddingAdapter`'s lazy-client pattern (`backend/app/readers/adapters/
openai_embedding.py`) — deferred `AsyncOpenAI` construction, honest failure on a missing API
key. It calls the Whisper transcription endpoint with `response_format="verbose_json"` to get
word/segment-level timestamps, then aligns those timestamps against a diarization pass (speaker
turns by time) to produce per-segment speaker labels. A labeled segment is matched against the
client account's existing stakeholder roster (the candidate name set — see the "attendee source"
correction below) only when the match is unambiguous; otherwise the segment's speaker stays
unattributed — never guessed, satisfying FR-007/SC-006.

**Rationale**: OpenAI's hosted Whisper transcription endpoint transcribes speech to text but
does not itself label *which* voice said what — diarization is a distinct step. Documenting
this now (rather than discovering it mid-implementation) matters because the feature brief
states diarization as a fixed decision; the actual shape is "Whisper for the words, a separate
diarization pass for who said them," not a single API call that does both.

**Correction (`/speckit-analyze` finding C2) — attendee source**: the original wording here
("the same identity information already available to every other source's identity resolution")
glossed over a real mismatch. Every other source's identity resolution
(`identity_map`/`resolve_identity`) matches an already-present textual identifier *in* the
message (an email's `From` address) to a stakeholder — a lookup. Diarization needs the opposite:
a candidate *set* of plausible names to match an anonymous voice segment against, and nothing in
this system currently captures "who attended this specific meeting occurrence." Resolved
decision: match against the client account's **whole stakeholder roster** (already loaded via
`ClientProfileContextPort`, the same one every reader already has access to), not a
per-occurrence attendee list — a deployment's roster is small and bounded (single- to
low-double-digit people per account, `spec.md`'s revised Assumptions), so treating the entire
roster as the candidate set is a reasonable, implementable default rather than a per-meeting
lookup this system has no data source for. This trades a small amount of attribution precision
(a roster member who wasn't actually in this specific meeting is technically a candidate) for
not inventing a second, per-occurrence attendee-list mechanism — consistent with FR-007's "never
guess": a low-confidence match against even the full roster still stays unattributed.

**Alternatives considered**: Skipping diarization and attributing every segment to "unknown
speaker" — rejected, defeats FR-006/the product's own request for stakeholder-attributed
commitments, which is most of this feature's value (a commitment's weight in scoring depends on
*who* made it). Building a custom speaker-embedding model — rejected outright as far beyond
this feature's scope (P10); an off-the-shelf diarization pass is an implementation-level choice
for `/speckit-tasks`, not a scope decision for this plan.

**Correction (deployment build-size finding) — diarization pass moved to the pyannote.ai hosted
API**: `T001`/`tasks.md` originally pinned the off-the-shelf diarization pass to `pyannote-audio`
run locally (`pyannote_diarization.py`, a `Pipeline.from_pretrained(...)` call). Deploying this
feature showed the deployed image ballooning to ~20GB — not from the pretrained model weights
(a few hundred MB, downloaded at runtime, never baked into the image) but from `pyannote-audio`'s
own dependency closure: it pulls in PyTorch, and PyTorch on Linux pulls in the full NVIDIA CUDA
wheel set (`nvidia-cuda-nvrtc`, `cuda-bindings`, etc. — `uv.lock` shows several of these alone
exceeding 40–90MB compressed each) even though this deployment has no GPU and never uses one.
Revised decision: `pyannote_diarization.py`'s `diarize()` calls the **pyannote.ai hosted API**
(`pyannoteai-sdk` — already a transitive dependency of `pyannote-audio` itself, so this swaps an
existing indirect dependency to a direct one rather than introducing a new library) instead of
running a pipeline locally. This removes PyTorch and its CUDA closure from the image entirely.

**Consequences accepted**: (1) `diarize()` is no longer a pure-local, network-free call — it now
uploads the recording to pyannote.ai's own temporary storage (auto-deleted within 24h per their
API) and polls a hosted job to completion. This is the same category of third-party exposure the
Whisper transcription call already accepts for this same audio (both send audio to a hosted API
under the account's own consent gate, research.md Decision 4/`spec.md` User Story 2) — not a new
kind of risk this feature didn't already carry. (2) The call is now network- and poll-bound
rather than CPU-bound; `WhisperTranscriptionAdapter.transcribe()` wraps it in `asyncio.to_thread`
(`whisper_transcription.py`) so a long diarization job can no longer stall the FastAPI event loop
for concurrent requests (notably the on-demand manual-refresh endpoint, User Story 3) the way an
inline blocking call would — `AudioCollector.fetch()`'s own per-item timeout/isolation behavior
(FR-013) is otherwise unchanged. (3) Requires a `PYANNOTEAI_API_KEY` (honest-empty-default,
`config.py`), the same pattern `openai_api_key`/`anthropic_api_key` already use.

**Alternatives considered**: A CPU-only PyTorch build (`--extra-index-url
https://download.pytorch.org/whl/cpu`) — rejected: still bundles PyTorch itself (hundreds of MB)
and the rest of `pyannote-audio`'s scientific-Python dependency chain (scipy, pytorch-lightning,
torchaudio), a smaller image but not a materially different architecture, and this deployment has
no local-inference requirement to justify carrying that weight at all. Keeping the local pipeline
and accepting the large image — rejected: 20GB is a real deployment blocker (registry push/pull
time, cold-start time, hosting cost), not a cosmetic concern, for a feature whose own `spec.md`
Assumptions frame it as needing to be demoable within the project's existing timeline.

## Decision 8 — audio never touches persistent storage

**Decision**: `AudioCollector` downloads each Drive file's bytes into memory (or, for larger
files, a `tempfile.NamedTemporaryFile` created under the container's ephemeral filesystem, never
a mounted/persistent volume), passes it directly to the transcription call, and deletes it in a
`finally` block immediately after — regardless of whether transcription succeeded.

**Rationale**: directly satisfies FR-008/SC-004 and the brief's explicit risk mitigation ("audio
descartado tras transcribir"). A `finally` block (not a happy-path-only cleanup) is required
because a Whisper call that raises must not leave the audio behind.

**Alternatives considered**: none seriously — the spec is unambiguous on this point (FR-008),
this decision documents *how*, not *whether*.

## Decision 9 — polling cadence, "refresh" scope, and consent authority (from `/speckit-specify`'s resolved clarifications)

**Decision**: Scheduled polling joins `backend/app/worker.py`'s existing `APScheduler`
`BackgroundScheduler` (`worker.py:136-150`) as a fourth job,
`scheduler.add_job(_run_audio_collector, "interval", hours=settings.audio_poll_interval_hours,
id="audio_collector")`, default `audio_poll_interval_hours = 4` (new `Settings` field,
`backend/app/config.py`), configurable per deployment like every other timing knob in that file
(`retention_window_days`, `token_lifetime_hours`). Manual refresh (FR-002) is a new,
CS-lead-only endpoint that runs one synchronous `RunCollectorUseCase.execute(audio_collector,
...)` cycle and returns a summary — the same trust boundary `profile_router.py`'s
`POST /api/profile/reload` already uses. Consent recording (FR-016) is a CS-lead-only dashboard
control per the same RBAC boundary, resolved during `/speckit-specify`.

**Rationale**: reuses the exact scheduling mechanism, RBAC boundary, and "manual trigger mirrors
a scheduled run" pattern (`worker.py`'s own `--run-once` flag) already established for the
absence collector, score recompute, and retention job — no new scheduling infrastructure, no new
authorization mechanism.

## Decision 10 — idempotency is checked before download/transcription, not only before persistence (`/speckit-analyze` finding F1)

**Decision**: `AudioCollector.fetch()` lists each consented series-folder's files (Drive's list
API returns file ID and metadata without downloading content), computes each file's
`Envelope.idempotency_key` from that listing metadata alone (`source_type="transcripts"` +
Drive file ID as `source_native_id`), and calls
`CollectorRunRepositoryPort.envelope_exists(idempotency_key)` — **before** downloading or
transcribing anything. A file already processed in a prior cycle is skipped at this point.
Only files that pass this check are downloaded, transcribed, and returned as raw items.
`AudioCollector`'s constructor gains a `collector_runs: CollectorRunRepositoryPort` dependency
(the same port `RunCollectorUseCase` itself already depends on) to make this check.

**Rationale**: `RunCollectorUseCase.execute()`'s own dedup (`use_cases.py:382`,
`envelope_exists()`) already runs — but only *after* `fetch()` and `normalize()` have both
already produced an `Envelope`, i.e. after the expensive work (download + Whisper transcription)
already happened. For `SimulatedCollector`, whose `fetch()` only reads a committed local JSON
file, this ordering was harmless — nothing expensive happens before the existing dedup check.
`AudioCollector` is the first collector where `fetch()` itself does real, billable, per-item
work, so the existing post-fetch dedup alone leaves FR-011 ("SHALL NOT re-transcribe... a
recording that was already successfully processed," revised by this same analysis pass to be
explicit that the check applies before processing, not only before persistence) genuinely
violated in production: every scheduled poll would re-download and re-transcribe every
recording still sitting in its Drive folder, for as long as it stays there — unbounded, silent,
recurring cost with no functional symptom to notice it by.

**Alternatives considered**: Leaving the check where `RunCollectorUseCase.execute()` already
does it, and treating "no duplicate `events` row" as sufficient — rejected: this is exactly the
gap `/speckit-analyze` found; it satisfies the requirement's persistence-layer outcome while
violating its plain-language intent every single polling cycle. Having `AudioCollector` track
"already seen" file IDs in its own local/in-memory state instead of querying
`CollectorRunRepositoryPort` — rejected: would duplicate state the ledger already durably
tracks, drifts on collector restart, and breaks the moment two `AudioCollector` instances (or a
manual refresh racing a scheduled poll) exist — the same class of problem the existing
`envelope_exists()` mechanism was already built to avoid.

## Decision 11 — a Drive folder matching no known series is skipped and logged, never implicitly trusted (`/speckit-analyze` finding C1)

**Decision**: When `AudioCollector.fetch()` lists series-folders under
`settings.google_drive_root_folder_id`, a folder whose name does not match any `series_id` the
system already knows about (from prior `meeting_series_consent` or `events` rows, or — for a
never-before-seen series — simply not resolvable to any expected identifier) is skipped and
logged as an unmapped folder. It is never treated as consented by default (there is no
`meeting_series_consent` row for an unrecognized `series_id`, so Decision 3's gate already
excludes it structurally) and never surfaces as a coverage gap for a series nothing ever expected
to exist, mirroring `RunCollectorUseCase._POST_MVP_SOURCE_TYPES`'s existing "expected" ==
"actually present this run" reasoning rather than inventing a second kind of gap.

**Rationale**: FR-015's folder-per-series convention (`/speckit-specify`'s resolved
clarification) depends on an exact string match between a human-created Drive folder name and
the `series_id` values `meeting_series_consent`/`structured_payload` already use — a typo or a
folder created before its series is registered is a realistic, not hypothetical, operational
mistake. The consent gate (Decision 3) already makes the *safe* failure mode automatic (no
matching series means no matching consent record means nothing is collected); this decision's
only addition is making that outcome *visible* (logged, not silently absorbed) so a CS lead
setting up a new series has something to look at when a folder they just created isn't producing
evidence yet.

**Alternatives considered**: Treating an unmapped folder as an error that fails the whole cycle
— rejected: one misnamed folder among several correctly-named ones shouldn't block collection
for every other series, the same per-item-failure-isolation reasoning FR-013 already applies to
a single bad recording.
