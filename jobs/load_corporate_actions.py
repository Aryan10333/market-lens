"""Loads splits, bonuses and consolidations from NSE's corporate actions list.

Why: stored prices are raw. After a 1:1 bonus a share worth 2656 trades at 1337, which
would look like a 50% crash in any calculation. Each action gives a factor that older
prices are multiplied by (see jobs/adjustments.py).

The table is rebuilt each run (it is small). For every action we also work out the ratio
actually seen in our prices (close on the ex-date / previous close), so a wrong or
mis-read action shows up as a mismatch in `jobs.check_data`.

Run:  .venv\\Scripts\\python -m jobs.load_corporate_actions
"""

import logging
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from jobs.adjustments import parse_action
from jobs.config import ConfigError, load_settings
from jobs.dates import today_ist
from jobs.db import connect
from jobs.download import Downloader
from jobs.log import setup_logging
from jobs.runs import JobRun
from jobs.sources import nse
from jobs.sync_universe import UNIVERSE

log = logging.getLogger("load_corporate_actions")

CHUNK_DAYS = 90  # the API is queried in chunks of about three months


@dataclass(frozen=True)
class CombinedAction:
    """All actions a company has on one ex-date, as a single factor."""

    factor: Decimal
    kind: str
    description: str


def combine(existing: CombinedAction | None, action, subject: str) -> CombinedAction:
    """Add one action to what is already known for that company and ex-date.

    Two actions on the same day multiply: BAJFINANCE on 16 Jun 2025 had a 4:1 bonus
    (0.2) and a split from Rs 2 to Re 1 (0.5), so prices before that day are x0.1.
    """
    if existing is None:
        return CombinedAction(action.factor, action.kind, subject)
    return CombinedAction(
        factor=(existing.factor * action.factor).quantize(Decimal("0.00000001")),
        kind="multiple",
        description=f"{existing.description} + {subject}",
    )


def date_chunks(start: date, end: date, size: int = CHUNK_DAYS) -> list[tuple[date, date]]:
    chunks = []
    at = start
    while at <= end:
        stop = min(at + timedelta(days=size - 1), end)
        chunks.append((at, stop))
        at = stop + timedelta(days=1)
    return chunks


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1
    setup_logging(settings.log_level)
    downloader = Downloader()

    with JobRun(settings, "load_corporate_actions") as run:
        # 1. Read what we need from the database, then let the connection go: downloads
        #    can take a while, and an idle connection may be closed by the server.
        with connect(settings) as conn:
            companies = conn.execute(
                "select c.id, c.isin, c.nse_symbol from public.companies c "
                "join public.universe_members u on u.company_id = c.id "
                "where u.universe = %s and u.removed_on is null",
                (UNIVERSE,),
            ).fetchall()
            first_day, last_day = conn.execute(
                "select min(trade_date), max(trade_date) from public.daily_prices"
            ).fetchone()
        if first_day is None:
            raise RuntimeError("No prices loaded yet. Run jobs.load_prices first.")
        by_isin = {isin: cid for cid, isin, _ in companies}
        by_symbol = {sym: cid for cid, _, sym in companies if sym}
        last_day = min(last_day, today_ist())

        # 2. Download the corporate actions for the period we hold prices for.
        # (company, ex-date) -> combined action. Two actions can share an ex-date.
        found: dict[tuple[int, date], CombinedAction] = {}
        ignored = 0
        for chunk_start, chunk_end in date_chunks(first_day, last_day):
            url = nse.corporate_actions_url(chunk_start, chunk_end)
            content = downloader.get(url, nse.CORPORATE_ACTIONS_REFERER)
            if content is None:
                log.warning("No corporate actions returned", extra={"fields": {"url": url}})
                continue
            rows = nse.parse_corporate_actions(content.decode("utf-8", "ignore"))
            used = 0
            for r in rows:
                company_id = by_isin.get(r.isin) or by_symbol.get(r.symbol)
                if company_id is None:
                    continue
                action = parse_action(r.subject)
                if action is None:
                    ignored += 1  # dividend, rights, buyback, AGM ...
                    continue
                key = (company_id, r.ex_date)
                found[key] = combine(found.get(key), action, r.subject)
                used += 1
            log.info(
                "Corporate actions read",
                extra={
                    "fields": {
                        "from": chunk_start,
                        "to": chunk_end,
                        "rows": len(rows),
                        "kept": used,
                    }
                },
            )

        # 3. Write them, with the price move actually seen on each ex-date for checking.
        with connect(settings) as conn:
            observed = {}
            if found:
                observed = {
                    (cid, day): (close / prev) if prev and prev > 0 else None
                    for cid, day, close, prev in conn.execute(
                        "select company_id, trade_date, close, prev_close from public.daily_prices "
                        "where (company_id, trade_date) in "
                        "(select * from unnest(%s::bigint[], %s::date[]))",
                        (
                            [cid for cid, _ in found],
                            [ex_date for _, ex_date in found],
                        ),
                    )
                }
            with conn.transaction():
                conn.execute("delete from public.price_adjustments")
                with conn.cursor() as cur:
                    cur.executemany(
                        "insert into public.price_adjustments (company_id, ex_date, factor, "
                        "action_type, description, observed_ratio) values (%s, %s, %s, %s, %s, %s)",
                        [
                            (cid, ex_date, c.factor, c.kind, c.description,
                             observed.get((cid, ex_date)))
                            for (cid, ex_date), c in found.items()
                        ],
                    )  # fmt: skip

        run.rows_written = len(found)
        run.message = (
            f"{first_day} to {last_day}: {len(found)} splits/bonuses for universe companies "
            f"({ignored} other actions ignored)"
        )
        log.info("Done", extra={"fields": {"summary": run.message}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
