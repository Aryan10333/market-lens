"""Checks that the jobs can reach the database and that the expected tables exist.

Run from the project folder:  .venv\\Scripts\\python -m jobs.health_check
"""

import logging
import sys

from jobs.config import ConfigError, load_settings
from jobs.db import connect
from jobs.log import setup_logging

log = logging.getLogger("health_check")

EXPECTED_TABLES = [
    "profiles",
    "companies",
    "job_runs",
    "universe_members",
    "price_files",
    "daily_prices",
    "index_prices",
    "price_adjustments",
]


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1
    setup_logging(settings.log_level)

    try:
        with connect(settings) as conn:
            server_time = conn.execute("select now()").fetchone()[0]
            rows = conn.execute(
                "select table_name from information_schema.tables "
                "where table_schema = 'public' and table_name = any(%s)",
                (EXPECTED_TABLES,),
            ).fetchall()
    except ConfigError as exc:
        log.error(str(exc))
        return 1
    except Exception:
        log.exception("Could not connect to the database")
        return 1

    found = {r[0] for r in rows}
    missing = [t for t in EXPECTED_TABLES if t not in found]
    if missing:
        log.error(
            "Database reachable but tables are missing. Run: python -m jobs.migrate",
            extra={"fields": {"missing_tables": missing}},
        )
        return 1

    log.info(
        "Health check passed",
        extra={
            "fields": {"env": settings.app_env, "db_time": server_time, "tables": sorted(found)}
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
