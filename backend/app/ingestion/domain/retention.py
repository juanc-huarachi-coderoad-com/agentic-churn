"""Pure retention-window arithmetic (specs/011-production-hardening, FR-001) — no
I/O, no database, matching `business_hours.py`/`hash_chain.py`'s precedent for pure
domain logic in this module.
"""

from datetime import UTC, date, datetime, timedelta


def is_bucket_expired(bucket_id: str, *, retention_window_days: int, now: datetime) -> bool:
    """A bucket is eligible for shredding once its *latest possible* event
    (any moment on `bucket_id`'s own UTC calendar day) is older than the
    retention window — i.e. once a full day has passed since the bucket's own
    day ended. This is the scheduling-margin guarantee spec.md's Edge Cases
    section describes: the job only ever targets a bucket whose entire day has
    already fully elapsed relative to the window, never the current or most
    recently-written one.
    """
    bucket_date = date.fromisoformat(bucket_id)
    bucket_end = datetime.combine(bucket_date, datetime.min.time(), tzinfo=UTC) + timedelta(
        days=1
    )
    return now - bucket_end >= timedelta(days=retention_window_days)
