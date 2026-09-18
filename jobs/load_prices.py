"""Loads end-of-day prices from NSE into the database.

For every day in the date range that is not loaded yet (weekends included: NSE
sometimes holds a Saturday/Sunday session):
  * equity bhavcopy -> daily_prices   (only companies in the universe)
  * index closes    -> index_prices   (all NSE indices)
Each file is recorded in price_files. A day with no file is recorded as 'no_file'
(weekend or market holiday), but only once it is at least 3 days old, because today's
file may simply not be published yet.

The first run loads PRICE_HISTORY_YEARS of history (takes a while). Later runs only fetch
the new days. If a company joins the universe, its history is back-filled automatically.

Run:
  .venv\\Scripts\\python -m jobs.load_prices                          # normal (incremental)
  .venv\\Scripts\\python -m jobs.load_prices --start 2026-09-01 --end 2026-09-10 --reload
"""

import argparse
import logging
import sys
from datetime import date, timedelta
from functools import partial

from jobs.config import ConfigError, load_settings
from jobs.dates import all_days, today_ist, years_before
from jobs.db import open_connection, with_reconnect
from jobs.download import Downloader, unzip_single
from jobs.log import setup_logging
from jobs.runs import JobRun
from jobs.sources import nse
from jobs.sync_universe import UNIVERSE

log = logging.getLogger("load_prices")

HOLIDAY_AFTER_DAYS = 3

UPSERT_PRICE = """
insert into public.daily_prices
  (company_id, trade_date, series, open, high, low, close, prev_close,
   volume, traded_value, num_trades)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict (company_id, trade_date) do update set
  series = excluded.series, open = excluded.open, high = excluded.high, low = excluded.low,
  close = excluded.close, prev_close = excluded.prev_close, volume = excluded.volume,
  traded_value = excluded.traded_value, num_trades = excluded.num_trades
"""

UPSERT_INDEX = """
insert into public.index_prices (index_name, trade_date, open, high, low, close)
values (%s, %s, %s, %s, %s, %s)
on conflict (index_name, trade_date) do update set
  open = excluded.open, high = excluded.high, low = excluded.low, close = excluded.close
"""

UPSERT_FILE = """
insert into public.price_files
  (exchange, kind, trade_date, status, file_format, source_url,
   rows_in_file, rows_saved, rows_rejected)
values ('NSE', %s, %s, %s, %s, %s, %s, %s, %s)
on conflict (exchange, kind, trade_date) do update set
  status = excluded.status, file_format = excluded.file_format, source_url = excluded.source_url,
  rows_in_file = excluded.rows_in_file, rows_saved = excluded.rows_saved,
  rows_rejected = excluded.rows_rejected, loaded_at = now()
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Load NSE end-of-day prices")
    p.add_argument("--start", type=date.fromisoformat, help="first date, YYYY-MM-DD")
    p.add_argument("--end", type=date.fromisoformat, help="last date, YYYY-MM-DD (default today)")
    p.add_argument("--reload", action="store_true", help="download again even if already loaded")
    return p.parse_args()


def match_prices(rows, isin_map, symbol_map, only_ids=None):
    """Match bhavcopy rows to company ids. ISIN match wins over symbol match.

    Returns (rows to save as {company_id: PriceRow}, rejected count).
    """
    chosen: dict[int, tuple[bool, nse.PriceRow]] = {}
    rejected = 0
    for r in rows:
        by_isin = isin_map.get(r.isin)
        company_id = by_isin or symbol_map.get(r.symbol)
        if company_id is None or (only_ids is not None and company_id not in only_ids):
            continue
        problems = nse.validate_price(r)
        if problems:
            rejected += 1
            log.warning(
                "Rejected price row",
                extra={"fields": {"symbol": r.symbol, "date": r.trade_date, "problems": problems}},
            )
            continue
        if company_id not in chosen or (by_isin and not chosen[company_id][0]):
            chosen[company_id] = (by_isin is not None, r)
    return {cid: r for cid, (_, r) in chosen.items()}, rejected


def load_equity_day(conn, *, downloader, day, isin_map, symbol_map, only_ids=None) -> str:
    """Load one day's equity prices. Returns 'loaded', 'no_file' or 'not_yet'."""
    content = file_format = url = None
    for fmt, candidate in nse.bhavcopy_urls(day):
        content = downloader.get(candidate, nse.REFERER)
        if content:
            file_format, url = fmt, candidate
            break
    if not content:
        return _no_file(conn, "equity", day, record=only_ids is None)

    rows, total = nse.parse_bhavcopy(unzip_single(content).decode("utf-8", "ignore"), file_format)
    wrong_date = [r for r in rows if r.trade_date != day]
    if wrong_date:
        raise RuntimeError(f"File for {day} contains rows dated {wrong_date[0].trade_date}: {url}")

    to_save, rejected = match_prices(rows, isin_map, symbol_map, only_ids)
    with conn.transaction():
        with conn.cursor() as cur:
            cur.executemany(
                UPSERT_PRICE,
                [
                    (cid, r.trade_date, r.series, r.open, r.high, r.low, r.close, r.prev_close,
                     r.volume, r.traded_value, r.num_trades)
                    for cid, r in to_save.items()
                ],
            )  # fmt: skip
        if only_ids is None:
            conn.execute(
                UPSERT_FILE,
                ("equity", day, "loaded", file_format, url, total, len(to_save), rejected),
            )
    log.info(
        "Equity prices loaded",
        extra={"fields": {"date": day, "format": file_format, "saved": len(to_save),
                          "rejected": rejected, "backfill_only": only_ids is not None}},
    )  # fmt: skip
    return "loaded"


def load_index_day(conn, *, downloader, day) -> str:
    url = nse.index_close_url(day)
    content = downloader.get(url, nse.REFERER)
    if not content:
        return _no_file(conn, "index", day, record=True)
    rows = [
        r for r in nse.parse_index_close(content.decode("utf-8", "ignore")) if r.trade_date == day
    ]
    with conn.transaction():
        with conn.cursor() as cur:
            cur.executemany(
                UPSERT_INDEX,
                [(r.index_name, r.trade_date, r.open, r.high, r.low, r.close) for r in rows],
            )
        conn.execute(UPSERT_FILE, ("index", day, "loaded", None, url, len(rows), len(rows), 0))
    return "loaded"


def _no_file(conn, kind, day, record) -> str:
    if (today_ist() - day).days < HOLIDAY_AFTER_DAYS:
        return "not_yet"
    if record:
        conn.execute(UPSERT_FILE, (kind, day, "no_file", None, None, 0, 0, 0))
    return "no_file"


def main() -> int:
    args = parse_args()
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1
    setup_logging(settings.log_level)

    today = today_ist()
    end = args.end or today
    start = args.start or years_before(today, settings.price_history_years)
    if start > end:
        print("--start must be on or before --end", file=sys.stderr)
        return 1
    downloader = Downloader()

    with JobRun(settings, "load_prices") as run, open_connection(settings) as conn:
        companies = conn.execute(
            "select c.id, c.isin, c.nse_symbol from public.companies c "
            "join public.universe_members u on u.company_id = c.id "
            "where u.universe = %s and u.removed_on is null",
            (UNIVERSE,),
        ).fetchall()
        if not companies:
            raise RuntimeError("No companies in the universe. Run jobs.sync_universe first.")
        isin_map = {isin: cid for cid, isin, _ in companies}
        symbol_map = {sym: cid for cid, _, sym in companies if sym}

        done = {
            (kind, d)
            for kind, d in conn.execute(
                "select kind, trade_date from public.price_files "
                "where trade_date between %s and %s",
                (start, end),
            )
        }
        loaded_equity_days = sorted(
            d
            for (d,) in conn.execute(
                "select trade_date from public.price_files where kind = 'equity' "
                "and status = 'loaded' and trade_date between %s and %s",
                (start, end),
            )
        )
        # Companies that joined the universe in the last 7 days and have no prices yet
        # need the past days too. (Limited to recent joiners so a company that never
        # matches a price row does not trigger a full re-download on every run.)
        missing_history = {
            cid
            for (cid,) in conn.execute(
                "select u.company_id from public.universe_members u "
                "where u.universe = %s and u.removed_on is null and u.added_on >= %s "
                "and not exists (select 1 from public.daily_prices p "
                "where p.company_id = u.company_id)",
                (UNIVERSE, today - timedelta(days=7)),
            )
        }

        counts = {"equity_days": 0, "index_days": 0, "holidays": 0, "backfilled_days": 0}
        if missing_history and loaded_equity_days and not args.reload:
            log.info(
                "Back-filling companies without history",
                extra={
                    "fields": {"companies": len(missing_history), "days": len(loaded_equity_days)}
                },
            )
            for day in loaded_equity_days:
                work = partial(
                    load_equity_day,
                    downloader=downloader,
                    day=day,
                    isin_map=isin_map,
                    symbol_map=symbol_map,
                    only_ids=missing_history,
                )
                _, conn = with_reconnect(settings, conn, work, f"back-fill {day}")
                counts["backfilled_days"] += 1

        days = all_days(start, end)
        for i, day in enumerate(days, 1):
            if args.reload or ("equity", day) not in done:
                work = partial(
                    load_equity_day,
                    downloader=downloader,
                    day=day,
                    isin_map=isin_map,
                    symbol_map=symbol_map,
                )
                status, conn = with_reconnect(settings, conn, work, f"equity {day}")
                counts["equity_days"] += status == "loaded"
                counts["holidays"] += status == "no_file"
            if args.reload or ("index", day) not in done:
                work = partial(load_index_day, downloader=downloader, day=day)
                status, conn = with_reconnect(settings, conn, work, f"index {day}")
                counts["index_days"] += status == "loaded"
            if i % 50 == 0:
                log.info("Progress", extra={"fields": {"done": i, "of": len(days), "at": day}})

        run.rows_written = counts["equity_days"] + counts["index_days"]
        run.message = (
            f"{start} to {end}: equity days {counts['equity_days']}, index days "
            f"{counts['index_days']}, holidays {counts['holidays']}, "
            f"back-filled days {counts['backfilled_days']}"
        )
        log.info("Done", extra={"fields": {"summary": run.message}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
