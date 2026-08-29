"""`RunAlertCheckUseCase` (specs/031-production-deployment-hardening-ii, FR-006..010) —
evaluates the three fixed conditions `research.md` Decision 3 enumerates, opens/fires a
webhook for a newly-true one, stays silent for an already-open one (FR-010), and resolves
any open alert whose condition has gone back to healthy. Constitution P6 ("Silence Is a
Success State") applies directly here: a fully healthy system's own alert-check cycle sends
zero webhooks and opens zero rows.
"""

import logging
from datetime import UTC, datetime

from app.alerting.application.ports import (
    AlertConditionReaderPort,
    AlertRepositoryPort,
    WebhookNotifierPort,
)

logger = logging.getLogger(__name__)


class RunAlertCheckUseCase:
    def __init__(
        self,
        conditions: AlertConditionReaderPort,
        alerts: AlertRepositoryPort,
        notifier: WebhookNotifierPort,
    ) -> None:
        self._conditions = conditions
        self._alerts = alerts
        self._notifier = notifier

    async def execute(self) -> None:
        occurred_at = datetime.now(UTC)

        checks: dict[str, str | None] = {
            "score_source_degraded": (
                "Latest score run is degraded — a source stopped reporting reliably."
                if await self._conditions.is_score_source_degraded()
                else None
            ),
            "backup_job_failed": await self._conditions.backup_job_failure_message(),
            "retention_job_failed": await self._conditions.retention_job_failure_message(),
        }

        for condition_name, message in checks.items():
            if message is not None:
                if not await self._alerts.has_open_alert(condition_name):
                    await self._alerts.open_alert(condition_name, message)
                    await self._notifier.send(condition_name, message, occurred_at)
                    logger.warning("alert fired: %s — %s", condition_name, message)
                # else: already open and still true — FR-010, no repeat notification.
            else:
                await self._alerts.resolve_alert(condition_name)
