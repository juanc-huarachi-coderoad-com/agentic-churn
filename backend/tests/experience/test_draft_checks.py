"""REQ-M10-07 — the draft composer's five pure pre-display checks. No DB,
no LLM, mirroring `test_fact_check.py`'s own precedent exactly. Covers
spec.md's User Story 2 acceptance scenarios 1-3 and `/speckit-analyze`
findings G1/U1 (the two checks added after that pass)."""

from app.experience.domain.entities import VerifiedDateSet
from app.experience.domain.services import (
    build_verified_date_set,
    build_verified_fact_set,
    verify_dates,
    verify_facts,
    verify_no_concession,
    verify_no_invented_cause,
    verify_no_leak,
)
from app.narrator.domain.entities import VerifiedFactSet

# ---------------------------------------------------------------------------
# verify_facts
# ---------------------------------------------------------------------------


def test_draft_using_only_verified_facts_passes():
    facts = VerifiedFactSet(numbers=frozenset({"19", "4", "456"}), names=frozenset({"Ana"}))
    result = verify_facts(
        "Ana — we took 19 hours to respond to ticket #456; we promised 4.", facts
    )
    assert result.passed


def test_draft_containing_an_unverified_name_fails():
    facts = VerifiedFactSet(numbers=frozenset({"19"}), names=frozenset({"Ana"}))
    result = verify_facts("We also spoke with David about this.", facts)
    assert not result.passed
    assert "David" in result.extracted_names


def test_draft_multi_sentence_leading_word_is_never_treated_as_a_claimed_name():
    """Regression guard: checking a whole multi-sentence draft as one
    string (instead of splitting first) would apply `fact_check`'s
    leading-word exclusion to only the draft's first word, reproducing the
    exact false-positive feature 008 already found and fixed for the
    Narrator ("Engineering is on it today" discarded)."""
    facts = VerifiedFactSet(numbers=frozenset({"19"}), names=frozenset({"Ana"}))
    result = verify_facts(
        "Ana — we took 19 hours to respond. Engineering is on it today.", facts
    )
    assert result.passed


def test_build_verified_fact_set_includes_stakeholder_and_client_names():
    facts = build_verified_fact_set(
        evidence_texts=["We took 19 hours to respond to ticket #456."],
        thread_history_texts=[],
        stakeholder_name="Ana",
        client_name="Meridian Logistics",
    )
    assert "19" in facts.numbers
    assert "456" in facts.numbers
    assert "Ana" in facts.names
    assert "Meridian Logistics" in facts.names


# ---------------------------------------------------------------------------
# verify_dates
# ---------------------------------------------------------------------------


def test_due_date_matching_mention_passes():
    dates = VerifiedDateSet(dates=frozenset({"Thursday"}))
    result = verify_dates("I will call you before Thursday.", dates)
    assert result.passed


def test_invented_date_fails():
    dates = VerifiedDateSet(dates=frozenset({"Thursday"}))
    result = verify_dates("I will call you before Friday.", dates)
    assert not result.passed
    assert "Friday" in result.unverified_dates


def test_build_verified_date_set_from_agreed_actions():
    from app.experience.domain.entities import AgreedAction

    actions = [
        AgreedAction(
            text="Call Ana",
            owner="Marta",
            due_date="Thursday",
            finding_type="broken_response_promise",
        )
    ]
    dates = build_verified_date_set(actions)
    assert "Thursday" in dates.dates


# ---------------------------------------------------------------------------
# verify_no_invented_cause (`/speckit-analyze` finding U1)
# ---------------------------------------------------------------------------


def test_causal_clause_naming_only_evidenced_entities_passes():
    facts = VerifiedFactSet(numbers=frozenset(), names=frozenset({"Meridian"}))
    result = verify_no_invented_cause(
        "The reply was late because Meridian's ticket volume spiked.", facts
    )
    assert result.passed


def test_causal_clause_naming_an_unverified_entity_fails():
    facts = VerifiedFactSet(numbers=frozenset(), names=frozenset({"Ana"}))
    result = verify_no_invented_cause(
        "This happened because we lost the Meridian contract with Acme.", facts
    )
    assert not result.passed
    assert result.unverified_causal_clauses


def test_draft_with_no_causal_connective_passes_trivially():
    facts = VerifiedFactSet(numbers=frozenset(), names=frozenset())
    result = verify_no_invented_cause("Ana — we took 19 hours to respond.", facts)
    assert result.passed


# ---------------------------------------------------------------------------
# verify_no_leak
# ---------------------------------------------------------------------------


def test_clean_draft_passes_leak_check():
    result = verify_no_leak("Ana — we took 19 hours to respond to ticket #456.")
    assert result.passed


def test_score_mention_fails_leak_check():
    result = verify_no_leak("Your risk score dropped this week.")
    assert not result.passed
    assert "risk" in result.leaked_terms
    assert "score" in result.leaked_terms


def test_monitoring_mention_fails_leak_check():
    result = verify_no_leak("We are monitoring this account closely.")
    assert not result.passed


# ---------------------------------------------------------------------------
# verify_no_concession (`/speckit-analyze` finding G1)
# ---------------------------------------------------------------------------


def test_clean_draft_passes_concession_check():
    result = verify_no_concession("Engineering is on it today, and I'll call you before Thursday.")
    assert result.passed


def test_discount_offer_fails_concession_check():
    result = verify_no_concession("We can offer you a 10% discount on your next renewal.")
    assert not result.passed
    assert "discount" in result.matched_terms


def test_waived_fee_fails_concession_check():
    result = verify_no_concession("We'll waive the fee for this quarter.")
    assert not result.passed
