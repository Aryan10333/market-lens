"""Works out the Stage (1-4) for every company and day, and saves the evidence.

The rules live in jobs/stages.py and their thresholds in config/stages.json, versioned the
same way as the scanners: the configuration is stored once in rule_versions, and the job
refuses to run if the file changed without its version changing.

Run:
  .venv\\Scripts\\python -m jobs.classify_stages              # days not classified yet
  .venv\\Scripts\\python -m jobs.classify_stages --rebuild    # the whole history again
"""

import argparse
import json
import logging
import sys
from collections import Counter

from jobs.config import ConfigError, load_settings
from jobs.db import connect, open_connection, with_reconnect
from jobs.log import setup_logging
from jobs.run_scanners import register_rule_version
from jobs.runs import JobRun
from jobs.stages import classify, confirm_changes, load_config
from jobs.sync_universe import UNIVERSE

log = logging.getLogger("classify_stages")

COLUMNS = [
    "close_adj", "wma_30w", "wma_30w_slope", "pct_from_high_52w",
    "pct_above_low_52w", "rs_rank_63d", "days_in_range",
]  # fmt: skip

UPSERT = """
insert into public.daily_stages
  (company_id, trade_date, stage, stage_since, rule_version, evidence)
values (%s, %s, %s, %s, %s, %s)
on conflict (company_id, trade_date) do update set
  stage = excluded.stage, stage_since = excluded.stage_since,
  rule_version = excluded.rule_version, evidence = excluded.evidence, calculated_at = now()
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify Stage 1-4 for every company and day")
    parser.add_argument("--rebuild", action="store_true", help="classify the whole history again")
    args = parser.parse_args()

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1
    setup_logging(settings.log_level)
    config = load_config()

    with JobRun(settings, "classify_stages") as run, connect(settings) as conn:
        version = register_rule_version(conn, config, kind="stage")

        start = None
        if not args.rebuild:
            start = conn.execute(
                "select max(trade_date) from public.daily_stages where rule_version = %s",
                (version,),
            ).fetchone()[0]

        rows = conn.execute(
            f"select f.company_id, f.trade_date, {', '.join('f.' + c for c in COLUMNS)} "
            "from public.daily_features f "
            "join public.universe_members u on u.company_id = f.company_id "
            "     and u.universe = %s and u.removed_on is null "
            "where %s::date is null or f.trade_date >= %s::date",
            (UNIVERSE, start, start),
        ).fetchall()

        # Group by company so a stage change can be confirmed over several days.
        by_company: dict[int, list] = {}
        for company_id, trade_date, *values in rows:
            row = {
                name: (float(v) if v is not None else None)
                for name, v in zip(COLUMNS, values, strict=True)
            }
            by_company.setdefault(company_id, []).append((trade_date, row))

        results = []
        counts = Counter()
        too_early = 0
        changes = 0
        for company_id, days in by_company.items():
            days.sort(key=lambda d: d[0])
            decided = [classify(row, config) for _, row in days]
            raw = [d[0] if d else None for d in decided]
            confirmed = confirm_changes(raw, config["confirm_days"])

            previous_stage = None
            since = None
            for (trade_date, _), decision, stage in zip(days, decided, confirmed, strict=True):
                if decision is None or stage is None:
                    too_early += 1  # not enough history for a 30-week average yet
                    continue
                today_says, evidence = decision
                counts[stage] += 1

                changed = stage != previous_stage
                if changed:
                    since = trade_date
                    changes += 1
                previous_stage = stage

                # The evidence belongs to the day the stage changed: that is when the
                # decision was made. Storing it for every day made the table huge.
                stored = (
                    json.dumps(
                        {
                            **evidence,
                            "today_alone_suggests": today_says,
                            "confirm_days": config["confirm_days"],
                        }
                    )
                    if changed
                    else None
                )
                results.append((company_id, trade_date, stage, since, version, stored))

        writer = open_connection(settings)
        try:
            for start_at in range(0, len(results), 10_000):
                batch = results[start_at : start_at + 10_000]

                def work(c, batch=batch):
                    with c.transaction(), c.cursor() as cur:
                        cur.executemany(UPSERT, batch)

                _, writer = with_reconnect(settings, writer, work, f"stages from {start_at}")
        finally:
            writer.close()

        run.rows_written = len(results)
        run.message = (
            f"{len(results)} days classified ({version}); "
            + ", ".join(f"stage {s} {n:,}" for s, n in sorted(counts.items()))
            + f"; {changes:,} stage changes; {too_early:,} days had too little history"
        )
        log.info("Done", extra={"fields": {"summary": run.message}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
