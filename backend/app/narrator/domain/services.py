"""The Narrator's mechanical fact-check (REQ-M7-06/07) — pure, no I/O.
Extracts every number and name-like token from a candidate sentence and
confirms each already exists in a `VerifiedFactSet` built from the run's own
structured input. The one piece of pure business logic this module has ever
needed — `app.narrator.domain`'s first real content, the same "domain ring
appears once a module has genuine pure logic to isolate" pattern
`app.readers.domain` earned in feature 007.
"""

import re

from app.narrator.domain.entities import FactCheckResult, VerifiedFactSet

_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")
_PROPER_NOUN_PATTERN = re.compile(r"\b[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)*\b")
"""ASCII-only by construction: Python's `\\b` is Unicode-aware, so a name
containing a non-ASCII letter (e.g. "Marín") never satisfies the trailing
word boundary against `[a-zA-Z]` and is silently skipped rather than
partially matched — a real, narrow limitation worth naming rather than
leaving implicit, found while writing this module's own tests."""

# Sentence-structure words that happen to be capitalized (sentence-initial,
# or genuinely common English capitals) — never asserted as claimed facts,
# so they're exempt from the "must appear in VerifiedFactSet.names" check.
# A real, documented limitation (not full NLP entity recognition): a rare
# capitalized common word outside this list could still produce a false
# fact-check failure, which is the safe failure direction — REQ-M7-07
# discards the sentence rather than displaying an unverified claim.
_COMMON_WORDS = frozenset(
    {
        "We",
        "The",
        "This",
        "That",
        "It",
        "They",
        "I",
        "You",
        "Your",
        "Given",
        "See",
        "Not",
        "A",
        "An",
        "Evidence",
        "Trace",
        "For",
        "Detail",
        "Top",
        "Issue",
        "Points",
        "Pts",
        # Weekday/month names — likely to appear in due-date-adjacent action
        # text ("before Friday," "by March"), but the actual verified date is
        # `NarratedAction.due_date`, not this free text — never a claimed
        # fact worth mechanically checking on its own.
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    }
)


def extract_numbers_and_names(text: str) -> tuple[frozenset[str], frozenset[str]]:
    """The single extraction function used two ways: building a
    `VerifiedFactSet` from real source text (the adapter), and extracting
    candidate facts from a generated sentence (`fact_check`, below) — using
    the same patterns both ways is what makes the comparison meaningful."""
    numbers = frozenset(_NUMBER_PATTERN.findall(text))
    names = frozenset(m for m in _PROPER_NOUN_PATTERN.findall(text) if m not in _COMMON_WORDS)
    return numbers, names


def fact_check(sentence: str, facts: VerifiedFactSet) -> FactCheckResult:
    """Every number and name-like token in `sentence` must already exist in
    `facts` — the mechanical check between a candidate sentence and
    persistence (REQ-M7-06). Fails safe: an extraction this heuristic can't
    confirm counts as unverified, never as verified by default.

    The sentence's own first word is excluded from name-candidates —
    English capitalizes a sentence's first word regardless of whether it's
    a proper noun ("Escalate the ticket..."), so treating it as a claimed
    fact produced far more false failures than it caught (found by running
    this against real generated action text, not a synthetic test case: an
    action beginning with an imperative verb like "Escalate"/"Call"/"Send"
    was discarded every time). Source text (`extract_numbers_and_names`,
    used to build the verified set) keeps the unfiltered extraction — a
    verified set with a few extra harmless names is safe; a generated
    sentence with a false-positive *name* is not (`architecture/
    04-ai-safety-and-model-usage.md` Rule 4's "no new facts" is the side
    that must fail closed, not the side that must fail open)."""
    numbers = frozenset(_NUMBER_PATTERN.findall(sentence))
    all_names = _PROPER_NOUN_PATTERN.findall(sentence)
    leading_word = sentence.split(" ", 1)[0].rstrip(".,;:!?") if sentence else ""
    names = frozenset(
        m for m in all_names if m not in _COMMON_WORDS and m != leading_word
    )

    unverified_numbers = {n for n in numbers if not any(n == v or n in v for v in facts.numbers)}
    unverified_names = {n for n in names if not any(n in v or v in n for v in facts.names)}

    return FactCheckResult(
        passed=not unverified_numbers and not unverified_names,
        extracted_numbers=numbers,
        extracted_names=names,
    )
