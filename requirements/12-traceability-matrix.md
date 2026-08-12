# 12 · Traceability matrix

Maps every requirement block to its module, source spec section, and acceptance-criteria location, so no requirement is unmoored from the source spec and no spec section is unaddressed.

## REQ-ID → module → spec section

| REQ-ID range | Module | File | Spec section(s) | Acceptance criteria |
|---|---|---|---|---|
| REQ-M1-01 … REQ-M1-10, REQ-M1-P1 … P5 | M1 · Signal collectors | `01-signal-collectors.md` | §7 (M1), §6.1, §6.3, §6.4, §13.2, §14.3 | `01-signal-collectors.md` §Acceptance criteria |
| REQ-M2-01 … REQ-M2-09, REQ-M2-P1 … P3 | M2 · Event ledger | `02-event-ledger.md` | §7 (M2), §6.4, §9.4, §14.3 | `02-event-ledger.md` §Acceptance criteria |
| REQ-M3-01 … REQ-M3-07, REQ-M3-P1 … P2 | M3 · Client profile | `03-client-profile.md` | §7 (M3), §6.2, §9.2, §17 Q2 | `03-client-profile.md` §Acceptance criteria |
| REQ-M4-01 … REQ-M4-05, REQ-M4-P1 … P2 | M4 · Feedback memory | `04-feedback-memory.md` | §7 (M4), §8.1, §11.4, §15 | `04-feedback-memory.md` §Acceptance criteria |
| REQ-M5-01 … REQ-M5-15, REQ-M5-P1 … P4 | M5 · Interpreters | `05-interpreters-readers.md` | §7 (M5), §8.1, §10, §12.4, §12.5, §15 | `05-interpreters-readers.md` §Acceptance criteria |
| REQ-M5A-01 … REQ-M5A-04 | M5a · Validation gate | `05-interpreters-readers.md` | §7 (M5a), §10, §14.3 | same |
| REQ-M6-01 … REQ-M6-28, REQ-M6-P1 … P4 | M6 · Scoring engine | `06-scoring-engine.md` | §7 (M6), §8.1–8.9, §10, §14.3 | `06-scoring-engine.md` §Acceptance criteria |
| REQ-M7-01 … REQ-M7-08, REQ-M7-P1 … P3 | M7 · Narrator | `07-narrator.md` | §7 (M7), §12.1, §12.5, §17 Q7 | `07-narrator.md` §Acceptance criteria |
| REQ-M8-01 … REQ-M8-10, REQ-M8-P1 … P2 | M8 · Health dashboard | `08-health-dashboard.md` | §7 (M8), §11.1–11.7, §14.2 | `08-health-dashboard.md` §Acceptance criteria |
| REQ-M9-01 … REQ-M9-08, REQ-M9-P1 … P3 | M9 · Ask agent | `09-ask-agent.md` | §7 (M9), §9.3, §9.4, §12.2 | `09-ask-agent.md` §Acceptance criteria |
| REQ-M10-01 … REQ-M10-09, REQ-M10-P1 … P6 | M10 · Draft composer | `10-draft-composer.md` | §7 (M10), §12.3, P4 | `10-draft-composer.md` §Acceptance criteria |
| REQ-NFR-01 … REQ-NFR-33 | Cross-cutting | `11-non-functional-requirements.md` | §6.3, §6.4, §9.4, §13, §14.1–14.3, §15 | `11-non-functional-requirements.md` |
| REQ-M6-CAL-01 … REQ-M6-CAL-08 | M6 · Scoring engine (calibration) | `13-scoring-calibration-appendix.md` | §8 (fills in values §8 implied but didn't state) | Worked checks inline in each REQ-M6-CAL entry |
| REQ-AUTH-01 … REQ-AUTH-09, REQ-AUTH-P1 … P3 | Authentication (cross-cutting) | `14-authentication.md` | New in v1.1 — not in the original spec, added per explicit build-start request | `14-authentication.md` §Acceptance criteria |

## Spec section → requirements coverage (reverse index)

| Spec section | Covered by |
|---|---|
| §1 Executive summary | `00-overview-and-glossary.md` (context only, non-normative) |
| §2 The problem | `00-overview-and-glossary.md` (context only, non-normative) |
| §3 Users and scope | `00-overview-and-glossary.md` (personas, scope table) |
| §4 Product principles P1–P7 | `00-overview-and-glossary.md` (principle → enforcement mapping) |
| §5 Glossary | `00-overview-and-glossary.md` |
| §6.1 Sources | REQ-M1-01 |
| §6.2 Client profile | REQ-M3-01 |
| §6.3 Data not collected | REQ-NFR-17 … REQ-NFR-20 |
| §6.4 Privacy and security | REQ-NFR-10 … REQ-NFR-16 |
| §7 Features by module | REQ-M1 … REQ-M10 (all module files) |
| §8 The scoring model | REQ-M6-01 … REQ-M6-28 |
| §9.1–9.3 Architecture, loops | `architecture/01-architecture-overview.md` (non-normative diagram); loops reflected in `sequences/01,02,03` |
| §9.4 Non-functional requirements | REQ-NFR-01 … REQ-NFR-09 |
| §10 End-to-end walkthrough | `sequences/01-sequence-signal-to-score.md` |
| §11 UI components | REQ-M8-01 … REQ-M8-10 |
| §12.1 Narrator | REQ-M7-01 … REQ-M7-08 |
| §12.2 Ask agent | REQ-M9-01 … REQ-M9-08 |
| §12.3 Draft composer | REQ-M10-01 … REQ-M10-09 |
| §12.4 Where AI is/isn't used | `architecture/02-component-catalog.md` (technology-class column) |
| §12.5 Model safety | `architecture/04-ai-safety-and-model-usage.md` |
| §13.1 Hard boundaries | REQ-NFR-21 … REQ-NFR-26 |
| §13.2 Honest limitations | REQ-M1-07/08, REQ-M8-07 |
| §13.3 Anti-goals in the interface | REQ-M8-09 |
| §14.1 Demo success | `00-overview-and-glossary.md` (executive framing, non-normative) |
| §14.2 Product success | `11-non-functional-requirements.md` §Success metrics |
| §14.3 Engineering acceptance criteria | REQ-NFR-27 … REQ-NFR-33 |
| §15 Risks | Referenced per-module in "Traceability" sections where a mitigation is implemented |
| §16 Build order | Not a requirement — sequencing guidance; see project plan / build phases, out of scope for this requirements set |
| §17 / §17.1 Open questions & resolutions | All eight resolved as of spec v1.1 — see `decisions/00-open-questions-resolved.md`. Flagged inline in REQ-M3, REQ-M7 traceability notes; still non-normative (scope/process decisions, not testable requirements) |

## Orphan check

- Every REQ-ID in `01`–`11`, `13`, `14` appears in the forward table above. ✅
- Every numbered spec section (§1–§17) has at least one entry in the reverse index. ✅
- §16 (Build order) and §17 (Open questions) are intentionally non-normative — they inform delivery sequencing and outstanding decisions, not testable requirements — and are marked as such rather than force-fit into a REQ-ID.
- `13-scoring-calibration-appendix.md` and `14-authentication.md` are additive: the calibration appendix fills in values REQ-M6-* always implied but never stated; authentication is genuinely new, added at the user's explicit request rather than traced from the original spec.
