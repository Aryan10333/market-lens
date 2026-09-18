"""Applies new database migrations from supabase/migrations/.

Each .sql file runs once, inside a transaction. Applied files are recorded in
supabase_migrations.schema_migrations, the same table the Supabase CLI uses,
so `npx supabase db push` stays compatible.

Usage (from the project folder):
  .venv\\Scripts\\python -m jobs.migrate                     # apply all pending files
  .venv\\Scripts\\python -m jobs.migrate --list              # show applied / pending
  .venv\\Scripts\\python -m jobs.migrate --mark-applied 20260917000000
        # record a file as applied without running it (it was already run by hand)
"""

import argparse
import sys
from pathlib import Path

from jobs.config import ConfigError, load_settings
from jobs.db import connect

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "supabase" / "migrations"

HISTORY_TABLE_SQL = """
create schema if not exists supabase_migrations;
create table if not exists supabase_migrations.schema_migrations (
  version text primary key,
  statements text[],
  name text
);
"""


def migration_files() -> list[tuple[str, str, Path]]:
    """Return (version, name, path) for each migration file, oldest first.

    File names look like 20260917120000_market_data.sql -> version 20260917120000, name market_data.
    """
    files = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version, _, name = path.stem.partition("_")
        if not version.isdigit():
            raise ValueError(f"Migration file name must start with a number: {path.name}")
        files.append((version, name, path))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply database migrations")
    parser.add_argument("--list", action="store_true", help="show applied and pending migrations")
    parser.add_argument("--mark-applied", metavar="VERSION", help="record VERSION as applied")
    args = parser.parse_args()

    try:
        settings = load_settings()
        conn = connect(settings)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    with conn:
        conn.execute(HISTORY_TABLE_SQL)
        conn.commit()
        applied = {
            r[0] for r in conn.execute("select version from supabase_migrations.schema_migrations")
        }
        conn.commit()  # close the read transaction so each file below gets its own transaction
        files = migration_files()

        if args.mark_applied:
            match = [f for f in files if f[0] == args.mark_applied]
            if not match:
                print(f"No migration file with version {args.mark_applied}", file=sys.stderr)
                return 1
            version, name, _ = match[0]
            conn.execute(
                "insert into supabase_migrations.schema_migrations (version, name, statements) "
                "values (%s, %s, '{}') on conflict (version) do nothing",
                (version, name),
            )
            conn.commit()
            print(f"Marked as applied: {version}_{name}")
            return 0

        if args.list:
            for version, name, _ in files:
                print(f"{'applied' if version in applied else 'PENDING'}  {version}_{name}")
            return 0

        pending = [f for f in files if f[0] not in applied]
        if not pending:
            print("Database is up to date. No pending migrations.")
            return 0

        for version, name, path in pending:
            sql = path.read_text(encoding="utf-8")
            try:
                with conn.transaction():
                    conn.execute(sql)
                    conn.execute(
                        "insert into supabase_migrations.schema_migrations "
                        "(version, name, statements) values (%s, %s, %s)",
                        (version, name, [sql]),
                    )
            except Exception as exc:
                print(f"FAILED {version}_{name}: {exc}", file=sys.stderr)
                print("Nothing from this file was applied (rolled back).", file=sys.stderr)
                return 1
            print(f"Applied {version}_{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
