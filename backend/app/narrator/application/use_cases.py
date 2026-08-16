"""`NarrateScoreRunUseCase` — reads a score run's already-ranked
`score_contributions`, generates a headline/reasons/actions via `LLMPort`,
mechanically fact-checks every sentence, and persists exactly one
`narrator_outputs` row. Mirrors `RecomputeScoreUseCase`'s existing shape:
Application orchestrates ports; the pure fact-check function is Domain,
zero I/O.
"""

from uuid import UUID

from app.narrator.application.ports import (
    ClientContextPort,
    NarratorOutputRepositoryPort,
    PlaybookPort,
    ScoreContextPort,
)
from app.narrator.application.prompts.narration_v1 import (
    VERSION,
    NarrationModelOutput,
    build_prompt,
)
from app.narrator.domain.entities import (
    NarratedAction,
    NarratedReason,
    NarratorOutput,
    RankedContribution,
    VerifiedFactSet,
)
from app.narrator.domain.services import fact_check
from app.readers.application.ports import LLMPort

_FALLBACK_TEMPLATE = (
    "{score} — {band}. Top issue: {label} ({points} pts). See evidence trace for detail."
)
"""`architecture/06-error-handling.md`'s deterministic, non-LLM fallback —
used when every LLM-generated headline candidate fails its own fact-check
(REQ-M7-07's "discard, never display an unverifiable claim," applied to the
headline itself)."""


class NarrateScoreRunUseCase:
    def __init__(
        self,
        llm: LLMPort,
        score_context: ScoreContextPort,
        client_context: ClientContextPort,
        playbook: PlaybookPort,
        repository: NarratorOutputRepositoryPort,
    ) -> None:
        self._llm = llm
        self._score_context = score_context
        self._client_context = client_context
        self._playbook = playbook
        self._repository = repository

    async def execute(self, score_run_id: UUID) -> NarratorOutput | None:
        contributions = await self._score_context.get_ranked_contributions(score_run_id)
        if not contributions:
            # Nothing to narrate — a genuinely healthy run (Edge Cases,
            # REQ-M8-05's own "Nothing needs you today" state handles this,
            # not a placeholder narration).
            return None

        facts = await self._build_verified_facts(contributions)
        playbook_flat = await self._collect_playbook_templates(contributions)
        prompt = build_prompt(
            contributions=[
                {
                    "finding_type": c.finding_type,
                    "points": c.points,
                    "is_positive": c.is_positive,
                    "cited_event_ids": [str(e) for e in c.cited_event_ids],
                }
                for c in contributions
            ],
            playbook=playbook_flat,
        )

        try:
            candidate = await self._llm.generate_structured(prompt, NarrationModelOutput)
        except ValueError:
            # Systemic misconfiguration (missing key/model id) — surfaces
            # loudly, never silently treated as "nothing to narrate."
            raise
        except Exception:
            candidate = None

        headline, headline_passed = await self._resolve_headline(
            candidate, facts, contributions, score_run_id
        )
        reasons = self._resolve_reasons(candidate, facts)
        actions = self._resolve_actions(candidate, facts, playbook_flat)

        output = NarratorOutput(
            headline=headline,
            reasons=tuple(reasons),
            actions=tuple(actions),
            fact_check_passed=headline_passed,
            prompt_version=VERSION,
        )
        await self._repository.persist(output, score_run_id)
        return output

    async def _build_verified_facts(
        self, contributions: list[RankedContribution]
    ) -> VerifiedFactSet:
        all_cited_ids = [eid for c in contributions for eid in c.cited_event_ids]
        verified_numbers, verified_names = await self._client_context.build_verified_facts(
            all_cited_ids
        )
        # Every point value is itself a real, citable number — extend the
        # verified set so a reason quoting "39.0 points" isn't discarded for
        # citing a number no source event happened to contain verbatim.
        point_numbers = {str(round(abs(c.points))) for c in contributions} | {
            f"{abs(c.points):.1f}" for c in contributions
        }
        return VerifiedFactSet(numbers=verified_numbers | point_numbers, names=verified_names)

    async def _collect_playbook_templates(
        self, contributions: list[RankedContribution]
    ) -> list[dict[str, object]]:
        seen_types: set[str] = set()
        flat: list[dict[str, object]] = []
        for c in contributions:
            if c.finding_type in seen_types:
                continue
            seen_types.add(c.finding_type)
            for t in await self._playbook.list_active(c.finding_type):
                flat.append(
                    {
                        "id": str(t.id),
                        "template_text": t.template_text,
                        "default_owner_role": t.default_owner_role,
                        "default_sla_days": t.default_sla_days,
                    }
                )
        return flat

    async def _resolve_headline(
        self,
        candidate: NarrationModelOutput | None,
        facts: VerifiedFactSet,
        contributions: list[RankedContribution],
        score_run_id: UUID,
    ) -> tuple[str, bool]:
        if candidate is not None and fact_check(candidate.headline, facts).passed:
            return candidate.headline, True

        score_and_band = await self._score_context.get_score_and_band(score_run_id)
        top_issue = await self._score_context.get_top_issue(score_run_id)
        score, band = score_and_band if score_and_band is not None else (0.0, "unknown")
        label = top_issue.label if top_issue is not None else contributions[0].finding_type
        points = top_issue.points if top_issue is not None else abs(contributions[0].points)
        headline = _FALLBACK_TEMPLATE.format(
            score=round(score, 2), band=band, label=label, points=round(abs(points), 1)
        )
        return headline, False

    def _resolve_reasons(
        self, candidate: NarrationModelOutput | None, facts: VerifiedFactSet
    ) -> list[NarratedReason]:
        if candidate is None:
            return []
        reasons: list[NarratedReason] = []
        for r in candidate.reasons:
            if not fact_check(r.text, facts).passed:
                continue
            reasons.append(
                NarratedReason(
                    text=r.text,
                    points=r.points,
                    evidence_event_ids=tuple(UUID(e) for e in r.evidence_event_ids),
                )
            )
        return reasons

    def _resolve_actions(
        self,
        candidate: NarrationModelOutput | None,
        facts: VerifiedFactSet,
        playbook_flat: list[dict[str, object]],
    ) -> list[NarratedAction]:
        if candidate is None:
            return []
        valid_playbook_ids = {t["id"] for t in playbook_flat}
        actions: list[NarratedAction] = []
        for a in candidate.actions:
            if not a.owner or not a.due_date:
                continue  # REQ-M7-05 — both required
            if a.playbook_id not in valid_playbook_ids:
                continue  # REQ-M7-04/P3 — never outside the playbook
            if not fact_check(a.text, facts).passed:
                continue
            actions.append(
                NarratedAction(
                    text=a.text, owner=a.owner, due_date=a.due_date, playbook_id=UUID(a.playbook_id)
                )
            )
        return actions
