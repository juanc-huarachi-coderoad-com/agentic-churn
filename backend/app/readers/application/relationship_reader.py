"""`RelationshipReader` (REQ-M5-11) — diffs the current profile's stakeholder
list against ledger-active participants over a rolling 4-week window
(2026-08-14 clarification). Reduced strength in this feature (email/ticket-
cadence signals only, `spec.md`'s Assumptions) — honest fixed magnitude/
confidence rather than a false-precision formula (`research.md`'s Decision).
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.readers.application.ports import FindingRepositoryPort, RelationshipContextPort
from app.readers.application.reader import Reader
from app.readers.domain.services import relationship_change_finding
from app.scoring.domain.entities import Finding

_FINDING_TYPE = "relationship_change"
_WINDOW_DAYS = 28


class RelationshipReader(Reader):
    reader_type = "relationship"
    reader_version = "v1"

    def __init__(
        self,
        context: RelationshipContextPort,
        findings: FindingRepositoryPort,
    ) -> None:
        self._context = context
        self._findings = findings

    async def interpret(self) -> list[Finding]:
        since = datetime.now(UTC) - timedelta(days=_WINDOW_DAYS)
        active = await self._context.active_stakeholder_ids(since=since)
        magnitude, confidence = relationship_change_finding()

        emitted: list[Finding] = []
        for stakeholder_id in await self._context.list_stakeholders():
            if stakeholder_id in active:
                continue

            evidence_event_id = await self._context.most_recent_event_for_stakeholder(
                stakeholder_id
            )
            if evidence_event_id is None:
                continue

            if await self._findings.already_interpreted(
                reader_type=self.reader_type,
                reader_version=self.reader_version,
                event_id=evidence_event_id,
            ):
                continue

            emitted.append(
                Finding(
                    id=uuid4(),
                    reader_type=self.reader_type,
                    reader_version=self.reader_version,
                    finding_type=_FINDING_TYPE,
                    magnitude=magnitude,
                    confidence=confidence,
                    cited_event_ids=(evidence_event_id,),
                    stakeholder_id=stakeholder_id,
                    product_area_id=None,
                    status="pending_validation",
                    state=None,
                    is_positive=False,
                )
            )
        return emitted
