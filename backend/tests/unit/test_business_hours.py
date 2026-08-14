"""REQ-M2-05 — matches data-model.md's exact worked numbers: 19.0h `open_overdue` for
ticket #456, 2.0h `resolved` for ticket #398, and 4.0h for the Friday-to-Monday
weekend-boundary case (H2 remediation, SC-003)."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.ingestion.domain.business_hours import WorkingCalendar, compute_business_hours_elapsed

_CALENDAR = WorkingCalendar(
    working_hours_start=time(8, 0),
    working_hours_end=time(18, 0),
    timezone=ZoneInfo("America/Bogota"),
)


def test_ticket_398_two_hours_same_day():
    created = datetime.fromisoformat("2026-08-11T11:02:00-05:00")
    resolved = datetime.fromisoformat("2026-08-11T13:02:00-05:00")

    assert compute_business_hours_elapsed(created, resolved, _CALENDAR) == 2.0


def test_ticket_456_nineteen_hours_open_overdue():
    reopened = datetime.fromisoformat("2026-08-10T07:40:00-05:00")
    as_of = datetime.fromisoformat("2026-08-11T17:00:00-05:00")

    assert compute_business_hours_elapsed(reopened, as_of, _CALENDAR) == 19.0


def test_weekend_boundary_skips_saturday_and_sunday():
    friday_afternoon = datetime.fromisoformat("2026-08-14T16:00:00-05:00")
    monday_morning = datetime.fromisoformat("2026-08-17T10:00:00-05:00")

    assert compute_business_hours_elapsed(friday_afternoon, monday_morning, _CALENDAR) == 4.0


def test_as_of_before_start_is_zero():
    start = datetime.fromisoformat("2026-08-11T13:00:00-05:00")
    as_of = datetime.fromisoformat("2026-08-11T09:00:00-05:00")

    assert compute_business_hours_elapsed(start, as_of, _CALENDAR) == 0.0
