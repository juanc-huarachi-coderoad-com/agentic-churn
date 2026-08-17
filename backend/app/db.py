from collections.abc import AsyncIterator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

# The retention job's only connection (specs/011-production-hardening, research.md
# Decision 1) — same host/port/database as `engine` above, but authenticated as
# `shredder_role` instead of the unrestricted default user, so the grant `0001_
# initial_schema.py`/`0003_production_hardening.py` provisioned (`UPDATE
# (body_encrypted) ON events`, `UPDATE (payload_encrypted) ON raw_envelopes`,
# `SELECT` on both) is exercised by a real connection for the first time — every
# other session in this codebase still connects as the unrestricted default user.
_shredder_url = make_url(settings.database_url).set(
    username="shredder_role", password=settings.shredder_role_password
)
shredder_engine = create_async_engine(_shredder_url)
shredder_session_factory = async_sessionmaker(shredder_engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped async session."""
    async with async_session_factory() as session:
        yield session
