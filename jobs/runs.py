"""Records each job run in the job_runs table (start, finish, status, rows, message).

Usage:
    with JobRun(settings, "load_prices") as run:
        ...
        run.rows_written += 10
        run.message = "loaded 3 days"

If the code inside raises an error, the run is saved as 'failed' with the error text.
The run is recorded on its own connection, so it is saved even if the job's work is rolled back.
"""

from jobs.config import Settings
from jobs.db import connect


class JobRun:
    def __init__(self, settings: Settings, job_name: str):
        self.settings = settings
        self.job_name = job_name
        self.rows_written = 0
        self.message = ""
        self._id = None

    def __enter__(self) -> "JobRun":
        with connect(self.settings) as conn:
            self._id = conn.execute(
                "insert into public.job_runs (job_name) values (%s) returning id", (self.job_name,)
            ).fetchone()[0]
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        status = "failed" if exc else "success"
        message = f"{exc_type.__name__}: {exc}" if exc else self.message
        with connect(self.settings) as conn:
            conn.execute(
                "update public.job_runs set status = %s, finished_at = now(), "
                "rows_written = %s, message = %s where id = %s",
                (status, self.rows_written, message[:2000], self._id),
            )
        # Returning None lets any error continue to the caller.
