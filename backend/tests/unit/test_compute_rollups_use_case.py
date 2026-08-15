"""REQ-M2-06 — real-DB test confirming `ComputeRollupsUseCase` populates `rollups`
from the real Meridian fixture's warehouse events. `rollups` has been unpopulated
since feature 001's migration until this feature's first run
(`specs/003-ingestion-and-context/spec.md`'s documented deferral).
"""

from sqlalchemy import text

from app.db import async_session_factory
from app.ingestion.adapters.sqlalchemy_repositories import SqlAlchemyEventRepository
from app.ingestion.application.use_cases import ComputeRollupsUseCase


async def test_compute_rollups_populates_from_real_warehouse_events():
    async with async_session_factory() as session:
        use_case = ComputeRollupsUseCase(events=SqlAlchemyEventRepository(session))
        count = await use_case.execute()

    assert count >= 6  # w29..w34, at minimum (data-model.md's fixture)

    async with async_session_factory() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT subject_type, metric, value FROM rollups "
                    "WHERE metric = 'weekly_active_usage' ORDER BY window_end"
                )
            )
        ).all()

    assert len(rows) >= 6
    assert all(r.subject_type == "product_area" for r in rows)
    values = [float(r.value) for r in rows]
    assert -22.0 in values
