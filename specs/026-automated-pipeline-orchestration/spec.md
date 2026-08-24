# Feature Specification: Automated Pipeline Orchestration

**Feature Branch**: `026-automated-pipeline-orchestration`

**Created**: 2026-08-24

**Status**: Draft

**Input**: User description: "Wire RunReadersUseCase and NarrateScoreRunUseCase into backend/app/worker.py, following the exact shape of the existing _run_absence_detection/_run_score_recompute jobs. Today only the collector run and score recompute are automated (hourly heartbeat); readers and the narrator are 100% manual, only ever run via backend/scripts/run_readers.py and backend/scripts/run_narrator.py. Must resolve: (1) polling vs LISTEN/NOTIFY trigger; (2) a 'nothing new since last run' short-circuit before invoking readers, since two of the eight readers make real LLM calls and the Recurrence reader re-embeds+re-clusters the full candidate corpus every run. Second feature in a 7-feature production-readiness roadmap; depends on feature 025 (CI/CD) only for its now-enforced CI gate, no code dependency."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A new signal updates the dashboard with no manual step (Priority: P1)

A new email, ticket, or other signal arrives for a client. Today, that signal only ever turns into an updated score, findings, and a narrated explanation if a person manually runs `scripts/run_readers.py` and then `scripts/run_narrator.py` after the collector picks it up. This story replaces that manual sequence with an automatic one: once the signal has been ingested, the system itself runs the readers, recomputes the score, and generates the narration — the CS lead simply sees an up-to-date dashboard the next time they look.

**Why this priority**: This is the core problem this feature exists to solve. `scripts/run_narrator.py`'s own documentation states plainly that no automatic path to narration exists anywhere in this pipeline today — meaning the single most CS-lead-visible output of the whole system (the narrated explanation on the dashboard) currently depends entirely on an engineer remembering to run two scripts in order. Every other story in this feature depends on this one existing.

**Independent Test**: Ingest a new signal (e.g. trigger the existing collector), wait without running any script by hand, and confirm the dashboard's findings, score, and narrated explanation reflect the new signal within the system's existing "event to updated score" latency target.

**Acceptance Scenarios**:

1. **Given** a new signal has just been ingested into the ledger, **When** no person runs any script, **Then** the readers, score recompute, and narration all run automatically and the dashboard reflects the result within the existing latency target.
2. **Given** the automatic pipeline has just run and produced new findings, **When** a CS lead opens the dashboard, **Then** they see the same result they would have seen if an engineer had manually run the full script sequence.
3. **Given** one reader fails for an unrelated reason (e.g. a missing credential), **When** the automatic pipeline runs, **Then** the other readers still complete and their findings are still scored and narrated — a single reader's failure never silently blocks the rest of the pipeline (matching the isolation the manual path already guarantees today).

---

### User Story 2 - A quiet period costs nothing (Priority: P2)

When nothing new has happened for a client since the last cycle, the system does not repeat expensive work (re-running readers that make real AI calls, or re-embedding and re-clustering the full ticket history) just because a scheduled check happened to fire. A healthy, quiet account stays quiet — and cheap.

**Why this priority**: Without this, User Story 1's automation would come at a real, recurring cost: every scheduled check would re-run all eight readers — including two that make paid AI calls and one that re-embeds and re-clusters the full candidate history — regardless of whether any new signal actually arrived. This directly protects the product's own "silence is a success state" principle: a healthy account should not generate hidden background cost just because time passed.

**Independent Test**: Let two scheduled cycles pass with no new signal ingested in between, and confirm (via logs or call counts) that the second cycle performed no reader or narration work.

**Acceptance Scenarios**:

1. **Given** no new events have been ingested since the last automatic cycle, **When** the next scheduled check fires, **Then** it performs no reader re-run, no re-embedding, and no narration work.
2. **Given** a new event was ingested since the last cycle, **When** the next scheduled check fires, **Then** it does perform the full readers → score → narration sequence.

---

### User Story 3 - An operator can still trigger the full pipeline on demand (Priority: P3)

For verification, demos, or troubleshooting, an operator can still deliberately trigger the full readers → score → narration sequence immediately, without waiting for the next scheduled cycle — the same way the existing manual scripts already allow today.

**Why this priority**: This preserves an existing, already-relied-upon capability (this repository's own quickstart/verification walkthroughs run these steps manually and in order) rather than removing it in favor of automation alone. It is lower priority than Stories 1/2 because it is not solving a new problem — it is making sure automating the pipeline doesn't take away a tool people already use.

**Independent Test**: Trigger the pipeline manually (independent of the schedule) and confirm it runs to completion the same way the existing `scripts/run_readers.py`/`scripts/run_narrator.py` sequence does today.

**Acceptance Scenarios**:

1. **Given** an operator wants to force a full pipeline run right now, **When** they trigger it manually, **Then** the readers, score recompute, and narration all run immediately, regardless of whether anything is new.
2. **Given** the existing manual scripts (`scripts/run_readers.py`, `scripts/run_narrator.py`), **When** an operator runs them directly as before, **Then** they continue to work exactly as they do today, unchanged — this feature adds an automatic path, it does not remove the manual one.

---

### Edge Cases

- What happens when a scheduled cycle is still running and the next scheduled check fires before it finishes? The system must not start a second, overlapping run of the same cycle — it should skip or wait, never run two cycles concurrently against the same client's data.
- What happens when the score recompute inside an automatic cycle produces no new findings at all (a healthy account)? Narration must not run on nothing — matching the existing manual path, where the narrator already has nothing to narrate for a score run with no findings.
- What happens when readers run automatically but the score recompute step that must follow them fails? The cycle must fail visibly (logged), not silently leave findings persisted with no corresponding score/narration update.
- What happens to a client whose ingestion has genuinely gone silent for a long time (no new signals at all)? The automatic pipeline correctly does nothing new each cycle (User Story 2) — this must not be confused with, or reported as, a system failure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST automatically run the full readers pipeline after new signals have been ingested, without requiring a person to run a script.
- **FR-002**: The system MUST automatically generate a narrated explanation after an automatic score recompute produces at least one finding, without requiring a person to run a script.
- **FR-003**: The system MUST run readers, score recompute, and narration in that dependency order within an automatic cycle, so narration always describes the score that was just computed, never a stale one.
- **FR-004**: The system MUST skip the readers/score/narration work for an automatic cycle when no new signal has been ingested since the previous cycle.
- **FR-005**: The automatic pipeline MUST preserve the existing per-reader failure isolation — one reader failing MUST NOT prevent the other readers, score recompute, or narration from proceeding.
- **FR-006**: The system MUST NOT run two automatic cycles concurrently for the same deployment.
- **FR-007**: An operator MUST be able to trigger one full pipeline cycle on demand, independent of the automatic schedule, for verification and troubleshooting purposes.
- **FR-008**: The existing manual scripts MUST continue to function unchanged as standalone tools, independent of whether the automatic path also exists.
- **FR-009**: When an automatic score recompute produces zero findings (a healthy account), the system MUST NOT attempt to generate a narration for that cycle.
- **FR-010**: A failure in the score recompute or narration step of an automatic cycle MUST be recorded/logged visibly, not silently swallowed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a new signal is ingested, the dashboard reflects the resulting updated findings, score, and narration within the system's existing event-to-updated-score latency target, with zero manual script execution.
- **SC-002**: Across a period with no new signals, the automatic pipeline performs zero reader re-runs and zero narration generations — verified by observing no new AI-backed calls occur during that period.
- **SC-003**: A person can operate this system for a full day without manually running the readers or narrator scripts, and the dashboard still reflects current data for every signal that arrived.
- **SC-004**: No two automatic pipeline cycles for the same deployment are ever observed running at the same time.

## Assumptions

- This feature only adds an automatic trigger path; it does not change what the readers, scoring engine, or narrator themselves compute — their existing behavior, contracts, and failure-isolation guarantees (already relied upon by the current manual scripts) are preserved unchanged.
- "New signal ingested since the last cycle" is evaluated by the automatic pipeline itself before doing any reader/narration work — the mechanism for detecting this is a technical decision for the implementation plan, not specified here.
- The automatic cycle's check frequency is chosen to keep the system inside its existing event-to-updated-score latency target from `requirements/11-non-functional-requirements.md`, not a new target introduced by this feature.
- This feature does not change how or when the client-facing dashboard is served — it only changes how the underlying findings/score/narration data becomes current without manual intervention.
- Per the approved production-readiness roadmap, this feature does not introduce any message broker or event-streaming platform — the automatic trigger is built on the same class of mechanism (a scheduled, in-process check) already used by this system's existing automated jobs.
