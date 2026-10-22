"""database.create() refuses reserved names: the NEEDINFO sentinel and 'bed'.

A reserved name means the database name was never configured (NEEDINFO) or
was left at the packaged default (bed). Creating it is refused before any SQL
runs, and the error tells the sysop to set the name.
"""

from unittest.mock import MagicMock

import pytest

from bbsengine6 import database

ARGS = MagicMock(debug=False)


class _Conn:
    """Connection that fails the test if any SQL is issued."""

    autocommit = True

    def cursor(self):
        raise AssertionError("create() must not issue SQL for a reserved name")

    def execute(self, *a, **k):
        raise AssertionError("create() must not issue SQL for a reserved name")


@pytest.mark.unit
@pytest.mark.parametrize("name", ["NEEDINFO", "bed"])
def test_create_refuses_reserved_name_without_sql(name, monkeypatch):
    monkeypatch.setattr(database, "_echo_reserved", lambda *a, **k: None)
    assert database.create(ARGS, name, conn=_Conn()) is False


@pytest.mark.unit
def test_reserved_names_include_the_sentinel_and_bed():
    assert "NEEDINFO" in database.RESERVED_DATABASE_NAMES
    assert "bed" in database.RESERVED_DATABASE_NAMES
    assert database.BBSENGINE6_DBNAME_DEFAULT in database.RESERVED_DATABASE_NAMES


@pytest.mark.unit
def test_reserved_refusal_logs_a_sysop_message(monkeypatch):
    messages = []
    monkeypatch.setattr(
        database.io, "echo", lambda msg, *a, **k: messages.append((msg, k.get("level")))
    )
    assert database.create(ARGS, "NEEDINFO", conn=_Conn()) is False
    joined = " ".join(m for m, _ in messages)
    assert "NEEDINFO" in joined
    assert "sysop" in joined.lower()
    assert any(level == "error" for _, level in messages)


@pytest.mark.unit
def test_checkdatabase_does_not_reach_create_for_reserved_name(monkeypatch):
    from bbsengine6.backend import checkdatabase

    args = MagicMock(databasename="NEEDINFO", debug=False)
    pool = MagicMock()
    conn = MagicMock()
    conn.autocommit = False
    monkeypatch.setattr(database, "exists", lambda *a, **k: False)
    monkeypatch.setattr(checkdatabase.database, "connect", _ctx(conn))
    created = []
    monkeypatch.setattr(
        checkdatabase.database, "create", lambda *a, **k: created.append(a) or False
    )
    checkdatabase.main(args, pool=pool)
    # create() is called (it owns the gate) but refuses; the gate itself is tested above.
    assert created, "checkdatabase must route through database.create()"


@pytest.mark.unit
def test_backend_database_routes_reserved_name_through_create(monkeypatch):
    from bbsengine6.backend import database as backend_db

    args = MagicMock(databasename="bed", debug=False)
    conn = MagicMock()
    conn.autocommit = False
    monkeypatch.setattr(backend_db.database, "exists", lambda *a, **k: False)
    created = []

    def fake_create(_args, name, **k):
        created.append(name)
        return False

    monkeypatch.setattr(backend_db.database, "create", fake_create)
    assert backend_db.main(args, conn=conn) is False
    assert created, "backend database runner must route through database.create()"


def _ctx(conn):
    from contextlib import contextmanager

    @contextmanager
    def cm(*a, **k):
        yield conn

    return cm
