from jobs.stages import STAGE_NAMES, classify, confirm_changes, load_config, trend_of

CONFIG = load_config()


def row(**values):
    """A company-day, with a healthy advancing stock as the starting point."""
    base = {
        "close_adj": 120.0,
        "wma_30w": 100.0,
        "wma_30w_slope": 0.08,  # average up 8% over 10 weeks: rising
        "pct_from_high_52w": 0.05,
        "pct_above_low_52w": 0.60,
        "rs_rank_63d": 70.0,
        "days_in_range": 0,
    }
    return {**base, **values}


def stage_of(**values):
    result = classify(row(**values), CONFIG)
    return result[0] if result else None


# ---------------------------------------------------------------------------
# The rule the methodology insists on
# ---------------------------------------------------------------------------
def test_above_the_average_alone_is_not_stage_2():
    """The methodology is explicit: price above a moving average is not Stage 2."""
    assert stage_of(wma_30w_slope=0.0) != 2  # flat average
    assert stage_of(pct_from_high_52w=0.40) != 2  # far below its high
    assert stage_of(rs_rank_63d=10.0) != 2  # among the weakest stocks


def test_stage_2_needs_everything_together():
    assert stage_of() == 2
    evidence = classify(row(), CONFIG)[1]
    assert evidence["price_vs_30w"] == "above"
    assert evidence["30w_trend"] == "rising"
    assert "rising" in evidence["why"]


# ---------------------------------------------------------------------------
# The other stages
# ---------------------------------------------------------------------------
def test_stage_4_is_below_a_falling_average():
    assert stage_of(close_adj=80.0, wma_30w=100.0, wma_30w_slope=-0.10) == 4


def test_stage_3_when_the_advance_stalls():
    # Still above the average, but the average has flattened.
    assert stage_of(wma_30w_slope=0.0, pct_from_high_52w=0.12) == 3
    # Or price has slipped below an average that is still rising.
    assert stage_of(close_adj=95.0, wma_30w=100.0, pct_from_high_52w=0.15) == 3


def test_below_a_rising_average_is_topping_not_declining():
    """A share can only be declining once the long-term trend itself turns down."""
    assert stage_of(close_adj=95.0, wma_30w=100.0, wma_30w_slope=0.06) == 3
    # ...even for a recent listing with no 52-week high yet.
    assert stage_of(close_adj=95.0, wma_30w=100.0, wma_30w_slope=0.06, pct_from_high_52w=None) == 3


def test_stage_1_is_a_quiet_base_near_the_lows():
    assert (
        stage_of(
            close_adj=98.0,
            wma_30w=100.0,
            wma_30w_slope=0.0,
            pct_from_high_52w=0.45,
            pct_above_low_52w=0.08,
            days_in_range=90,
        )
        == 1
    )


def test_a_falling_stock_without_a_base_stays_stage_4():
    assert (
        stage_of(
            close_adj=90.0,
            wma_30w=100.0,
            wma_30w_slope=-0.01,  # flat-ish but no base
            pct_above_low_52w=0.80,
            days_in_range=2,
        )
        == 4
    )


# ---------------------------------------------------------------------------
# Trend and missing data
# ---------------------------------------------------------------------------
def test_trend_boundaries():
    limit = CONFIG["rising_slope"]
    assert trend_of(limit, limit) == "rising"
    assert trend_of(limit - 0.001, limit) == "flat"
    assert trend_of(-limit, limit) == "falling"
    assert trend_of(None, limit) == "unknown"


def test_no_stage_without_a_30_week_average():
    assert classify(row(wma_30w=None), CONFIG) is None
    assert classify(row(wma_30w_slope=None), CONFIG) is None


def test_every_stage_has_a_name():
    assert set(STAGE_NAMES) == {1, 2, 3, 4}


def test_evidence_always_explains_itself():
    for values in [{}, {"wma_30w_slope": 0.0}, {"close_adj": 50.0, "wma_30w_slope": -0.2}]:
        stage, evidence = classify(row(**values), CONFIG)
        assert stage in STAGE_NAMES
        assert evidence["why"]
        assert evidence["30w_trend"] in ("rising", "falling", "flat")


# ---------------------------------------------------------------------------
# Confirming a change (stops day-to-day flipping)
# ---------------------------------------------------------------------------
def test_a_one_day_wobble_does_not_change_the_stage():
    raw = [2, 2, 2, 3, 2, 2, 2]
    assert confirm_changes(raw, 5) == [2, 2, 2, 2, 2, 2, 2]


def test_a_change_that_holds_is_accepted_on_the_fifth_day():
    raw = [2, 2, 3, 3, 3, 3, 3, 3]
    assert confirm_changes(raw, 5) == [2, 2, 2, 2, 2, 2, 3, 3]


def test_flip_flopping_never_confirms_a_change():
    raw = [2, 3, 2, 3, 2, 3, 2, 3]
    assert set(confirm_changes(raw, 5)) == {2}


def test_the_first_stage_is_taken_straight_away():
    assert confirm_changes([4, 4, 4], 5) == [4, 4, 4]


def test_days_without_a_stage_stay_empty():
    assert confirm_changes([None, None, 2, 2], 5) == [None, None, 2, 2]
