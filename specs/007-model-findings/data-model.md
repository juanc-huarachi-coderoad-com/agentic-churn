# Phase 1 Data Model: Model Findings

No new tables and no migration — every table this feature writes to already
exists since feature 001's `0001_initial_schema.py`
(`data-base/05-schema-reasoning.md`: `findings`, `quarantine`,
`quarantine_reasons`, `finding_type_config`; `data-base/03-schema-ledger.md`:
`baseline_confirmations`). This feature is the first real *writer* of
`quarantine`/`quarantine_reasons`/`baseline_confirmations`, and adds two seed
rows to `finding_type_config` (`data-base/11-seed-data.sql`, `research.md`
Decision 7).

## `Finding` (existing entity, `app.scoring.domain.entities`, re-exported by `readers`)

No field changes. This feature is the first to construct `Finding` instances
with `reader_type ∈ {tone, intent}` and, for the first time since feature 005,
the first to construct instances with `status` values other than
`pending_validation` — because `Finding` is a **frozen** dataclass, the gate
cannot mutate a reader's output in place; it constructs a new `Finding`
(`dataclasses.replace(finding, status=...)`) carrying the decided status
before that final version is persisted. Nothing in this feature adds a
`Finding` field — `magnitude`/`confidence`/`cited_event_ids` are set once, by
the reader, and never touched again (matches `architecture/08-class-
diagrams.md`'s existing note: "nothing mutates `magnitude`, `confidence`, or
`cited_event_ids`").

| Field | Set by | Note for this feature |
|---|---|---|
| `reader_type` | Reader | `"tone"` / `"intent"`, new real values (enum already includes them, feature 001) |
| `finding_type` | Reader | `tone_deterioration` (Tone); `escalation_language` / `competitive_mention` / `contractual_reference` (Intent, per its `category`) |
| `magnitude`, `confidence` | Reader (from the LLM's structured output) | Both required, both in `[0, 1]`, kept as two separate numbers per REQ-M5-03 |
| `cited_event_ids` | Reader | Non-empty; DB `CHECK` already enforces this, gate's schema check re-verifies before insert (`research.md` Decision 6.1) |
| `status` | **New in this feature** — `ValidationGate`, not the reader | Reader constructs with `pending_validation`; gate replaces with `validated` or `quarantined` before the one and only `persist()` call |

## `ValidationGateResult` (new value object, `app.readers.domain`)

Pure, no I/O — the gate's decision for one finding, before anything is
persisted.

| Field | Type | Description |
|---|---|---|
| `passed` | `bool` | True only if all four checks passed |
| `failed_checks` | `list[FailedCheck]` | Empty if `passed`; one entry per failed check (a finding can fail more than one) |

## `FailedCheck` (new value object, `app.readers.domain`)

One row's worth of quarantine detail — maps 1:1 to a `quarantine_reasons` row.

| Field | Type | Description |
|---|---|---|
| `check_name` | `str` | One of `schema_invalid`, `cited_event_missing`, `insufficient_evidence`, `confidence_below_floor` — matches `quarantine.failed_check`'s existing DB enum exactly |
| `expected` | `str` | e.g. `"≥ 0.65"` |
| `actual` | `str` | e.g. `"0.55"` — mirrors `data-base/05-schema-reasoning.md`'s own worked `q-1` example row |

## `ConfirmedBaselineWindow` (new value object, `app.readers.domain`)

What the Tone reader actually receives as "how this stakeholder normally
writes" (`research.md` Decision 2) — a resolved, human-confirmed window plus
the raw message text sampled from it, not a rolled-up scalar.

| Field | Type | Description |
|---|---|---|
| `stakeholder_id` | `UUID` | |
| `window_start` / `window_end` | `datetime` | From `baseline_confirmations` |
| `sample_texts` | `list[str]` | Decrypted body text of every message-type event within the window — the LLM's actual comparison material |
| `sample_count` | `int` | `len(sample_texts)` — compared against REQ-M6-CAL-04's floor of 5 before the reader even calls the model |

**On `baseline_confirmations.metric`** (found under-specified during
`/speckit-analyze`): the table is part-keyed by `(subject_type, subject_id,
metric, window)`, and `scripts/confirm_baseline.py` takes a `--metric` flag,
but `ConfirmedBaselineRepositoryPort.get_confirmed_window` (below) takes only
`stakeholder_id` — it deliberately does not filter by `metric`. This feature
assumes **at most one confirmed baseline window per stakeholder** at a time;
`metric` is retained as a free-text descriptive label on the row (consistent
with the column already existing in the schema since feature 001) but is not
part of this feature's read query. If a deployment ever confirms two windows
for the same stakeholder under different metric labels, `get_confirmed_window`
returns whichever the underlying query's default ordering picks — undefined
beyond "one of them" — a real limitation, not a bug, and one no reasonable
Phase 1 workflow triggers (`confirm_baseline.py` is a manual, one-at-a-time
script). Revisit if a second real metric type is ever needed.

## `MessageEventInfo` (new value object, `app.readers.domain`)

The shared candidate corpus both Tone and Intent iterate over — both cite the
same real event (`gmail-msg-8831`) in `examples/01-end-to-end-walkthrough.md`
§6's `fnd-6`/`fnd-7`, proving they read the same underlying data, not two
separate feeds.

| Field | Type | Description |
|---|---|---|
| `event_id` | `UUID` | |
| `occurred_at` | `datetime` | |
| `stakeholder_id` | `UUID \| None` | The message's resolved sender, when identity resolution succeeded (feature 003) |
| `text` | `str` | Decrypted body/title text — Gmail body, Zendesk ticket title/description, or Slack message |

## New ports (`app.readers.application.ports`)

Reader-owned, same convention as every existing port in this file — no
cross-module adapter import.

| Port | Method(s) | Used by |
|---|---|---|
| `LLMPort` | `generate_structured(prompt: str, schema: type[T]) -> T` | Tone, Intent (`ToneReader`/`IntentReader` hold this; `architecture/09`'s already-named single-method interface) |
| `MessageEventRepositoryPort` | `list_all() -> list[MessageEventInfo]` | Tone **and** Intent (Foundational — the shared candidate corpus both readers self-fetch from; cache filtering against already-interpreted events happens inside each reader via the existing `FindingRepositoryPort.already_interpreted`, not in this port) |
| `ConfirmedBaselineRepositoryPort` | `get_confirmed_window(stakeholder_id: UUID) -> ConfirmedBaselineWindow \| None` | Tone reader |
| `FindingTypeConfigPort` | `get_thresholds(finding_type: str) -> tuple[float, int] \| None` — `(confidence_floor, min_evidence_count)`, `None` if `finding_type` isn't a configured row | `ValidationGate` — a `None` result *is* how the schema check's `finding_type`-membership sub-check is implemented (`research.md` Decision 6, corrected during `/speckit-analyze` to actually be reachable rather than only described in prose) |
| `EventExistencePort` | `existing_ids(ids: list[UUID]) -> set[UUID]` — which of the given IDs are real rows in `events` | `ValidationGate` |
| `QuarantineRepositoryPort` | `record(finding_id: UUID, failed_checks: list[FailedCheck]) -> None` | `ValidationGate` (via `RunReadersUseCase`) |

`FindingRepositoryPort` (existing) needs no new method — `persist(finding)`
is called exactly once per finding, after the gate has already decided its
final `status`, matching the existing single-write shape.

## New adapters (`app.readers.adapters`)

| Adapter | Implements | Note |
|---|---|---|
| `AnthropicLLMAdapter` | `LLMPort` | The only class importing `anthropic` (mirrors `OpenAIEmbeddingAdapter`, feature 005's precedent). Calls `client.messages.parse(output_format=schema)` — the SDK's native structured-output mechanism (`research.md` Decision 4); no `tools` parameter is ever passed. |
| `SqlAlchemyMessageEventRepository` | `MessageEventRepositoryPort` | Reads message-bearing events (Gmail/Zendesk/Slack), decrypting bodies the same way feature 003's ledger read path already does |
| `SqlAlchemyConfirmedBaselineRepository` | `ConfirmedBaselineRepositoryPort` | Joins `baseline_confirmations` → `events`, decrypts message bodies the same way every other reader-facing event read already does (feature 003's `pgcrypto` column decryption) |
| `SqlAlchemyFindingTypeConfigRepository` | `FindingTypeConfigPort` | Reads `finding_type_config` — same table `app.scoring`'s own port reads, different columns/shape, not a cross-module import (`research.md`'s established convention) |
| `SqlAlchemyEventExistenceRepository` | `EventExistencePort` | A single `SELECT id FROM events WHERE id = ANY(:ids)`-shaped existence check |
| `SqlAlchemyQuarantineRepository` | `QuarantineRepositoryPort` | Inserts one `quarantine` row (`UNIQUE(finding_id)`, REQ-M5A-03) plus one `quarantine_reasons` row per failed check |

## `RunReadersUseCase` (extended, not replaced)

Current shape (feature 005): iterate readers → persist every emitted finding
directly at `pending_validation`. New shape:

```
for reader in self._readers:
    try:
        emitted = await reader.interpret()
    except Exception as exc:
        record error, continue to next reader   # unchanged (FR-014)
        continue
    for finding in emitted:
        try:
            result = self._gate.evaluate(finding)
            final = dataclasses.replace(
                finding,
                status="validated" if result.passed else "quarantined",
            )
            await self._findings.persist(final)
            if not result.passed:
                await self._quarantine.record(final.id, result.failed_checks)
        except Exception as exc:
            record error against this finding, continue to the next finding
            # extends FR-014's per-reader isolation down to per-finding: one
            # bad finding (or a transient DB error on its persist/quarantine
            # write) must not abort the rest of this reader's batch, let
            # alone the readers still queued after it (gap found during
            # `/speckit-analyze` — the gate/persist step was previously
            # outside any try/except at all)
```

`ValidationGate.evaluate()` itself never raises for an ordinary "unconfigured
finding_type" case — `FindingTypeConfigPort.get_thresholds()` returns `None`
rather than raising, and the gate treats a `None` result as a `schema_invalid`
failure (one more reason `finding_type` membership belongs in the schema
check, `research.md` Decision 6.1) — so the `try` above is a defensive
backstop for genuine infrastructure failures (a dropped DB connection mid-
write), not the mechanism for an expected validation outcome. `ValidationGate`
takes no I/O dependency beyond `FindingTypeConfigPort` and `EventExistencePort`
— it stays a pure Chain-of-Responsibility over four fixed checks
(`architecture/09`'s named pattern), never itself calling an LLM or another
reader.

## Finding-type config (data change, not schema change)

Two new rows in `data-base/11-seed-data.sql`, appended after the existing
nine (`research.md` Decision 7):

| finding_type | base_points | confidence_floor | min_evidence_count | half_life_days | version |
|---|---|---|---|---|---|
| `competitive_mention` | 14.00 | 0.60 | 1 | 14 | v1 |
| `contractual_reference` | 14.00 | 0.60 | 1 | 14 | v1 |

## State transitions

`Finding.status`: `pending_validation` (reader's construction-time default,
never persisted at this value anymore once the gate is wired in) →
`validated` | `quarantined` (gate's decision, terminal — REQ-M5A-03, never
re-evaluated).

`baseline_confirmations`: append-only, never truncated, never edited
(`data-base/03-schema-ledger.md`'s own description) — this feature's
`scripts/confirm_baseline.py` only inserts new rows.
