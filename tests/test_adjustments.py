from datetime import date
from decimal import Decimal as D

import pytest

from jobs.adjustments import adjustment_multiplier, parse_action
from jobs.load_corporate_actions import combine, date_chunks
from jobs.sources.nse import parse_corporate_actions

ACTIONS_JSON = """[
 {"symbol":"RELIANCE","isin":"INE002A01018","exDate":"28-Oct-2024","subject":"Bonus 1:1","series":"EQ"},
 {"symbol":"GPIL","isin":"INE177H01013","exDate":"04-Oct-2024",
  "subject":"Face Value Split (Sub-Division) - From Rs 5/- Per Share To Re 1/- Per Share","series":"EQ"},
 {"symbol":"NODATE","isin":"INE111A01011","exDate":"-","subject":"Bonus 1:1","series":"EQ"},
 {"symbol":"NOTINDIA","isin":"IN0020200104","exDate":"01-Jan-2025","subject":"Bonus 1:1","series":"GB"}
]"""


@pytest.mark.parametrize(
    "subject, kind, factor",
    [
        ("Bonus 1:1", "bonus", "0.5"),  # 1 free share per 1 held -> twice the shares
        ("Bonus 1:2", "bonus", "0.66666667"),
        ("Bonus 2:1", "bonus", "0.33333333"),
        ("Bonus 3:5", "bonus", "0.625"),
        ("bonus 1:10", "bonus", "0.90909091"),
        (
            "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Re 1/- Per Share",
            "split",
            "0.1",
        ),
        (
            "Face Value Split (Sub-Division) - From Rs10/- Per Share To Rs 5/- Per Share",
            "split",
            "0.5",
        ),
        (
            "Consolidation Of Equity Shares From Re 1 Per Share To Rs 10 Per Share",
            "consolidation",
            "10",
        ),
    ],
)
def test_actions_that_change_the_share_count(subject, kind, factor):
    action = parse_action(subject)
    assert action is not None
    assert action.kind == kind
    assert action.factor == D(factor)


@pytest.mark.parametrize(
    "subject",
    [
        "Dividend - Rs 6 Per Share",
        "Rights 1:2 @ Premium Re 1/-",
        "Annual General Meeting",
        "Buy Back",
        "Demerger",
        "Bonus Ncrps 1:10",  # preference shares: equity share count does not change
        "Scheme Of Arrangement - Bonus Ncrps 3:1",
    ],
)
def test_actions_that_do_not_change_prices_are_ignored(subject):
    assert parse_action(subject) is None


def test_multiplier_applies_only_before_ex_date():
    factors = [(date(2026, 1, 2), D("0.5")), (date(2026, 6, 2), D("0.5"))]
    assert adjustment_multiplier(date(2026, 1, 1), factors) == D("0.25")  # before both
    assert adjustment_multiplier(date(2026, 3, 1), factors) == D("0.5")  # between
    assert adjustment_multiplier(date(2026, 6, 2), factors) == D("1")  # on/after last ex-date


def test_parse_corporate_actions_keeps_usable_indian_equity_rows():
    rows = parse_corporate_actions(ACTIONS_JSON)
    assert [r.symbol for r in rows] == ["RELIANCE", "GPIL"]  # no missing date, no bond
    assert rows[0].ex_date == date(2024, 10, 28)
    assert rows[0].isin == "INE002A01018"


def test_parse_corporate_actions_survives_bad_json():
    assert parse_corporate_actions("<html>error</html>") == []
    assert parse_corporate_actions('{"message": "no data"}') == []


def test_date_chunks_cover_the_range_without_gaps():
    chunks = date_chunks(date(2024, 1, 1), date(2024, 5, 1), size=60)
    assert chunks[0][0] == date(2024, 1, 1)
    assert chunks[-1][1] == date(2024, 5, 1)
    for (_, end), (next_start, _) in zip(chunks, chunks[1:], strict=False):
        assert (next_start - end).days == 1


def test_two_actions_on_the_same_day_multiply():
    """BAJFINANCE, 16 Jun 2025: bonus 4:1 (x0.2) and split Rs 2 -> Re 1 (x0.5) = x0.1."""
    bonus = parse_action("Bonus 4:1")
    split = parse_action(
        "Face Value Split (Sub-Division) - From Rs 2/- Per Share To Re 1/- Per Share"
    )
    first = combine(None, bonus, "Bonus 4:1")
    both = combine(first, split, "Face Value Split")
    assert first.factor == D("0.2")
    assert first.kind == "bonus"
    assert both.factor == D("0.1")
    assert both.kind == "multiple"
    assert both.description == "Bonus 4:1 + Face Value Split"
