"""Production calendar — workdays, shifts, holidays."""

from __future__ import annotations

from datetime import date, timedelta


def workdays_between(start: date, end: date, holidays: list[date] | None = None) -> int:
    """Count workdays (Mon-Fri) between two dates, excluding holidays."""
    holidays_set = set(holidays or [])
    count = 0
    d = start
    while d < end:
        if d.weekday() < 5 and d not in holidays_set:
            count += 1
        d += timedelta(days=1)
    return count


def add_workdays(start: date, days: int, holidays: list[date] | None = None) -> date:
    """Add N workdays to a start date."""
    holidays_set = set(holidays or [])
    d = start
    added = 0
    while added < days:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in holidays_set:
            added += 1
    return d


def shift_hours_per_day(shifts: int = 1, hours_per_shift: float = 8.0) -> float:
    """Available production hours per day."""
    return shifts * hours_per_shift


def available_hours_in_period(
    start: date,
    end: date,
    shifts: int = 1,
    hours_per_shift: float = 8.0,
    efficiency: float = 0.85,
    holidays: list[date] | None = None,
) -> float:
    """Total available production hours in a period, adjusted for efficiency."""
    days = workdays_between(start, end, holidays)
    return days * shifts * hours_per_shift * efficiency
