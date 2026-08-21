"""Real-DB, real-ASGI-app: `POST /api/meeting-audio/refresh`
(specs/019-meeting-audio-ingestion, `contracts/meeting-audio.md`). Patches
`_build_audio_collector` to return a real `AudioCollector` wired to fake
local storage/transcription collaborators (mirrors `test_audio_collector.py`'s
fakes) — no real filesystem, OpenAI, or pyannote calls, but the real router,
real `RunCollectorUseCase`, and real database.

Also covers `/speckit-analyze` finding E2 (a real, if loose, timing
assertion for SC-003) and User Story 4's degraded-response shape (finding
F2's `trigger` fix is what makes attributing `source_error` to *this*
specific run possible at all).

2026-08-20 revision: migrated from a fake Google Drive client to a fake
local storage client (`research.md` Decision 12) — the router-level behavior
under test is otherwise unchanged.
"""

import time
import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.domain.password import hash_password
from app.db import engine
from app.ingestion.adapters.audio_collector import AudioCollector
from app.ingestion.adapters.local_storage_client import (
    LocalRecording,
    LocalStorageAccessError,
)
from app.main import app

_PASSWORD = "test-password-123"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def ae_token(client):
    async with engine.begin() as conn:
        user_id = uuid.uuid4()
        username = f"ae-refresh-test-{user_id.hex[:8]}"
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, role, "
                "is_active) VALUES (:id, :username, :password_hash, 'AE Test', "
                "'account_executive'::user_role, true)"
            ),
            {"id": user_id, "username": username, "password_hash": hash_password(_PASSWORD)},
        )
    resp = await client.post("/auth/login", json={"username": username, "password": _PASSWORD})
    yield resp.json()["token"]
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM auth_tokens WHERE user_id = :id"), {"id": user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


@pytest.fixture
async def cs_lead_token(client):
    resp = await client.post(
        "/auth/login", json={"username": "marta", "password": "agentic-demo-2026"}
    )
    return resp.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class _FakeLocalStorage:
    def __init__(self, recordings=None, fail: bool = False) -> None:
        self._recordings = recordings or []
        self._fail = fail

    def list_recordings(self):
        if self._fail:
            raise LocalStorageAccessError("meeting audio storage location is not accessible")
        return self._recordings

    def read(self, file_id: str) -> bytes:
        return b"fake-audio"


class _FakeTranscriber:
    async def transcribe(self, audio_bytes, filename, candidate_stakeholder_names):
        return type("R", (), {"text": "", "primary_speaker_name": None})()


def _fake_collector_factory(storage) -> object:
    # `_build_audio_collector` in the real router is a plain sync function
    # (constructing adapters has no I/O) — this fake must match that exact
    # signature, or the router's un-awaited `collector = _build_audio_
    # collector(session)` call silently receives a coroutine object instead
    # of an `AudioCollector` (a real bug found writing this test: an `async
    # def` fake here produced a 500 with no useful message).
    def _build(session):
        from app.ingestion.adapters.sqlalchemy_repositories import (
            SqlAlchemyClientProfileContext,
            SqlAlchemyCollectorRunRepository,
            SqlAlchemyMeetingSeriesConsentRepository,
        )

        return AudioCollector(
            storage=storage,
            transcriber=_FakeTranscriber(),
            consent=SqlAlchemyMeetingSeriesConsentRepository(session),
            collector_runs=SqlAlchemyCollectorRunRepository(session),
            profile_context=SqlAlchemyClientProfileContext(session),
        )

    return _build


async def test_nothing_new_returns_all_zero_counts_not_an_error(client, cs_lead_token):
    with patch(
        "app.ingestion.adapters.audio_refresh_router._build_audio_collector",
        new=_fake_collector_factory(_FakeLocalStorage([])),
    ):
        start = time.monotonic()
        resp = await client.post("/api/meeting-audio/refresh", headers=_auth(cs_lead_token))
        elapsed = time.monotonic() - start

    assert resp.status_code == 200
    body = resp.json()
    assert body["recordings_found"] == 0
    assert body["transcribed"] == 0
    assert body["skipped_no_consent"] == 0
    assert body["failed"] == 0
    assert body["source_error"] is None
    # `/speckit-analyze` finding E2 — SC-003's "under one minute, excluding
    # transcription time" — a real, if generous, upper bound with the local
    # storage/Whisper calls mocked to return immediately.
    assert elapsed < 5.0


async def test_account_executive_gets_403(client, ae_token):
    resp = await client.post("/api/meeting-audio/refresh", headers=_auth(ae_token))
    assert resp.status_code == 403


async def test_a_recording_found_but_not_consented_is_counted_and_not_transcribed(
    client, cs_lead_token
):
    recording = LocalRecording(
        file_id=f"file-{uuid.uuid4().hex[:8]}",
        name="meeting.mp3",
        modified_time="2026-08-19T10:00:00+00:00",
        series_id=f"never-consented-{uuid.uuid4().hex[:8]}",
    )
    with patch(
        "app.ingestion.adapters.audio_refresh_router._build_audio_collector",
        new=_fake_collector_factory(_FakeLocalStorage([recording])),
    ):
        resp = await client.post("/api/meeting-audio/refresh", headers=_auth(cs_lead_token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["recordings_found"] == 1
    assert body["skipped_no_consent"] == 1
    assert body["transcribed"] == 0


async def test_an_inaccessible_local_storage_location_returns_the_degraded_shape(
    client, cs_lead_token
):
    """User Story 4 — a whole-connection failure surfaces as `source_error`,
    never a `500` and never indistinguishable from "nothing new"."""
    with patch(
        "app.ingestion.adapters.audio_refresh_router._build_audio_collector",
        new=_fake_collector_factory(_FakeLocalStorage([], fail=True)),
    ):
        resp = await client.post("/api/meeting-audio/refresh", headers=_auth(cs_lead_token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["source_error"] is not None
    assert "storage location is not accessible" in body["source_error"]

    # GET /api/coverage reflects the same gap — `sources.status` is now
    # self-healing (`finish_run()`, a fix found necessary while building
    # this route's own degraded case: the column had never been written by
    # anything past its initial 'connected' default, for any source, before
    # this feature).
    coverage_resp = await client.get("/api/coverage", headers=_auth(cs_lead_token))
    sources = {s["source_type"]: s for s in coverage_resp.json()["sources"]}
    assert sources["transcripts"]["status"] == "degraded"
