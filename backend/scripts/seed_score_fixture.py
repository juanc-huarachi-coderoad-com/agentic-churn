"""Applies the hand-authored score-engine proof fixture
(`demo/fixtures/score-engine-findings.json`) — reproduces `examples/01-end-to-end-
walkthrough.md` §9's worked example (`specs/004-score-engine/data-model.md`, corrected
for a rank-order inconsistency found during `/speckit-analyze`). Separate from
`scripts/seed.py`'s real-deployment seed data — this fixture is explicitly synthetic
proof data (`research.md`'s Decision).

Prerequisites: ``alembic upgrade head``, ``scripts/seed.py``, and
``scripts/run_collector.py --source simulated`` (real MVP-source events must already
exist in the ledger for six of the nine findings to cite). Run:
    uv run python scripts/seed_score_fixture.py
"""

import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import async_session_factory  # noqa: E402
from app.ingestion.adapters.encryption import FernetEncryption  # noqa: E402
from app.ingestion.adapters.sqlalchemy_repositories import (  # noqa: E402
    SqlAlchemyCollectorRunRepository,
    SqlAlchemyCommitmentLookup,
    SqlAlchemyEventRepository,
)
from app.ingestion.application.ports import NewEvent  # noqa: E402
from app.ingestion.application.use_cases import DetectAbsenceUseCase  # noqa: E402

# demo/ sits in two different places relative to this file depending on where it
# runs: a sibling of backend/ on a host checkout (backend/scripts/../../demo), but a
# child of backend/'s container root under Docker (docker-compose.yml mounts
# ./demo:/app/demo, and this script's CWD-independent parents[1] already resolves to
# /app there) — try both rather than hardcoding one layout.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = next(
    path
    for path in (
        _BACKEND_ROOT / "demo" / "fixtures" / "score-engine-findings.json",
        _BACKEND_ROOT.parent / "demo" / "fixtures" / "score-engine-findings.json",
    )
    if path.exists()
)


async def _resolve_mvp_event(session, native_id: str) -> UUID:
    row = (
        await session.execute(
            text(
                "SELECT e.id FROM events e "
                "JOIN raw_envelopes re ON re.id = e.envelope_id "
                "WHERE re.source_native_id = :native_id LIMIT 1"
            ),
            {"native_id": native_id},
        )
    ).one_or_none()
    if row is None:
        raise SystemExit(
            f"No real event found for source_native_id={native_id!r} — "
            "run scripts/run_collector.py --source simulated first"
        )
    return row.id


async def _resolve_synthetic_csat_event(
    session, encryption: FernetEncryption, occurred_at: datetime, citation: dict
) -> UUID:
    """Inserts one synthetic `survey_response` event via the real, hash-chained
    `EventRepositoryPort.append` path (not a bypass) — CSAT is a Post-MVP source with
    no live collector yet (`research.md`'s Decision). Idempotent by native_id, same
    lookup-first pattern as `_resolve_mvp_event` — this script is re-run safe (a
    second run against a demo environment that already has this fixture applied finds
    and reuses the existing event rather than colliding on `idempotency_key`)."""
    existing = (
        await session.execute(
            text(
                "SELECT ledger_event_id FROM raw_envelopes "
                "WHERE source_native_id = 'csat-resp-score-engine-fixture'"
            )
        )
    ).one_or_none()
    if existing is not None and existing.ledger_event_id is not None:
        return existing.ledger_event_id

    source = (
        await session.execute(text("SELECT id FROM sources WHERE source_type = 'csat' LIMIT 1"))
    ).one()
    run_id = uuid4()
    envelope_id = uuid4()
    await session.execute(
        text(
            "INSERT INTO collector_runs (id, source_id, trigger, window_start, window_end) "
            "VALUES (:id, :source_id, 'manual'::collector_trigger, :occurred_at, :occurred_at)"
        ),
        {"id": run_id, "source_id": source.id, "occurred_at": occurred_at},
    )
    payload_encrypted = encryption.encrypt(
        f"CSAT score {citation['score']} (previous {citation['previous_score']}): "
        "Support has been slower than we'd like lately."
    )
    await session.execute(
        text(
            "INSERT INTO raw_envelopes (id, collector_run_id, source_native_id, "
            "idempotency_key, occurred_at, identity_status, payload_encrypted, data_key_ref) "
            "VALUES (:id, :run_id, :native_id, :native_id, :occurred_at, "
            "'resolved'::identity_status, :payload, :data_key_ref)"
        ),
        {
            "id": envelope_id,
            "run_id": run_id,
            "native_id": "csat-resp-score-engine-fixture",
            "occurred_at": occurred_at,
            "payload": payload_encrypted,
            "data_key_ref": settings.encryption_key_id,
        },
    )
    await session.commit()

    events = SqlAlchemyEventRepository(session)
    event_id = await events.append(
        NewEvent(
            envelope_id=envelope_id,
            event_type="survey_response",
            occurred_at=occurred_at,
            body_encrypted=payload_encrypted,
            structured_payload={
                "score": citation["score"],
                "previous_score": citation["previous_score"],
            },
        ),
        data_key_ref=settings.encryption_key_id,
    )
    await session.execute(
        text("UPDATE raw_envelopes SET ledger_event_id = :event_id WHERE id = :envelope_id"),
        {"event_id": event_id, "envelope_id": envelope_id},
    )
    await session.commit()
    return event_id


async def _resolve_stakeholder(session, identifier: str | None) -> UUID | None:
    if identifier is None:
        return None
    row = (
        await session.execute(
            text(
                "SELECT s.id FROM stakeholders s "
                "JOIN client_profile_versions pv ON pv.id = s.profile_version_id "
                "WHERE pv.is_current AND :identifier = ANY(s.identifiers) LIMIT 1"
            ),
            {"identifier": identifier},
        )
    ).one_or_none()
    return row.id if row is not None else None


async def _resolve_product_area(session, key: str | None) -> UUID | None:
    if key is None:
        return None
    row = (
        await session.execute(
            text(
                "SELECT pa.id FROM product_areas pa "
                "JOIN client_profile_versions pv ON pv.id = pa.profile_version_id "
                "WHERE pv.is_current AND pa.key = :key LIMIT 1"
            ),
            {"key": key},
        )
    ).one_or_none()
    return row.id if row is not None else None


async def seed() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text())
    encryption = FernetEncryption(settings.encryption_key_path)

    async with async_session_factory() as session:
        # Guarantee a real `absence`-type event exists for fnd-4/fnd-5 to cite —
        # anchored well past the ledger's last real contact so it's unambiguously
        # overdue, regardless of when this script happens to run (research.md's
        # Decision; same anchoring lesson as specs/003's tests/conftest.py).
        commitments = SqlAlchemyCommitmentLookup(session)
        last_contact = await commitments.last_contact_at()
        absence_as_of = (last_contact or datetime.now(UTC)) + timedelta(days=8)

        absence_use_case = DetectAbsenceUseCase(
            commitments=commitments,
            collector_runs=SqlAlchemyCollectorRunRepository(session),
            events=SqlAlchemyEventRepository(session),
            encryption=encryption,
            data_key_ref=settings.encryption_key_id,
        )
        appended = await absence_use_case.execute(as_of=absence_as_of)
        if appended:
            absence_event_id = appended[0]
            print(f"DetectAbsenceUseCase produced a real absence event: {absence_event_id}")
        else:
            # Already produced by an earlier run of this script (or the worker's
            # heartbeat) — find the most recent real absence event instead.
            row = (
                await session.execute(
                    text(
                        "SELECT id FROM events WHERE event_type = 'absence'::event_type "
                        "ORDER BY occurred_at DESC LIMIT 1"
                    )
                )
            ).one()
            absence_event_id = row.id

        csat_occurred_at = absence_as_of + timedelta(hours=1)
        csat_event_id: UUID | None = None

        issue_ids: dict[str, UUID] = {}
        for issue in fixture["issues"]:
            issue_id = uuid4()
            await session.execute(
                text(
                    "INSERT INTO issues (id, label, cluster_method) "
                    "VALUES (:id, :label, (:cluster_method)::cluster_method)"
                ),
                {
                    "id": issue_id,
                    "label": issue["label"],
                    "cluster_method": issue["cluster_method"],
                },
            )
            issue_ids[issue["id"]] = issue_id
        await session.commit()

        finding_ids: dict[str, UUID] = {}
        for finding in fixture["findings"]:
            citation = finding["citation"]
            if citation["type"] == "mvp_event":
                cited_event_id = await _resolve_mvp_event(session, citation["native_id"])
                print(
                    f"{finding['id']}: cites real MVP event "
                    f"{citation['native_id']!r} -> {cited_event_id}"
                )
            elif citation["type"] == "absence_event":
                cited_event_id = absence_event_id
            elif citation["type"] == "synthetic_csat_event":
                if csat_event_id is None:
                    csat_event_id = await _resolve_synthetic_csat_event(
                        session, encryption, csat_occurred_at, citation
                    )
                    print(f"Inserted synthetic CSAT survey_response event: {csat_event_id}")
                cited_event_id = csat_event_id
            else:
                raise SystemExit(f"Unknown citation type: {citation['type']!r}")

            stakeholder_id = await _resolve_stakeholder(session, finding.get("stakeholder"))
            product_area_id = await _resolve_product_area(session, finding.get("product_area"))

            finding_id = uuid4()
            await session.execute(
                text(
                    "INSERT INTO findings (id, reader_type, reader_version, finding_type, "
                    "magnitude, confidence, cited_event_ids, stakeholder_id, "
                    "product_area_id, status) "
                    "VALUES (:id, (:reader_type)::reader_type, :reader_version, "
                    ":finding_type, :magnitude, :confidence, :cited_event_ids, "
                    ":stakeholder_id, :product_area_id, 'validated'::finding_status)"
                ),
                {
                    "id": finding_id,
                    "reader_type": finding["reader_type"],
                    "reader_version": "score-engine-fixture-v1",
                    "finding_type": finding["finding_type"],
                    "magnitude": finding["magnitude"],
                    "confidence": finding["confidence"],
                    "cited_event_ids": [cited_event_id],
                    "stakeholder_id": stakeholder_id,
                    "product_area_id": product_area_id,
                },
            )
            finding_ids[finding["id"]] = finding_id

            if finding.get("issue"):
                # rank_within_issue is NOT NULL — a placeholder here, immediately
                # overwritten by IssueGrouper on the first real scoring run
                # (research.md's Decision: never seeded meaningfully).
                await session.execute(
                    text(
                        "INSERT INTO finding_issue_map (finding_id, issue_id, rank_within_issue) "
                        "VALUES (:finding_id, :issue_id, 1)"
                    ),
                    {
                        "finding_id": finding_id,
                        "issue_id": issue_ids[finding["issue"]],
                    },
                )
        await session.commit()

    membership_count = sum(1 for f in fixture["findings"] if f.get("issue"))
    print(
        f"{len(finding_ids)} findings inserted, {len(issue_ids)} issues, "
        f"{membership_count} finding_issue_map rows"
    )


if __name__ == "__main__":
    asyncio.run(seed())
