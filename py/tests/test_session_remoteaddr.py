"""Session address fields: build() carries remoteaddr and remoteaddr_source; the source is checked."""

import importlib
import os

import pytest

session_lib = importlib.import_module("bbsengine6.session.lib")


def _row(**over):
    row = {
        "id": "s1", "expiry": None, "lastactivity": None, "data": {},
        "remoteaddr": None, "remoteaddr_source": None, "useragent": "xterm",
        "datecreated": None, "dateupdated": None, "moniker": "alice",
    }
    row.update(over)
    return row


@pytest.mark.parametrize("addr", ["203.0.113.9", "2001:db8::7"])
def test_build_carries_ipv4_and_ipv6(addr):
    s = session_lib.build(_row(remoteaddr=addr, remoteaddr_source="utmp"))
    assert s["remoteaddr"] == addr
    assert s["remoteaddr_source"] == "utmp"


def test_build_with_no_address_keeps_both_fields_as_none():
    s = session_lib.build(_row())
    assert s["remoteaddr"] is None and s["remoteaddr_source"] is None


def test_build_has_no_ipaddress_key():
    assert "ipaddress" not in session_lib.build(_row())


def test_buildsession_sets_address_and_source(monkeypatch):
    """buildsession records the address and its source on the new session dict."""
    from argparse import Namespace
    from unittest.mock import patch

    from bbsengine6 import util

    monkeypatch.setattr(session_lib.member, "getcurrentmoniker", lambda args, **kw: "alice")
    with patch.object(util, "getremoteaddr", return_value="2001:db8::7"), \
         patch.object(util, "remoteaddr_source", return_value="ssh_env"):
        s = session_lib.buildsession(Namespace(debug=False), sessionid="sid-1")
    assert s["remoteaddr"] == "2001:db8::7"
    assert s["remoteaddr_source"] == "ssh_env"
    assert s["moniker"] == "alice"


def test_buildsession_with_no_address_records_none(monkeypatch):
    from argparse import Namespace
    from unittest.mock import patch

    from bbsengine6 import util

    monkeypatch.setattr(session_lib.member, "getcurrentmoniker", lambda args, **kw: "alice")
    with patch.object(util, "getremoteaddr", return_value=None), \
         patch.object(util, "remoteaddr_source", return_value=None):
        s = session_lib.buildsession(Namespace(debug=False), sessionid="sid-2")
    assert s["remoteaddr"] is None and s["remoteaddr_source"] is None


DSN = os.environ.get("CASINO_TEST_DB") or os.environ.get("BBS_SESSION_CHECK_DB")


@pytest.mark.skipif(not DSN, reason="set BBS_SESSION_CHECK_DB to a test database to check the table")
def test_database_view_exposes_both_fields_and_check_allows_only_known_sources():
    """engine.session exposes both columns, and the CHECK allows exactly utmp and ssh_env.

    Reads the constraint definition rather than inserting, so it does not depend on the
    connecting role having insert rights.
    """
    import argparse

    from bbsengine6 import database

    args = argparse.Namespace(databasename=DSN, debug=False, database=DSN)
    with database.connect(args) as conn, database.cursor(conn) as cur:
        cur.execute(
            "select column_name from information_schema.columns "
            "where table_schema='engine' and table_name='session' "
            "and column_name in ('remoteaddr','remoteaddr_source')"
        )
        cols = {r["column_name"] for r in cur.fetchall()}
        assert cols == {"remoteaddr", "remoteaddr_source"}
        cur.execute(
            "select pg_get_constraintdef(oid) as d from pg_constraint "
            "where conrelid='engine.__session'::regclass and contype='c' "
            "and conname like '%remoteaddr_source%'"
        )
        rows = cur.fetchall()
        assert rows, "no remoteaddr_source CHECK constraint on engine.__session"
        definition = rows[0]["d"]
        assert "utmp" in definition and "ssh_env" in definition
