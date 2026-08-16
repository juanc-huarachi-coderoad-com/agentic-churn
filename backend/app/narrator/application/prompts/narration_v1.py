"""Versioned structured-output narration prompt (REQ-M7-08) — changing this
template means creating `narration_v2.py`, never editing this file's prompt
text in place, so a run always records exactly which prompt version produced
it (`prompt_version = "narration_v1"`).
"""

from dataclasses import dataclass

VERSION = "narration_v1"


@dataclass
class NarrationReasonOutput:
    text: str
    points: float
    evidence_event_ids: list[str]


@dataclass
class NarrationActionOutput:
    text: str
    owner: str
    due_date: str
    playbook_id: str


@dataclass
class NarrationModelOutput:
    """The model's closed, structured output schema — headline, reasons,
    actions, nothing else. Every field is mechanically fact-checked before
    display (REQ-M7-06); this schema only constrains *shape*, not truth."""

    headline: str
    reasons: list[NarrationReasonOutput]
    actions: list[NarrationActionOutput]


def build_prompt(
    *,
    contributions: list[dict[str, object]],
    playbook: list[dict[str, object]],
) -> str:
    """`contributions`: `[{finding_type, points, is_positive, cited_event_ids,
    names}]`, already ranked, most impactful first — never reordered here.
    `playbook`: `[{id, template_text, default_owner_role, default_sla_days}]`
    — the only source actions may personalize (REQ-M7-04, REQ-M7-P3)."""
    return (
        "You are writing a short, plain-language explanation of why a "
        "client account's health score is what it is, for a customer "
        "success lead who already trusts the number — your job is to "
        "explain it, not to invent new facts.\n\n"
        "Rules:\n"
        "- Every reason must follow the pattern: a person, a number, and "
        "why it matters here (e.g. 'We took 19 hours to reply to ticket "
        "#456 — we promised 4.'). Never generic sentiment language "
        "('the client seems unhappy').\n"
        "- Use only the names, numbers, and events given below — never "
        "invent a fact, a person, or a number not present in this input.\n"
        "- Every action must be a personalization of one of the playbook "
        "templates below, filled in with real names/dates from this input "
        "— never an action outside this list.\n"
        "- Every action needs both an owner and a due_date.\n"
        "- Set evidence_event_ids on each reason to the real event IDs it "
        "is based on, taken only from this input.\n"
        "- Set playbook_id on each action to the real playbook template id "
        "it personalizes.\n\n"
        f"Ranked findings (most impactful first — do not reorder):\n{contributions}\n\n"
        f"Available playbook action templates:\n{playbook}\n"
    )
