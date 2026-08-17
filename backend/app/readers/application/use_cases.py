"""`RunReadersUseCase` (`architecture/09-clean-architecture-and-patterns.md`'s
named Command) — iterates all eight registered readers, isolates each one's
failure (FR-014a, 2026-08-14 clarification: one reader's exception is caught
and reported, the other readers still run and persist normally). Every
emitted finding now passes through `ValidationGate.evaluate()` before its one
and only `persist()` call (`research.md` Decision 5) — replacing the
unconditional `pending_validation` write feature 005 shipped, since
`ValidationGate` (M5a) didn't exist until feature 007. The gate-evaluate-then-
persist step is wrapped in its own `try`/`except` per finding, not just each
reader's `interpret()` call (`/speckit-analyze` finding: an unhandled
exception here would otherwise have silently skipped every reader still
queued after the failing one).
"""

import dataclasses
from dataclasses import dataclass

from app.observability.adapters.tracing import traced
from app.readers.application.ports import (
    FindingRepositoryPort,
    QuarantineRepositoryPort,
)
from app.readers.application.reader import Reader
from app.readers.application.validation_gate import ValidationGate

# `traced()` is treated as infrastructure-utility-grade here, the same way this
# codebase already calls Python's stdlib `logging` directly from application-layer
# code (e.g. `RunRetentionUseCase`, specs/011-production-hardening) without a
# dedicated port — unlike a business-domain-relevant concrete exception type (see
# `research.md`/`data-model.md`'s `EncryptionKeyError` note, kept out of the
# application layer for exactly that reason), a generic cross-cutting tracing
# helper carries no business rule and needs no port to stay consistent with P8.


@dataclass(frozen=True)
class ReaderRunResult:
    reader_type: str
    findings_persisted: int
    findings_quarantined: int
    error: str | None


class RunReadersUseCase:
    def __init__(
        self,
        readers: list[Reader],
        findings: FindingRepositoryPort,
        gate: ValidationGate,
        quarantine: QuarantineRepositoryPort,
    ) -> None:
        self._readers = readers
        self._findings = findings
        self._gate = gate
        self._quarantine = quarantine

    async def execute(self) -> list[ReaderRunResult]:
        results: list[ReaderRunResult] = []
        for reader in self._readers:
            with traced(f"reader_execution:{reader.reader_type}") as span:
                try:
                    emitted = await reader.interpret()
                except Exception as exc:
                    # Isolated by design (FR-014a) — this reader failed, but the
                    # run continues, so the trace records a recovered outcome,
                    # not the same "failure" a genuinely unhandled exception
                    # would (specs/011-production-hardening FR-011).
                    span.mark_degraded()
                    results.append(
                        ReaderRunResult(
                            reader_type=reader.reader_type,
                            findings_persisted=0,
                            findings_quarantined=0,
                            error=str(exc),
                        )
                    )
                    continue

                persisted = 0
                quarantined = 0
                finding_error: str | None = None
                for finding in emitted:
                    try:
                        result = await self._gate.evaluate(finding)
                        final = dataclasses.replace(
                            finding,
                            status="validated" if result.passed else "quarantined",
                        )
                        await self._findings.persist(final)
                        persisted += 1
                        if not result.passed:
                            await self._quarantine.record(final.id, list(result.failed_checks))
                            quarantined += 1
                    except Exception as exc:
                        # One finding's failure (a genuine infrastructure error —
                        # ValidationGate.evaluate() never raises for an ordinary
                        # unconfigured-finding_type case, see its own docstring)
                        # must not abort the rest of this reader's batch.
                        finding_error = str(exc)
                        continue

                if finding_error is not None:
                    span.mark_degraded()
                results.append(
                    ReaderRunResult(
                        reader_type=reader.reader_type,
                        findings_persisted=persisted,
                        findings_quarantined=quarantined,
                        error=finding_error,
                    )
                )
        return results
