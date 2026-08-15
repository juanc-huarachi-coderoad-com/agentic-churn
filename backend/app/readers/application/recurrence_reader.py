"""`RecurrenceReader` (REQ-M5-09) — real text embeddings + HDBSCAN clustering,
never a generative call. Re-embeds and re-clusters the full candidate corpus on
every run (2026-08-14 clarification — no incremental clustering at this
feature's fixture-sized data volume, constitution P10/YAGNI). One finding per
recognized cluster, citing every member event (REQ-M5-05).
"""

from uuid import uuid4

from app.readers.application.ports import (
    CandidateCorpusPort,
    EmbeddingPort,
    FindingRepositoryPort,
)
from app.readers.application.reader import Reader
from app.readers.domain.services import cluster_candidates, recurrence_magnitude
from app.scoring.domain.entities import Finding

_FINDING_TYPE = "recurring_issue"


class RecurrenceReader(Reader):
    reader_type = "recurrence"
    reader_version = "v1"

    def __init__(
        self,
        candidates: CandidateCorpusPort,
        embeddings: EmbeddingPort,
        findings: FindingRepositoryPort,
    ) -> None:
        self._candidates = candidates
        self._embeddings = embeddings
        self._findings = findings

    async def interpret(self) -> list[Finding]:
        candidates = await self._candidates.list_candidates()
        if len(candidates) < 2:
            return []

        vectors = [await self._embeddings.embed(c.title) for c in candidates]
        groups = cluster_candidates(candidates, vectors)

        emitted: list[Finding] = []
        for group in groups:
            member_event_ids = [m.event_id for m in group.members]
            already_covered = [
                await self._findings.already_interpreted(
                    reader_type=self.reader_type,
                    reader_version=self.reader_version,
                    event_id=event_id,
                )
                for event_id in member_event_ids
            ]
            if all(already_covered):
                continue

            confidence = min(group.confidences) if group.confidences else 0.5
            emitted.append(
                Finding(
                    id=uuid4(),
                    reader_type=self.reader_type,
                    reader_version=self.reader_version,
                    finding_type=_FINDING_TYPE,
                    magnitude=recurrence_magnitude(len(group.members)),
                    confidence=confidence,
                    cited_event_ids=tuple(member_event_ids),
                    stakeholder_id=None,
                    product_area_id=None,
                    status="pending_validation",
                    state=None,
                    is_positive=False,
                )
            )
        return emitted
