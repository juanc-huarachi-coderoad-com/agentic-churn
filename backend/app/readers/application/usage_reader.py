"""`UsageReader` (REQ-M5-08) — flags deviation from a metric's own statistically
defined variance threshold (a z-score against its rolling-window rollup,
REQ-M2-06), never a fixed percentage. `spec.md`'s User Story 2 — the first real
consumer of `rollups`, deferred since feature 003 specifically because no reader
existed yet to need it.
"""

from uuid import uuid4

from app.readers.application.ports import FindingRepositoryPort, RollupRepositoryPort
from app.readers.application.reader import Reader
from app.readers.domain.services import is_usage_deviation, usage_deviation_magnitude, z_score
from app.scoring.domain.entities import Finding

_FINDING_TYPE = "usage_deviation"
# FR-022: a CSAT-score deviation is scored as its own finding_type — a
# seeded `finding_type_config` row (`data-base/11-seed-data.sql`) already
# anticipated this from Phase 1, distinct base_points/confidence_floor/
# half_life from the warehouse-metric `usage_deviation` row it's paired with
# here.
_CSAT_FINDING_TYPE = "csat_deviation"
_CONFIDENCE = 0.9


class UsageReader(Reader):
    reader_type = "usage"
    reader_version = "v1"

    def __init__(
        self,
        rollups: RollupRepositoryPort,
        findings: FindingRepositoryPort,
    ) -> None:
        self._rollups = rollups
        self._findings = findings

    async def interpret(self) -> list[Finding]:
        emitted: list[Finding] = []
        for subject_type, subject_id, metric in await self._rollups.list_subjects():
            historical = await self._rollups.historical_values(
                subject_type=subject_type, subject_id=subject_id, metric=metric
            )
            latest = await self._rollups.latest_value(
                subject_type=subject_type, subject_id=subject_id, metric=metric
            )
            if latest is None:
                continue
            latest_value, event_id = latest

            if await self._findings.already_interpreted(
                reader_type=self.reader_type,
                reader_version=self.reader_version,
                event_id=event_id,
            ):
                continue

            z = z_score(historical, latest_value)
            if z is None or not is_usage_deviation(z):
                continue

            emitted.append(
                Finding(
                    id=uuid4(),
                    reader_type=self.reader_type,
                    reader_version=self.reader_version,
                    finding_type=(
                        _CSAT_FINDING_TYPE if subject_type == "stakeholder" else _FINDING_TYPE
                    ),
                    magnitude=usage_deviation_magnitude(z),
                    confidence=_CONFIDENCE,
                    cited_event_ids=(event_id,),
                    stakeholder_id=subject_id if subject_type == "stakeholder" else None,
                    product_area_id=subject_id if subject_type == "product_area" else None,
                    status="pending_validation",
                    state=None,
                    is_positive=False,
                )
            )
        return emitted
