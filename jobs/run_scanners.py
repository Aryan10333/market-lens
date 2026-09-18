"""Runs the scanners over calculated features and saves the signals.

Each signal records the scanner, the rule version, and the actual numbers behind it, so the
app can always show why a stock appeared.

The exact thresholds are stored once in rule_versions. If config/scanners.json changes
without its version being bumped, the job stops: old signals would no longer be explained
by the stored configuration.

Run:
  .venv\\Scripts\\python -m jobs.run_scanners                      # the latest trading day
  .venv\\Scripts\\python -m jobs.run_scanners --days 30            # the last 30 trading days
  .venv\\Scripts\\python -m jobs.run_scanners --from 2023-09-18    # replay history
"""

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import date

from jobs.config import ConfigError, load_settings
from jobs.db import connect
from jobs.log import setup_logging
from jobs.runs import JobRun
from jobs.scanners import load_config, run_all
from jobs.sync_universe import UNIVERSE

log = logging.getLogger("run_scanners")

FEATURE_COLUMNS = [
    "close_adj", "return_1d", "volume_ratio_20", "volume_avg_20", "value_avg_20",
    "high_52w", "pct_from_high_52w", "wma_30w", "wma_30w_slope",
    "range_high_120", "range_width_120", "days_in_range", "rs_rank_63d",
]  # fmt: skip

# Everything a scanner may look at, for one company on one day.
SELECT_ROWS = f"""
select f.company_id, f.trade_date, c.nse_symbol, c.sector,
       {", ".join("f." + c for c in FEATURE_COLUMNS)},
       lag(f.days_in_range) over (partition by f.company_id order by f.trade_date)
         as days_in_range_prev,
       lag(f.close_adj) over (partition by f.company_id order by f.trade_date) as close_adj_prev,
       lag(f.wma_30w) over (partition by f.company_id order by f.trade_date) as wma_30w_prev,
       lag(s.rank_relative_21d) over (partition by f.company_id order by f.trade_date)
         as sector_rank_relative_21d_prev,
       s.index_name as sector_index, s.return_21d as sector_return_21d,
       s.relative_21d as sector_relative_21d, s.rank_relative_21d as sector_rank_relative_21d
from public.daily_features f
join public.companies c on c.id = f.company_id
join public.universe_members u on u.company_id = f.company_id
     and u.universe = %s and u.removed_on is null
left join public.sector_features s on s.sector = c.sector and s.trade_date = f.trade_date
where f.trade_date >= %s and f.trade_date <= %s
order by f.company_id, f.trade_date
"""

INSERT_SIGNAL = """
insert into public.signals (company_id, trade_date, scanner, rule_version, evidence)
values (%s, %s, %s, %s, %s)
on conflict (company_id, trade_date, scanner, rule_version) do update
  set evidence = excluded.evidence, created_at = now()
"""


def register_rule_version(conn, config: dict, kind: str = "scanner") -> str:
    """Store the thresholds for this version, or check they have not changed."""
    version = config["version"]
    stored = conn.execute(
        "select config from public.rule_versions where version = %s", (version,)
    ).fetchone()
    if stored is None:
        conn.execute(
            "insert into public.rule_versions (version, kind, config) values (%s, %s, %s)",
            (version, kind, json.dumps(config)),
        )
        log.info("Rule version saved", extra={"fields": {"version": version}})
    elif stored[0] != config:
        raise RuntimeError(
            f"The configuration for '{version}' differs from the stored one. "
            "Bump the version in the file so old results stay explainable."
        )
    return version


def to_float(value):
    return float(value) if value is not None else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the scanners and save signals")
    parser.add_argument("--from", dest="start", type=date.fromisoformat, help="first day")
    parser.add_argument("--to", dest="end", type=date.fromisoformat, help="last day")
    parser.add_argument("--days", type=int, default=1, help="how many recent trading days")
    args = parser.parse_args()

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1
    setup_logging(settings.log_level)
    config = load_config()

    with JobRun(settings, "run_scanners") as run, connect(settings) as conn:
        version = register_rule_version(conn, config)

        end = (
            args.end
            or conn.execute("select max(trade_date) from public.daily_features").fetchone()[0]
        )
        if end is None:
            raise RuntimeError("No features found. Run jobs.build_features first.")
        if args.start:
            start = args.start
        else:
            recent = conn.execute(
                "select distinct trade_date from public.daily_features where trade_date <= %s "
                "order by trade_date desc limit %s",
                (end, args.days),
            ).fetchall()
            start = min(d for (d,) in recent)

        # The previous day's "days in range" is needed, so read one extra day of history.
        read_from = conn.execute(
            "select coalesce(max(trade_date), %s) from public.daily_features where trade_date < %s",
            (start, start),
        ).fetchone()[0]

        columns = (
            ["company_id", "trade_date", "nse_symbol", "sector"]
            + FEATURE_COLUMNS
            + ["days_in_range_prev", "close_adj_prev", "wma_30w_prev",
               "sector_rank_relative_21d_prev", "sector_index", "sector_return_21d",
               "sector_relative_21d", "sector_rank_relative_21d"]
        )  # fmt: skip
        rows = conn.execute(SELECT_ROWS, (UNIVERSE, read_from, end)).fetchall()

        found: list[tuple] = []
        counts = Counter()
        for values in rows:
            row = dict(zip(columns, values, strict=True))
            if row["trade_date"] < start:
                continue  # only read for the lag value
            numbers = {
                k: to_float(v) if k not in ("nse_symbol", "sector", "sector_index") else v
                for k, v in row.items()
                if k not in ("company_id", "trade_date")
            }
            for scanner, evidence in run_all(numbers, config).items():
                counts[scanner] += 1
                found.append(
                    (
                        row["company_id"],
                        row["trade_date"],
                        scanner,
                        version,
                        json.dumps({"symbol": row["nse_symbol"], **evidence}),
                    )
                )

        with conn.transaction(), conn.cursor() as cur:
            cur.executemany(INSERT_SIGNAL, found)

        run.rows_written = len(found)
        run.message = f"{start} to {end} ({version}): " + (
            ", ".join(f"{name} {n}" for name, n in sorted(counts.items())) or "no signals"
        )
        log.info("Done", extra={"fields": {"summary": run.message}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
