"""Real-DB integration for `POST /api/drafts` + `.../copy` +
`.../log-as-sent`, against the real, already-scored Meridian database —
matching `tests/unit/test_evidence_route.py`'s own real-DB HTTP pattern.
`AnthropicLLMAdapter.generate_structured` is monkeypatched per test (no live
Anthropic call needed to prove the route/use-case/checks wiring is real);
covers spec.md's User Story 1/2/3 acceptance scenarios and the scripted
red-team case per check (`quickstart.md` §4), plus `/speckit-analyze`
finding U3's stakeholder-404 case and the `/send` 404 probe (REQ-M10-P1).
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.domain.password import hash_password
from app.db import engine
from app.experience.application.prompts.draft_composer_v1 import DraftModelOutput
from app.main import app
from app.readers.adapters.anthropic_llm import AnthropicLLMAdapter

TEST_PASSWORD = "test-password-123"
_CHECK_FAILURE_DETAIL = "Couldn't generate a draft — try again"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_token(client):
    user_id = uuid.uuid4()
    username = f"drafttest-{user_id.hex[:8]}"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, is_active) "
                "VALUES (:id, :username, :password_hash, 'Draft Test', true)"
            ),
            {"id": user_id, "username": username, "password_hash": hash_password(TEST_PASSWORD)},
        )
    login = await client.post("/auth/login", json={"username": username, "password": TEST_PASSWORD})
    token = login.json()["token"]
    yield token
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM auth_tokens WHERE user_id = :id"), {"id": user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


@pytest.fixture
async def issue_and_stakeholder():
    """The real "Issue A — tracking_api reliability" / Ana Reyes fixture
    (`examples/01-end-to-end-walkthrough.md`'s own worked example), skipped
    honestly if this database hasn't been seeded/scored yet."""
    async with engine.begin() as conn:
        issue_row = (
            await conn.execute(
                text(
                    "SELECT i.id FROM issues i "
                    "JOIN finding_issue_map fim ON fim.issue_id = i.id "
                    "JOIN findings f ON f.id = fim.finding_id AND f.status = 'validated' "
                    "WHERE i.label ILIKE '%Issue A%' LIMIT 1"
                )
            )
        ).one_or_none()
        stakeholder_row = (
            await conn.execute(
                text("SELECT id FROM stakeholders WHERE name ILIKE 'Ana%' LIMIT 1")
            )
        ).one_or_none()
    if issue_row is None or stakeholder_row is None:
        pytest.skip("Issue A / Ana fixture not seeded yet")
    return issue_row.id, stakeholder_row.id


async def _cleanup_drafts(issue_id: uuid.UUID, stakeholder_id: uuid.UUID) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "DELETE FROM draft_messages WHERE issue_id = :issue_id "
                "AND stakeholder_id = :stakeholder_id"
            ),
            {"issue_id": issue_id, "stakeholder_id": stakeholder_id},
        )


def _fake_llm(
    monkeypatch: pytest.MonkeyPatch, draft_text: str, tone_variant: str = "direct"
) -> None:
    async def _fake_generate(self, prompt: str, schema):  # noqa: ANN001, ARG001
        return DraftModelOutput(draft_text=draft_text, tone_variant=tone_variant)

    monkeypatch.setattr(AnthropicLLMAdapter, "generate_structured", _fake_generate)


def _draft_request(issue_id, stakeholder_id, tone_variant: str = "direct") -> dict:
    return {
        "issue_id": str(issue_id),
        "stakeholder_id": str(stakeholder_id),
        "tone_variant": tone_variant,
    }


async def test_draft_requires_authentication(client):
    response = await client.post(
        "/api/drafts", json=_draft_request(uuid.uuid4(), uuid.uuid4())
    )
    assert response.status_code == 401


async def test_draft_generates_and_persists_against_the_real_fixture(
    client, auth_token, issue_and_stakeholder, monkeypatch
):
    issue_id, stakeholder_id = issue_and_stakeholder
    _fake_llm(
        monkeypatch,
        "Ana — we're looking into the slow API response you reported. "
        "Engineering is on it today.",
    )

    response = await client.post(
        "/api/drafts",
        json=_draft_request(issue_id, stakeholder_id),
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["checks_passed"] is True
    assert "Ana" in body["draft_text"]
    assert body["evidence_event_ids"]

    async with engine.begin() as conn:
        columns = (
            await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'draft_messages'"
                )
            )
        ).all()
    # No `sent_at`/`sent_by` column exists at all — a schema-level guarantee
    # (REQ-M10-P1), not just an API-response omission.
    assert not any(c.column_name.startswith("sent_") for c in columns)

    await _cleanup_drafts(issue_id, stakeholder_id)


async def test_draft_404_for_nonexistent_issue(client, auth_token, issue_and_stakeholder):
    _, stakeholder_id = issue_and_stakeholder
    response = await client.post(
        "/api/drafts",
        json=_draft_request(uuid.uuid4(), stakeholder_id),
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 404


async def test_draft_404_for_nonexistent_stakeholder(client, auth_token, issue_and_stakeholder):
    """`/speckit-analyze` finding U3."""
    issue_id, _ = issue_and_stakeholder
    response = await client.post(
        "/api/drafts",
        json=_draft_request(issue_id, uuid.uuid4()),
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "draft_text",
    [
        pytest.param("Ana — we spoke with David about the 999-hour delay.", id="unverified_fact"),
        pytest.param("Ana — I'll call you before Friday.", id="invented_date"),
        pytest.param("Ana — your risk score dropped this week.", id="internal_leak"),
        pytest.param("Ana — we can offer a 10% discount this quarter.", id="concession"),
        pytest.param(
            "Ana — this happened because we lost the Acme contract.", id="invented_cause"
        ),
    ],
)
async def test_draft_check_failure_returns_422_and_persists_nothing(
    client, auth_token, issue_and_stakeholder, monkeypatch, draft_text
):
    """`quickstart.md` §4 — a scripted red-team case per check."""
    issue_id, stakeholder_id = issue_and_stakeholder
    _fake_llm(monkeypatch, draft_text)

    async with engine.begin() as conn:
        before = (
            await conn.execute(
                text("SELECT count(*) AS n FROM draft_messages WHERE issue_id = :id"),
                {"id": issue_id},
            )
        ).one()

    response = await client.post(
        "/api/drafts",
        json=_draft_request(issue_id, stakeholder_id),
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == _CHECK_FAILURE_DETAIL

    async with engine.begin() as conn:
        after = (
            await conn.execute(
                text("SELECT count(*) AS n FROM draft_messages WHERE issue_id = :id"),
                {"id": issue_id},
            )
        ).one()
    assert after.n == before.n


async def test_copy_and_log_as_sent_stamp_independently(
    client, auth_token, issue_and_stakeholder, monkeypatch
):
    issue_id, stakeholder_id = issue_and_stakeholder
    _fake_llm(
        monkeypatch, "Ana, thanks for flagging this — we are on it and will follow up soon."
    )

    create = await client.post(
        "/api/drafts",
        json=_draft_request(issue_id, stakeholder_id),
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert create.status_code == 200
    draft_id = create.json()["id"]

    copy_response = await client.post(
        f"/api/drafts/{draft_id}/copy", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert copy_response.status_code == 204

    log_response = await client.post(
        f"/api/drafts/{draft_id}/log-as-sent", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert log_response.status_code == 204

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT copied_at, logged_manually_at FROM draft_messages WHERE id = :id"
                ),
                {"id": draft_id},
            )
        ).one()
    assert row.copied_at is not None
    assert row.logged_manually_at is not None

    await _cleanup_drafts(issue_id, stakeholder_id)


async def test_copy_404_for_nonexistent_draft(client, auth_token):
    response = await client.post(
        f"/api/drafts/{uuid.uuid4()}/copy", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404


async def test_different_tone_variant_is_a_new_row_not_an_update(
    client, auth_token, issue_and_stakeholder, monkeypatch
):
    """`research.md` Decision 9."""
    issue_id, stakeholder_id = issue_and_stakeholder
    _fake_llm(
        monkeypatch,
        "Ana, thanks for flagging this — we are on it and will follow up soon.",
        tone_variant="direct",
    )

    first = await client.post(
        "/api/drafts",
        json=_draft_request(issue_id, stakeholder_id, "direct"),
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert first.status_code == 200

    _fake_llm(monkeypatch, "Ana, quick update — engineering's on it.", tone_variant="brief")
    second = await client.post(
        "/api/drafts",
        json=_draft_request(issue_id, stakeholder_id, "brief"),
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert second.status_code == 200
    assert second.json()["id"] != first.json()["id"]
    assert second.json()["tone_variant"] == "brief"

    await _cleanup_drafts(issue_id, stakeholder_id)


async def test_no_send_route_exists(client, auth_token):
    """REQ-M10-P1 — there is no `/send` route to hit, anywhere."""
    response = await client.post(
        f"/api/drafts/{uuid.uuid4()}/send", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404
