from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.experience.application.ports import ClientProfileRecord, ClientProfileRepositoryPort


class SqlAlchemyClientProfileRepository(ClientProfileRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current(self) -> ClientProfileRecord | None:
        result = await self._session.execute(
            text("SELECT client_name FROM client_profile_versions WHERE is_current = true")
        )
        row = result.one_or_none()
        if row is None:
            return None
        return ClientProfileRecord(client_name=row.client_name)
