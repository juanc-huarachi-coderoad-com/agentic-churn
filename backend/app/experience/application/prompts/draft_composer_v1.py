"""Versioned structured-output draft-composer prompt (REQ-M10's analog of
REQ-M7-08) — changing this template means creating `draft_composer_v2.py`,
never editing this file's prompt text in place, so a run always records
exactly which prompt version produced it (`prompt_version =
"draft_composer_v1"`).

Lives in `application/prompts/`, not `adapters/`, matching
`narration_v1.py`'s own precedent (feature 008 T040 — a real
`import-linter` violation was found and fixed once for exactly this
placement, `research.md` Decision 2).
"""

from dataclasses import dataclass

VERSION = "draft_composer_v1"


@dataclass
class DraftModelOutput:
    """The model's closed, structured output schema — draft text and tone
    variant, nothing else. This schema only constrains *shape*; every fact
    in `draft_text` is mechanically checked before display (REQ-M10-07)."""

    draft_text: str
    tone_variant: str


def build_prompt(
    *,
    stakeholder_name: str,
    tone_variant: str,
    issue_label: str,
    evidence_texts: list[str],
    communication_norms: str | None,
    thread_history_texts: list[str],
    agreed_actions: list[dict[str, object]],
) -> str:
    """`agreed_actions`: `[{text, owner, due_date}]` — the only source a
    dated promise may draw from (REQ-M10-07). `evidence_texts`/
    `thread_history_texts` are the only source any other fact may draw
    from (REQ-M10-P1's Narrator-equivalent discipline, applied here)."""
    return (
        "You are drafting a short client-facing message on behalf of a "
        f"customer success lead, addressed to {stakeholder_name} about "
        f"'{issue_label}'. You are not the one who will send it — a human "
        "reviews and sends it themselves; there is no send capability "
        "anywhere in this product.\n\n"
        "Rules:\n"
        "- Open by acknowledging the specific failure below, concretely "
        "(e.g. 'we took 19 hours to respond; we promised 4') — never a "
        "generic apology or greeting.\n"
        "- Contain exactly one ask of the reader — never zero, never more "
        "than one.\n"
        "- Match this account's declared communication rhythm: "
        f"{communication_norms or 'no specific norms recorded — use a neutral, '
        'professional register'}.\n"
        "- If a call is clearly the more appropriate medium than a written "
        "message for this issue, say so explicitly and provide talking "
        "points instead of message text.\n"
        "- Use only the facts, dates, and names given below — never invent "
        "one not present in this input.\n"
        "- Any date you mention (e.g. 'call you before Thursday') must "
        "come from one of the agreed actions listed below — never invent "
        "a date.\n"
        "- Never contain blame language directed at the client.\n"
        "- Never offer a discount or commercial concession.\n"
        "- Never mention that this relationship is being monitored, "
        "scored, or tracked by any internal tool.\n"
        "- Never mention any other client.\n"
        f"- Write in the requested tone: {tone_variant}.\n\n"
        f"Issue: {issue_label}\n\n"
        f"Evidence:\n{evidence_texts}\n\n"
        f"Real thread history:\n{thread_history_texts}\n\n"
        f"Actions the team has already agreed to:\n{agreed_actions}\n"
    )
