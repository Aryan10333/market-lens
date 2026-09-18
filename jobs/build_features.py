"""Calculates weekly bars and technical features for every company in the universe.

Reads raw prices + corporate actions, applies split adjustment, runs the calculations in
jobs/features.py, and writes weekly_prices and daily_features.

By default only days newer than what is already stored are written (the calculations still
run over the full history, because a 200-day average needs 200 days of past prices).
Use --rebuild after changing a calculation.

Run:
  .venv\\Scripts\\python -m jobs.build_features
  .venv\\Scripts\\python -m jobs.build_features --rebuild
"""

import argparse
import logging
import sys
from datetime import date

import pandas as pd

from jobs.config import ConfigError, load_settings
from jobs.db import connect
from jobs.features import FEATURE_VERSION, adjust_for_splits, build_features, rank_within_universe
from jobs.features import weekly_bars as to_weekly
from jobs.log import setup_logging
from jobs.runs import JobRun
from jobs.sync_universe import UNIVERSE

log = logging.getLogger("build_features")

BENCHMARK = "Nifty 500"

FEATURE_COLUMNS = [
    "close_adj", "return_1d", "return_5d", "return_21d", "return_63d", "return_252d",
    "sma_20", "sma_50", "sma_100", "sma_200", "wma_30w", "wma_30w_slope",
    "volume_avg_20", "volume_ratio_20", "value_avg_20",
    "high_52w", "low_52w", "pct_from_high_52w", "pct_above_low_52w", "volatility_21d",
    "range_high_120", "range_low_120", "range_width_120", "days_in_range",
    "rs_ratio", "rs_change_63d", "rs_change_252d", "rs_rank_63d",
]  # fmt: skip

UPSERT_FEATURES = f"""
insert into public.daily_features
  (company_id, trade_date, feature_version, {", ".join(FEATURE_COLUMNS)}, calculated_at)
values ({", ".join(["%s"] * (len(FEATURE_COLUMNS) + 3))}, now())
on conflict (company_id, trade_date) do update set
  feature_version = excluded.feature_version, calculated_at = now(),
  {", ".join(f"{c} = excluded.{c}" for c in FEATURE_COLUMNS)}
"""

UPSERT_WEEKLY = """
insert into public.weekly_prices
  (company_id, week_start, week_end, open, high, low, close, volume, trading_days)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict (company_id, week_start) do update set
  week_end = excluded.week_end, open = excluded.open, high = excluded.high,
  low = excluded.low, close = excluded.close, volume = excluded.volume,
  trading_days = excluded.trading_days
"""


def clean(value):
    """Turn pandas values into something psycopg can store (NaN/NaT -> None)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    return value


def load_inputs(conn):
    """Read prices, corporate actions and the benchmark from the database."""
    companies = conn.execute(
        "select c.id, c.nse_symbol from public.companies c "
        "join public.universe_members u on u.company_id = c.id "
        "where u.universe = %s and u.removed_on is null order by c.id",
        (UNIVERSE,),
    ).fetchall()

    price_rows = conn.execute(
        "select company_id, trade_date, open, high, low, close, volume, traded_value "
        "from public.daily_prices order by company_id, trade_date"
    ).fetchall()
    prices = pd.DataFrame(
        price_rows,
        columns=["company_id", "trade_date", "open", "high", "low", "close", "volume",
                 "traded_value"],
    )  # fmt: skip
    prices["trade_date"] = pd.to_datetime(prices["trade_date"])
    for column in ("open", "high", "low", "close", "volume", "traded_value"):
        prices[column] = prices[column].astype("float64")

    actions: dict[int, list] = {}
    for company_id, ex_date, factor in conn.execute(
        "select company_id, ex_date, factor from public.price_adjustments order by ex_date"
    ):
        actions.setdefault(company_id, []).append((ex_date, factor))

    benchmark_rows = conn.execute(
        "select trade_date, close from public.index_prices where index_name = %s "
        "order by trade_date",
        (BENCHMARK,),
    ).fetchall()
    benchmark = pd.Series(
        [float(c) for _, c in benchmark_rows],
        index=pd.to_datetime([d for d, _ in benchmark_rows]),
        dtype="float64",
    )
    return companies, prices, actions, benchmark


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate technical features")
    parser.add_argument(
        "--rebuild", action="store_true", help="rewrite every day, not just new ones"
    )
    parser.add_argument("--from-date", type=date.fromisoformat, help="write rows from this date on")
    args = parser.parse_args()

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1
    setup_logging(settings.log_level)

    with JobRun(settings, "build_features") as run, connect(settings) as conn:
        companies, prices, actions, benchmark = load_inputs(conn)
        if prices.empty:
            raise RuntimeError("No prices found. Run jobs.load_prices first.")
        if benchmark.empty:
            raise RuntimeError(f"No index values for '{BENCHMARK}'. Run jobs.load_prices first.")

        write_from = args.from_date
        if write_from is None and not args.rebuild:
            last = conn.execute(
                "select max(trade_date) from public.daily_features where feature_version = %s",
                (FEATURE_VERSION,),
            ).fetchone()[0]
            write_from = last  # rows after this date are new; that day is rewritten too
        log.info(
            "Calculating",
            extra={"fields": {"companies": len(companies), "price_rows": len(prices),
                              "write_from": write_from or "everything"}},
        )  # fmt: skip

        by_company = dict(tuple(prices.groupby("company_id")))
        features_by_company: dict[int, pd.DataFrame] = {}
        weekly_rows: list[tuple] = []

        for company_id, symbol in companies:
            company_prices = by_company.get(company_id)
            if company_prices is None or company_prices.empty:
                log.warning("No prices", extra={"fields": {"symbol": symbol}})
                continue
            frame = company_prices.set_index("trade_date").sort_index()
            adjusted = adjust_for_splits(frame, actions.get(company_id, []))
            features_by_company[company_id] = build_features(adjusted, benchmark)

            for week_start, w in to_weekly(adjusted).iterrows():
                if write_from is not None and w["week_end"] < write_from:
                    continue
                weekly_rows.append(
                    (company_id, week_start.date(), w["week_end"], clean(w["open"]),
                     clean(w["high"]), clean(w["low"]), clean(w["close"]),
                     int(w["volume"]), int(w["trading_days"]))
                )  # fmt: skip

        # Rank each day's 3-month relative strength across the whole universe.
        rs_frame = pd.DataFrame(
            {cid: f["rs_change_63d"] for cid, f in features_by_company.items() if len(f)}
        )
        ranks = rs_frame.apply(rank_within_universe, axis=1) if not rs_frame.empty else rs_frame

        feature_rows: list[tuple] = []
        for company_id, frame in features_by_company.items():
            if len(frame) and not ranks.empty:
                frame = frame.assign(rs_rank_63d=ranks[company_id])
            else:
                frame = frame.assign(rs_rank_63d=pd.NA)
            if write_from is not None:
                frame = frame[frame.index >= pd.Timestamp(write_from)]
            for trade_date, row in frame.iterrows():
                feature_rows.append(
                    (company_id, trade_date.date(), FEATURE_VERSION)
                    + tuple(clean(row[c]) for c in FEATURE_COLUMNS)
                )

        with conn.transaction():
            with conn.cursor() as cur:
                cur.executemany(UPSERT_WEEKLY, weekly_rows)
                cur.executemany(UPSERT_FEATURES, feature_rows)

        run.rows_written = len(feature_rows) + len(weekly_rows)
        run.message = (
            f"{len(feature_rows)} feature rows and {len(weekly_rows)} weekly bars "
            f"for {len(features_by_company)} companies ({FEATURE_VERSION})"
        )
        log.info("Done", extra={"fields": {"summary": run.message}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
