"""REQ-M7-06/07 — the mechanical fact-check, pure, no DB, no LLM. Covers
spec.md's User Story 1 acceptance scenarios 5-6."""

from app.narrator.domain.entities import VerifiedFactSet
from app.narrator.domain.services import extract_numbers_and_names, fact_check


def test_sentence_using_only_verified_facts_passes():
    facts = VerifiedFactSet(numbers=frozenset({"19", "4"}), names=frozenset({"Ana Reyes"}))
    result = fact_check("We took 19 hours to reply — we promised 4. Ana Reyes noticed.", facts)
    assert result.passed


def test_sentence_containing_an_unverified_number_fails():
    facts = VerifiedFactSet(numbers=frozenset({"19"}), names=frozenset())
    result = fact_check("We took 999 hours to reply.", facts)
    assert not result.passed
    assert "999" in result.extracted_numbers


def test_sentence_containing_an_unverified_name_fails():
    facts = VerifiedFactSet(numbers=frozenset(), names=frozenset({"Ana Reyes"}))
    result = fact_check("We heard from Diego about the outage.", facts)
    assert not result.passed
    assert "Diego" in result.extracted_names


def test_sentence_leading_word_is_never_treated_as_a_claimed_name():
    """Regression: found via live verification against real data (T019) —
    an action beginning with an imperative verb ("Escalate the ticket...")
    was discarded every time before this fix, because the sentence's own
    first word is always capitalized regardless of whether it's a name."""
    facts = VerifiedFactSet(numbers=frozenset(), names=frozenset())
    result = fact_check("Escalate the ticket with engineering today", facts)
    assert result.passed


def test_a_genuine_leading_name_still_extracts_but_is_exempted():
    """Documents the accepted trade-off from the fix above: a real name
    that happens to open a sentence is not flagged as unverified either —
    the safer failure direction given the alternative discarded nearly
    every generated action (see services.py's docstring)."""
    facts = VerifiedFactSet(numbers=frozenset(), names=frozenset())
    result = fact_check("Ana should be contacted about this.", facts)
    assert result.passed  # "Ana" is the leading word, exempted from verification


def test_confidence_style_decimal_is_verified_as_a_number():
    facts = VerifiedFactSet(numbers=frozenset({"85.63"}), names=frozenset())
    result = fact_check("The score moved to 85.63.", facts)
    assert result.passed


def test_extract_numbers_and_names_is_unfiltered_for_source_text():
    """Source-text extraction (building the verified set) intentionally
    does not exempt the leading word — over-including a verified name is
    safe; the asymmetry with `fact_check` is deliberate, not an oversight."""
    numbers, names = extract_numbers_and_names("Ana Reyes wrote 3 times about ticket 456.")
    assert "3" in numbers
    assert "456" in numbers
    assert "Ana Reyes" in names
