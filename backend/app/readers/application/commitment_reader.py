"""`CommitmentReader` (REQ-M5-07) — reads already-computed `response_pairs` rows
(feature 003's `ReplayUseCase`) and applies deterministic business-hours
arithmetic, no model call. The simplest of this feature's five readers: zero new
external dependencies, the lowest-risk foundation (`spec.md`'s User Story 1).
"""

from uuid import uuid4

from app.readers.application.ports import FindingRepositoryPort, ResponsePairRepositoryPort
from app.readers.application.reader import Reader
from app.readers.domain.services import evaluate_commitment
from app.scoring.domain.entities import Finding, is_positive_finding_type


class CommitmentReader(Reader):
    reader_type = "commitment"
    reader_version = "v1"

    def __init__(
        self,
        response_pairs: ResponsePairRepositoryPort,
        findings: FindingRepositoryPort,
    ) -> None:
        self._response_pairs = response_pairs
        self._findings = findings

    async def interpret(self) -> list[Finding]:
        emitted: list[Finding] = []
        for pair in await self._response_pairs.list_all():
            if await self._findings.already_interpreted(
                reader_type=self.reader_type,
                reader_version=self.reader_version,
                event_id=pair.client_event_id,
            ):
                continue

            result = evaluate_commitment(pair)
            if result is None:
                continue

            emitted.append(
                Finding(
                    id=uuid4(),
                    reader_type=self.reader_type,
                    reader_version=self.reader_version,
                    finding_type=result.finding_type,
                    magnitude=result.magnitude,
                    confidence=result.confidence,
                    cited_event_ids=(pair.client_event_id,),
                    stakeholder_id=None,
                    product_area_id=None,
                    status="pending_validation",
                    state=None,
                    is_positive=is_positive_finding_type(result.finding_type),
                )
            )
        return emitted
