# 03 · Client profile (M3)

Tier 2 · Context — spec §7 (M3), §6.2

## Purpose

The lens that converts a signal into a severity. Structured, versioned, human-authored — the single most important input in the product.

## User stories

- As a **CS lead**, I want to declare who the sponsor is and which product area is critical, so that the score reflects what actually matters to this client, not generic sentiment.
- As an **engineer**, I want every scoring run to record which profile version it used, so that a score is always explainable against the context that produced it.

## Functional requirements

| ID | Requirement |
|---|---|
| REQ-M3-01 | THE SYSTEM SHALL store the client profile as a structured, versioned document (YAML source of truth, per spec §6.2) with fields: `client`, `renewal_date`, `contract_value_band`, `business_goals`, `stakeholders[]`, `product_areas[]`, `commitments[]`, `communication`, `exclusions[]`, `history[]`. |
| REQ-M3-02 | WHEN a profile is edited, THE SYSTEM SHALL create a new immutable profile version rather than overwrite the previous one. |
| REQ-M3-03 | THE SYSTEM SHALL supply an `influence` multiplier per stakeholder (e.g. sponsor 1.6, daily user 1.2, unknown 0.8) and a `criticality` multiplier per product area (e.g. critical 1.5, standard 1.0, peripheral 0.6) to the scoring engine (M6). |
| REQ-M3-04 | THE SYSTEM SHALL supply communication norms (working hours, timezone, languages, tone norms) to the interpreters (M5), used as calendar/baseline context — never as scoring logic itself. |
| REQ-M3-05 | WHEN a scoring run executes, THE SYSTEM SHALL record the exact profile version ID it used. |
| REQ-M3-06 | WHEN a profile version changes, THE SYSTEM SHALL trigger a full replay (per REQ-M2-07) so the score reflects the new context immediately. |
| REQ-M3-07 | THE SYSTEM SHALL validate a submitted profile against a schema (required fields, valid multiplier ranges, at least one stakeholder with `signs_renewal: true`) before accepting a new version. |

## Explicit prohibitions

| ID | Prohibition |
|---|---|
| REQ-M3-P1 | The client profile SHALL NOT contain scoring logic (formulas, thresholds) — only the multiplier values and context that M6 consumes as inputs. |
| REQ-M3-P2 | THE SYSTEM SHALL NOT infer stakeholder influence or product-area criticality automatically — these are always human-authored. |

## Inputs / Outputs

- **Input:** human-authored YAML/form edits from the CS lead (profile editor, spec §11.2).
- **Output:** `client_profile_versions`, `stakeholders`, `product_areas`, `commitments` tables (see `data-base/04-schema-context.md`), consumed by M1 (identity targets), M5 (interpretation context), M6 (multipliers).

## Non-functional constraints

- Profile is versioned like code — every version retained indefinitely for audit and replay.
- Schema validation must reject an invalid profile edit before it can affect scoring.

## Acceptance criteria

- [ ] Editing the profile never mutates a past version; the prior version remains queryable.
- [ ] A scoring run's stored `profile_version_id` always resolves to the exact multipliers used in its arithmetic.
- [ ] Submitting a profile missing a required field is rejected with a specific validation error.

## Traceability

Spec (v1.2) §7 M3, §6.2 (profile schema example), §9.2 (component responsibilities), §17 Q2 / §17.1 (who authors the profile — resolved: CS lead edits the YAML file directly in the MVP; profile editor UI Post-MVP).
