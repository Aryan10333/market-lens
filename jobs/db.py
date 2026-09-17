"""Database connection helper for the Supabase Postgres database."""

import psycopg

from jobs.config import Settings, require


def connect(settings: Settings) -> psycopg.Connection:
    """Open a Postgres connection. Close it with `with connect(...) as conn:`."""
    url = require(settings.database_url, "DATABASE_URL")
    # prepare_threshold=None: the Supabase pooler does not support prepared statements.
    return psycopg.connect(url, connect_timeout=10, prepare_threshold=None)
