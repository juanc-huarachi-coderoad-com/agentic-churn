"""`GET`/`POST /api/meeting-audio/consent` (specs/019-meeting-audio-ingestion,
`contracts/meeting-audio.md`). Both routes require a bearer token; `POST`
additionally requires `require_full_access` (FR-016 — CS lead only, the same
RBAC boundary `POST /api/profile/reload` already uses).

No separate `RecordMeetingSeriesConsentUseCase` — found during implementation
that one would be a pure passthrough to `SqlAlchemyMeetingSeriesConsentRepository.
record()`, which already performs the only real business rule here (the
all-parties validation) at the adapter boundary. Mirrors
`profile_router.py`'s `get_profile` route, which calls its repository
directly for the same reason: an application-layer use case earns its place
by orchestrating something a single repository call doesn't already do
(constitution P10), not by existing on principle.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.dependencies import CurrentUser, get_current_user, require_full_access
from app.db import get_session
from app.ingestion.adapters.sqlalchemy_repositories import (
    MeetingSeriesConsentValidationError,
    SqlAlchemyMeetingSeriesConsentRepository,
)
from app.ingestion.application.ports import MeetingSeriesConsentRecord

router = APIRouter()


class ConsentEntry(BaseModel):
    series_id: str
    status: str
    all_parties_confirmed: bool
    documented_by: str
    documented_at: str
    note: str | None


class ConsentListResponse(BaseModel):
    series: list[ConsentEntry]


class ConsentRequest(BaseModel):
    series_id: str
    status: Literal["granted", "revoked"]
    all_parties_confirmed: bool
    note: str | None = None


async def _resolve_usernames(
    session: AsyncSession, records: list[MeetingSeriesConsentRecord]
) -> dict[str, str]:
    """One query for every `documented_by_user_id` this response needs,
    rather than N+1 lookups — usernames are an auth-layer concept, resolved
    here at the router boundary rather than folded into the ingestion port's
    own `MeetingSeriesConsentRecord` shape (module boundary discipline,
    constitution P8)."""
    user_ids = {r.documented_by_user_id for r in records}
    if not user_ids:
        return {}
    rows = (
        await session.execute(
            text("SELECT id, username FROM users WHERE id = ANY(:ids)"),
            {"ids": list(user_ids)},
        )
    ).all()
    return {str(r.id): r.username for r in rows}


def _to_entry(record: MeetingSeriesConsentRecord, usernames: dict[str, str]) -> ConsentEntry:
    return ConsentEntry(
        series_id=record.series_id,
        status=record.status,
        all_parties_confirmed=record.all_parties_confirmed,
        documented_by=usernames.get(str(record.documented_by_user_id), "unknown"),
        documented_at=record.documented_at.isoformat(),
        note=record.note,
    )


@router.get("/api/meeting-audio/consent", response_model=ConsentListResponse)
async def list_consent(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ConsentListResponse:
    records = await SqlAlchemyMeetingSeriesConsentRepository(session).list_current()
    usernames = await _resolve_usernames(session, records)
    return ConsentListResponse(series=[_to_entry(r, usernames) for r in records])


@router.post("/api/meeting-audio/consent", response_model=ConsentEntry, status_code=201)
async def record_consent(
    body: ConsentRequest,
    current_user: CurrentUser = Depends(require_full_access),
    session: AsyncSession = Depends(get_session),
) -> ConsentEntry:
    try:
        record = await SqlAlchemyMeetingSeriesConsentRepository(session).record(
            series_id=body.series_id,
            status=body.status,
            all_parties_confirmed=body.all_parties_confirmed,
            documented_by_user_id=current_user.user_id,
            note=body.note,
        )
    except MeetingSeriesConsentValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    usernames = await _resolve_usernames(session, [record])
    return _to_entry(record, usernames)
