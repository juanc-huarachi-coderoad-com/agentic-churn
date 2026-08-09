# 08 · Health dashboard (M8)

Tier 4 · Experience — spec §7 (M8), §11

## Purpose

Ambient awareness. Answers one question: *does anything need me today?* Calculates nothing — everything is precomputed by M6/M7 and read directly.

## User stories

- As a **CS lead**, I want a near-empty screen when the client is healthy, so that I trust the tool instead of ignoring manufactured concern (P6).
- As a **CS lead**, I want every number to be a door — one click to the reason, one more to the source message — so that I never have to take the score on faith.
- As a **support lead**, I want to see which sources are degraded, so I know when a quiet score means "healthy" versus "we're blind right now."

## Functional requirements

| ID | Requirement |
|---|---|
| REQ-M8-01 | THE SYSTEM SHALL render the dashboard purely from precomputed, stored data (`score_runs`, `narrator_outputs`, `rollups`) — no client-facing computation of the score. |
| REQ-M8-02 | THE SYSTEM SHALL render these components: client header (name, band pill, days to renewal), score block (number, trend, sparkline), contribution bars (per-cause points, positives in green), pulse timeline (recent events, severity dot, quoted text), stakeholder cards (person, role, tone trajectory, last seen), coverage line, ask bar. |
| REQ-M8-03 | THE SYSTEM SHALL animate the score display from its previous value to its current value on load, so the direction of movement is visible. |
| REQ-M8-04 | Client quoted words SHALL render in a serif typeface as quotes; system-generated words SHALL render in a sans-serif typeface — never visually conflated. |
| REQ-M8-05 | WHEN the account is Healthy with no pending items, THE SYSTEM SHALL display a near-empty screen with the message "Nothing needs you today. Last checked [N] minutes ago." |
| REQ-M8-06 | THE SYSTEM SHALL display a coverage line stating how many of the connected sources are currently readable and how current the data is (e.g. "Reading 4 of 5 sources · complete to 09:12"). |
| REQ-M8-07 | THE SYSTEM SHALL render one of the defined system states verbatim when applicable: Healthy, Learning ("still learning — N of 6 signal types available"), Source down, Catching up, Unresolved person. |
| REQ-M8-08 | Every number on the dashboard SHALL be clickable through to the evidence trace panel, and from there to the original source message. |
| REQ-M8-09 | THE SYSTEM SHALL NOT render: ticket-volume charts, per-message sentiment lines, monthly sentiment averages, category pie charts, or any metric that would not change a decision if it changed value. |
| REQ-M8-10 | Nothing SHALL render in the risk accent color (red) until a promise is broken or a sponsor has disengaged; amber covers drift; healthy states use no risk color. |

## Explicit prohibitions

| ID | Prohibition |
|---|---|
| REQ-M8-P1 | The dashboard SHALL NEVER perform scoring, ranking, or aggregation logic client-side — it is a read layer only. |
| REQ-M8-P2 | The dashboard SHALL NEVER manufacture a concern-looking element on a quiet week (no gauges/speedometers/pulsing alarms per spec §11.1). |

## Inputs / Outputs

- **Input:** `score_runs`, `score_contributions`, `narrator_outputs`, `rollups`, `coverage_reports`, `stakeholders`.
- **Output:** rendered UI; user interactions (clicks into evidence, feedback verdicts) routed to M2 (evidence lookups) and M4 (feedback memory).

## Non-functional constraints

- Dashboard load < 1 second — a pure database read, no live computation (spec §9.4).
- < 1 interruption per week when the account is healthy (spec §14.2 target).

## Acceptance criteria

- [ ] Dashboard load time stays under 1s against a warm database in a representative load test.
- [ ] The Healthy state renders with the exact copy defined in spec §11.5 when the score/band/pending-actions conditions are met.
- [ ] None of the forbidden chart types (§11.7) exist anywhere in the component library.
- [ ] Every number on the dashboard has a working click-through to its evidence trace.

## Traceability

Spec §7 M8, §11.1–§11.7 (UI components, design direction, states), §14.2 ("quiet weeks are quiet" success metric).
