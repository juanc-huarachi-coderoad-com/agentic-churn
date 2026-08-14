"""Applies data-base/11-seed-data.sql — kept separate from the schema migration
(decisions/02-repo-and-tooling.md §ORM and migrations, FR-003).

Run after ``alembic upgrade head``:
    uv run python scripts/seed.py
"""

import asyncio
import sys
from pathlib import Path

# Allows `uv run python scripts/seed.py` to find the `app` package regardless of
# invocation style (Python adds the script's own directory to sys.path, not backend/).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg  # noqa: E402

from app.config import settings  # noqa: E402

SEED_FILE = Path(__file__).resolve().parents[2] / "data-base" / "11-seed-data.sql"


async def seed() -> None:
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    sql = SEED_FILE.read_text()
    connection = await asyncpg.connect(dsn)
    try:
        # No bind parameters, so asyncpg's simple query protocol runs the whole
        # multi-statement script (BEGIN ... COMMIT) in one call — unlike SQLAlchemy's
        # asyncpg dialect (see migrations/versions/0001_initial_schema.py's docstring),
        # a parameterless asyncpg.Connection.execute() is not restricted to one command.
        await connection.execute(sql)
    finally:
        await connection.close()
    print(f"Seeded from {SEED_FILE}")


if __name__ == "__main__":
    asyncio.run(seed())
