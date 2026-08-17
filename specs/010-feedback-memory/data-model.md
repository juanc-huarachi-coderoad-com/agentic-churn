# Data Model: Feedback Memory

No migration — `feedback_verdicts` and `damping_weights` have existed,
unpopulated (`feedback_verdicts`) or default-only (`damping_weights`, every
row implicitly `weight = 1.000` by never existing), since feature 001's
initial `0001_initial_schema` migration (`data-base/10-ddl-appendix.md`
"07 · Feedback memory" section). This feature is the first real writer of
both tables, the same status `draft_messages` had before feature 009 and
`narrator_outputs`/`ask_queries` had before feature 008.

## Domain (`backend/app/context/domain/`)

### `damping_calculator.py` (NEW) — pure, no I/O

```python
def pattern_signature(reader_type: str, finding_type: str) -> str:
    """Canonical key format — MUST match app.scoring's existing consumer
    exactly (research.md Decision 1/2)."""
    return f"{reader_type}+{finding_type}"

def compute_weight(false_alarm_count: int, correct_count: int) -> float:
    """REQ-M6-CAL-03a. resolved_count never enters this formula (REQ-M6-CAL-03b,
    research.md Decision 6) — a resolved verdict simply never increments
    false_alarm_count or correct_count, so the weight it recomputes to is
    unchanged by construction, with no verdict-type branch needed here."""
    raw = (0.5 ** false_alarm_count) * (1.15 ** correct_count)
    return max(0.0, min(1.0, raw))

def build_disclosure_text(false_alarm_count: int, correct_count: int, resolved_count: int) -> str | None:
    """REQ-M4-04. None when the pattern has never received a false_alarm/
    correct verdict (weight is still the undamped 1.0 default) — no
    disclosure is shown for a pattern nothing has ever been said about."""
    ...
```

### `entities.py` (NEW)

```python
@dataclass(frozen=True)
class DampingWeight:
    pattern_signature: str
    weight: float
    false_alarm_count: int
    resolved_count: int
    correct_count: int
    disclosure_text: str | None
    last_updated_at: datetime
```

State transitions: a `DampingWeight` is created (all counts zero,
`weight = 1.0`, `disclosure_text = None`) on the first verdict matching its
pattern (FR-008, upsert semantics) and is thereafter only ever upserted in
place — never deleted (mirrors `feedback_verdicts`' own append-only
discipline; the *count* history is append-only via `feedback_verdicts`,
even though the *weight* row itself is mutated, matching
`data-base/07-schema-feedback.md`'s own "upserted as new verdicts arrive"
description).

## Application (`backend/app/context/application/`)

### `ports.py` (extend)

```python
@dataclass(frozen=True)
class FindingPatternComponents:
    reader_type: str
    finding_type: str

class FeedbackFindingReadPort(ABC):
    @abstractmethod
    async def get_pattern_components(self, finding_id: UUID) -> FindingPatternComponents | None:
        """None if finding_id doesn't exist or isn't validated (mirrors
        SqlAlchemyFindingReader.get_finding's existing status='validated'
        filter, app.experience precedent)."""

class IssueTopFindingReadPort(ABC):
    @abstractmethod
    async def get_top_finding_id(self, issue_id: UUID) -> UUID | None:
        """rank_within_issue = 1 for the given issue; None if the issue
        doesn't exist or has no mapped findings."""

class FeedbackVerdictRepositoryPort(ABC):
    @abstractmethod
    async def get_damping(self, pattern_signature: str) -> DampingWeight:
        """A zeroed, weight=1.0 default if no row exists yet — never None
        (FR-008's upsert semantics live at the write, not the read)."""

    @abstractmethod
    async def record(
        self,
        *,
        finding_id: UUID | None,
        issue_id: UUID | None,
        verdict: str,
        submitted_by_user_id: UUID,
        updated: DampingWeight,
    ) -> None:
        """One transaction: append to feedback_verdicts, upsert damping_weights."""
```

### `use_cases.py` (extend)

```python
class VerdictRequiresFindingError(Exception):
    """FR-005a — false_alarm/correct submitted with only issue_id."""

class FindingNotFoundError(Exception): ...
class IssueNotFoundError(Exception): ...

class RecordFeedbackVerdictUseCase:
    def __init__(
        self,
        findings: FeedbackFindingReadPort,
        issues: IssueTopFindingReadPort,
        verdicts: FeedbackVerdictRepositoryPort,
    ) -> None: ...

    async def execute(
        self, *, finding_id: UUID | None, issue_id: UUID | None,
        verdict: str, submitted_by_user_id: UUID,
    ) -> None:
        """
        1. FR-005a: verdict in {false_alarm, correct} requires finding_id —
           VerdictRequiresFindingError otherwise.
        2. Resolve the target finding: finding_id directly, or (resolved +
           issue_id only) the issue's top-ranked finding — IssueNotFoundError
           if the issue has none.
        3. Look up reader_type/finding_type — FindingNotFoundError if the
           finding doesn't exist/isn't validated.
        4. pattern_signature = pattern_signature(reader_type, finding_type).
        5. current = await verdicts.get_damping(pattern_signature).
        6. Increment exactly one counter based on verdict (false_alarm_count,
           correct_count, or resolved_count) — resolved touches only its own
           counter, never false_alarm_count/correct_count (REQ-M6-CAL-03b).
        7. weight = compute_weight(new.false_alarm_count, new.correct_count).
        8. disclosure_text = build_disclosure_text(new.false_alarm_count,
           new.correct_count, new.resolved_count).
        9. await verdicts.record(..., updated=DampingWeight(...)) — single
           append + upsert (research.md Decision 5: read-then-upsert, not a
           locking transaction, at this scale).
        """
```

## Adapters (`backend/app/context/adapters/`)

### `sqlalchemy_repository.py` (extend)

- `SqlAlchemyFeedbackFindingReader(FeedbackFindingReadPort)` —
  `SELECT reader_type, finding_type FROM findings WHERE id = :id AND status = 'validated'`.
- `SqlAlchemyIssueTopFindingReader(IssueTopFindingReadPort)` —
  `SELECT finding_id FROM finding_issue_map WHERE issue_id = :id ORDER BY rank_within_issue ASC LIMIT 1`.
- `SqlAlchemyFeedbackVerdictRepository(FeedbackVerdictRepositoryPort)` —
  `INSERT INTO feedback_verdicts (...)` then
  `INSERT INTO damping_weights (...) ON CONFLICT (pattern_signature) DO UPDATE SET ...`,
  both in the same DB transaction (session commit at the router level,
  matching every other write use case's existing pattern in this
  codebase).

### `feedback_router.py` (NEW)

`POST /api/feedback` — see `contracts/feedback.md`.

## Cross-module read-side extension (`backend/app/experience/`) — disclosure surfacing, REQ-M4-04

### `application/ports.py` (extend)

```python
@dataclass(frozen=True)
class DisclosureRecord:
    disclosure_text: str

class DampingDisclosurePort(ABC):
    @abstractmethod
    async def get_disclosure(self, pattern_signature: str) -> DisclosureRecord | None:
        """None whenever weight >= 1.0 — the FR-011 'only when true and
        relevant' rule enforced at the read, not left to the caller."""
```

### `adapters/sqlalchemy_repository.py` (extend)

- `SqlAlchemyDampingDisclosureReader(DampingDisclosurePort)` —
  `SELECT disclosure_text FROM damping_weights WHERE pattern_signature = :ps AND weight < 1.000`.

### `application/use_cases.py` (extend)

`GetEvidenceTraceUseCase` — after resolving the finding's `reader_type`
(already read for other purposes, or newly read via the same
`SqlAlchemyFindingReader` extended to return `reader_type` too), computes
`pattern_signature(reader_type, finding_type)` (imported from
`app.context.domain.damping_calculator`, research.md Decision 2) and calls
`DampingDisclosurePort.get_disclosure`, attaching the result to
`EvidenceTraceResponse.disclosure_text`.

## Entity relationship (unchanged tables, new writers/readers only)

```
findings ──┐
           ├─(reader_type, finding_type)─► pattern_signature() ─┬─► feedback_verdicts (append)
issues ────┘ (via finding_issue_map,                            └─► damping_weights (upsert)
              rank_within_issue = 1,
              resolved+issue-scoped only)

damping_weights ─(pattern_signature)─► DampingRepositoryPort.get_weight()   [feature 004, unchanged]
                 ─(pattern_signature)─► DampingDisclosurePort.get_disclosure() [NEW, this feature]
```
