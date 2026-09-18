"""Database connections, and surviving a dropped one.

Long jobs keep a connection open for minutes. A sleeping laptop or a network blip closes it,
and without this the whole job would stop part-way.
"""

import logging
import time

import psycopg

from jobs.config import Settings, require

log = logging.getLogger("db")


def connect(settings: Settings) -> psycopg.Connection:
    """Open a Postgres connection. Close it with `with connect(...) as conn:`."""
    url = require(settings.database_url, "DATABASE_URL")
    # prepare_threshold=None: the Supabase pooler does not support prepared statements.
    return psycopg.connect(url, connect_timeout=10, prepare_threshold=None)


def open_connection(settings: Settings) -> psycopg.Connection:
    """A connection where each `with conn.transaction()` is its own transaction."""
    conn = connect(settings)
    conn.autocommit = True
    return conn


def with_reconnect(settings: Settings, conn, work, what: str):
    """Run work(conn). If the connection drops, open a new one and try again.

    Returns (result, the connection to keep using).
    """
    for attempt in range(1, 4):
        try:
            return work(conn), conn
        except psycopg.OperationalError as exc:
            log.warning(
                "Database connection lost, reconnecting",
                extra={"fields": {"task": what, "attempt": attempt, "error": str(exc)[:200]}},
            )
            try:
                conn.close()
            except Exception:
                pass
            time.sleep(5 * attempt)
            conn = open_connection(settings)
    raise RuntimeError(f"Could not reach the database while doing: {what}")
