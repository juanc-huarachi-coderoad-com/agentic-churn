"""`ValidationGate` (M5a, REQ-M5A-01..04) — rejects anything unproven before
it can reach the scoring engine. Runs on every finding from every reader
(`RunReadersUseCase`, `research.md` Decision 5), not just Tone/Intent's.
Orchestration only — no LLM call, no ranking, purely a Chain of
Responsibility over `domain/services.py`'s four pure checks
(`architecture/09-clean-architecture-and-patterns.md`).
"""

from app.readers.application.ports import EventExistencePort, FindingTypeConfigPort
from app.readers.domain.entities import ValidationGateResult
from app.readers.domain.services import evaluate_finding
from app.scoring.domain.entities import Finding


class ValidationGate:
    def __init__(
        self,
        finding_type_config: FindingTypeConfigPort,
        event_existence: EventExistencePort,
    ) -> None:
        self._finding_type_config = finding_type_config
        self._event_existence = event_existence

    async def evaluate(self, finding: Finding) -> ValidationGateResult:
        """Never raises for an unconfigured `finding_type` — that's the
        `thresholds is None` / `schema_invalid` path, handled entirely inside
        `evaluate_finding`. Only genuine infrastructure failures (a dropped
        DB connection) can propagate, which is exactly what `RunReadersUseCase`'s
        own per-finding `try`/`except` exists to contain."""
        thresholds = await self._finding_type_config.get_thresholds(finding.finding_type)
        existing_ids = await self._event_existence.existing_ids(list(finding.cited_event_ids))
        return evaluate_finding(finding, thresholds, existing_ids)
