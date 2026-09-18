"""Stage analysis: which of the four stages a share is in.

From the methodology (Weinstein's framework):

  Stage 1  Basing     - sideways after a fall, the long average flat. Watch, do not buy.
  Stage 2  Advancing  - above a RISING long average, structure intact. The buy zone.
  Stage 3  Topping    - the advance stalls, the average flattens, price whipsaws around it.
  Stage 4  Declining  - below a falling long average, lower highs and lows.

The long average is the 30-week one. The rule the methodology insists on, and that most
people skip: **price being above a moving average is not Stage 2**. Stage 2 also needs the
average to be rising, the stock to be near its highs rather than recovering off the floor,
and it must not be among the weakest stocks in the market.

Every decision returns the checks behind it, so the app can show why, and thresholds live in
config/stages.json with a version.
"""

import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "stages.json"

STAGE_NAMES = {1: "Basing", 2: "Advancing", 3: "Topping", 4: "Declining"}

Row = dict[str, Any]


def load_config(path: Path = CONFIG_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def trend_of(slope: float | None, rising_slope: float) -> str:
    """The 30-week average is rising, falling, or flat."""
    if slope is None:
        return "unknown"
    if slope >= rising_slope:
        return "rising"
    if slope <= -rising_slope:
        return "falling"
    return "flat"


def classify(row: Row, config: dict) -> tuple[int, dict] | None:
    """Decide the stage for one company-day. None when there is not enough history.

    Needs the 30-week average and its slope, which take 40 weeks of prices to produce.
    """
    close = row.get("close_adj")
    wma = row.get("wma_30w")
    slope = row.get("wma_30w_slope")
    if close is None or wma is None or slope is None:
        return None

    trend = trend_of(slope, config["rising_slope"])
    above = close > wma
    from_high = row.get("pct_from_high_52w")
    above_low = row.get("pct_above_low_52w")
    rs_rank = row.get("rs_rank_63d")
    days_in_range = row.get("days_in_range") or 0

    checks = {
        "price_vs_30w": "above" if above else "below",
        "30w_trend": trend,
        "pct_from_high_52w": from_high,
        "pct_above_low_52w": above_low,
        "rs_rank_63d": rs_rank,
        "days_in_range": days_in_range,
    }

    s2, s1 = config["stage2"], config["stage1"]

    # Stage 2: above a rising average, near the highs, not the weakest.
    near_high = from_high is not None and from_high <= s2["max_pct_from_high_52w"]
    strong_enough = rs_rank is None or rs_rank >= s2["min_rs_rank_63d"]
    if above and trend == "rising" and near_high and strong_enough:
        return 2, {**checks, "why": "Above a rising 30-week average, close to its 52-week high"}

    # Stage 4: below a falling average.
    if not above and trend == "falling":
        return 4, {**checks, "why": "Below a falling 30-week average"}

    # Stage 3: the advance has stalled.
    if above and trend != "rising":
        return 3, {**checks, "why": f"Above the 30-week average but the average is {trend}"}
    if above and trend == "rising" and not near_high:
        return 3, {**checks, "why": "Rising average, but price has fallen well below its high"}
    if not above and trend == "rising":
        # A share can only be declining once the long trend turns down.
        return 3, {**checks, "why": "Price slipped below a still-rising 30-week average"}

    # Stage 1: flat average, price in a range near the lows.
    quiet = days_in_range >= s1["min_days_in_range"]
    near_lows = above_low is not None and above_low <= s1["max_pct_above_low_52w"]
    if trend == "flat" and (quiet or near_lows):
        return 1, {**checks, "why": "Flat 30-week average with price in a range near its lows"}

    # Anything left is still weak: below a flat or falling average, with no base yet.
    if not above:
        return 4, {**checks, "why": "Below the 30-week average without a base"}
    return 3, {**checks, "why": "Advance has stalled"}


def confirm_changes(raw_stages: list[int | None], confirm_days: int) -> list[int | None]:
    """Smooth day-to-day flipping: a new stage must hold for `confirm_days` days.

    A share wobbling around its 30-week average would otherwise change stage every few
    days, which says nothing useful. The change is dated to the day it is confirmed.
    """
    out: list[int | None] = []
    current: int | None = None
    pending: int | None = None
    run = 0

    for stage in raw_stages:
        if stage is None:
            out.append(None)
            continue
        if current is None:
            current, pending, run = stage, None, 0
        elif stage == current:
            pending, run = None, 0
        else:
            run = run + 1 if stage == pending else 1
            pending = stage
            if run >= confirm_days:
                current, pending, run = stage, None, 0
        out.append(current)
    return out
