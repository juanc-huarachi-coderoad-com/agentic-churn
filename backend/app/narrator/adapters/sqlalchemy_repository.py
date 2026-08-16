"""SQLAlchemy implementations of the narrator (M7) application ports. Raw
parameterized SQL, matching the rest of the codebase's DDL-first pattern.
"""

import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.application.ports import EncryptionPort
from app.narrator.application.ports import (
    ClientContextPort,
    NarratorOutputRepositoryPort,
    PlaybookPort,
    PlaybookTemplate,
    ScoreContextPort,
)
from app.narrator.domain.entities import IssueSummary, NarratorOutput, RankedContribution
from app.narrator.domain.services import extract_numbers_and_names


def _quoted_text(
    structured_payload: dict[str, object], body_encrypted: bytes | None, encryption: EncryptionPort
) -> str | None:
    if body_encrypted is not None:
        return encryption.decrypt(body_encrypted)
    title = structured_payload.get("title")
    return str(title) if title else None


class SqlAlchemyScoreContextRepository(ScoreContextPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_ranked_contributions(self, score_run_id: UUID) -> list[RankedContribution]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT sc.finding_id, f.finding_type, sc.points_contributed, "
                    "sc.is_positive, f.cited_event_ids "
                    "FROM score_contributions sc JOIN findings f ON f.id = sc.finding_id "
                    "WHERE sc.score_run_id = :score_run_id "
                    "ORDER BY sc.points_contributed ASC"
                ),
                {"score_run_id": score_run_id},
            )
        ).all()
        return [
            RankedContribution(
                finding_id=r.finding_id,
                finding_type=r.finding_type,
                points=float(r.points_contributed),
                is_positive=r.is_positive,
                cited_event_ids=tuple(r.cited_event_ids),
            )
            for r in rows
        ]

    async def get_top_issue(self, score_run_id: UUID) -> IssueSummary | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT i.label, sum(abs(sc.points_contributed)) AS total_points "
                    "FROM score_contributions sc "
                    "JOIN issues i ON i.id = sc.issue_id "
                    "WHERE sc.score_run_id = :score_run_id "
                    "GROUP BY i.id, i.label "
                    "ORDER BY total_points DESC LIMIT 1"
                ),
                {"score_run_id": score_run_id},
            )
        ).one_or_none()
        if row is None:
            return None
        return IssueSummary(label=row.label, points=float(row.total_points))

    async def get_score_and_band(self, score_run_id: UUID) -> tuple[float, str] | None:
        row = (
            await self._session.execute(
                text("SELECT score, band FROM score_runs WHERE id = :id"),
                {"id": score_run_id},
            )
        ).one_or_none()
        if row is None:
            return None
        return float(row.score), row.band


class SqlAlchemyClientContextRepository(ClientContextPort):
    def __init__(self, session: AsyncSession, encryption: EncryptionPort) -> None:
        self._session = session
        self._encryption = encryption

    async def build_verified_facts(
        self, cited_event_ids: list[UUID]
    ) -> tuple[frozenset[str], frozenset[str]]:
        if not cited_event_ids:
            return frozenset(), frozenset()

        rows = (
            await self._session.execute(
                text(
                    "SELECT id, structured_payload, body_encrypted, stakeholder_id "
                    "FROM events WHERE id = ANY((:ids)::uuid[])"
                ),
                {"ids": cited_event_ids},
            )
        ).all()

        numbers: set[str] = set()
        names: set[str] = set()
        stakeholder_ids: set[UUID] = set()
        for r in rows:
            text_content = _quoted_text(r.structured_payload, r.body_encrypted, self._encryption)
            if text_content:
                extracted_numbers, extracted_names = extract_numbers_and_names(text_content)
                numbers |= extracted_numbers
                names |= extracted_names
            ticket_number = r.structured_payload.get("ticket_number")
            if ticket_number is not None:
                numbers.add(str(ticket_number))
            if r.stakeholder_id is not None:
                stakeholder_ids.add(r.stakeholder_id)

        if stakeholder_ids:
            stakeholder_rows = (
                await self._session.execute(
                    text("SELECT name FROM stakeholders WHERE id = ANY((:ids)::uuid[])"),
                    {"ids": list(stakeholder_ids)},
                )
            ).all()
            for s in stakeholder_rows:
                names.add(s.name)
                names |= {part for part in s.name.split() if part[0:1].isupper()}

        return frozenset(numbers), frozenset(names)


class SqlAlchemyPlaybookRepository(PlaybookPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self, finding_type: str) -> list[PlaybookTemplate]:
        rows = (
            await self._session.execute(
                text(
                    "SELECT id, template_text, default_owner_role, default_sla_days "
                    "FROM playbook_actions "
                    "WHERE is_active AND applies_to_finding_type = :finding_type"
                ),
                {"finding_type": finding_type},
            )
        ).all()
        return [
            PlaybookTemplate(
                id=r.id,
                template_text=r.template_text,
                default_owner_role=r.default_owner_role,
                default_sla_days=r.default_sla_days,
            )
            for r in rows
        ]


class SqlAlchemyNarratorOutputRepository(NarratorOutputRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist(self, output: NarratorOutput, score_run_id: UUID) -> None:
        reasons_json = json.dumps(
            [
                {
                    "text": r.text,
                    "points": r.points,
                    "evidence_event_ids": [str(e) for e in r.evidence_event_ids],
                }
                for r in output.reasons
            ]
        )
        actions_json = json.dumps(
            [
                {
                    "text": a.text,
                    "owner": a.owner,
                    "due_date": a.due_date,
                    "playbook_id": str(a.playbook_id),
                }
                for a in output.actions
            ]
        )
        await self._session.execute(
            text(
                "INSERT INTO narrator_outputs "
                "(score_run_id, headline, reasons, actions, fact_check_passed, prompt_version) "
                "VALUES (:score_run_id, :headline, CAST(:reasons AS jsonb), "
                "CAST(:actions AS jsonb), :fact_check_passed, :prompt_version)"
            ),
            {
                "score_run_id": score_run_id,
                "headline": output.headline,
                "reasons": reasons_json,
                "actions": actions_json,
                "fact_check_passed": output.fact_check_passed,
                "prompt_version": output.prompt_version,
            },
        )
        await self._session.commit()
