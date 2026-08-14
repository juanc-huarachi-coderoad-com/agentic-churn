"""Elapsed-business-hours calculator (REQ-M2-05) — a hand-rolled pure function, not a
general-purpose business-calendar library (research.md's YAGNI decision: the client
profile schema has no holiday-calendar field to drive one).
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

_WEEKEND = frozenset({5, 6})  # Saturday, Sunday (date.weekday())


@dataclass(frozen=True)
class WorkingCalendar:
    working_hours_start: time
    working_hours_end: time
    timezone: ZoneInfo


def _day_window(day: date, calendar: WorkingCalendar) -> tuple[datetime, datetime]:
    start = datetime.combine(day, calendar.working_hours_start, tzinfo=calendar.timezone)
    end = datetime.combine(day, calendar.working_hours_end, tzinfo=calendar.timezone)
    return start, end


def compute_business_hours_elapsed(
    start: datetime, as_of: datetime, calendar: WorkingCalendar
) -> float:
    """Elapsed business hours between `start` and `as_of`, skipping weekends entirely
    and clipping each day to the working-hours window. `as_of` is an explicit
    parameter, not `datetime.now()` — a still-open response pair's elapsed-so-far
    figure is "now" relative to whenever this is called, so passing it in keeps the
    calculation deterministic and testable (research.md).
    """
    if as_of <= start:
        return 0.0

    start_local = start.astimezone(calendar.timezone)
    as_of_local = as_of.astimezone(calendar.timezone)

    total = timedelta()
    day = start_local.date()
    end_date = as_of_local.date()

    while day <= end_date:
        if day.weekday() not in _WEEKEND:
            window_start, window_end = _day_window(day, calendar)
            segment_start = start_local if day == start_local.date() else window_start
            segment_end = as_of_local if day == end_date else window_end
            segment_start = max(segment_start, window_start)
            segment_end = min(segment_end, window_end)
            if segment_end > segment_start:
                total += segment_end - segment_start
        day += timedelta(days=1)

    return round(total.total_seconds() / 3600, 2)
