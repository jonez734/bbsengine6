"""Ctrl-D (EOFError) from the menu is a normal exit, not an error.

database.connect used to log every exception as a traceback at 'connect.400', so a sysop who
pressed Ctrl-D in the member menu saw a stack trace. EOF and Ctrl-C are user exits: the
transaction is rolled back (nothing half-written persists) and the exception still propagates
so the menu loop ends cleanly. Real errors keep their traceback.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import database


def _run_connect(exc):
    pool = MagicMock()
    conn = MagicMock()
    conn.pgconn.transaction_status = 2  # in a transaction
    pool.getconn.return_value = conn
    args = MagicMock(debug=False)
    with patch.object(database.io, "echo_traceback") as tb, patch.object(database.io, "echo"):
        with pytest.raises(type(exc)):
            with database.connect(args, pool=pool, auto_commit=False):
                raise exc
    return conn, tb


@pytest.mark.unit
def test_eof_rolls_back_and_does_not_print_a_traceback():
    conn, tb = _run_connect(EOFError())
    conn.rollback.assert_called()
    tb.assert_not_called()


@pytest.mark.unit
def test_interrupt_rolls_back_and_does_not_print_a_traceback():
    conn, tb = _run_connect(KeyboardInterrupt())
    conn.rollback.assert_called()
    tb.assert_not_called()


@pytest.mark.unit
def test_real_error_still_prints_its_traceback():
    conn, tb = _run_connect(RuntimeError("boom"))
    conn.rollback.assert_called()
    tb.assert_called_once()
