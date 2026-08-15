"""`RunReadersUseCase` (`architecture/09-clean-architecture-and-patterns.md`'s
named Command) — iterates all five registered readers, isolates each one's
failure (FR-014a, 2026-08-14 clarification: one reader's exception is caught
and reported, the other four still run and persist normally), persists every
emitted finding directly at `status = pending_validation` — `ValidationGate`
(M5a) doesn't exist until feature 007 (`research.md`'s Decision), so this is a
deliberately partial realization of `architecture/08`'s full wiring.
"""

from dataclasses import dataclass

from app.readers.application.ports import FindingRepositoryPort
from app.readers.application.reader import Reader


@dataclass(frozen=True)
class ReaderRunResult:
    reader_type: str
    findings_persisted: int
    error: str | None


class RunReadersUseCase:
    def __init__(self, readers: list[Reader], findings: FindingRepositoryPort) -> None:
        self._readers = readers
        self._findings = findings

    async def execute(self) -> list[ReaderRunResult]:
        results: list[ReaderRunResult] = []
        for reader in self._readers:
            try:
                emitted = await reader.interpret()
                for finding in emitted:
                    await self._findings.persist(finding)
                results.append(
                    ReaderRunResult(
                        reader_type=reader.reader_type,
                        findings_persisted=len(emitted),
                        error=None,
                    )
                )
            except Exception as exc:
                results.append(
                    ReaderRunResult(
                        reader_type=reader.reader_type,
                        findings_persisted=0,
                        error=str(exc),
                    )
                )
        return results
