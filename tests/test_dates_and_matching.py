from datetime import UTC, date, datetime
from decimal import Decimal as D

from jobs.dates import all_days, today_ist, years_before
from jobs.load_prices import match_prices
from jobs.sources.nse import PriceRow


def test_today_ist_crosses_midnight_before_utc():
    # 20:00 UTC on 16 Sep is 01:30 IST on 17 Sep
    assert today_ist(datetime(2026, 9, 16, 20, 0, tzinfo=UTC)) == date(2026, 9, 17)


def test_all_days_includes_weekend():
    # Weekends are downloaded too: NSE sometimes holds a Saturday/Sunday session.
    days = all_days(date(2026, 9, 18), date(2026, 9, 21))  # Fri to Mon
    assert days == [date(2026, 9, 18), date(2026, 9, 19), date(2026, 9, 20), date(2026, 9, 21)]


def test_years_before_leap_day():
    assert years_before(date(2028, 2, 29), 3) == date(2025, 2, 28)
    assert years_before(date(2026, 9, 17), 3) == date(2023, 9, 17)


def _row(symbol, isin, close="100"):
    c = D(close)
    return PriceRow(date(2026, 9, 16), symbol, "EQ", isin, c, c, c, c, c, 10, D("1000"), 1)


def test_match_by_isin_then_symbol():
    rows = [
        _row("AAA", "INE000A01011"),
        _row("NEWNAME", "INE000B01011"),
        _row("ZZZ", "INE999Z01011"),
    ]
    saved, rejected = match_prices(
        rows, isin_map={"INE000A01011": 1}, symbol_map={"NEWNAME": 2, "AAA": 1}
    )
    assert set(saved) == {1, 2}
    assert rejected == 0


def test_isin_match_preferred_over_symbol_match():
    by_symbol = _row("AAA", "INE000X01011", close="50")  # old ISIN, same symbol
    by_isin = _row("AAA-NEW", "INE000A01011", close="100")
    saved, _ = match_prices(
        [by_symbol, by_isin], isin_map={"INE000A01011": 1}, symbol_map={"AAA": 1}
    )
    assert saved[1].close == D("100")


def test_bad_rows_rejected_and_only_ids_filter():
    bad = PriceRow(date(2026, 9, 16), "BAD", "EQ", "INE000C01011",
                   D("10"), D("9"), D("11"), D("10"), None, 1, D("10"), 1)  # fmt: skip
    rows = [bad, _row("AAA", "INE000A01011")]
    saved, rejected = match_prices(
        rows, isin_map={"INE000C01011": 3, "INE000A01011": 1}, symbol_map={}, only_ids={3}
    )
    assert saved == {}
    assert rejected == 1
