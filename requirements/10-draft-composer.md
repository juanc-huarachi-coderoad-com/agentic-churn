# 10 · Draft composer (M10)

Tier 4 · Experience — spec §7 (M10), §12.3, P4

## Purpose

Writes the client-facing message. Opens beside the evidence. Offers tone variants. **No send button exists — not disabled, absent.**

## User stories

- As a **CS lead**, I want a draft that acknowledges the specific failure first ("we took 19 hours; we promised 4"), so the message doesn't read as generic corporate apology.
- As a **CS lead**, I want to copy the finished draft into my own email client to send it myself, so a human is always the one who presses send.

## Functional requirements

| ID | Requirement |
|---|---|
| REQ-M10-01 | THE SYSTEM SHALL generate a draft from: the top issue and its evidence, the client's communication preferences (profile `communication` block), real thread history, and actions the team has actually agreed to. |
| REQ-M10-02 | Generated drafts SHALL acknowledge the specific failure first (concrete fact from evidence), not a generic apology. |
| REQ-M10-03 | Generated drafts SHALL contain exactly one ask per message. |
| REQ-M10-04 | Generated drafts SHALL match the client's communication rhythm (e.g. short/terse stakeholders receive short drafts) as declared in the profile. |
| REQ-M10-05 | THE SYSTEM SHALL offer tone variants (e.g. more formal / more direct) for the same underlying content. |
| REQ-M10-06 | WHEN the appropriate action is a call rather than a message, THE SYSTEM SHALL say so explicitly and provide talking points instead of message text. |
| REQ-M10-07 | THE SYSTEM SHALL run automatic checks before displaying any draft: every fact stated exists in the evidence; no dated promise appears unless a human supplied that date; nothing internal (scores, internal notes, other clients) leaks into the text. |
| REQ-M10-08 | **(Resolves the mockup's "Send & Log to CRM" affordance.)** THE SYSTEM SHALL provide only a **"Copy draft"** action and a **"Log to CRM"** action (writes an activity record to the CRM — subject, body, timestamp, logged-by-user — with no transmission to the client). THE SYSTEM SHALL NOT provide, render, or expose via API any action that transmits the drafted message to the client or any external recipient. |
| REQ-M10-09 | WHEN the human sends the message through their own email/chat client and it is picked up by a collector (M1) as a normal outbound event, THE SYSTEM SHALL close the response clock for the related commitment and let subsequent runs observe whether the suggestion worked. |

## Explicit prohibitions

| ID | Prohibition |
|---|---|
| REQ-M10-P1 | THE SYSTEM SHALL NEVER contain a send capability of any kind — no send button, no send API endpoint, no scheduled-send feature. This is an architectural absence, not a disabled/hidden control. |
| REQ-M10-P2 | Drafts SHALL NEVER contain blame language directed at the client. |
| REQ-M10-P3 | Drafts SHALL NEVER contain invented dates or causes not present in the evidence. |
| REQ-M10-P4 | Drafts SHALL NEVER contain discounts or commercial concessions. |
| REQ-M10-P5 | Drafts SHALL NEVER mention, hint at, or allude to the fact that the client relationship is being monitored or scored. |
| REQ-M10-P6 | Drafts SHALL NEVER mention any other client. |

## Inputs / Outputs

- **Input:** top issue + evidence (M6/M7 output), client profile communication norms, thread history (M2), human-supplied dates/commitments.
- **Output:** `draft_messages` (content, tone variant, evidence references, `logged_to_crm_at` nullable — **no `sent_at` column exists in the schema by design**).

## Non-functional constraints

- Every automatic pre-display check (REQ-M10-07) must run and pass before a draft is rendered to the user — a failed check blocks display, it does not silently strip content.

## Acceptance criteria

- [ ] No code path, UI element, or API route exists that transmits a drafted message to an external recipient (verified by architecture review — this is a structural, not a UI-only, guarantee).
- [ ] A draft referencing a fact absent from the evidence is blocked from display in a scripted red-team test.
- [ ] A draft never contains the words "score," "risk," "monitoring," or equivalent self-referential language about the tool itself.
- [ ] "Log to CRM" writes an activity record and never contacts the client.

## Traceability

Spec §7 M10, §12.3 (craft rules, never-writes list, automatic checks), P4 (a human always sends), `requirements/00-overview-and-glossary.md` (resolved mockup discrepancy).
