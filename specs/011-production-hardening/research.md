# Phase 0 Research: Production Hardening

Six independent decisions, one per user story, each grounded by reading the actual shipped
code (`backend/app/`) rather than assuming the prose docs (`data-base/`, `architecture/`)
already match it — following features 004/007/008/009/010's own precedent of catching
doc/code drift at plan time rather than at implementation time.

## Decision 1 — Retention/crypto-shredding needs time-bucketed data keys (User Story 1)

**Finding, not assumed:** `backend/app/config.py`'s `encryption_key_id: str = "local-v1"` and
`backend/app/worker.py`/every ingestion use case pass this **one constant** as `data_key_ref`
for every event and envelope, always. `backend/app/ingestion/adapters/encryption.py`'s
`FernetEncryption` wraps a **single** Fernet key loaded once from
`settings.encryption_key_path`. Meanwhile `data-base/10-ddl-appendix.md` and
`data-base/03-schema-ledger.md` already document the crypto-shredding *mechanism* precisely:
`data_key_ref` is permanent and `NOT NULL`; `body_encrypted`/`payload_encrypted` are the
columns a narrowly-scoped `shredder_role` (already granted `UPDATE (body_encrypted)` on
`events`, nothing else, in the existing DDL) nulls once "the key it depends on is destroyed in
the key store."

**The gap:** destroying *the* key today would make every message body ever ingested
permanently unrecoverable at once — not just the ones past the retention window — which
violates FR-001's "leaving ... findings, and score history intact" requirement in spirit (the
data survives, but nothing newer than the oldest message could ever be decrypted again either,
since Fernet keys aren't per-message). This is a genuine, previously undiscovered
implementation gap between the schema's design intent and the MVP's single-key shortcut — the
same class of finding features 004/010 documented in `specs/ROADMAP.md`'s Log.

**Decision:** Move from one static key to **daily key-rotation buckets**, implemented as a
**key ring behind the existing `EncryptionPort` interface — zero signature change**. `Encryption
Port.encrypt(plaintext) -> bytes` / `.decrypt(ciphertext) -> str` stay exactly as they are
today; a new `BucketedFernetEncryption` (`app.ingestion.adapters.encryption`, implementing the
same `EncryptionPort` ABC) replaces `FernetEncryption` at every one of its ~8 composition-root
construction sites (`app.main`, `app.worker`, and the five router files that build one inline
for a read path) with **no other call site touched**: `encrypt()` always encrypts under
*today's* bucket key (creating that day's key file on first use); `decrypt()` tries every
currently-loaded, non-destroyed bucket key in turn until one succeeds — Fernet ciphertext
carries no key-id header, but at this data scale (a few hundred keys/year even after a full
year of daily rotation) trying each key is cheap, and it's only ever exercised on a genuine
read path (evidence trace, readers, narrator), never the ingestion hot path. `data_key_ref`
becomes the ISO date (`YYYY-MM-DD`, UTC) of the bucket used at encryption time — the ~4 call
sites that currently pass the constant `settings.encryption_key_id` as `data_key_ref`
(`app.ingestion.application.use_cases`, `app.worker`) switch to a new `KeyStorePort.current_
bucket_id() -> str` instead. A new `FileKeyStore` (`app.ingestion.adapters.key_store`,
implementing a new `KeyStorePort`) keeps one key file per bucket under a new `secrets/data-keys/`
directory (`architecture/03-technology-stack.md`'s noted Cloud-KMS upgrade path is a later,
swappable adapter — this feature only needs a directory of per-day files, which already
supports destroying one bucket's key without touching any other). The daily retention job
(FR-001) resolves every bucket whose *newest possible event* (bucket-day + 1, end of day) is
older than the retention window, calls `KeyStorePort.destroy(bucket_id)` (deletes that bucket's
key file — the next `decrypt()` call's key-ring reload simply won't find it anymore, so any
ciphertext under it fails to decrypt everywhere, uniformly, which *is* crypto-shredding), and
nulls `events.body_encrypted` for every row whose `data_key_ref` matches it — via the existing
`shredder_role` grant, connected through a new, dedicated `shredder_session_factory` (`app.db`)
that authenticates as `shredder_role` using `settings.shredder_role_password` (already
provisioned in `app/config.py` and the migration, but — a second, smaller plan-time finding —
never actually used to open a real connection anywhere in the running application before this
feature). `raw_envelopes.payload_encrypted` is deliberately **not** touched — a real correction
found during implementation, not at plan time: that column is `NOT NULL`, and
`data-base/10-ddl-appendix.md`'s own crypto-shredding note already documents that destroying the
key alone is sufficient there ("once destroyed, payload_encrypted is cryptographically
unrecoverable even though this row and its data_key_ref value are untouched") — only
`events.body_encrypted` was ever designed to be explicitly nulled. An earlier implementation
draft granted `shredder_role` `UPDATE`/`SELECT` on `raw_envelopes` for this mistaken reason;
removed before those grants were exercised by any real code path, and the migration corrected
in place (downgraded and re-applied against the local dev database, not shipped as a stale grant
followed by a second corrective migration, since this feature has no external consumers yet) —
every other session in this codebase still goes through the unrestricted `database_url`
connection instead.

**Alternatives considered:**
- *Thread `data_key_ref` through `EncryptionPort.decrypt(ciphertext, data_key_ref)`* — the
  "obvious" design, rejected once its blast radius was actually traced: `EncryptionPort.
  decrypt()` is called from `app.experience.adapters.sqlalchemy_repository` (3 call sites),
  `app.narrator.adapters.sqlalchemy_repository`, and `app.readers.adapters.sqlalchemy_
  repository` (2 call sites) — 6 call sites across 3 modules this feature has no other reason
  to touch, each of which would also need its surrounding SQL query to additionally `SELECT
  data_key_ref` alongside `body_encrypted`. The key-ring approach above gets the identical
  crypto-shredding guarantee — a destroyed bucket's ciphertext becomes unrecoverable everywhere
  — with a one-line composition-root swap at each site instead, honoring P10.
- *Per-message keys* (one Fernet key per event) — correct in principle but means storing one
  key per event forever until shredded, which is strictly more key-management surface than
  daily buckets need to solve "delete everything past N days" (the actual requirement), and
  works against REQ-NFR-05's "no unnecessary infrastructure at this scale" spirit.
- *Leave the single key, add a "logical" shred flag instead* — rejected outright: a boolean
  flag doesn't make the content cryptographically unrecoverable, which is what "crypto-
  shredding" and REQ-NFR-13 both specifically require, not just hiding it from queries.

## Decision 2 — RBAC needs `role` threaded through the existing auth chain (User Story 2)

**Finding:** `backend/app/auth/application/ports.py`'s `TokenRecord` carries only `user_id`,
`expires_at`, `revoked_at` — no role. `get_current_user` (`app/auth/application/dependencies.
py`) returns `CurrentUser(user_id=...)`, also role-less. Every one of the eight existing
routers (`dashboard_router.py`, `evidence_router.py`, `coverage_router.py`, `ask_router.py`,
`draft_router.py`, `feedback_router.py`, `profile_router.py`) already depends on
`get_current_user` uniformly — there is exactly one auth gate to extend, not eight.

**Decision:** Extend `TokenRecord`/`CurrentUser` with `role: str | None` (the query behind
`get_by_hash` gains a `JOIN users ON users.id = auth_tokens.user_id`, reading the same
`users.role` column that has existed, unenforced, since `data-base/12-users-and-auth.md`). Add
one new dependency, `require_full_access` (`app.auth.application.dependencies`), that wraps
`get_current_user` and raises `403` if `role == "account_executive"`. Every write-capable route
(`feedback_router.py`, `profile_router.py`'s two routes, `draft_router.py`'s three routes,
`ask_router.py`) swaps its `Depends(get_current_user)` for `Depends(require_full_access)`;
every read-only route (`dashboard_router.py`, `evidence_router.py`, `coverage_router.py`)
keeps `Depends(get_current_user)` unchanged, satisfying FR-007's "no new restriction on
`cs_lead` or any other role" by construction — the dependency swap only ever narrows the one
route set an account executive can reach, never any other role's access to any route.

**Alternatives considered:** A single `Depends(get_current_user, roles=[...])` parametrized
dependency (FastAPI doesn't support parametrizing `Depends()` callables directly without a
factory) — rejected for `require_full_access` being simpler to read at each call site and
match this codebase's existing one-dependency-per-concern style (`get_current_user` vs.
`get_bearer_token` are already two distinct, single-purpose dependencies for this reason).

## Decision 3 — Weight recalibration reuses an already-designed replay trigger (User Story 4)

**Finding:** `data-base/06-schema-scoring.md`'s `score_runs.trigger` enum **already includes**
`weight_edit_replay`, sitting unused alongside `profile_edit_replay` since the schema was
first authored — this feature is the first to actually fire it.
`SqlAlchemyFindingRepository.get_finding_type_config_version()`
(`app/scoring/adapters/sqlalchemy_repository.py`) executes `SELECT version FROM
finding_type_config LIMIT 1` — confirming `finding_type_config.version` is one shared string
across every row (a config-wide version, not per-finding-type), which is exactly what
`score_runs.finding_type_config_version` freezes per run for REQ-NFR-08 determinism (FR-015).

**Decision:** `UpdateFindingTypeWeightUseCase` (new, `app.scoring.application.use_cases`,
alongside `RecomputeScoreUseCase`) does three things in one transaction: (1) writes the new
`base_points` for the target `finding_type`, (2) bumps the shared `finding_type_config.version`
string (so every score run computed after this point carries a visibly different
`finding_type_config_version` than every run before it — the mechanism FR-015 depends on
already exists, it just needs a writer), (3) inserts one row into a new
`finding_type_config_changes` audit table (FR-014). It then triggers `RecomputeScoreUseCase`
with `trigger="weight_edit_replay"` — mirroring `profile_router.py`'s existing
`reload_profile` → `SubmitProfileUseCase` → `RecomputeScoreUseCase(trigger="profile_edit_
replay")` pattern exactly, not a new orchestration idea.

**Alternatives considered:** Per-`finding_type` versioning (each row gets its own version
string) — rejected: it would require every score run to record *N* config versions instead of
one, a schema change nothing in `score_runs` supports today, for a distinction (which specific
type changed) `finding_type_config_changes`'s audit rows already capture without it.

## Decision 4 — Profile editor reuses `SubmitProfileUseCase` unmodified (User Story 5)

**Finding:** `architecture/07-api-spec.md` already documents the exact intended shape:
"`POST /api/profile/reload` ... **MVP only** ... Post-MVP replaces this with a real editor UI
writing through `POST /api/profile` directly." `SubmitProfileUseCase.execute()`
(confirmed in `app/context/application/use_cases.py` via `profile_router.py`'s call site)
already accepts a parsed domain `ClientProfile` object, not YAML text — `load_profile_yaml`
(`app/context/adapters/yaml_profile_loader.py`) is a thin parser that builds that same object
before handing it off. The frontend already has a scaffolded, empty
`frontend/src/profile-editor/` directory (a `.gitkeep` placeholder dated back to feature 001,
explicitly deferred "when this module's own phase starts" — this is that phase).

**Decision:** Add `POST /api/profile` (`profile_router.py`) accepting a JSON body shaped
exactly like `ProfileResponse`'s fields (stakeholders, exclusions, renewal date, contract value
band, communication norms), validated by a new Pydantic request model, converted to the same
`ClientProfile` domain object `load_profile_yaml` already builds, then handed to the
**same, unmodified** `SubmitProfileUseCase`. Zero change to `SubmitProfileUseCase`,
`ReplayUseCase`, or the versioning rules — this route is a second front door to code that
already exists, exactly as the architecture doc anticipated. `frontend/src/profile-editor/`
gets its first real content: a form (React Hook Form + Zod, per constitution P11) posting to
this route, following `frontend/src/evidence/`'s feature-010 precedent for turning a reserved,
empty slot into real code without touching its sibling modules.

**Alternatives considered:** Reusing `/api/profile/reload` for both YAML-reload and
structured-JSON submission — rejected: the architecture doc already named `POST /api/profile`
as the distinct Post-MVP route, and conflating "re-read this file path" with "here is a new
profile body" would make the endpoint's contract ambiguous about which one wins in the FR-018
concurrent-edit edge case, requiring exactly the "second, conflicting resolution path" the spec
already ruled out.

## Decision 5 — Post-MVP source connectors extend `SimulatedCollector`, not a live API integration (User Story 6)

**Finding:** No source in this codebase — including the three "Phase 1" sources (Gmail,
Zendesk, warehouse) — is a live external API/OAuth integration today.
`app/ingestion/adapters/simulated_collector.py`'s `SimulatedCollector` is the **only**
concrete `Collector` implementation that exists, reading one committed fixture file
(`demo/fixtures/meridian-week.json`) and branching internally on `source_type` (`_normalize_
gmail`, `_normalize_zendesk`, `_normalize_warehouse`-equivalent). `requirements/01-signal-
collectors.md`'s "Phasing note" and `decisions/01-mvp-scope-and-phasing.md`'s sources table
describe Slack/CSAT/Calendar in terms of what they contribute to readers, not a specific
integration mechanism — and every prior feature's own verification in `specs/ROADMAP.md`'s Log
runs against this same fixture-driven collector, never a live external call (the only real
outbound calls anywhere in this codebase are to the Anthropic/OpenAI APIs, for readers/
narrator/ask-agent/draft-composer).

**Decision:** Extend the same, already-proven pattern: three new normalize functions
(`_normalize_slack`, `_normalize_csat`, `_normalize_calendar`) inside `simulated_collector.py`,
reading three new sections of an extended fixture file (`demo/fixtures/meridian-week.json`
gains `slack`/`csat`/`calendar` arrays, consent metadata included per calendar entry per
FR-023), each emitting the same `Envelope` shape the existing three sources already produce. A
new `MeetingReader` (`app.readers.application.meeting_reader`, mirroring `tone_reader.py`/
`intent_reader.py`'s existing LLM-reader shape) activates only for envelopes whose calendar
entry carries documented consent (FR-023) — reusing `ValidationGate`/`LLMPort` unchanged. The
existing Absence/Relationship readers (`app.readers`) gain the chat-silence/participant-graph
signals FR-021/022 describe by reading the newly-available `slack`-sourced events the same way
they already read email/ticket events — an input-data change, not a reader-interface change.

**Alternatives considered:** Building real OAuth flows for Slack Connect/a CSAT vendor/a
Calendar API — explicitly rejected for this codebase's actual state: it would be new
infrastructure this repository has never once needed for any of its other six external-looking
"sources," a much larger and differently-shaped effort than what "Post-MVP sources" has meant
in every other document that discusses it (`decisions/01-mvp-scope-and-phasing.md` frames the
Phase 1/2 split entirely in terms of what each source *unlocks for a reader*, never in terms of
integration engineering cost). If a future feature needs a genuinely live connector, that's a
new decision document, not a silent scope expansion of this one.

## Decision 6 — Observability is a lean, adapters-only cross-cutting package (User Story 3)

**Finding:** `architecture/03-technology-stack.md` already names the technology
("OpenTelemetry traces... once there's more than one deployment to compare") without
prescribing a module. `decisions/02-repo-and-tooling.md`'s own layout doc notes "not every
module needs all three rings on day one" — `narrator/`/`experience/` are cited as thin,
adapters-heavy examples already.

**Decision:** A new `app/observability/` package, adapters-only (no `domain/`, no
`application/` — there is no business rule here, only infrastructure setup, matching P10):
`tracing.py` wires the OpenTelemetry SDK once at composition-root time (`app.main`,
`app.worker`), and a small `traced()` context-manager helper wraps the four operation types
FR-009 names (collector run, score recomputation, reader execution, Ask agent query) at their
existing call sites — `worker.py`'s `_run_absence_detection`/`_run_score_recompute`, the new
retention job, `RunReadersUseCase`'s execute loop, `ask_router.py`'s route handler. No existing
port or use-case signature changes; instrumentation wraps calls from the adapter/composition-
root layer inward, never the reverse, keeping the Dependency Rule intact.

**Alternatives considered:** A full three-ring `app.observability` module with its own ports —
rejected under P10: there is no domain logic to isolate (tracing has no business rule to unit-
test independent of the tracing library itself), so ports/use-cases here would be exactly the
"speculative abstraction layer for a requirement the product does not have" the constitution
already warns against.
