"""Manual baseline-confirmation trigger (`research.md` Decision 3) — writes a
row directly to `baseline_confirmations`, mirroring `scripts/run_readers.py`/
`compute_score.py`'s "manual trigger script, no live UI" pattern. No Profile
Editor UI exists yet (Post-MVP, `decisions/01-mvp-scope-and-phasing.md`) to
build a real human-confirmation flow into.

Run after ``scripts/run_collector.py``:
    uv run python scripts/confirm_baseline.py --stakeholder ana \\
        --metric email_style --window-days 30
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.db import async_session_factory  # noqa: E402

# Seeded CS lead user (data-base/11-seed-data.sql) — the "confirmed_by" for
# every baseline confirmation this script writes; there is no logged-in
# session in a script context to attribute this to instead.
_DEFAULT_CONFIRMED_BY_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def run(stakeholder_query: str, metric: str, window_days: int) -> None:
    async with async_session_factory() as session:
        stakeholder = (
            await session.execute(
                text(
                    "SELECT id, name FROM stakeholders "
                    "WHERE external_id ILIKE :q OR name ILIKE :q LIMIT 2"
                ),
                {"q": f"%{stakeholder_query}%"},
            )
        ).all()
        if len(stakeholder) == 0:
            raise SystemExit(f"No stakeholder matching {stakeholder_query!r}")
        if len(stakeholder) > 1:
            raise SystemExit(f"Ambiguous stakeholder query {stakeholder_query!r}: {stakeholder}")
        stakeholder_id, stakeholder_name = stakeholder[0].id, stakeholder[0].name

        window_end = datetime.now(UTC)
        window_start = window_end - timedelta(days=window_days)

        confirmation_id = (
            await session.execute(
                text(
                    "INSERT INTO baseline_confirmations "
                    "(subject_type, subject_id, metric, window_start, window_end, "
                    "confirmed_by_user_id) "
                    "VALUES ('stakeholder'::rollup_subject_type, :subject_id, :metric, "
                    ":window_start, :window_end, :confirmed_by) "
                    "RETURNING id"
                ),
                {
                    "subject_id": stakeholder_id,
                    "metric": metric,
                    "window_start": window_start,
                    "window_end": window_end,
                    "confirmed_by": _DEFAULT_CONFIRMED_BY_USER_ID,
                },
            )
        ).scalar_one()
        await session.commit()

        print(
            f"baseline_confirmation_id={confirmation_id} "
            f"stakeholder={stakeholder_name!r} metric={metric!r} "
            f"window={window_start.isoformat()}..{window_end.isoformat()}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stakeholder", required=True, help="Name or external_id substring")
    parser.add_argument("--metric", default="email_style")
    parser.add_argument("--window-days", type=int, default=30)
    args = parser.parse_args()
    asyncio.run(run(args.stakeholder, args.metric, args.window_days))
