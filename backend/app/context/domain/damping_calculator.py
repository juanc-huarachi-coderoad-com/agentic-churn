"""M4 (feedback memory) — pure, no I/O. `decisions/02-repo-and-tooling.md`'s
module->package mapping table names this exact file for the damping formula.

`pattern_signature` is the single canonical construction of the matching key
`damping_weights` groups on — it MUST stay byte-identical to
`app.scoring.application.use_cases.RecomputeScoreUseCase`'s own use of it
(`specs/010-feedback-memory/research.md` Decision 1/2).

`compute_weight` delegates to `app.scoring.domain.services.DampingCalculator`
rather than reimplementing REQ-M6-CAL-03a's arithmetic a second time — feature
004 already built and unit-tested that exact formula (`tests/scoring/
test_damping_calculator.py`) ahead of this feature actually wiring a writer to
it, the same "built ahead of time, unpopulated until now" pattern this
codebase already uses elsewhere (`draft_messages` before feature 009). Found
during this feature's own Polish phase, not by inspection — a real, avoided
duplication, matching `research.md` Decision 2's identical reasoning for
`pattern_signature`. Domain -> Domain, cross-module, the same direction
feature 009 already established as legal and precedented.
"""

from app.scoring.domain.services import DampingCalculator

_damping_calculator = DampingCalculator()


def pattern_signature(reader_type: str, finding_type: str) -> str:
    return f"{reader_type}+{finding_type}"


def compute_weight(false_alarm_count: int, correct_count: int) -> float:
    """REQ-M6-CAL-03a. `resolved_count` never enters this formula
    (REQ-M6-CAL-03b) — a `resolved` verdict simply never increments
    `false_alarm_count`/`correct_count`, so this recomputes an unchanged
    weight for it with no branch needed here."""
    return _damping_calculator.compute_weight(
        false_alarm_count=false_alarm_count, correct_count=correct_count
    )


def build_disclosure_text(
    false_alarm_count: int, correct_count: int, resolved_count: int
) -> str | None:
    """REQ-M4-04. `None` when the pattern has never received any verdict —
    no disclosure is manufactured where none is warranted (constitution P6).

    Only the `false_alarm_count > 0` branch can ever describe a pattern the
    read side ("weight < 1.0") will actually surface — a `correct`-only or
    `resolved`-only pattern is described accurately here too, but is simply
    never read, since its weight never leaves 1.0 (`SqlAlchemyDamping-
    DisclosureReader` gates on `weight < 1.000`, the single source of truth
    for "should this ever be shown," not this function)."""
    if false_alarm_count == 0 and correct_count == 0 and resolved_count == 0:
        return None

    if false_alarm_count > 0:
        if false_alarm_count == 1:
            headline = "weight reduced — your team flagged this pattern as a false alarm"
        else:
            headline = f"weight reduced — your team dismissed this pattern {_times(false_alarm_count)}"
        if correct_count > 0:
            headline += f", partially restored after your team confirmed it {_times(correct_count)}"
    elif correct_count > 0:
        headline = f"your team confirmed this pattern {_times(correct_count)}"
    else:
        headline = f"your team marked this pattern resolved {_times(resolved_count)}"

    if resolved_count > 0 and false_alarm_count > 0:
        headline += f"; marked resolved {_times(resolved_count)}"

    return headline


def _times(count: int) -> str:
    if count == 1:
        return "once"
    if count == 2:
        return "twice"
    return f"{count} times"
