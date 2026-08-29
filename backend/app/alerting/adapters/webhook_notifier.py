"""`HttpxWebhookNotifier` (specs/031-production-deployment-hardening-ii, research.md
Decision 3) — a plain JSON POST to a configured URL, genuinely provider-agnostic (a Slack
incoming webhook, PagerDuty, or any endpoint that accepts JSON all work identically; this
adapter has no vendor-specific knowledge). Same honest-empty-default discipline as every
other secret in `config.py`: an unset `alert_webhook_url` degrades to logging only, never a
crash (FR-009) — the alert-check job must keep running even for a deployment that hasn't
configured a destination yet.
"""

import logging
from datetime import datetime

import httpx

from app.alerting.application.ports import WebhookNotifierPort

logger = logging.getLogger(__name__)


class HttpxWebhookNotifier(WebhookNotifierPort):
    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url

    async def send(self, condition_name: str, message: str, occurred_at: datetime) -> None:
        if not self._webhook_url:
            logger.warning(
                "alert condition %s fired but no alert_webhook_url is configured: %s",
                condition_name,
                message,
            )
            return

        payload = {
            "condition": condition_name,
            "message": message,
            "occurred_at": occurred_at.isoformat(),
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self._webhook_url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError:
            # A broken/unreachable notification channel must never crash the
            # alert-check job (FR-009's edge case) — the condition itself was
            # already recorded in `alerts` by the caller before this method runs.
            logger.exception(
                "failed to deliver alert webhook for condition %s", condition_name
            )
