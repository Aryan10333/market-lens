import psycopg
import pytest

from jobs import load_prices


class FakeConn:
    def __init__(self, name):
        self.name = name
        self.closed = False

    def close(self):
        self.closed = True


def patch_helpers(monkeypatch, new_conns):
    """No real sleeping, and reconnects hand out the given fake connections."""
    monkeypatch.setattr(load_prices.time, "sleep", lambda _: None)
    monkeypatch.setattr(load_prices, "open_connection", lambda _settings: new_conns.pop(0))


def test_work_runs_once_when_connection_is_fine(monkeypatch):
    patch_helpers(monkeypatch, [])
    conn = FakeConn("first")
    result, used = load_prices.with_reconnect(None, conn, lambda c: f"ok on {c.name}", "test")
    assert result == "ok on first"
    assert used is conn
    assert not conn.closed


def test_reconnects_and_retries_after_dropped_connection(monkeypatch):
    fresh = FakeConn("second")
    patch_helpers(monkeypatch, [fresh])
    dead = FakeConn("first")
    calls = []

    def work(conn):
        calls.append(conn.name)
        if conn.name == "first":
            raise psycopg.OperationalError("server closed the connection unexpectedly")
        return "loaded"

    result, used = load_prices.with_reconnect(None, dead, work, "equity 2026-09-17")
    assert result == "loaded"
    assert calls == ["first", "second"]
    assert used is fresh
    assert dead.closed  # the broken connection is closed


def test_gives_up_after_three_attempts(monkeypatch):
    patch_helpers(monkeypatch, [FakeConn("b"), FakeConn("c"), FakeConn("d")])

    def always_fails(_conn):
        raise psycopg.OperationalError("connection is lost")

    with pytest.raises(RuntimeError, match="Could not reach the database"):
        load_prices.with_reconnect(None, FakeConn("a"), always_fails, "equity 2026-09-17")
