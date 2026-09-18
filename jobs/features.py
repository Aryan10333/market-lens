"""The technical calculations, as plain functions over a price table.

No database here, so every rule can be tested with a made-up price series.

Input for one company: a pandas DataFrame indexed by trade_date with columns
open, high, low, close, volume, traded_value (raw prices, as published).

FEATURE_VERSION is stored with every row. Change it whenever a calculation changes,
so old and new results can be told apart.
"""

from datetime import date
from decimal import Decimal

import pandas as pd

FEATURE_VERSION = "features_v1"

RETURN_WINDOWS = {"return_1d": 1, "return_5d": 5, "return_21d": 21, "return_63d": 63,
                  "return_252d": 252}  # fmt: skip
SMA_WINDOWS = [20, 50, 100, 200]
WEEKS_52 = 252  # trading days in a year
RANGE_WINDOW = 120  # trading days used for the consolidation range
WEEKLY_MA_WEEKS = 30
WEEKLY_SLOPE_WEEKS = 10
VOLUME_WINDOW = 20
VOLATILITY_WINDOW = 21
TRADING_DAYS_PER_YEAR = 252


def adjust_for_splits(prices: pd.DataFrame, actions: list[tuple[date, Decimal]]) -> pd.DataFrame:
    """Apply split/bonus factors, so prices before an ex-date match today's scale.

    actions: (ex_date, factor) pairs. Prices strictly before an ex-date are multiplied
    by its factor; volume is divided by it (the same money, more shares).
    """
    out = prices.copy()
    if not len(out):
        return out
    multiplier = pd.Series(1.0, index=out.index)
    for ex_date, factor in actions:
        multiplier.loc[out.index < pd.Timestamp(ex_date)] *= float(factor)
    for column in ("open", "high", "low", "close"):
        if column in out:
            out[column] = out[column].astype("float64") * multiplier
    if "volume" in out:
        out["volume"] = out["volume"].astype("float64") / multiplier
    return out


def weekly_bars(prices: pd.DataFrame) -> pd.DataFrame:
    """Turn daily bars into weekly bars (Monday to Sunday).

    A week with no trading produces no row, and a short week (holiday) still counts,
    with trading_days showing how many days it actually had.
    """
    if not len(prices):
        return pd.DataFrame(
            columns=["week_end", "open", "high", "low", "close", "volume", "trading_days"]
        )
    weekly = prices.resample("W-MON", label="left", closed="left").agg(
        week_end=("close", lambda s: s.index[-1].date() if len(s) else None),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        trading_days=("close", "count"),
    )
    return weekly[weekly["trading_days"] > 0]


def _pct_change(series: pd.Series, periods: int) -> pd.Series:
    past = series.shift(periods)
    return (series - past) / past


def build_features(
    prices: pd.DataFrame,
    benchmark_close: pd.Series | None = None,
) -> pd.DataFrame:
    """Calculate every feature for one company. Prices must already be split-adjusted.

    Values are only produced once there is enough history (for example sma_200 stays
    empty until 200 trading days exist), so the numbers are never based on partial windows.
    """
    if not len(prices):
        return pd.DataFrame()

    close = prices["close"].astype("float64")
    volume = prices["volume"].astype("float64")
    out = pd.DataFrame(index=prices.index)
    out["close_adj"] = close
    # Adjusted open/high/low as well, so charts can show candles on the same scale.
    out["open_adj"] = prices["open"].astype("float64")
    out["high_adj"] = prices["high"].astype("float64")
    out["low_adj"] = prices["low"].astype("float64")

    for name, days in RETURN_WINDOWS.items():
        out[name] = _pct_change(close, days)

    for window in SMA_WINDOWS:
        out[f"sma_{window}"] = close.rolling(window).mean()

    # 30-week average: the weekly close average, spread back over the daily rows.
    weekly = weekly_bars(prices)
    if len(weekly):
        weekly_close = weekly["close"].astype("float64")
        wma = weekly_close.rolling(WEEKLY_MA_WEEKS).mean()
        slope = _pct_change(wma, WEEKLY_SLOPE_WEEKS)
        out["wma_30w"] = wma.reindex(out.index, method="ffill")
        out["wma_30w_slope"] = slope.reindex(out.index, method="ffill")
    else:
        out["wma_30w"] = pd.NA
        out["wma_30w_slope"] = pd.NA

    out["volume_avg_20"] = volume.rolling(VOLUME_WINDOW).mean()
    out["volume_ratio_20"] = volume / out["volume_avg_20"]
    out["value_avg_20"] = prices["traded_value"].astype("float64").rolling(VOLUME_WINDOW).mean()

    out["high_52w"] = prices["high"].astype("float64").rolling(WEEKS_52).max()
    out["low_52w"] = prices["low"].astype("float64").rolling(WEEKS_52).min()
    out["pct_from_high_52w"] = (out["high_52w"] - close) / out["high_52w"]
    out["pct_above_low_52w"] = (close - out["low_52w"]) / out["low_52w"]

    daily_returns = close.pct_change()
    out["volatility_21d"] = daily_returns.rolling(VOLATILITY_WINDOW).std() * (
        TRADING_DAYS_PER_YEAR**0.5
    )

    # Consolidation range: the high/low of the last 120 days, ending yesterday, so that
    # "price breaks out of its range" can be judged against a range today did not create.
    range_high = prices["high"].astype("float64").rolling(RANGE_WINDOW).max().shift(1)
    range_low = prices["low"].astype("float64").rolling(RANGE_WINDOW).min().shift(1)
    out["range_high_120"] = range_high
    out["range_low_120"] = range_low
    out["range_width_120"] = (range_high - range_low) / range_low
    out["days_in_range"] = _days_inside_range(close, range_high, range_low)

    if benchmark_close is not None and len(benchmark_close):
        bench = benchmark_close.reindex(out.index).ffill().astype("float64")
        rs = close / bench
        out["rs_ratio"] = rs
        out["rs_change_63d"] = _pct_change(rs, 63)
        out["rs_change_252d"] = _pct_change(rs, 252)
    else:
        out["rs_ratio"] = pd.NA
        out["rs_change_63d"] = pd.NA
        out["rs_change_252d"] = pd.NA

    out["feature_version"] = FEATURE_VERSION
    return out


def _days_inside_range(close: pd.Series, high: pd.Series, low: pd.Series) -> pd.Series:
    """How many days in a row the close has stayed inside the range (0 = it is outside)."""
    inside = (close <= high) & (close >= low)
    counter = 0
    values = []
    for is_inside in inside.to_numpy():
        counter = counter + 1 if is_inside else 0
        values.append(counter)
    return pd.Series(values, index=close.index, dtype="int64")


def build_sector_features(
    sector_closes: dict[str, pd.Series],
    benchmark_close: pd.Series,
) -> pd.DataFrame:
    """How each sector is doing, and how that compares with the benchmark.

    sector_closes: {sector label: closing values of its NSE index}.
    Returns one row per sector and day, with the sector's returns, its return minus the
    benchmark's ("relative"), and a 0-100 rank against the other sectors on that day.
    """
    frames = []
    for sector, closes in sector_closes.items():
        if closes is None or closes.empty:
            continue
        closes = closes.astype("float64").sort_index()
        bench = benchmark_close.reindex(closes.index).ffill().astype("float64")
        frame = pd.DataFrame(index=closes.index)
        frame["sector"] = sector
        frame["close"] = closes
        frame["return_21d"] = _pct_change(closes, 21)
        frame["return_63d"] = _pct_change(closes, 63)
        frame["relative_21d"] = frame["return_21d"] - _pct_change(bench, 21)
        frame["relative_63d"] = frame["return_63d"] - _pct_change(bench, 63)
        frames.append(frame)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames).reset_index(names="trade_date")
    combined["rank_relative_21d"] = (
        combined.groupby("trade_date")["relative_21d"].rank(pct=True) * 100
    )
    combined["feature_version"] = FEATURE_VERSION
    return combined


def rank_within_universe(values: pd.Series) -> pd.Series:
    """Rank one day's values across companies, 0 (worst) to 100 (best)."""
    if values.dropna().empty:
        return pd.Series(pd.NA, index=values.index, dtype="Float64")
    return values.rank(pct=True) * 100
