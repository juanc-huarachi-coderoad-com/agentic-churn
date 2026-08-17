"""OpenTelemetry tracing setup + the `traced()` helper (specs/011-production-
hardening, User Story 3). Deliberately adapters-only — no `domain`/`application`
ring anywhere in `app.observability` (`research.md` Decision 6): tracing has no
business rule to isolate behind a port, only infrastructure setup, and adding
ports/use-cases here would be exactly the "speculative abstraction layer" P10
already warns against.
"""

import time
from collections.abc import Generator
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.config import settings

_TRACER_NAME = "agentic-churn"


def setup_tracing() -> None:
    """Configures the global OTel `TracerProvider` once, at composition-root
    startup (`app.main`, `app.worker`). FR-012: an empty `otel_exporter_otlp_
    endpoint` means a `ConsoleSpanExporter` (stdout only, no network I/O) —
    this call can never prevent the app from starting, and `BatchSpanProcessor`
    exports asynchronously in a background thread, so even a configured but
    unreachable OTLP endpoint never blocks or fails the calling request."""
    provider = TracerProvider(resource=Resource.create({"service.name": _TRACER_NAME}))
    exporter = (
        OTLPSpanExporter(endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/traces")
        if settings.otel_exporter_otlp_endpoint
        else ConsoleSpanExporter()
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


class TracedSpan:
    """Yielded by `traced()` — lets a caller mark a span `degraded` instead of
    the default `success`, without conflating it with `failure` (FR-011/FR-014:
    a reader that raises and is isolated by `RunReadersUseCase`'s existing
    per-reader failure handling is a recovered, degraded outcome, not the same
    as the whole operation failing)."""

    def __init__(self) -> None:
        self.outcome = "success"

    def mark_degraded(self) -> None:
        self.outcome = "degraded"


@contextmanager
def traced(operation: str) -> Generator[TracedSpan, None, None]:
    """Records one span per call: start time (the span's own start timestamp),
    `duration_ms`, and `outcome` (`success` / `degraded` / `failure`) — the
    three things FR-009 names. Never swallows an exception (FR-012: tracing
    degrades the diagnostic signal, never the product) — `outcome = failure`
    is recorded and the original exception still propagates unchanged."""
    tracer = trace.get_tracer(_TRACER_NAME)
    start = time.monotonic()
    span_state = TracedSpan()
    with tracer.start_as_current_span(operation) as span:
        try:
            yield span_state
        except Exception:
            span.set_attribute("outcome", "failure")
            span.set_attribute("duration_ms", (time.monotonic() - start) * 1000)
            raise
        else:
            span.set_attribute("outcome", span_state.outcome)
            span.set_attribute("duration_ms", (time.monotonic() - start) * 1000)
