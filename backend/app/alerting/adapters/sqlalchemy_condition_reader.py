"""`SqlAlchemyAlertConditionReader` (specs/031-production-deployment-hardening-ii) — reads
`score_runs` (owned by `app.scoring`) and `backup_job_runs`/`retention_job_runs` (owned by
`app.ingestion`) directly via SQL, the same "read another module's table via your own
adapter" shape `app.narrator`'s `SqlAlchemyScoreContextRepository` already established for
`score_runs` specifically.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerting.application.ports import AlertConditionReaderPort


class SqlAlchemyAlertConditionReader(AlertConditionReaderPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_score_source_degraded(self) -> bool:
        row = (
            await self._session.execute(
                text(
                    "SELECT source_degraded FROM score_runs "
                    "ORDER BY computed_at DESC LIMIT 1"
                )
            )
        ).one_or_none()
        return bool(row.source_degraded) if row is not None else False

    async def backup_job_failure_message(self) -> str | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT status, error_detail FROM backup_job_runs "
                    "ORDER BY started_at DESC LIMIT 1"
                )
            )
        ).one_or_none()
        if row is None or row.status != "failed":
            return None
        return f"Backup job failed: {row.error_detail}"

    async def retention_job_failure_message(self) -> str | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT status, error_detail FROM retention_job_runs "
                    "ORDER BY started_at DESC LIMIT 1"
                )
            )
        ).one_or_none()
        if row is None or row.status != "failed":
            return None
        return f"Retention job failed: {row.error_detail}"
