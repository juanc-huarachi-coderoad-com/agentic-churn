"""`AbsenceReader` (REQ-M5-10) — emits `contact_absence` only from a real,
already-recorded `absence`-type event (feature 003's `DetectAbsenceUseCase`).
Never independently infers or computes a silence duration — that judgment
already happened at ledger-append time.
"""

from uuid import uuid4

from app.readers.application.ports import AbsenceEventRepositoryPort, FindingRepositoryPort
from app.readers.application.reader import Reader
from app.readers.domain.services import absence_confidence, absence_magnitude
from app.scoring.domain.entities import Finding

_FINDING_TYPE = "contact_absence"


class AbsenceReader(Reader):
    reader_type = "absence"
    reader_version = "v1"

    def __init__(
        self,
        absence_events: AbsenceEventRepositoryPort,
        findings: FindingRepositoryPort,
    ) -> None:
        self._absence_events = absence_events
        self._findings = findings

    async def interpret(self) -> list[Finding]:
        emitted: list[Finding] = []
        for event in await self._absence_events.list_all():
            if await self._findings.already_interpreted(
                reader_type=self.reader_type,
                reader_version=self.reader_version,
                event_id=event.event_id,
            ):
                continue

            cadence_days = (event.occurred_at - event.window_start).total_seconds() / 86400
            silence_days = (
                (event.occurred_at - event.last_contact_at).total_seconds() / 86400
                if event.last_contact_at is not None
                else None
            )

            emitted.append(
                Finding(
                    id=uuid4(),
                    reader_type=self.reader_type,
                    reader_version=self.reader_version,
                    finding_type=_FINDING_TYPE,
                    magnitude=absence_magnitude(
                        silence_days=silence_days, cadence_days=cadence_days
                    ),
                    confidence=absence_confidence(),
                    cited_event_ids=(event.event_id,),
                    stakeholder_id=None,
                    product_area_id=None,
                    status="pending_validation",
                    state=None,
                    is_positive=False,
                )
            )
        return emitted
