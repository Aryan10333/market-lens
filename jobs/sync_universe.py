"""Keeps the company list and the Nifty 500 membership up to date.

Steps:
  1. Download the current Nifty 500 list from NSE.
  2. Add new companies / update names, symbols and sectors (matched by ISIN, then by symbol).
  3. Fill in BSE scrip codes using the latest BSE bhavcopy (matched by ISIN).
  4. Record who joined or left the index in universe_members.

Run:  .venv\\Scripts\\python -m jobs.sync_universe
"""

import logging
import sys
from datetime import timedelta

from jobs.config import ConfigError, load_settings
from jobs.dates import today_ist
from jobs.db import connect
from jobs.download import Downloader
from jobs.log import setup_logging
from jobs.runs import JobRun
from jobs.sources import bse, nse

log = logging.getLogger("sync_universe")

UNIVERSE = "NIFTY500"
SOURCE = "nse_nifty500_list"


def latest_bse_codes(downloader: Downloader) -> dict[str, str]:
    """ISIN -> BSE code from the most recent BSE bhavcopy in the last 10 days."""
    today = today_ist()
    for back in range(10):
        day = today - timedelta(days=back)
        if day.weekday() >= 5:
            continue
        content = downloader.get(bse.bhavcopy_url(day), bse.REFERER)
        if content:
            codes = bse.parse_scrip_codes(content.decode("utf-8", errors="ignore"))
            if codes:
                log.info(
                    "BSE codes loaded", extra={"fields": {"file_date": day, "codes": len(codes)}}
                )
                return codes
    log.warning("No BSE bhavcopy found in the last 10 days; BSE codes not updated")
    return {}


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1
    setup_logging(settings.log_level)
    downloader = Downloader()
    today = today_ist()

    with JobRun(settings, "sync_universe") as run:
        content = downloader.get(nse.NIFTY500_LIST_URL, nse.REFERER)
        if content is None:
            raise RuntimeError("Nifty 500 list not found on NSE")
        members = nse.parse_nifty500_list(content.decode("utf-8", errors="ignore"))
        if len(members) < 450:
            raise RuntimeError(f"Nifty 500 list looks incomplete: only {len(members)} rows")
        bse_codes = latest_bse_codes(downloader)

        added = updated = isin_changed = 0
        with connect(settings) as conn:
            existing = conn.execute(
                "select id, isin, name, nse_symbol, sector, is_active, bse_code "
                "from public.companies"
            ).fetchall()
            by_isin = {r[1]: r for r in existing}
            by_symbol = {r[3]: r for r in existing if r[3]}

            member_ids = set()
            for m in members:
                row = by_isin.get(m.isin)
                symbol_row = by_symbol.get(m.symbol)

                if row is None and symbol_row is not None:
                    # Same symbol, new ISIN (usually after a face-value split). Same company.
                    conn.execute(
                        "update public.companies set isin = %s where id = %s",
                        (m.isin, symbol_row[0]),
                    )
                    log.info(
                        "ISIN changed",
                        extra={"fields": {"symbol": m.symbol, "old": symbol_row[1], "new": m.isin}},
                    )
                    isin_changed += 1
                    row = symbol_row
                elif row is not None and symbol_row is not None and symbol_row[0] != row[0]:
                    raise RuntimeError(
                        f"Symbol {m.symbol} belongs to company id {symbol_row[0]} "
                        f"but ISIN {m.isin} "
                        f"belongs to company id {row[0]}. Fix the companies table by hand."
                    )

                bse_code = bse_codes.get(m.isin) or (row[6] if row else None)
                if row is None:
                    company_id = conn.execute(
                        "insert into public.companies "
                        "(isin, name, nse_symbol, sector, bse_code, source) "
                        "values (%s, %s, %s, %s, %s, %s) returning id",
                        (m.isin, m.name, m.symbol, m.industry, bse_code, SOURCE),
                    ).fetchone()[0]
                    added += 1
                else:
                    company_id = row[0]
                    if (row[2], row[3], row[4], row[5], row[6]) != (
                        m.name,
                        m.symbol,
                        m.industry,
                        True,
                        bse_code,
                    ):
                        conn.execute(
                            "update public.companies set name = %s, nse_symbol = %s, sector = %s, "
                            "is_active = true, bse_code = %s where id = %s",
                            (m.name, m.symbol, m.industry, bse_code, company_id),
                        )
                        updated += 1
                member_ids.add(company_id)

            open_ids = {
                r[0]
                for r in conn.execute(
                    "select company_id from public.universe_members "
                    "where universe = %s and removed_on is null",
                    (UNIVERSE,),
                )
            }
            joined = member_ids - open_ids
            left = open_ids - member_ids
            for cid in joined:
                conn.execute(
                    "insert into public.universe_members (universe, company_id, added_on) "
                    "values (%s, %s, %s) on conflict do nothing",
                    (UNIVERSE, cid, today),
                )
            for cid in left:
                conn.execute(
                    "update public.universe_members set removed_on = %s "
                    "where universe = %s and company_id = %s and removed_on is null",
                    (today, UNIVERSE, cid),
                )

        run.rows_written = added + updated + len(joined) + len(left)
        run.message = (
            f"{len(members)} in list; companies added {added}, updated {updated}, "
            f"ISIN changed {isin_changed}; joined {len(joined)}, left {len(left)}; "
            f"BSE codes available {len(bse_codes)}"
        )
        log.info("Universe synced", extra={"fields": {"summary": run.message}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
