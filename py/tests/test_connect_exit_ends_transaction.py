"""A clean exit from database.connect must not return an open transaction to the pool.

With auto_commit=False, the console's read-only loop left the transaction open, so psycopg_pool
logged 'rolling back returned connection' (INTRANS) on exit. A clean exit now ends the
transaction itself: rollback when nothing was written, so the pool never sees INTRANS.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import database


def _pool_and_conn(status):
    conn = MagicMock()
    conn.pgconn.transaction_status = status
    pool = MagicMock()
    pool.getconn.return_value = conn
    return pool, conn


@pytest.mark.unit
def test_clean_exit_with_open_transaction_rolls_back_before_putconn():
    pool, conn = _pool_and_conn(2)  # 2 = INTRANS
    # The exit path ends the transaction first, then returns the connection.
    order = []
    conn.rollback.side_effect = lambda: order.append("rollback")
    pool.putconn.side_effect = lambda c: order.append("putconn")
    database._end_transaction_on_exit(conn, pool, auto_commit=False, exception_occurred=False)
    assert order == ["rollback", "putconn"], order


@pytest.mark.unit
def test_clean_exit_idle_connection_is_returned_without_rollback():
    pool, conn = _pool_and_conn(0)  # 0 = IDLE
    database._end_transaction_on_exit(conn, pool, auto_commit=False, exception_occurred=False)
    conn.rollback.assert_not_called()
    pool.putconn.assert_called_once_with(conn)


@pytest.mark.unit
def test_auto_commit_still_commits_on_clean_exit():
    pool, conn = _pool_and_conn(2)
    database._end_transaction_on_exit(conn, pool, auto_commit=True, exception_occurred=False)
    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()
    pool.putconn.assert_called_once_with(conn)


@pytest.mark.unit
def test_exception_exit_never_commits():
    pool, conn = _pool_and_conn(2)
    database._end_transaction_on_exit(conn, pool, auto_commit=True, exception_occurred=True)
    conn.commit.assert_not_called()
    pool.putconn.assert_called_once_with(conn)
