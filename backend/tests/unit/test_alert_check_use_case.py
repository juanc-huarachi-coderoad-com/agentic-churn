"""specs/031-production-deployment-hardening-ii — `RunAlertCheckUseCase` unit coverage
against fake ports (no real database needed, matching `test_warehouse_collector.py`'s
fake-client pattern) plus `HttpxWebhookNotifier`'s own honest-unconfigured-destination
behavior.
"""

from datetime import datetime

from app.alerting.adapters.webhook_notifier import HttpxWebhookNotifier
from app.alerting.application.ports import (
    AlertConditionReaderPort,
    AlertRepositoryPort,
    WebhookNotifierPort,
)
from app.alerting.application.use_cases import RunAlertCheckUseCase


class _FakeConditions(AlertConditionReaderPort):
    def __init__(
        self,
        score_degraded: bool = False,
        backup_failure: str | None = None,
        retention_failure: str | None = None,
    ) -> None:
        self._score_degraded = score_degraded
        self._backup_failure = backup_failure
        self._retention_failure = retention_failure

    async def is_score_source_degraded(self) -> bool:
        return self._score_degraded

    async def backup_job_failure_message(self) -> str | None:
        return self._backup_failure

    async def retention_job_failure_message(self) -> str | None:
        return self._retention_failure


class _FakeAlerts(AlertRepositoryPort):
    def __init__(self) -> None:
        self.open_conditions: set[str] = set()
        self.opened_calls: list[tuple[str, str]] = []
        self.resolved_calls: list[str] = []

    async def has_open_alert(self, condition_name: str) -> bool:
        return condition_name in self.open_conditions

    async def open_alert(self, condition_name: str, message: str) -> None:
        self.open_conditions.add(condition_name)
        self.opened_calls.append((condition_name, message))

    async def resolve_alert(self, condition_name: str) -> None:
        self.open_conditions.discard(condition_name)
        self.resolved_calls.append(condition_name)


class _FakeNotifier(WebhookNotifierPort):
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, datetime]] = []

    async def send(self, condition_name: str, message: str, occurred_at: datetime) -> None:
        self.sent.append((condition_name, message, occurred_at))


async def test_a_healthy_system_opens_and_sends_nothing():
    alerts = _FakeAlerts()
    notifier = _FakeNotifier()
    use_case = RunAlertCheckUseCase(_FakeConditions(), alerts, notifier)

    await use_case.execute()

    assert alerts.opened_calls == []
    assert notifier.sent == []


async def test_a_newly_true_condition_opens_exactly_one_alert_and_sends_one_webhook():
    alerts = _FakeAlerts()
    notifier = _FakeNotifier()
    conditions = _FakeConditions(backup_failure="Backup job failed: disk full")
    use_case = RunAlertCheckUseCase(conditions, alerts, notifier)

    await use_case.execute()

    assert alerts.opened_calls == [("backup_job_failed", "Backup job failed: disk full")]
    assert len(notifier.sent) == 1
    assert notifier.sent[0][0] == "backup_job_failed"


async def test_a_still_true_condition_with_an_open_alert_sends_no_additional_webhook():
    alerts = _FakeAlerts()
    alerts.open_conditions.add("retention_job_failed")
    notifier = _FakeNotifier()
    conditions = _FakeConditions(retention_failure="Retention job failed: timeout")
    use_case = RunAlertCheckUseCase(conditions, alerts, notifier)

    await use_case.execute()

    assert alerts.opened_calls == []
    assert notifier.sent == []


async def test_a_condition_going_from_true_to_false_resolves_its_open_alert():
    alerts = _FakeAlerts()
    alerts.open_conditions.add("score_source_degraded")
    notifier = _FakeNotifier()
    use_case = RunAlertCheckUseCase(_FakeConditions(score_degraded=False), alerts, notifier)

    await use_case.execute()

    assert "score_source_degraded" in alerts.resolved_calls
    assert "score_source_degraded" not in alerts.open_conditions


async def test_all_three_conditions_true_opens_three_alerts_independently():
    alerts = _FakeAlerts()
    notifier = _FakeNotifier()
    conditions = _FakeConditions(
        score_degraded=True,
        backup_failure="Backup job failed: x",
        retention_failure="Retention job failed: y",
    )
    use_case = RunAlertCheckUseCase(conditions, alerts, notifier)

    await use_case.execute()

    assert {c for c, _ in alerts.opened_calls} == {
        "score_source_degraded",
        "backup_job_failed",
        "retention_job_failed",
    }
    assert len(notifier.sent) == 3


async def test_webhook_notifier_with_no_url_configured_makes_no_http_call_and_does_not_raise():
    notifier = HttpxWebhookNotifier(webhook_url="")

    # Must not raise (FR-009) even though no destination is configured.
    await notifier.send("some_condition", "some message", datetime.now())
