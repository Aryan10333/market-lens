from datetime import date
from decimal import Decimal as D

import pandas as pd
import pytest

from jobs.features import (
    adjust_for_splits,
    build_features,
    rank_within_universe,
    weekly_bars,
)


def make_prices(closes, start="2024-01-01", volumes=None, highs=None, lows=None):
    """Daily bars on consecutive weekdays, with sensible defaults."""
    days = pd.bdate_range(start=start, periods=len(closes))
    volumes = volumes or [1000] * len(closes)
    return pd.DataFrame(
        {
            "open": closes,
            "high": highs or [c * 1.01 for c in closes],
            "low": lows or [c * 0.99 for c in closes],
            "close": closes,
            "volume": volumes,
            "traded_value": [c * v for c, v in zip(closes, volumes, strict=True)],
        },
        index=days,
    )


# ---------------------------------------------------------------------------
# Split adjustment
# ---------------------------------------------------------------------------
def test_prices_before_ex_date_are_scaled_and_volume_grows():
    prices = make_prices([1000, 1000, 500, 500])
    out = adjust_for_splits(prices, [(date(2024, 1, 3), D("0.5"))])  # 1:1 bonus
    assert list(out["close"]) == [500, 500, 500, 500]
    assert list(out["volume"]) == [2000, 2000, 1000, 1000]  # same money, twice the shares


def test_two_splits_multiply():
    prices = make_prices([400, 200, 100])
    out = adjust_for_splits(prices, [(date(2024, 1, 2), D("0.5")), (date(2024, 1, 3), D("0.5"))])
    assert list(out["close"]) == [100, 100, 100]


def test_no_actions_leaves_prices_alone():
    prices = make_prices([100, 101])
    assert list(adjust_for_splits(prices, [])["close"]) == [100, 101]


# ---------------------------------------------------------------------------
# Weekly bars
# ---------------------------------------------------------------------------
def test_weekly_bars_group_by_week():
    # 1 Jan 2024 is a Monday: two full weeks of 5 trading days.
    prices = make_prices(list(range(100, 110)))
    weekly = weekly_bars(prices)
    assert len(weekly) == 2
    assert list(weekly["trading_days"]) == [5, 5]
    assert weekly.iloc[0]["open"] == 100
    assert weekly.iloc[0]["close"] == 104  # Friday's close
    assert weekly.iloc[1]["close"] == 109
    assert weekly.iloc[0]["week_end"] == date(2024, 1, 5)


def test_short_week_is_kept_with_its_day_count():
    prices = make_prices([100, 101, 102])  # Mon-Wed only
    weekly = weekly_bars(prices)
    assert len(weekly) == 1
    assert weekly.iloc[0]["trading_days"] == 3


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------
def test_returns_and_moving_averages():
    closes = [100] * 19 + [110]  # flat, then +10% on the last day
    features = build_features(make_prices(closes))
    last = features.iloc[-1]
    assert last["return_1d"] == pytest.approx(0.10)
    assert last["sma_20"] == pytest.approx((100 * 19 + 110) / 20)
    assert pd.isna(features.iloc[-2]["sma_20"])  # only 19 days of history yet
    assert pd.isna(last["sma_50"])  # not enough history: stays empty


def test_volume_ratio_compares_with_its_own_average():
    volumes = [1000] * 19 + [3000]
    features = build_features(make_prices([100] * 20, volumes=volumes))
    last = features.iloc[-1]
    assert last["volume_avg_20"] == pytest.approx(1100)
    assert last["volume_ratio_20"] == pytest.approx(3000 / 1100)


def test_52_week_levels_and_distance():
    closes = [100] * 251 + [150]
    features = build_features(make_prices(closes))
    last = features.iloc[-1]
    assert last["high_52w"] == pytest.approx(151.5)  # highs are 1% above close
    assert last["low_52w"] == pytest.approx(99.0)
    assert last["pct_from_high_52w"] == pytest.approx((151.5 - 150) / 151.5)
    assert last["pct_above_low_52w"] == pytest.approx((150 - 99) / 99)


def test_consolidation_range_excludes_today_and_counts_days_inside():
    closes = [100] * 130 + [200]  # long flat stretch, then a jump out of it
    features = build_features(make_prices(closes))
    last = features.iloc[-1]
    assert last["range_high_120"] == pytest.approx(101.0)  # range built before today
    assert last["range_low_120"] == pytest.approx(99.0)
    assert last["range_width_120"] == pytest.approx((101.0 - 99.0) / 99.0)
    assert last["days_in_range"] == 0  # today's close broke out
    assert features.iloc[-2]["days_in_range"] > 0


def test_30_week_average_and_slope_need_30_weeks():
    prices = make_prices([100] * 200)  # 40 weeks
    features = build_features(prices)
    assert features.iloc[-1]["wma_30w"] == pytest.approx(100)
    assert features.iloc[-1]["wma_30w_slope"] == pytest.approx(0)
    assert pd.isna(features.iloc[20]["wma_30w"])  # only 5 weeks in


def test_rising_prices_give_a_rising_30_week_average():
    prices = make_prices([100 + i for i in range(220)])
    last = build_features(prices).iloc[-1]
    assert last["wma_30w_slope"] > 0
    assert last["close_adj"] > last["wma_30w"]


def test_relative_strength_against_benchmark():
    days = pd.bdate_range(start="2024-01-01", periods=70)
    prices = make_prices([100 + i for i in range(70)])  # rising
    benchmark = pd.Series([1000] * 70, index=days)  # flat
    last = build_features(prices, benchmark).iloc[-1]
    assert last["rs_ratio"] == pytest.approx(169 / 1000)
    assert last["rs_change_63d"] > 0  # beating a flat market


def test_features_are_stamped_with_a_version():
    features = build_features(make_prices([100] * 5))
    assert set(features["feature_version"]) == {"features_v1"}


def test_empty_input_gives_empty_output():
    empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume", "traded_value"])
    assert build_features(empty).empty
    assert weekly_bars(empty).empty


def test_rank_within_universe():
    ranks = rank_within_universe(pd.Series([1.0, 2.0, 3.0, 4.0]))
    assert list(ranks) == [25.0, 50.0, 75.0, 100.0]
