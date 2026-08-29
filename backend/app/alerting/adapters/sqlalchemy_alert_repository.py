"""`SqlAlchemyAlertRepository` (specs/031-production-deployment-hardening-ii) — the
`alerts` table's own adapter. FR-010's de-duplication is ultimately guaranteed by the
table's own `alerts_one_open_per_condition` partial unique index (`data-model.md`); this
class's `has_open_alert` check exists to avoid a needless failed-insert on the common
"still open" path, not as the sole guarantee.
"""

from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerting.application.ports import AlertRepositoryPort


class SqlAlchemyAlertRepository(AlertRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_open_alert(self, condition_name: str) -> bool:
        row = (
            await self._session.execute(
                text(
                    "SELECT 1 FROM alerts "
                    "WHERE condition_name = :condition_name AND resolved_at IS NULL"
                ),
                {"condition_name": condition_name},
            )
        ).one_or_none()
        return row is not None

    async def open_alert(self, condition_name: str, message: str) -> None:
        await self._session.execute(
            text(
                "INSERT INTO alerts (id, condition_name, message) "
                "VALUES (:id, :condition_name, :message)"
            ),
            {"id": uuid4(), "condition_name": condition_name, "message": message},
        )
        await self._session.commit()

    async def resolve_alert(self, condition_name: str) -> None:
        await self._session.execute(
            text(
                "UPDATE alerts SET resolved_at = now() "
                "WHERE condition_name = :condition_name AND resolved_at IS NULL"
            ),
            {"condition_name": condition_name},
        )
        await self._session.commit()
