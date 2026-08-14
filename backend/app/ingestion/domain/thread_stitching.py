"""Minimal thread stitching (REQ-M2-04) — ticket-reference matching only, per
research.md's scope decision. `participant_subject` and `timing_heuristic` are real
`stitch_method` enum values this feature doesn't implement (data-base/03-schema-
ledger.md) — left as documented future work, not silently dropped from the enum.
"""

import re

_TICKET_REFERENCE = re.compile(r"#(\d+)")

# Fixed, not computed — matches the confidence assigned to the worked example in
# data-base/03-schema-ledger.md ("Slack message mentioning '#456'" -> 0.88 there; this
# feature uses one fixed value for every ticket-reference match rather than a scoring
# formula, since REQ-M2-04 only requires *a* recorded confidence, not a calibrated one).
TICKET_REFERENCE_CONFIDENCE = 0.9

# The ticket's own state-change event is the thread's anchor row — full confidence,
# since it isn't a "reference" being matched at all, it's the thing being referenced.
ANCHOR_CONFIDENCE = 1.0


def find_ticket_references(text: str) -> set[int]:
    """Every `#<number>` found in `text`, as ticket numbers."""
    return {int(match) for match in _TICKET_REFERENCE.findall(text)}


def thread_key_for_ticket(ticket_number: int) -> str:
    return f"thread-{ticket_number}"
