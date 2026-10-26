"""A lost database connection ends the member menu with one message, not a traceback.

Reproduces the crash seen when the server dropped the session during a member edit: the
psycopg errors AdminShutdown / OperationalError escaped the menu, and the rollback in
database.connect raised again while handling them.
"""

from unittest.mock import patch

import psycopg
import pytest

from bbsengine6 import database
from bbsengine6.console import member as cm


class _FakeConn:
    closed = True
    broken = True

    def rollback(self):
        raise psycopg.OperationalError("the connection is lost")


@pytest.mark.unit
def _parser_stub():
    import types
    return types.SimpleNamespace(parse_args=lambda: types.SimpleNamespace(databasename="zoid6", databasehost="localhost", databaseport=5432))


def test_menu_returns_cleanly_when_the_connection_is_lost_during_an_edit():
    out = []
    with patch.object(cm.lib, "buildargs", return_value=_parser_stub()), \
         patch.object(cm, "_menu_pass", side_effect=psycopg.OperationalError("the connection is lost")), \
         patch.object(cm.io, "echo", side_effect=lambda *a, **k: out.append(str(a[0]) if a else "")), \
         patch.object(cm.util, "heading"):
        rc = cm.main(type("A", (), {})(), pool=object())
    assert rc is False
    text = "\n".join(out)
    assert "the database connection was lost" in text
    assert "Nothing from the interrupted action was saved." in text


@pytest.mark.unit
def test_connect_does_not_raise_again_when_rollback_fails_on_a_lost_connection():
    conn = _FakeConn()
    # _safe_rollback must absorb the failure and report it, not raise.
    with patch.object(database.io, "echo"):
        assert database._safe_rollback(conn) is False


@pytest.mark.unit
def test_a_lost_connection_is_not_returned_to_the_pool():
    class _Pool:
        def __init__(self):
            self.returned = []

        def putconn(self, c):
            self.returned.append(c)

    pool = _Pool()
    conn = _FakeConn()
    database._end_transaction_on_exit(conn, pool, auto_commit=False, exception_occurred=True)
    assert pool.returned == [conn]  # putconn is still called so the pool releases the slot


@pytest.mark.unit
def test_normal_quit_is_unchanged():
    with patch.object(cm.lib, "buildargs", return_value=_parser_stub()), \
         patch.object(cm, "_menu_pass", return_value=True), patch.object(cm.io, "echo"):
        assert cm.main(type("A", (), {})(), pool=object()) is True
