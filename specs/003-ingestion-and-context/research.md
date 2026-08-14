# Phase 0 Research: Ingestion and Context

The stack itself is already decided (`architecture/03-technology-stack.md`). This
resolves the choices specific to implementing M1/M2/M3 for real for the first time.

## Decision: Message-body encryption via `cryptography`'s Fernet

**Decision**: `cryptography` (the `Fernet` recipe — AES-128-CBC + HMAC, authenticated
symmetric encryption), keyed from a 32-byte urlsafe-base64 key read from
`ENCRYPTION_KEY_PATH` at startup. `raw_envelopes.data_key_ref` / `events.data_key_ref`
store a fixed key-identifier string (`settings.encryption_key_id`, default
`"local-v1"`), not the key itself — there is exactly one active key per deployment in
Phase 1 (`architecture/03-technology-stack.md` §Encryption (Phase 1)), so a static
identifier is sufficient; it becomes meaningful once Phase 11 introduces key rotation.

**Rationale**: `Fernet` is the standard, audited choice for "encrypt a blob with one
symmetric key" in Python — no protocol design needed, versioned ciphertext format,
built-in authentication (tamper detection). Matches architecture/03's "the data key
loaded from the deployment's `.env` file" framing directly (a key *file*, read once at
startup) rather than a database-side `pgcrypto` call, which would need the key threaded
into every query.

**Startup behavior**: the app MUST fail to start if `ENCRYPTION_KEY_PATH` doesn't
resolve to a valid Fernet key (spec.md Edge Cases: "fail loudly... never silently store
plaintext"). A missing key file is not a degraded-but-running state; there is nothing
in this codebase that is allowed to store a message body unencrypted.

**Local dev**: `docker-compose.yml` needs a `./secrets:/app/secrets:ro` mount (doesn't
exist yet — added by this feature) so the key file set up on the host is readable
inside the container; `quickstart.md` documents generating one locally with
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

## Decision: Hash chain computed in Python, verified against the DB's own function

**Decision**: Implement `data-base/03-schema-ledger.md`'s exact algorithm (SHA-256 over
the pipe-delimited canonical field string, NULLs as empty string, genesis =
`"0" * 64`) in `backend/app/ingestion/domain/hash_chain.py`. Verification uses the
already-existing `verify_hash_chain()` Postgres function (feature 001's DDL) as the
independent check — if the Python-computed hash and the DB function's recomputation
ever disagree, that's a bug in this feature, not a false negative in the test.

**Rationale**: The DDL already specifies the algorithm precisely and ships a runnable
verification function — reimplementing it in Python for the *write* path and reusing
the DB function for the *verify* path gives two independent implementations of the same
algorithm agreeing, which is a stronger correctness signal than one implementation
checking itself.

## Decision: Business-hours calculator — hand-rolled, no new dependency

**Decision**: A pure function in `backend/app/ingestion/domain/business_hours.py`
computing elapsed business hours between two timestamps against a working-hours
window, a timezone, and weekdays-only (no holiday calendar — none is modeled anywhere
in the client profile schema, `data-base/04-schema-context.md`).

**Rationale**: The calculation is genuinely simple (skip weekends, clip to the daily
window, sum the remainder) and the client profile schema has no holiday-calendar field
to drive a general-purpose business-calendar library with — adding one would be
solving a more general problem than this system actually has (constitution P10/YAGNI).

**Alternatives considered**: `businesstime`/`workalendar` — rejected; would need a
holiday calendar input this schema doesn't have, and buys nothing over a ~30-line pure
function for weekday-window arithmetic.

**Open tickets need an explicit reference time, not just two fixed timestamps.** A
still-open response pair's `business_hours_elapsed` (`REQ-M2-05`) is elapsed-*so-far* —
inherently relative to "now," which is why `response_pairs` is a rebuildable projection,
not a stored constant. The calculator signature is
`compute_business_hours_elapsed(start, as_of, calendar)`, where `as_of` defaults to
`datetime.now(UTC)` in the use case but is passed explicitly in tests, so
`examples/01`'s exact "19.0 hours, `open_overdue`" result is deterministically
reproducible rather than a moving target (`data-model.md`'s fixture documents the exact
reference time used).

## Decision: Client profile schema validation via Pydantic

**Decision**: A Pydantic model mirroring `REQ-M3-01`'s field list, with a validator
enforcing "at least one `signs_renewal: true` stakeholder" (`REQ-M3-07`).

**Rationale**: Pydantic is already a dependency (FastAPI, `pydantic-settings`) — using
it for the profile schema too means one validation library across the whole backend,
and its error messages are already structured (field path + reason), which is exactly
what FR-001's "specific validation error" needs.

## Decision: Thread stitching — ticket-reference regex only

**Decision**: `re.search(r"#(\d+)", message_text)` — if a message's text contains a
`#<number>` matching an existing ticket's native ID, link the message's event to that
ticket's `thread_key` with `stitch_method = ticket_reference` and a fixed high
confidence (0.9).

**Rationale**: Matches spec.md's explicit scope boundary (minimal, not exhaustive
stitching) and is exactly the mechanism `examples/01-end-to-end-walkthrough.md` §5's
worked example uses ("a Slack message later referenced 'ticket #456' directly").
`participant_subject` and `timing_heuristic` stitching are real `stitch_method` enum
values this feature doesn't implement — left as documented future work, not silently
dropped from the enum.

## Decision: Identity resolution — exact match only, fuzzy suggestion deferred

**Decision**: Resolve a participant identifier by exact string match against the
current profile's `stakeholders.identifiers`. No match → `unresolved`, full stop.

**Rationale**: `architecture/03-technology-stack.md` names `rapidfuzz` for fuzzy
*suggestions* — but a suggestion needs a UI/human-confirmation step to act on
(`REQ-M1-P5`: never auto-resolve below a confidence floor), and no such UI exists yet
(the "unresolved person" dashboard state is `requirements/08-health-dashboard.md`
territory, not built until later). Building the fuzzy-match half of a feature with no
consumer for its output is the same speculative-generality trap as the deferred
rollups decision in spec.md.

## Decision: Profile submission via the already-published `POST /api/profile/reload`

**Decision**: This feature implements `POST /api/profile/reload` exactly as
`architecture/07-api-spec.md` already specifies it — validates the on-disk YAML,
creates a new `client_profile_versions` row, triggers replay.

**Rationale**: The contract already exists in an approved architecture document; this
is the concrete trigger mechanism FR-001/FR-002 need, not a new design decision.

## Decision: `SimulatedCollector` triggered by a script, not a route or a timer

**Decision**: `backend/scripts/run_collector.py`, invoked manually (matching
`scripts/seed.py`'s existing pattern) — not a new HTTP route, not wired into the
worker's scheduled heartbeat.

**Rationale**: `SimulatedCollector` stands in for a real source that doesn't exist yet;
neither "receive a webhook" nor "poll on a timer" is meaningful for a fixture file that
doesn't change. A script mirrors exactly how `demo/03-environment-and-fixtures-
checklist.md` describes the demo's contingency ("replay mode... never calls a live
source API"). The absence collector, by contrast, *is* wired into `worker.py`'s
APScheduler heartbeat (already stubbed, feature 001) — it has a genuine recurring
purpose independent of which sources are connected.

## Implementation finding: appends must preserve global occurred_at order

**Found during verification, not design.** `verify_hash_chain()` walks
`ORDER BY occurred_at, id` (data-base/10-ddl-appendix.md), but
`SqlAlchemyEventRepository.append()` chains each new event to whichever event was
*most recently inserted* (`ORDER BY created_at DESC LIMIT 1`) — correct and cheap, but
only if insertion order and `occurred_at` order are the same sequence. The first
version of `RunCollectorUseCase` broke that: it grouped envelopes by `source_type` and
processed each group to completion before moving to the next, so a later-`occurred_at`
item from one source (e.g. `gmail-msg-8845`, day 4) could be appended before an
earlier-`occurred_at` item from another source (e.g. `zendesk-456-reopened`, day 1) —
individually ordered within each source, globally out of order across sources.
`verify_hash_chain()` caught this for real: 87 accumulated events across three
consecutive full test-suite runs, zero broken links only after the fix.

**Fix**: `SimulatedCollector.fetch()` already returns items in global `occurred_at`
order (sorted once, regardless of source); `RunCollectorUseCase.execute()` now
processes that single sorted list directly — per-source bookkeeping (`collector_runs`
rows, emitted/duplicate counts) is grouped by source, but the actual `events.append()`
sequence is not. Documented as a hard invariant on `EventRepositoryPort.append`'s
docstring: **appends must happen in `occurred_at` order across the whole run, not just
within one source** — the ledger has no mechanism to backfill an event chronologically
"in the middle" once later events already reference the wrong predecessor, since
`events` rows are immutable.

**Test-design consequence**: the same invariant applies across the whole test suite,
not just one run — `events` can never be deleted, so two test files choosing unrelated
fixed calendar dates (e.g. one test at 2026-09-01, another at 2032+) corrupt the chain
globally the moment they're both present, regardless of each test's own internal
correctness. `backend/tests/conftest.py`'s `ledger_floor()` helper (queries
`MAX(occurred_at)` and anchors new synthetic timestamps after it) is the fix used
throughout `test_hash_chain.py`, `test_replay.py`, `test_absence_collector.py`, and
`test_simulated_collector.py` — every test that appends real events derives its
timeline from the ledger's actual current state rather than a fixed date, so the suite
stays correct regardless of execution order or how many times it's been run against a
given database before. Relatedly, message-body ciphertext is also permanent once
appended, so every test that touches `body_encrypted` (directly or via `ReplayUseCase`,
which decrypts every message-type event in the whole ledger to check for thread
references) uses the one real, persistent `ENCRYPTION_KEY_PATH` key rather than a
throwaway per-test key — a throwaway key can decrypt what it wrote, but not what an
earlier test run wrote with a since-discarded key.

## Outcome

No `NEEDS CLARIFICATION` markers remain. All Technical Context fields in `plan.md` are
resolved either by citing an existing document or by a decision recorded above.
