"""database.connect(set_role=False) skips the context role; None still inherits it.

bed's bank and message helpers run definer functions as bed's own login role.
When a logged-in member's role is the context role, an inherited SET LOCAL ROLE
fails for bed. set_role=False must mean "no role switch" and must not reach
rolexists() or Identifier().
"""

import unittest
from unittest.mock import MagicMock, patch

from bbsengine6 import database


class _FakeCursor:
    def __init__(self, log):
        self._log = log

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, stmt, *args, **kwargs):
        self._log.append(stmt)


class _FakeConn:
    def __init__(self):
        self.autocommit = True
        self.executed = []
        self.pgconn = MagicMock(transaction_status=0)

    def cursor(self):
        return _FakeCursor(self.executed)

    def commit(self):
        pass

    def rollback(self):
        pass


class _FakePool:
    def __init__(self):
        self.conn = _FakeConn()

    def getconn(self):
        return self.conn

    def putconn(self, conn):
        pass


def _sql_texts(conn):
    return [str(s) for s in conn.executed]


class TestConnectSetRoleFalse(unittest.TestCase):
    def setUp(self):
        self.args = MagicMock(debug=False)
        self.pool = _FakePool()
        self._token = database._current_db_role.set("jam")

    def tearDown(self):
        database._current_db_role.reset(self._token)

    def test_false_issues_no_set_role_when_context_role_is_set(self):
        with patch.object(database, "rolexists") as rolexists:
            with database.connect(self.args, pool=self.pool, set_role=False):
                pass
        rolexists.assert_not_called()
        self.assertFalse(
            any("SET LOCAL ROLE" in t for t in _sql_texts(self.pool.conn)),
            _sql_texts(self.pool.conn),
        )

    def test_none_still_inherits_context_role(self):
        with patch.object(database, "rolexists", return_value=True):
            with database.connect(self.args, pool=self.pool):
                pass
        self.assertTrue(
            any("SET LOCAL ROLE" in t for t in _sql_texts(self.pool.conn)),
            _sql_texts(self.pool.conn),
        )

    def test_explicit_role_name_still_switches(self):
        with patch.object(database, "rolexists", return_value=True):
            with database.connect(self.args, pool=self.pool, set_role="opencode"):
                pass
        self.assertTrue(
            any("SET LOCAL ROLE" in t for t in _sql_texts(self.pool.conn)),
            _sql_texts(self.pool.conn),
        )


if __name__ == "__main__":
    unittest.main()
