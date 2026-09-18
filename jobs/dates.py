"""Date helpers. Indian markets run on IST (UTC+5:30, no daylight saving)."""

from datetime import UTC, date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), "IST")


def today_ist(now: datetime | None = None) -> date:
    now = now or datetime.now(UTC)
    return now.astimezone(IST).date()


def all_days(start: date, end: date) -> list[date]:
    """Every date from start to end, inclusive.

    Weekends are included on purpose: NSE sometimes trades on a Saturday or Sunday
    (Budget day, Diwali Muhurat session). Days with no trading are recorded as 'no_file'.
    """
    days = []
    d = start
    while d <= end:
        days.append(d)
        d += timedelta(days=1)
    return days


def years_before(day: date, years: int) -> date:
    """Same calendar day `years` earlier (29 Feb becomes 28 Feb)."""
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)
