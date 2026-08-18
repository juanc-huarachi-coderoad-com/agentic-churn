# Phase 1 Data Model: Ask Agent Flexible Response Formats

## New domain entities — `backend/app/experience/domain/entities.py` (new file)

Appended to this module's existing domain entities file (`app.experience.domain.entities` already holds dashboard/evidence/draft-composer value objects from features 006/009, and already imports `FactCheckResult` from `app.narrator.domain.entities` — the domain-to-domain reuse pattern this feature also relies on, research.md Decision 4, was already established here before this feature).

```python
from dataclasses import dataclass
from typing import Any, Literal

@dataclass(frozen=True)
class TextPart:
    kind: Literal["text"]
    markdown: str
    """Already fact-checked (research.md Decision 4) before this object is
    constructed — a TextPart is never created from an unverified sentence."""

@dataclass(frozen=True)
class ComponentPart:
    kind: Literal["component"]
    component: str
    """One of the existing closed set of 8 component types — unchanged."""
    component_props: dict[str, Any]

ResponsePart = TextPart | ComponentPart
```

## Modified: `ClassifyOutput` (`ask_agent_graph.py`)

```python
class ResponseMode(StrEnum):
    COMPONENT_ONLY = "component_only"
    TEXT_ONLY = "text_only"
    HYBRID = "hybrid"

@dataclass
class ClassifyOutput:
    intent: Intent            # unchanged
    subject_hint: str | None  # unchanged
    response_mode: ResponseMode  # NEW — same schema-constrained call
```

**Validation rule**: `response_mode` is only meaningful when `intent` maps to one of the 8 existing structured intents (`_COMPONENT_BY_INTENT`'s keys). For `Intent.NONE`/`Intent.PREDICTION`/`Intent.COLLEAGUE_JUDGMENT`/`Intent.WRITE_TO_STAKEHOLDER` (handoff, its own terminal shape), `response_mode` is ignored by `route_intent` — those paths are unchanged (research.md Decision 2).

## Modified: `AskAgentState` (`experience/application/ports.py`)

```python
class AskAgentState(TypedDict, total=False):
    question: str                        # unchanged
    asked_by_user_id: UUID               # unchanged
    intent: str | None                   # unchanged
    subject_hint: str | None             # unchanged
    response_mode: str | None            # NEW
    tool_results: dict[str, Any]         # unchanged
    component: str | None                # unchanged (still populated for the
                                          #   component_only/hybrid case's own
                                          #   component part — see below)
    component_props: dict[str, Any] | None  # unchanged
    generated_text: str | None           # NEW — the fact-checked Markdown, if any
    fallback_text: str | None            # unchanged
    sources: tuple[UUID, ...]            # unchanged
    declined_reason: str | None          # unchanged
    started_at: float                    # unchanged
```

`component`/`component_props`/`generated_text` are assembled into `parts` at the very end (`log_result`'s sibling, the result-construction step in `LangGraphAskAgent.answer`) — the graph's intermediate nodes keep writing to the same flat state keys they already do, minimizing the diff inside `resolve_and_render`'s existing per-intent branches.

## Modified: `AskAgentResult` (`experience/application/ports.py`)

```python
@dataclass(frozen=True)
class AskAgentResult:
    intent: str | None                      # unchanged
    parts: tuple[ResponsePart, ...]          # NEW — replaces component/component_props
                                              #   for the answered case; empty tuple when
                                              #   this is a decline/fallback result
    fallback_text: str | None                # unchanged
    sources: tuple[UUID, ...]                # unchanged
    declined_reason: str | None              # unchanged
    response_mode: str | None                # NEW — for ask_queries logging (research.md
                                              #   Decision 6); None for decline/fallback
    response_time_ms: int                    # unchanged
```

`component`/`component_props` fields are removed from `AskAgentResult` — every current caller reads `parts[0]` instead for the component_only case (there is always exactly one part in that case, research.md Decision 5).

## API contract shapes (`ask_router.py`) — see `contracts/ask.md` for the full contract

```python
class ResponsePartSchema(BaseModel):
    type: Literal["text", "component"]
    markdown: str | None = None            # present iff type == "text"
    component: str | None = None           # present iff type == "component"
    component_props: dict[str, Any] | None = None  # present iff type == "component"

class AskAnsweredResponse(BaseModel):  # replaces AskComponentResponse
    intent: str
    parts: list[ResponsePartSchema]

class AskFallbackResponse(BaseModel):  # UNCHANGED
    fallback_text: str
    sources: list[UUID]
    declined_reason: str | None = None
```

## Modified: `ask_queries` table (one additive Alembic migration)

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `response_mode` | `text` | yes | `component_only` \| `text_only` \| `hybrid` for answered queries; `NULL` for decline/fallback rows (mirrors `rendered_component`'s existing `NULL`-for-fallback convention) |

No other schema change. `matched_intent`, `rendered_component`, `declined_reason`, `response_time_ms` are all unchanged in meaning; `rendered_component` continues to record the *first* component part's type when one exists (unchanged for `component_only`; for `hybrid`, the same component name it always would have recorded).

## Reused, unmodified: `VerifiedFactSet` / `FactCheckResult` / `fact_check()` (`app.narrator.domain`)

```python
# app/narrator/domain/entities.py — imported, not modified
@dataclass(frozen=True)
class VerifiedFactSet:
    numbers: frozenset[str]
    names: frozenset[str]

@dataclass(frozen=True)
class FactCheckResult:
    passed: bool
    extracted_numbers: frozenset[str]
    extracted_names: frozenset[str]

# app/narrator/domain/services.py — imported, not modified
def fact_check(sentence: str, facts: VerifiedFactSet) -> FactCheckResult: ...
```

A new `_build_verified_facts_from_tool_results(component_props: dict) -> VerifiedFactSet` helper (in `experience/adapters/ask_agent_graph.py`, adjacent to the graph, not in the reused domain module) extracts numbers/names from the same `component_props` already assembled for the intent — mirroring the Narrator's own `_build_verified_facts` (extend the verified-numbers set with every point value's rounded and one-decimal string form, exactly as the Narrator already does for its own contribution points).

## State transitions

None new beyond what `route_intent` already governs. `response_mode` does not introduce a new terminal node — `resolve_and_render` still terminates the same way for every intent; the only addition is an optional text-generation + fact-check step invoked *after* `resolve_and_render` produces `component_props`, before `log_result`, gated on `response_mode != component_only`.
