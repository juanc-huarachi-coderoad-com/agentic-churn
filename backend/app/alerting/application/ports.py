"""Ports the alerting application layer depends on — implemented by
`app.alerting.adapters.*`. Application depends on these, never on a concrete adapter
(constitution P8, Dependency Inversion), enforced mechanically by `.importlinter`
(`app.alerting` is registered in the `global-dependency-rule` contract's `containers`
list, specs/031-production-deployment-hardening-ii).
"""

from abc import ABC, abstractmethod
from datetime import datetime


class AlertConditionReaderPort(ABC):
    """Reads the three fixed, real conditions `RunAlertCheckUseCase` evaluates
    (`research.md` Decision 3 — no dynamic/pluggable condition registry, P10). Each
    method reflects the *current* state (the latest run of the thing it checks), not a
    historical log — `RunAlertCheckUseCase` re-derives truth fresh every cycle rather
    than tracking "was it true when alert X fired." Implemented by
    `SqlAlchemyAlertConditionReader`, which reads `score_runs` (owned by `app.scoring`)
    and `backup_job_runs`/`retention_job_runs` (owned by `app.ingestion`) directly via
    SQL — the same "read another module's table via your own adapter, never by
    importing that module's repository classes" shape `app.narrator`'s own
    `SqlAlchemyScoreContextRepository` already established."""

    @abstractmethod
    async def is_score_source_degraded(self) -> bool:
        """True iff the most recent `score_runs` row has `source_degraded = true`.
        `False` (not an error) if no score run exists yet."""
        ...

    @abstractmethod
    async def backup_job_failure_message(self) -> str | None:
        """A human-readable message iff the most recent `backup_job_runs` row has
        `status = 'failed'`; `None` otherwise (including "no backup has run yet" —
        that's a different, not-yet-implemented concern, not a failure to alert on)."""
        ...

    @abstractmethod
    async def retention_job_failure_message(self) -> str | None:
        """Same shape as `backup_job_failure_message`, for `retention_job_runs`."""
        ...


class AlertRepositoryPort(ABC):
    """The `alerts` table's own port — `has_open_alert`/`open_alert`/`resolve_alert`
    together implement FR-010's de-duplication, backed by the table's own
    `alerts_one_open_per_condition` partial unique index (`data-model.md`) so the
    invariant holds even if this port's own read-then-write isn't perfectly atomic."""

    @abstractmethod
    async def has_open_alert(self, condition_name: str) -> bool: ...

    @abstractmethod
    async def open_alert(self, condition_name: str, message: str) -> None:
        """Inserts a new open `alerts` row. Caller's responsibility to have already
        checked `has_open_alert` is `False` — the DB constraint is the real backstop,
        not a substitute for this check (avoids a needless failed-insert-and-ignore
        pattern on the far more common "still open" path)."""
        ...

    @abstractmethod
    async def resolve_alert(self, condition_name: str) -> None:
        """Marks any open `alerts` row for `condition_name` resolved. Idempotent — a
        no-op if none is open, so the caller never needs to check first."""
        ...


class WebhookNotifierPort(ABC):
    @abstractmethod
    async def send(self, condition_name: str, message: str, occurred_at: datetime) -> None:
        """POSTs the three-field payload (`research.md` Decision 3) to whatever
        destination this deployment is configured with. Implementations MUST NOT raise
        when no destination is configured (FR-009) — log and return instead; a broken
        or unconfigured notification channel must never crash the alert-check job."""
        ...
