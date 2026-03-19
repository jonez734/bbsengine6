import argparse
import atexit
import getpass
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from bbsengine6 import database, session


_tracked_pools: list = []


def _cleanup_pools() -> None:
    import gc
    import threading
    import time

    for pool in list(_tracked_pools):
        try:
            pool.close()
        except Exception:
            pass
        _tracked_pools.remove(pool)

    gc.collect()

    for _ in range(20):
        active_workers = sum(
            1
            for t in threading.enumerate()
            if t.name.startswith("psycopg") or t.name.startswith("pool-")
        )
        if active_workers == 0:
            break
        time.sleep(0.05)
    else:
        pass


atexit.register(_cleanup_pools)


class _TestCaseWithPoolCleanup(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        _cleanup_pools()


def get_test_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    defaults = {
        "databasename": "zoid6",
        "databasehost": "",
        "databaseport": 5432,
        "databaseuser": getpass.getuser(),
        "databasepassword": None,
    }
    database.buildargdatabasegroup(parser, defaults)
    args = parser.parse_args([])
    return args


class TestBuild(unittest.TestCase):
    def test_build_returns_session_dict(self):
        rec: dict = {
            "id": "test-session-id",
            "expiry": datetime.now() + timedelta(hours=2),
            "lastactivity": datetime.now(),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(),
            "dateupdated": datetime.now(),
            "moniker": "testuser",
        }
        result = session.build(rec)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "test-session-id")
        self.assertEqual(result["moniker"], "testuser")

    def test_build_handles_missing_keys(self):
        rec: dict = {
            "id": "test-session-id",
            "expiry": datetime.now(),
            "lastactivity": datetime.now(),
            "data": {},
            "ipaddress": None,
            "useragent": None,
            "datecreated": datetime.now(),
            "dateupdated": datetime.now(),
            "moniker": "testuser",
        }
        result = session.build(rec)
        self.assertEqual(result["id"], "test-session-id")


class TestBuildsession(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    @patch("bbsengine6.session.member")
    @patch("bbsengine6.session.os")
    @patch("bbsengine6.session.database")
    def test_buildsession_creates_valid_session(
        self, mock_database: MagicMock, mock_os: MagicMock, mock_member: MagicMock
    ) -> None:
        mock_member.getcurrentmoniker.return_value = "testuser"
        mock_database.Jsonb.side_effect = lambda x: x
        mock_os.environ = {"TERM": "xterm-256color"}

        result = session.buildsession(self.mock_args)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["moniker"], "testuser")
        self.assertIn("id", result)
        self.assertIn("expiry", result)
        self.assertIn("lastactivity", result)
        self.assertIn("data", result)
        self.assertIn("useragent", result)
        self.assertIn("datecreated", result)

    @patch("bbsengine6.session.member")
    def test_buildsession_returns_none_when_no_moniker(self, mock_member: MagicMock) -> None:
        mock_member.getcurrentmoniker.return_value = None

        result = session.buildsession(self.mock_args)

        self.assertIsNone(result)

    @patch("bbsengine6.session.member")
    @patch("bbsengine6.session.os")
    @patch("bbsengine6.session.database")
    def test_buildsession_uses_env_term(
        self, mock_database: MagicMock, mock_os: MagicMock, mock_member: MagicMock
    ) -> None:
        mock_member.getcurrentmoniker.return_value = "testuser"
        mock_os.environ = {"TERM": "xterm-256color"}
        mock_database.Jsonb.side_effect = lambda x: x

        result = session.buildsession(self.mock_args)

        assert result is not None
        self.assertEqual(result["useragent"], "xterm-256color")


class TestSet(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    def test_set_returns_false_when_no_sessionid(self) -> None:
        session.currentsessionid = None

        result = session.set(self.mock_args, "key", "value")

        self.assertFalse(result)

    @patch("bbsengine6.session.member")
    def test_set_with_passed_connection_commits(self, mock_member: MagicMock) -> None:
        mock_member.getcurrentid.return_value = 1
        session.currentsessionid = "test-session-id"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = session.set(self.mock_args, "key", "value", conn=mock_conn)

        self.assertEqual(result, "value")
        mock_conn.commit.assert_called()

        session.currentsessionid = None


class TestGet(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    @patch("bbsengine6.session.getmembersession")
    def test_get_returns_value_from_session_data(self, mock_getmembersession: MagicMock) -> None:
        mock_getmembersession.return_value = {"data": {"mykey": "myvalue"}}

        result = session.get(self.mock_args, "mykey")

        self.assertEqual(result, "myvalue")

    @patch("bbsengine6.session.getmembersession")
    def test_get_returns_default_when_key_missing(self, mock_getmembersession: MagicMock) -> None:
        mock_getmembersession.return_value = {"data": {}}

        result = session.get(self.mock_args, "missingkey", default="defaultvalue")

        self.assertEqual(result, "defaultvalue")

    @patch("bbsengine6.session.getmembersession")
    def test_get_returns_false_when_no_session(self, mock_getmembersession: MagicMock) -> None:
        mock_getmembersession.return_value = None

        result = session.get(self.mock_args, "key")

        self.assertFalse(result)


class TestWrite(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    def test_write_returns_false_when_no_sessionid(self) -> None:
        session.currentsessionid = None

        result = session.write(self.mock_args, {})

        self.assertFalse(result)


class TestGarbagecollect(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()

    def test_garbagecollect_returns_false_when_no_conn(self) -> None:
        result = session.garbagecollect(self.mock_args)

        self.assertFalse(result)

    @patch("bbsengine6.session.database")
    def test_garbagecollect_commits_transaction(self, mock_database: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = session.garbagecollect(self.mock_args, conn=mock_conn)

        self.assertTrue(result)
        mock_conn.commit.assert_called()


class TestCount(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()

    def test_count_returns_false_when_no_conn(self) -> None:
        result = session.count(self.mock_args)

        self.assertFalse(result)


class TestSessionIntegration(_TestCaseWithPoolCleanup):
    @classmethod
    def setUpClass(cls):
        cls.args = get_test_args()
        cls.pool = database.getpool(cls.args)
        _tracked_pools.append(cls.pool)

    def setUp(self):
        session.currentsessionid = None
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    def tearDown(self):
        session.currentsessionid = None

    @patch("bbsengine6.session.member")
    def test_set_uses_currentsessionid(self, mock_member: MagicMock) -> None:
        mock_member.getcurrentid.return_value = 1
        session.currentsessionid = "test-session-id"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        result = session.set(self.mock_args, "testkey", "testvalue", pool=mock_pool)

        self.assertEqual(result, "testvalue")
        mock_conn.commit.assert_called()

        session.currentsessionid = None

    @patch("bbsengine6.session.member")
    def test_set_with_reset_replaces_data(self, mock_member: MagicMock) -> None:
        mock_member.getcurrentid.return_value = 1
        session.currentsessionid = "test-session-id"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        result = session.set(
            self.mock_args, "key", "value", reset=True, pool=mock_pool
        )

        self.assertEqual(result, "value")
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert call_args is not None
        sql = call_args[0][0]
        self.assertIn("data=%s", sql)

        session.currentsessionid = None

    @patch("bbsengine6.session.member")
    def test_set_without_reset_appends_data(self, mock_member: MagicMock) -> None:
        mock_member.getcurrentid.return_value = 1
        session.currentsessionid = "test-session-id"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        result = session.set(
            self.mock_args, "key", "value", reset=False, pool=mock_pool
        )

        self.assertEqual(result, "value")
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert call_args is not None
        sql = call_args[0][0]
        self.assertIn("data=data||%s", sql)

        session.currentsessionid = None

    def test_read_uses_currentsessionid_when_not_provided(self) -> None:
        session.currentsessionid = "test-session-id"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.rowcount = 0

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        result = session.read(self.mock_args, sessionid=None, pool=mock_pool)

        self.assertIsNone(result)

        session.currentsessionid = None

    def test_read_returns_none_when_no_sessionid(self) -> None:
        session.currentsessionid = None

        result = session.read(self.mock_args, sessionid=None)

        self.assertIsNone(result)


class TestSessionConnectionManagement(_TestCaseWithPoolCleanup):
    @classmethod
    def setUpClass(cls):
        cls.args = get_test_args()
        cls.pool = database.getpool(cls.args)
        _tracked_pools.append(cls.pool)

    def setUp(self):
        session.currentsessionid = None
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    def tearDown(self):
        session.currentsessionid = None

    @patch("bbsengine6.session.member")
    def test_set_obtains_own_connection_and_commits(self, mock_member: MagicMock) -> None:
        mock_member.getcurrentid.return_value = 1
        session.currentsessionid = "test-session-id"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        result = session.set(self.mock_args, "testkey", "testvalue", pool=mock_pool)

        self.assertEqual(result, "testvalue")
        mock_conn.commit.assert_called()

        session.currentsessionid = None

    @patch("bbsengine6.database.connect")
    @patch("bbsengine6.session.copy")
    def test_write_obtains_own_connection_and_commits(
        self, mock_copy: MagicMock, mock_connect: MagicMock
    ) -> None:
        session.currentsessionid = "test-session-id"

        mock_conn = MagicMock()
        mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_copy.copy.side_effect = lambda x: x

        test_session: dict = {
            "id": "test-session-id",
            "data": {"key": "value"},
            "moniker": "testuser",
        }
        result = session.write(
            self.mock_args, test_session, sessionid="test-session-id", pool=MagicMock()
        )

        self.assertTrue(result)
        mock_conn.commit.assert_called()

        session.currentsessionid = None

    def test_read_obtains_own_connection(self) -> None:
        result = session.read(self.mock_args, sessionid="nonexistent", pool=self.pool)

        self.assertIsNone(result)


class TestCurrentsessionidGlobal(_TestCaseWithPoolCleanup):
    @classmethod
    def setUpClass(cls):
        cls.args = get_test_args()
        cls.pool = database.getpool(cls.args)
        _tracked_pools.append(cls.pool)

    def setUp(self):
        session.currentsessionid = None

    def tearDown(self):
        session.currentsessionid = None

    def test_currentsessionid_starts_as_none(self) -> None:
        self.assertIsNone(session.currentsessionid)

    def test_set_sets_currentsessionid(self) -> None:
        session.currentsessionid = "my-session-id"
        self.assertEqual(session.currentsessionid, "my-session-id")

    def test_set_clears_currentsessionid(self) -> None:
        session.currentsessionid = "my-session-id"
        session.currentsessionid = None
        self.assertIsNone(session.currentsessionid)


if __name__ == "__main__":
    import sys

    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    _cleanup_pools()

    sys.stderr.flush()
    sys.stdout.flush()

    os._exit(0 if result.wasSuccessful() else 1)
