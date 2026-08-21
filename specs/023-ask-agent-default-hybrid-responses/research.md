# Phase 0 Research: Ask Agent Default Hybrid Responses

No `NEEDS CLARIFICATION` markers remain in spec.md — the one material ambiguity ("how
short is short") was resolved during `/speckit-clarify` (a hard 3-sentence cap). What
follows are the technical decisions needed to implement that spec against the actual
current codebase, all grounded in direct reading of
`backend/app/experience/adapters/ask_agent_graph.py` (specs/014's implementation).

## Decision 1: Collapse `ResponseMode` from three values to two

**Decision**: `ResponseMode` (currently `COMPONENT_ONLY | TEXT_ONLY | HYBRID`) becomes
`TEXT_ONLY | HYBRID`. `ClassifyOutput.response_mode`'s default changes from
`ResponseMode.COMPONENT_ONLY` to `ResponseMode.HYBRID`. `_classify_prompt`'s
response-mode section drops the `component_only` category and its "prefer it when in
doubt" bias entirely; the surviving instruction is reworded so hybrid is presented as
the default outcome for any structured-data question, with `text_only` reserved for
phrasing that is genuinely conversational/explanatory with no visual fit (the existing
discriminating examples — "why does this matter", "explain in plain terms", "how
should I..." — carry over unchanged, since that judgment call is untouched by this
feature).

**Rationale**: The user's request is unconditional — "usually/always" both together —
which is a product decision, not a per-question judgment call. A prompt-bias flip
alone (keeping 3 modes, just changing which one is "preferred") would only make
hybrid *more likely*, not guaranteed, which doesn't satisfy FR-001's "MUST." Removing
the mode entirely is also the smaller, simpler surface (P10/YAGNI): one less branch in
`route_after_resolve_and_render`, one less case in the `answer()` parts-assembly
`if/elif/else`, one less category for the classify prompt to get wrong.

**Tension with `specs/014-ask-agent-response-formats` research.md Decision 1,
addressed directly**: That decision's rationale was that *whether a visual fits the
question's phrasing at all* is a genuine judgment call worth leaving to the model —
"a hardcoded per-intent mapping would defeat the point of the feature." That axis is
fully preserved here: `text_only` vs. "else" is still an LLM judgment call from the
question's phrasing, exactly as before. What's being removed is a second, different
axis `014` bundled into the same enum alongside it: "given that a visual renders,
should it also get an explanatory blurb?" `014` never needed to leave that question
open-ended; this feature's own spec has now answered it unconditionally (FR-001).
Collapsing the enum resolves a question `014`'s rationale didn't depend on keeping
open — it does not undo `014`'s actual reasoning.

**Alternatives considered**:
- Keep 3 modes, only reword the prompt bias toward hybrid — rejected: leaves the
  outcome probabilistic, not guaranteed, contradicting spec.md FR-001's "MUST."
- Keep 3 modes, but change `route_after_resolve_and_render` to always call
  `generate_text` even for `component_only`, and treat `component_only` +
  successful text as hybrid at assembly time — rejected: this achieves the same
  runtime behavior as the collapse, but leaves a permanently-unreachable
  `COMPONENT_ONLY` value alive in the enum, the classify prompt, and the log column's
  implied vocabulary — a dead code path future readers would have to figure out is
  dead. YAGNI favors actually removing it.

## Decision 2: `route_after_resolve_and_render` always generates text once a component exists

**Decision**: Simplify the routing function to unconditionally return
`"generate_text"` whenever `state["component"]` is not `None` — delete the
`mode in (TEXT_ONLY, HYBRID)` gate, since both surviving modes need the text step
(`text_only` already needed it to produce its sole text part; the retired
`component_only` path never called it, but no surviving mode skips it now).

**Rationale**: Direct mechanical consequence of Decision 1 — once `component_only` no
longer exists, every component-bearing state needs the same next step.

## Decision 3: Reframe `_text_generation_prompt` around explaining the visual

**Decision**: Replace the "write a short, clear, conversational Markdown answer to
this question" framing with instructions to explain, in plain executive language,
what the component is showing the CS manager and why it matters — or, when the
numbers already speak for themselves, to surface the single most useful additional
insight instead of restating them — explicitly telling the model not to narrate the
data field-by-field or restate the question. Tighten the length instruction from
"2 to 4 sentences" to a hard "at most 3 sentences" (or an equivalently short bullet
list), matching spec.md FR-002/SC-002 exactly. All existing grounding rules are kept
verbatim: only state facts literally present in the data, never quote a `*_id`/UUID,
use headings/emphasis/lists only where genuinely helpful, code fences only for
literal code.

**Rationale**: Directly implements FR-003. The prior framing was written for
`text_only` (a real generated *answer* to a real question) and reused as-is for
`hybrid`; now that hybrid is the default outcome, the accompanying text needs its own
framing tuned for "explaining a visual the manager can already see," which is a
different communicative task than "answering a question with no visual at all."
`text_only` responses still exist (for genuinely conversational questions with no
component) and are close enough to the original framing that no separate prompt
variant is needed — YAGNI: one prompt, reworded, not two.

**Alternatives considered**:
- Keep two separate prompt functions, one for `text_only` and one for `hybrid` —
  rejected: the underlying task ("write short, grounded, fact-checked Markdown from
  this data") is the same; a single reframed prompt already produces good output for
  both cases (a `text_only` answer *is* effectively "explain what the data shows,"
  just with no visual sitting next to it), and two near-duplicate prompt functions
  would be exactly the kind of speculative duplication P10 warns against.

## Decision 4: `write_to_stakeholder` stays exempt — no code change, comment only

**Decision**: No behavior change needed. `route_intent` already sends
`Intent.WRITE_TO_STAKEHOLDER` straight to the `handoff` node, which edges directly to
`log_result` — it never touches `resolve_and_render`, `route_after_resolve_and_render`,
or `generate_text`. Add a short comment on the `handoff` → `log_result` edge noting
this exemption is intentional (the draft itself is already prose; a generic blurb on
top would be redundant), so a future refactor doesn't accidentally wire it into the
now-universal hybrid path.

**Rationale**: Directly satisfies FR-005/SC-003 (US3). Confirmed via direct reading of
`route_intent`'s branch and the graph's edges that this path structurally cannot reach
the changed code at all — a documentation note, not a functional change, is all that's
needed to keep it that way on purpose.

## Decision 5: `log_result`'s default response_mode string changes to `"hybrid"`

**Decision**: The `(state.get("response_mode") or "component_only") if component else
None` fallback in `log_result` becomes `(state.get("response_mode") or "hybrid") if
component else None`, matching the new default. Historical rows already logged as
`"component_only"` are left as-is (no backfill) — `ask_queries.response_mode` is a
free-text nullable column with no DB-level enum constraint (confirmed via
`migrations/versions/0005_ask_queries_response_mode.py`), so old and new values
coexist as legitimate history, matching how this table already treats
`matched_intent`/`declined_reason` value changes over time.

**Rationale**: Directly implements FR-009 (no logging gap) — the log should record
what the system actually decided, and the new decision defaults to hybrid, not
component_only.

## Decision 6: Blast radius confirmation — no migration, no frontend, no other consumer

**Decision**: Confirmed via repo-wide grep (word-boundary, excluding the
`response_model` FastAPI-parameter false-positive substring match) that
`response_mode` is referenced only in: `ask_agent_graph.py` (the file being changed),
`ask_router.py` (docstring only — the API response schema itself,
`AskAnsweredResponse`, does **not** expose `response_mode` as a field at all; only
`intent`/`parts` are public, so the API contract is untouched by the enum collapse),
`ports.py`/`sqlalchemy_repository.py` (both typed as plain `str | None`, no enum
coupling), the migration that added the column, and the two test files. No
dashboard/analytics view, no other backend module, and no frontend file reads this
value. `AnswerRenderer`/`ResponsePart` (frontend) already render an ordered `parts`
list generically and require no change.

**Rationale**: Establishes the actual scope is exactly what plan.md's Project
Structure names — one adapter file and two test files — with no hidden downstream
coupling to the removed enum value.

## Decision 7: Constitution amendment content (MINOR, follow-up task)

**Decision**: As flagged in plan.md's Constitution Check, two passages in
`.specify/memory/constitution.md`'s **Development Workflow & Quality Gates** section
need a follow-up MINOR amendment (version bump with a fresh Sync Impact Report,
following this project's own amendment procedure) as an implementation task for this
feature, not a silent drift:

1. **AI safety Rule 1**: the sentence "The Ask agent's own response-format decision
   (`component_only` vs `text_only` vs `hybrid`) is itself a schema-constrained field
   on the same classify call that already decides `intent` — never a free judgment."
   becomes "...(`text_only` vs `hybrid`)..." — a two-value inventory instead of three.
2. **Resilience budgets paragraph**: the clause "Ask agent `component_only` 2.5s with
   no retry (a retry would already blow its 3s budget — falls back to plain text
   immediately); Ask agent `text_only`/`hybrid` adds a second call..." is rewritten to
   drop the now-unreachable `component_only` fast path as a distinct case, stating
   instead that every structured-intent answer now goes through the classify call
   plus the (already-existing, already-accepted) 15s-capped text-generation call —
   the ceiling itself is unchanged from what `014` already shipped and the
   constitution already accepted; only its applicability (virtually all responses,
   not a subset) changes.

**Rationale**: This project's constitution explicitly amended itself (v1.3.0 → v1.4.0)
*for* `specs/014` when hybrid was first introduced, precisely because the Development
Workflow & Quality Gates section names concrete, current Ask-agent behavior verbatim
rather than describing it abstractly. The Governance section is explicit that a
disagreement between the constitution's stated text and actual behavior "is a bug to
fix, not a judgment call to make silently — flag it." Leaving the three-way language
in place after this feature ships would create exactly that kind of drift. Per
existing precedent, this amendment happens as part of this feature's own
implementation (a `tasks.md` item), not during `/speckit-plan` itself.

**Alternatives considered**:
- Leave the constitution text as-is, treating it as "close enough" — rejected: this
  is the exact class of silent drift the Governance section calls out as a bug, and
  the project's own history shows the correct response is a scoped MINOR amendment,
  not a shrug.
- Bump MAJOR instead of MINOR — rejected: no Core Principle (P1-P11) is redefined or
  relaxed; this is a factual-inventory update to an already-existing rule's stated
  detail, matching the MINOR classification used for the `014` amendment that first
  introduced this exact language.

## Decision 8: No new `prompt_version` tracking for the Ask agent's prompts

**Decision**: Out of scope. Unlike the Narrator (`narration_v1.py`) and Draft composer
(`draft_composer_v1.py`), the Ask agent's `_classify_prompt`/`_text_generation_prompt`
were never given a versioned-file-plus-logged-field treatment, even when `014`
introduced/changed this exact prompt text. This is a pre-existing convention gap,
not one this feature introduces or worsens — `ask_queries` has no `prompt_version`
column today (confirmed via `migrations/versions/0001_initial_schema.py`'s
`ask_queries` table definition). Rule 5's "version-controlled" requirement is
satisfied today at the git-history level for this specific touchpoint, consistent
with how `014` already changed this same prompt without adding formal version
tracking.

**Rationale**: P10/YAGNI — introducing a new versioning mechanism for one file's
prompts is a real scope expansion beyond what this feature's spec asks for, and would
apply an inconsistent standard (retrofitting one touchpoint but not fixing the
pattern project-wide). If the project wants Narrator/Draft-composer-style versioning
for the Ask agent's prompts, that is a separate, explicitly-scoped feature.
