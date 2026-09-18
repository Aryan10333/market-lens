import pytest

from jobs.scanners import SCANNERS, is_liquid, load_config, run_all

CONFIG = load_config()

LIQUID = {"value_avg_20": 50_000_000}  # Rs 5 crore a day: comfortably above the limit


def row(**values):
    """A company-day with everything the scanners look at, overridden as needed."""
    base = {
        "close_adj": 100.0,
        "return_1d": 0.0,
        "volume_ratio_20": 1.0,
        "volume_avg_20": 100000.0,
        "high_52w": 150.0,
        "pct_from_high_52w": 0.30,
        "wma_30w": 95.0,
        "wma_30w_slope": 0.01,
        "range_high_120": 105.0,
        "range_width_120": 0.20,
        "days_in_range_prev": 100,
        "rs_rank_63d": 60.0,
        "sector": "Information Technology",
        "sector_index": "Nifty IT",
        "sector_return_21d": 0.05,
        "sector_relative_21d": 0.02,
        "sector_rank_relative_21d": 90.0,
        # yesterday: sector was not yet leading, so today is the first day
        "sector_rank_relative_21d_prev": 40.0,
        "close_adj_prev": 99.0,
        "wma_30w_prev": 95.0,
    }
    return {**base, **LIQUID, **values}


# ---------------------------------------------------------------------------
# Liquidity gate
# ---------------------------------------------------------------------------
def test_thin_stocks_are_skipped_by_every_scanner():
    thin = row(value_avg_20=100_000, return_1d=0.10, volume_ratio_20=10.0)
    assert not is_liquid(thin, CONFIG)
    assert run_all(thin, CONFIG) == {}


def test_missing_liquidity_value_is_not_liquid():
    assert not is_liquid(row(value_avg_20=None), CONFIG)


# ---------------------------------------------------------------------------
# Consolidation breakout
# ---------------------------------------------------------------------------
def test_consolidation_breakout_triggers_above_the_range_on_volume():
    hit = SCANNERS["consolidation_breakout"](
        row(close_adj=110.0, range_high_120=105.0, volume_ratio_20=2.0), CONFIG
    )
    assert hit is not None
    assert hit["breakout_level"] == 105.0
    assert hit["above_level_pct"] == pytest.approx((110 - 105) / 105)
    assert hit["days_in_range"] == 100


def test_no_breakout_when_price_stays_inside_the_range():
    assert (
        SCANNERS["consolidation_breakout"](row(close_adj=104.0, volume_ratio_20=2.0), CONFIG)
        is None
    )


def test_no_breakout_without_a_long_enough_range():
    assert (
        SCANNERS["consolidation_breakout"](
            row(close_adj=110.0, volume_ratio_20=2.0, days_in_range_prev=20), CONFIG
        )
        is None
    )


def test_no_breakout_on_quiet_volume():
    assert (
        SCANNERS["consolidation_breakout"](row(close_adj=110.0, volume_ratio_20=1.0), CONFIG)
        is None
    )


def test_no_breakout_when_the_range_is_too_wide_to_be_a_consolidation():
    assert (
        SCANNERS["consolidation_breakout"](
            row(close_adj=110.0, volume_ratio_20=2.0, range_width_120=1.5), CONFIG
        )
        is None
    )


# ---------------------------------------------------------------------------
# New high breakout
# ---------------------------------------------------------------------------
def test_new_high_triggers_at_the_52_week_high():
    hit = SCANNERS["new_high_breakout"](
        row(close_adj=150.0, pct_from_high_52w=0.0, volume_ratio_20=1.5), CONFIG
    )
    assert hit is not None
    assert hit["high_52w"] == 150.0


def test_no_new_high_when_price_is_well_below_it():
    assert (
        SCANNERS["new_high_breakout"](row(pct_from_high_52w=0.05, volume_ratio_20=2.0), CONFIG)
        is None
    )


def test_no_new_high_when_the_long_term_trend_is_falling():
    # The methodology is explicit: being near a high is not enough, the trend must be rising.
    assert (
        SCANNERS["new_high_breakout"](
            row(pct_from_high_52w=0.0, volume_ratio_20=2.0, wma_30w_slope=-0.05), CONFIG
        )
        is None
    )


# ---------------------------------------------------------------------------
# Volume expansion and price+volume surge
# ---------------------------------------------------------------------------
def test_volume_expansion_needs_three_times_normal_volume():
    assert SCANNERS["volume_expansion"](row(volume_ratio_20=3.5), CONFIG) is not None
    assert SCANNERS["volume_expansion"](row(volume_ratio_20=2.5), CONFIG) is None


def test_volume_expansion_ignores_falling_prices():
    assert SCANNERS["volume_expansion"](row(volume_ratio_20=5.0, return_1d=-0.02), CONFIG) is None


def test_price_volume_surge_needs_both_price_and_volume():
    assert (
        SCANNERS["price_volume_surge"](row(return_1d=0.05, volume_ratio_20=2.5), CONFIG) is not None
    )
    assert SCANNERS["price_volume_surge"](row(return_1d=0.05, volume_ratio_20=1.2), CONFIG) is None
    assert SCANNERS["price_volume_surge"](row(return_1d=0.02, volume_ratio_20=3.0), CONFIG) is None


# ---------------------------------------------------------------------------
# Sector trend
# ---------------------------------------------------------------------------
def test_sector_trend_needs_a_leading_sector_and_a_rising_stock():
    hit = SCANNERS["sector_trend"](row(), CONFIG)
    assert hit is not None
    assert hit["sector_index"] == "Nifty IT"


def test_no_sector_trend_when_the_sector_lags():
    assert SCANNERS["sector_trend"](row(sector_rank_relative_21d=40.0), CONFIG) is None
    assert SCANNERS["sector_trend"](row(sector_relative_21d=-0.03), CONFIG) is None


def test_sector_trend_only_fires_on_the_day_it_becomes_true():
    """A stock in an already-leading sector, already above its average, is not news."""
    continuing = row(sector_rank_relative_21d_prev=90.0, close_adj_prev=99.0, wma_30w_prev=95.0)
    assert SCANNERS["sector_trend"](continuing, CONFIG) is None

    # ...but the day the stock climbs back above its 30-week average, it triggers.
    crossed_back = row(sector_rank_relative_21d_prev=90.0, close_adj_prev=94.0, wma_30w_prev=95.0)
    hit = SCANNERS["sector_trend"](crossed_back, CONFIG)
    assert hit is not None
    assert hit["started_because"] == "price climbed back above its 30-week average"


def test_sector_trend_reason_when_the_sector_takes_the_lead():
    hit = SCANNERS["sector_trend"](row(), CONFIG)
    assert hit["started_because"] == "sector moved into the lead"


def test_no_sector_trend_when_the_stock_is_below_its_30_week_average():
    assert SCANNERS["sector_trend"](row(close_adj=90.0, wma_30w=95.0), CONFIG) is None


def test_sectors_without_an_index_are_skipped():
    no_sector = row(sector_rank_relative_21d=None, sector_relative_21d=None)
    assert SCANNERS["sector_trend"](no_sector, CONFIG) is None


# ---------------------------------------------------------------------------
# Missing history
# ---------------------------------------------------------------------------
def test_young_stocks_without_long_windows_trigger_nothing():
    young = row(
        high_52w=None, pct_from_high_52w=None, wma_30w=None, wma_30w_slope=None,
        range_high_120=None, range_width_120=None, days_in_range_prev=None,
        rs_rank_63d=None, sector_rank_relative_21d=None, sector_relative_21d=None,
    )  # fmt: skip
    assert run_all(young, CONFIG) == {}


def test_run_all_can_return_several_scanners_at_once():
    strong = row(
        close_adj=150.0, pct_from_high_52w=0.0, return_1d=0.06, volume_ratio_20=4.0,
        range_high_120=140.0,
    )  # fmt: skip
    assert set(run_all(strong, CONFIG)) >= {
        "new_high_breakout",
        "volume_expansion",
        "price_volume_surge",
        "consolidation_breakout",
    }


def test_config_has_a_version_and_every_scanner():
    assert CONFIG["version"].startswith("scanner_v")
    for name in SCANNERS:
        assert name in CONFIG, f"config/scanners.json has no thresholds for {name}"
