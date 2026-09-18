"""The scanners: rules that pick out stocks worth looking at.

Each scanner is a plain function of one day's numbers for one company, so it can be tested
with made-up values and replayed over history. A scanner returns the evidence behind the
trigger (or None), and that evidence is stored with the signal, so the app can always answer
"why did this appear?" without anyone reading the code.

Thresholds live in config/scanners.json, not here, and every signal records which version
of that file produced it.
"""

import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "scanners.json"

Row = dict[str, Any]  # one company's features for one day, plus sector values


def load_config(path: Path = CONFIG_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _has(row: Row, *names: str) -> bool:
    """True when every named value exists (long windows are empty early in a stock's history)."""
    return all(row.get(n) is not None for n in names)


def is_liquid(row: Row, config: dict) -> bool:
    limit = config["liquidity"]["min_value_avg_20"]
    return _has(row, "value_avg_20") and row["value_avg_20"] >= limit


# ---------------------------------------------------------------------------
# Scanners
# ---------------------------------------------------------------------------
def consolidation_breakout(row: Row, config: dict) -> dict | None:
    """Price leaves a long sideways range (the methodology's "bamboo" setup).

    `days_in_range_prev` is yesterday's count, because today's breakout resets it to 0.
    """
    c = config["consolidation_breakout"]
    if not _has(row, "close_adj", "range_high_120", "range_width_120", "volume_ratio_20"):
        return None
    if row.get("days_in_range_prev") is None:
        return None
    if row["close_adj"] <= row["range_high_120"]:
        return None
    if row["days_in_range_prev"] < c["min_days_in_range"]:
        return None
    if row["range_width_120"] > c["max_range_width"]:
        return None
    if row["volume_ratio_20"] < c["min_volume_ratio"]:
        return None
    return {
        "close": row["close_adj"],
        "breakout_level": row["range_high_120"],
        "above_level_pct": (row["close_adj"] - row["range_high_120"]) / row["range_high_120"],
        "days_in_range": row["days_in_range_prev"],
        "range_width": row["range_width_120"],
        "volume_ratio_20": row["volume_ratio_20"],
        "pct_from_high_52w": row.get("pct_from_high_52w"),
    }


def new_high_breakout(row: Row, config: dict) -> dict | None:
    """Price reaches a new 52-week high with the long-term trend rising."""
    c = config["new_high_breakout"]
    if not _has(row, "close_adj", "high_52w", "pct_from_high_52w", "volume_ratio_20"):
        return None
    if row["pct_from_high_52w"] > c["max_pct_from_high_52w"]:
        return None
    if row["volume_ratio_20"] < c["min_volume_ratio"]:
        return None
    if c["require_rising_30w"]:
        if not _has(row, "wma_30w_slope") or row["wma_30w_slope"] <= 0:
            return None
    return {
        "close": row["close_adj"],
        "high_52w": row["high_52w"],
        "pct_from_high_52w": row["pct_from_high_52w"],
        "volume_ratio_20": row["volume_ratio_20"],
        "wma_30w": row.get("wma_30w"),
        "wma_30w_slope": row.get("wma_30w_slope"),
        "rs_rank_63d": row.get("rs_rank_63d"),
    }


def volume_expansion(row: Row, config: dict) -> dict | None:
    """Volume far above its own average: someone is doing something."""
    c = config["volume_expansion"]
    if not _has(row, "volume_ratio_20", "return_1d", "volume_avg_20"):
        return None
    if row["volume_ratio_20"] < c["min_volume_ratio"]:
        return None
    if row["return_1d"] < c["min_return_1d"]:
        return None
    return {
        "close": row.get("close_adj"),
        "volume_ratio_20": row["volume_ratio_20"],
        "volume_avg_20": row["volume_avg_20"],
        "return_1d": row["return_1d"],
        "pct_from_high_52w": row.get("pct_from_high_52w"),
    }


def price_volume_surge(row: Row, config: dict) -> dict | None:
    """Unusual price move on unusual volume — the methodology's first-level screen."""
    c = config["price_volume_surge"]
    if not _has(row, "return_1d", "volume_ratio_20"):
        return None
    if row["return_1d"] < c["min_return_1d"]:
        return None
    if row["volume_ratio_20"] < c["min_volume_ratio"]:
        return None
    return {
        "close": row.get("close_adj"),
        "return_1d": row["return_1d"],
        "volume_ratio_20": row["volume_ratio_20"],
        "pct_from_high_52w": row.get("pct_from_high_52w"),
        "sector": row.get("sector"),
    }


def sector_trend(row: Row, config: dict) -> dict | None:
    """A rising stock whose sector has just taken the lead.

    This is a state that can last for weeks, so it only triggers on the day it becomes
    true - when the sector moves into the leading group, or the stock climbs back above
    its 30-week average. Otherwise every stock in a strong sector would signal every day.
    """
    c = config["sector_trend"]
    if not _has(row, "sector_rank_relative_21d", "sector_relative_21d", "rs_rank_63d"):
        return None
    if row["sector_rank_relative_21d"] < c["min_sector_rank"]:
        return None
    if row["sector_relative_21d"] < c["min_relative_21d"]:
        return None
    if row["rs_rank_63d"] < c["min_rs_rank_63d"]:
        return None
    if c["require_above_30w"]:
        if not _has(row, "close_adj", "wma_30w") or row["close_adj"] <= row["wma_30w"]:
            return None

    # Only on the day it starts: yesterday the sector was not leading, or the stock
    # was not above its 30-week average.
    sector_was_leading = (row.get("sector_rank_relative_21d_prev") or 0) >= c["min_sector_rank"]
    was_above_30w = (row.get("close_adj_prev") or 0) > (row.get("wma_30w_prev") or 0)
    if sector_was_leading and was_above_30w:
        return None

    return {
        "close": row.get("close_adj"),
        "started_because": "sector moved into the lead"
        if not sector_was_leading
        else "price climbed back above its 30-week average",
        "sector": row.get("sector"),
        "sector_index": row.get("sector_index"),
        "sector_return_21d": row.get("sector_return_21d"),
        "sector_relative_21d": row["sector_relative_21d"],
        "sector_rank": row["sector_rank_relative_21d"],
        "rs_rank_63d": row["rs_rank_63d"],
        "wma_30w": row.get("wma_30w"),
    }


SCANNERS = {
    "consolidation_breakout": consolidation_breakout,
    "new_high_breakout": new_high_breakout,
    "volume_expansion": volume_expansion,
    "price_volume_surge": price_volume_surge,
    "sector_trend": sector_trend,
}


def run_all(row: Row, config: dict) -> dict[str, dict]:
    """Run every scanner on one company-day. Returns {scanner name: evidence}."""
    if not is_liquid(row, config):
        return {}
    found = {}
    for name, scanner in SCANNERS.items():
        evidence = scanner(row, config)
        if evidence is not None:
            found[name] = evidence
    return found
