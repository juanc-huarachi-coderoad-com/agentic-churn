"""`SqlAlchemyMeetingSeriesConsentRepository` (specs/019-meeting-audio-ingestion,
FR-004/FR-005) — the append-only consent audit trail `AudioCollector`/
`SimulatedCollector`'s consent gate reads, and `consent_router.py`'s
endpoints write to.
"""

import uuid

from sqlalchemy import text

from app.db import async_session_factory, engine
from app.ingestion.adapters.sqlalchemy_repositories import (
    MeetingSeriesConsentValidationError,
    SqlAlchemyMeetingSeriesConsentRepository,
)


async def _seed_user() -> uuid.UUID:
    user_id = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, role, is_active) "
                "VALUES (:id, :username, 'x', 'Consent Test User', 'cs_lead'::user_role, true)"
            ),
            {"id": user_id, "username": f"consent-test-{user_id.hex[:8]}"},
        )
    return user_id


async def test_granting_without_all_parties_confirmed_is_rejected():
    user_id = await _seed_user()
    series_id = f"series-{uuid.uuid4().hex[:8]}"
    async with async_session_factory() as session:
        repo = SqlAlchemyMeetingSeriesConsentRepository(session)
        threw = False
        try:
            await repo.record(
                series_id=series_id,
                status="granted",
                all_parties_confirmed=False,
                documented_by_user_id=user_id,
                note=None,
            )
        except MeetingSeriesConsentValidationError:
            threw = True
        assert threw, "granting without all_parties_confirmed must be rejected"
        assert await repo.is_active(series_id) is False


async def test_grant_revoke_regrant_produces_three_rows_and_is_active_reflects_latest():
    user_id = await _seed_user()
    series_id = f"series-{uuid.uuid4().hex[:8]}"
    async with async_session_factory() as session:
        repo = SqlAlchemyMeetingSeriesConsentRepository(session)

        await repo.record(
            series_id=series_id,
            status="granted",
            all_parties_confirmed=True,
            documented_by_user_id=user_id,
            note=None,
        )
        assert await repo.is_active(series_id) is True

        await repo.record(
            series_id=series_id,
            status="revoked",
            all_parties_confirmed=True,
            documented_by_user_id=user_id,
            note="withdrawn",
        )
        assert await repo.is_active(series_id) is False

        await repo.record(
            series_id=series_id,
            status="granted",
            all_parties_confirmed=True,
            documented_by_user_id=user_id,
            note="re-confirmed",
        )
        assert await repo.is_active(series_id) is True

    async with engine.begin() as conn:
        count = (
            await conn.execute(
                text("SELECT count(*) AS n FROM meeting_series_consent WHERE series_id = :sid"),
                {"sid": series_id},
            )
        ).one()
    assert count.n == 3


async def test_never_decided_series_is_not_active():
    """spec.md's Edge Cases: a series with no consent decision at all is
    treated identically to a revoked one — never active."""
    series_id = f"series-{uuid.uuid4().hex[:8]}"
    async with async_session_factory() as session:
        repo = SqlAlchemyMeetingSeriesConsentRepository(session)
        assert await repo.is_active(series_id) is False


async def test_list_current_returns_only_the_latest_row_per_series():
    user_id = await _seed_user()
    series_a = f"series-{uuid.uuid4().hex[:8]}"
    series_b = f"series-{uuid.uuid4().hex[:8]}"
    async with async_session_factory() as session:
        repo = SqlAlchemyMeetingSeriesConsentRepository(session)
        await repo.record(
            series_id=series_a,
            status="granted",
            all_parties_confirmed=True,
            documented_by_user_id=user_id,
            note=None,
        )
        await repo.record(
            series_id=series_a,
            status="revoked",
            all_parties_confirmed=True,
            documented_by_user_id=user_id,
            note=None,
        )
        await repo.record(
            series_id=series_b,
            status="granted",
            all_parties_confirmed=True,
            documented_by_user_id=user_id,
            note=None,
        )

        current = await repo.list_current()

    by_series = {r.series_id: r for r in current}
    assert by_series[series_a].status == "revoked"
    assert by_series[series_b].status == "granted"
