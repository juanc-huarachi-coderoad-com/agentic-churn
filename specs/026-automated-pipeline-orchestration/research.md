# Research: Automated Pipeline Orchestration

## Decision 1: Short-interval polling, not `LISTEN`/`NOTIFY`

**Decision**: The new automatic cycle is a fifth APScheduler job in `backend/app/worker.py`, on a
short fixed interval (Decision 3), using the exact same `BackgroundScheduler.add_job(..., "interval",
...)` primitive the four existing jobs already use — not Postgres `LISTEN`/`NOTIFY`.

**Rationale**: `architecture/03-technology-stack.md` names `LISTEN`/`NOTIFY` as part of the
adopted scheduling stack, but a full-repo grep for `LISTEN`/`NOTIFY` (case-insensitive, `backend/`
and `architecture/`) returns **zero implementation hits** — it exists only as a name in that one
doc, never built. Introducing it for real here would mean: a new asyncpg connection held open
specifically for `LISTEN`, a notification payload contract, a reconnect/backoff story for when
that connection drops (which polling doesn't need at all — a dropped poll just retries next
interval), and triggers on every table a "new signal" could land in (`events`, and indirectly
`raw_envelopes`). That is real, new operational surface for a single-process, single-deployment
system already polling successfully for its other three time-sensitive jobs. Per constitution
P10 (YAGNI) and the architecture doc's own stated reason for avoiding a broker in the first place
("a Postgres table with a 30-second batching window... comfortably meets the <60s latency target
without the operational cost"), polling is the smaller, already-proven mechanism for the actual
requirement.

**Alternatives considered**: Real `LISTEN`/`NOTIFY` — rejected above. A dedicated always-open
asyncpg listener task inside the `api` process instead of `worker` — rejected as a second place
background work happens, splitting the existing "all scheduled jobs live in `worker`" convention
for no measured benefit.

## Decision 2: "Nothing new since last cycle" — an in-memory high-water-mark on `events.created_at`

**Decision**: The new job holds one in-process variable (`_last_seen_event_at: datetime | None`,
module-level in `worker.py`, mirroring the existing module's plain-function style — no new class).
Each tick: query `SELECT MAX(created_at) FROM events`. If the result is `<=` the held value (or
the table is still empty), skip the cycle entirely — no reader, no recompute, no narration call.
Otherwise, **capture the new max value before running the pipeline** (not after), run the full
readers → recompute → narrate sequence, then store the captured value as the new high-water-mark.

**Rationale**: `events.id` is a `UUID` (`gen_random_uuid()`, `data-base/10-ddl-appendix.md`), not
monotonically sortable — `MAX(events.id)` would be meaningless as a progress marker.
`events.created_at` (`DEFAULT now()`, insertion time) is monotonic by construction and is exactly
"has anything been appended to the ledger since I last looked," which is the actual question
FR-004 asks — not "has anything new *happened*" (`occurred_at`, which can arrive out of order via
backfills or the meeting-audio collector's delayed transcription path, and would make the
high-water-mark jump around instead of only advancing). Capturing the cursor **before** running
the pipeline, not after, is the standard read-cursor/do-work/save-cursor ordering — it guarantees
an event appended mid-cycle is never permanently missed (it will simply be the trigger for the
*next* tick), rather than racing a "did anything arrive while I was busy" gap. An in-memory
(not persisted) high-water-mark means a process restart re-runs one cycle unnecessarily if
nothing changed — an accepted, harmless cost: `RunReadersUseCase` and its readers already
tolerate redundant invocation via their own idempotency checks (`already_interpreted()`,
`RecurrenceReader`'s per-member-event dedup), so a spurious extra cycle produces zero duplicate
findings, just one wasted (cheap, infrequent) check. Persisting the cursor in a new table/column
to avoid that one-time cost would be real schema surface for a problem whose worst case is "one
harmless no-op cycle after a deploy" — not justified under P10.

**Alternatives considered**: A persisted cursor row (new migration) — rejected as disproportionate
to the cost being avoided. Counting `collector_runs` rows since the last cycle instead of querying
`events` directly — rejected: some real "new signal" events are never associated with a fresh
`collector_runs` row (e.g. `DetectAbsenceUseCase`'s synthetic absence events, appended directly to
`events` by the existing hourly absence job), and those genuinely should trigger a reader cycle
(the Absence reader exists specifically to read them) — filtering by `collector_runs` would miss
them.

## Decision 3: Poll interval — 30 seconds

**Decision**: The new job's `interval` is `seconds=30`.

**Rationale**: `requirements/11-non-functional-requirements.md` REQ-NFR-02 targets ~40s typical,
60s cap, event-to-updated-score. `architecture/03-technology-stack.md`'s own stated design intent
for this exact scenario is "a Postgres table with a 30-second batching window" — this feature
finally builds the thing that sentence already assumed existed. A 30s tick leaves real headroom
under the 60s cap for the pipeline's own execution time (readers, including two LLM-backed ones
and one embedding+clustering pass, plus score recompute, plus narration) to complete within the
following tick or two without ever exceeding the cap in the common case.

**Alternatives considered**: Matching the existing jobs' hourly interval — rejected outright, it
would miss REQ-NFR-02 by two orders of magnitude; this new job is solving a materially
faster-latency problem than the absence/retention jobs, so it is not expected to share their
interval. A sub-10s interval — rejected as unnecessarily aggressive relative to the 60s cap and
the pipeline's own real execution time (two real LLM calls per cycle when readers actually run),
with no corresponding requirement asking for it.

**Live-tested, not just estimated**: a real `--run-once pipeline` run against the Meridian fixture
(real OpenAI embedding calls + real Anthropic calls, not mocked) measured **32.68s** end to end for
a cycle with genuine new findings — comfortably under the 60s cap, but real enough headroom that a
"new event" cycle can occasionally still be in progress when the next 30s tick fires. That's an
expected, harmless case, not a bug: `research.md` Decision 6's `max_instances=1` default simply
skips that one overlapping tick, and the following tick (30s later) catches up, since nothing new
arrived in between anyway. This matches the same "live-tested, not a planning-time guess" discipline
`specs/014-ask-agent-response-formats` already set precedent for (its own 15s narration cap was
derived from a real measurement, not assumed).

## Decision 4: Reuse `score_trigger`'s existing, already-defined-but-unused `'new_event'` value

**Decision**: The automatic cycle's `RecomputeScoreUseCase.execute(trigger="new_event")` call uses
the `new_event` value already present in `data-base/10-ddl-appendix.md`'s `score_trigger` enum
(`CREATE TYPE score_trigger AS ENUM ('new_event','burst_batch','urgent_fast_path',
'hourly_heartbeat','profile_edit_replay','weight_edit_replay','manual')`) — confirmed unused by
any current caller (`grep -rn 'trigger="new_event"' backend/app` returns nothing before this
feature). No migration needed.

**Rationale**: This is exactly the trigger this feature adds a caller for — the schema already
anticipated "a score recompute because a new event arrived," distinctly from
`hourly_heartbeat` (recency/ageing decay, not new evidence) and `manual` (an operator-initiated
one-off). Reusing it keeps `score_runs.trigger` an honest audit trail of *why* each run happened,
matching the precedent `RecomputeScoreUseCase`'s three other real trigger values already set.

**Alternatives considered**: Reusing `manual` — rejected, would misrepresent an automatic cycle as
operator-initiated in the audit trail, undermining the exact auditability `score_runs.trigger`
exists for. Adding a new enum value — rejected, unnecessary: `new_event` already exists and fits.

## Decision 5: Narration's existing "nothing to narrate" behavior already satisfies FR-009

**Decision**: Call `NarrateScoreRunUseCase.execute(score_run.id)` unconditionally after every
successful automatic score recompute — no new "does this run have findings" check is added in
`worker.py` itself.

**Rationale**: Read directly from `backend/app/narrator/application/use_cases.py`:
`NarrateScoreRunUseCase.execute()` already returns `None` immediately when
`get_ranked_contributions()` comes back empty ("a genuinely healthy run... `REQ-M8-05`'s own
'Nothing needs you today' state handles this, not a placeholder narration"). This is the exact
same call `scripts/run_narrator.py` already makes and already prints "Nothing to narrate — this
score run has no findings (a healthy account)" for. FR-009 is therefore satisfied by an existing,
already-tested behavior, not new logic this feature must build — adding a duplicate "skip if
empty" check in `worker.py` before calling it would be redundant with what the use case already
guarantees.

## Decision 6: Overlap prevention (FR-006) is APScheduler's own default, not new code

**Decision**: Rely on `BackgroundScheduler`'s default `max_instances=1` per job (confirmed by
reading `apscheduler/schedulers/base.py`'s `job_defaults.get("max_instances", 1)` in this
project's own installed `apscheduler==3.11.3`) — no explicit `max_instances` argument is passed,
matching every existing job in `worker.py`.

**Rationale**: With the library default, if a tick fires while the previous run of the *same job
id* is still executing, APScheduler skips the new run rather than starting a second concurrent
one — exactly FR-006's requirement, already the behavior of every job currently in this file.
Nothing new to build; a research decision worth recording explicitly (per this feature's own
requirement to resolve concurrency, not assume it away) rather than silently relying on unverified
library behavior.

**Alternatives considered**: A manual `asyncio.Lock`/DB advisory lock — rejected, redundant with a
library guarantee already in effect and already relied upon (silently) by the existing jobs.
