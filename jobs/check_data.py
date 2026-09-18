"""Data quality report for the market data.

Checks:
  * universe size is close to 500
  * every universe company has prices, and prices are recent
  * missing days: a company has no price on a day the exchange file was loaded
  * rows rejected while loading
  * index data present for the benchmark (Nifty 500)
  * splits/bonuses found

Prints a plain-text report. Exits with code 1 if a serious problem is found,
so the scheduled GitHub workflow shows as failed.

Run:  .venv\\Scripts\\python -m jobs.check_data
"""

import sys

from jobs.config import ConfigError, load_settings
from jobs.dates import today_ist
from jobs.db import connect
from jobs.sync_universe import UNIVERSE

BENCHMARK = "Nifty 500"
STALE_AFTER_DAYS = 7  # latest loaded file older than this = data is not updating


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    problems: list[str] = []
    warnings: list[str] = []
    lines: list[str] = []

    with connect(settings) as conn:
        q = lambda sql, *p: conn.execute(sql, p).fetchall()  # noqa: E731

        members = q(
            "select count(*) from public.universe_members "
            "where universe = %s and removed_on is null",
            UNIVERSE,
        )[0][0]
        lines.append(f"Universe {UNIVERSE}: {members} companies")
        if not 480 <= members <= 520:
            problems.append(f"universe has {members} companies, expected about 500")

        first, last, loaded, holidays = q(
            "select min(trade_date) filter (where status = 'loaded'), "
            "max(trade_date) filter (where status = 'loaded'), "
            "count(*) filter (where status = 'loaded'), count(*) filter (where status = 'no_file') "
            "from public.price_files where kind = 'equity'"
        )[0]
        lines.append(
            f"Equity files: {loaded} trading days loaded ({first} to {last}), "
            f"{holidays} non-trading days (weekends/holidays)"
        )
        if last is None:
            problems.append("no equity price files loaded")
        elif (today_ist() - last).days > STALE_AFTER_DAYS:
            problems.append(f"latest equity file is {last}, more than {STALE_AFTER_DAYS} days old")

        price_rows, companies_with_prices = q(
            "select count(*), count(distinct company_id) from public.daily_prices"
        )[0]
        lines.append(f"Price rows: {price_rows:,} for {companies_with_prices} companies")

        rejected = q("select coalesce(sum(rows_rejected), 0) from public.price_files")[0][0]
        lines.append(f"Rows rejected while loading (bad values): {rejected}")
        if rejected:
            warnings.append(f"{rejected} price rows were rejected; see load_prices logs")

        # Members with no price on the latest loaded day.
        not_on_last = q(
            "select c.nse_symbol from public.universe_members u "
            "join public.companies c on c.id = u.company_id "
            "where u.universe = %s and u.removed_on is null and not exists ("
            "  select 1 from public.daily_prices p where p.company_id = u.company_id "
            "  and p.trade_date = %s) order by 1",
            UNIVERSE,
            last,
        )
        lines.append(f"Members without a price on {last}: {len(not_on_last)}")
        if not_on_last:
            symbols = ", ".join(r[0] for r in not_on_last[:20])
            warnings.append(
                f"no price on {last} for: {symbols}" + (" ..." if len(not_on_last) > 20 else "")
            )
        if members and len(not_on_last) > members * 0.05:
            problems.append(f"{len(not_on_last)} members have no price on {last}")

        # Gaps: loaded days after a company's first price where it has no row.
        gaps = q(
            "with span as ("
            "  select company_id, min(trade_date) first_day, count(*) have "
            "  from public.daily_prices group by company_id) "
            "select c.nse_symbol, "
            "  (select count(*) from public.price_files f where f.kind = 'equity' "
            "   and f.status = 'loaded' and f.trade_date >= s.first_day) - s.have as missing "
            "from span s join public.companies c on c.id = s.company_id "
            "order by missing desc limit 10"
        )
        gaps = [(sym, n) for sym, n in gaps if n > 0]
        lines.append("Most missing days (after first price): " + (
            ", ".join(f"{sym} {n}" for sym, n in gaps) if gaps else "none"
        ))  # fmt: skip

        bench = q(
            "select count(*), max(trade_date) from public.index_prices where index_name = %s",
            BENCHMARK,
        )[0]
        lines.append(f"Benchmark '{BENCHMARK}': {bench[0]} days, latest {bench[1]}")
        if bench[0] == 0:
            problems.append(f"no index values for benchmark '{BENCHMARK}'")
        index_count = q("select count(distinct index_name) from public.index_prices")[0][0]
        lines.append(f"Indices stored: {index_count}")

        adjustments = q(
            "select c.nse_symbol, a.ex_date, a.factor, a.action_type "
            "from public.price_adjustments a join public.companies c on c.id = a.company_id "
            "order by a.ex_date desc limit 6"
        )
        total_adj = q("select count(*) from public.price_adjustments")[0][0]
        latest = ", ".join(f"{s} {d} {t} x{f:.4f}" for s, d, f, t in adjustments) or "none"
        lines.append(f"Splits/bonuses/consolidations: {total_adj}. Latest: {latest}")

        # Each official action should match the price move on its ex-date.
        mismatches = q(
            "select c.nse_symbol, a.ex_date, a.factor, a.observed_ratio, a.description "
            "from public.price_adjustments a join public.companies c on c.id = a.company_id "
            "where a.observed_ratio is not null "
            "and abs(a.observed_ratio / a.factor - 1) > 0.25 order by a.ex_date desc"
        )
        checked = q(
            "select count(*) from public.price_adjustments where observed_ratio is not null"
        )[0][0]
        lines.append(
            f"Actions checked against prices: {checked - len(mismatches)} of {checked} match"
        )
        for sym, ex, factor, observed, desc in mismatches[:5]:
            warnings.append(
                f"{sym} {ex}: '{desc}' expects x{factor:.4f} but prices moved x{observed:.4f}"
            )

        size = q("select pg_size_pretty(pg_database_size(current_database()))")[0][0]
        lines.append(f"Database size: {size} (Supabase Free limit: 500 MB)")

    print("=== Market data check ===")
    for line in lines:
        print(f"  {line}")
    for w in warnings:
        print(f"  WARNING: {w}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    print("Result:", "FAILED" if problems else "OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
