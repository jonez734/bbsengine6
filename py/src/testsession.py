import argparse
import atexit
import getpass
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from bbsengine6 import database, session


_tracked_pools: list = []


def _cleanup_pools() -> None:
    import gc
    import threading
    import time

    database.reset_pool_cache()

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
            "expiry": datetime.now(timezone.utc) + timedelta(hours=2),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": "testuser",
        }
        result = session.build(rec)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "test-session-id")
        self.assertEqual(result["moniker"], "testuser")

    def test_build_handles_missing_keys(self):
        rec: dict = {
            "id": "test-session-id",
            "expiry": datetime.now(timezone.utc),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": None,
            "useragent": None,
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
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
    def test_buildsession_returns_none_when_no_moniker(
        self, mock_member: MagicMock
    ) -> None:
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
        session.setcurrentsessionid(None)

        result = session.set(self.mock_args, "key", "value")

        self.assertFalse(result)

    @patch("bbsengine6.session.member")
    def test_set_with_passed_connection_commits(self, mock_member: MagicMock) -> None:
        mock_member.getcurrentid.return_value = 1
        session.setcurrentsessionid("test-session-id")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {
            "id": "test-session-id",
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": "testuser",
        }
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = session.set(self.mock_args, "key", "value", conn=mock_conn)

        self.assertEqual(result, "value")
        mock_conn.commit.assert_called()

        session.setcurrentsessionid(None)


class TestGet(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    @patch("bbsengine6.session.getmembersession")
    def test_get_returns_value_from_session_data(
        self, mock_getmembersession: MagicMock
    ) -> None:
        mock_getmembersession.return_value = {
            "data": {"mykey": "myvalue"},
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
        }

        result = session.get(self.mock_args, "mykey")

        self.assertEqual(result, "myvalue")

    @patch("bbsengine6.session.getmembersession")
    def test_get_returns_default_when_key_missing(
        self, mock_getmembersession: MagicMock
    ) -> None:
        mock_getmembersession.return_value = {
            "data": {},
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
        }

        result = session.get(self.mock_args, "missingkey", default="defaultvalue")

        self.assertEqual(result, "defaultvalue")

    @patch("bbsengine6.session.getmembersession")
    def test_get_returns_false_when_no_session(
        self, mock_getmembersession: MagicMock
    ) -> None:
        mock_getmembersession.return_value = None

        result = session.get(self.mock_args, "key")

        self.assertFalse(result)


class TestWrite(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    def test_write_returns_false_when_no_sessionid(self) -> None:
        session.setcurrentsessionid(None)

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
        session.setcurrentsessionid(None)
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    def tearDown(self):
        session.setcurrentsessionid(None)

    @patch("bbsengine6.session.member")
    def test_set_uses_currentsessionid(self, mock_member: MagicMock) -> None:
        mock_member.getcurrentid.return_value = 1
        session.setcurrentsessionid("test-session-id")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {
            "id": "test-session-id",
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": "testuser",
        }
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        result = session.set(self.mock_args, "testkey", "testvalue", pool=mock_pool)

        self.assertEqual(result, "testvalue")
        mock_conn.commit.assert_called()

        session.setcurrentsessionid(None)

    @patch("bbsengine6.session.member")
    def test_set_with_reset_replaces_data(self, mock_member: MagicMock) -> None:
        mock_member.getcurrentid.return_value = 1
        session.setcurrentsessionid("test-session-id")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {
            "id": "test-session-id",
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": "testuser",
        }
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        result = session.set(self.mock_args, "key", "value", reset=True, pool=mock_pool)

        self.assertEqual(result, "value")
        # execute is called twice: once for read(), once for set update
        self.assertEqual(mock_cursor.execute.call_count, 2)
        call_args = mock_cursor.execute.call_args  # Gets the last call
        assert call_args is not None
        sql = call_args[0][0]
        # Convert sql.Composed to string for pattern matching
        sql_str = str(sql)
        # Check for UPDATE and SET keywords which indicate reset behavior
        self.assertIn("UPDATE", sql_str)
        self.assertIn("SET", sql_str)
        self.assertIn("data", sql_str)

        session.setcurrentsessionid(None)

    @patch("bbsengine6.session.member")
    def test_set_without_reset_appends_data(self, mock_member: MagicMock) -> None:
        mock_member.getcurrentid.return_value = 1
        session.setcurrentsessionid("test-session-id")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {
            "id": "test-session-id",
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": "testuser",
        }
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        result = session.set(
            self.mock_args, "key", "value", reset=False, pool=mock_pool
        )

        self.assertEqual(result, "value")
        # execute is called twice: once for read(), once for set update
        self.assertEqual(mock_cursor.execute.call_count, 2)
        call_args = mock_cursor.execute.call_args
        assert call_args is not None
        sql = call_args[0][0]
        # Convert sql.Composed to string for pattern matching
        sql_str = str(sql)
        self.assertIn("data", sql_str)
        self.assertIn("data", sql_str)  # Check it's using data || %s pattern

        session.setcurrentsessionid(None)

    def test_read_uses_currentsessionid_when_not_provided(self) -> None:
        session.setcurrentsessionid("test-session-id")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.rowcount = 0

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        result = session.read(self.mock_args, sessionid=None, pool=mock_pool)

        self.assertIsNone(result)

        session.setcurrentsessionid(None)

    def test_read_returns_none_when_no_sessionid(self) -> None:
        session.setcurrentsessionid(None)

        result = session.read(self.mock_args, sessionid=None)

        self.assertIsNone(result)


class TestSessionConnectionManagement(_TestCaseWithPoolCleanup):
    @classmethod
    def setUpClass(cls):
        cls.args = get_test_args()
        cls.pool = database.getpool(cls.args)
        _tracked_pools.append(cls.pool)

    def setUp(self):
        session.setcurrentsessionid(None)
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    def tearDown(self):
        session.setcurrentsessionid(None)

    @patch("bbsengine6.session.member")
    def test_set_obtains_own_connection_and_commits(
        self, mock_member: MagicMock
    ) -> None:
        mock_member.getcurrentid.return_value = 1
        session.setcurrentsessionid("test-session-id")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {
            "id": "test-session-id",
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": "testuser",
        }
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        result = session.set(self.mock_args, "testkey", "testvalue", pool=mock_pool)

        self.assertEqual(result, "testvalue")
        mock_conn.commit.assert_called()

        session.setcurrentsessionid(None)

    @patch("bbsengine6.database.connect")
    @patch("bbsengine6.session.copy")
    def test_write_obtains_own_connection_and_commits(
        self, mock_copy: MagicMock, mock_connect: MagicMock
    ) -> None:
        session.setcurrentsessionid("test-session-id")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {
            "id": "test-session-id",
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": "testuser",
        }
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
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

        session.setcurrentsessionid(None)

    @patch("bbsengine6.database.connect")
    def test_read_obtains_own_connection(self, mock_connect: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)

        result = session.read(self.mock_args, sessionid="nonexistent", pool=MagicMock())

        self.assertIsNone(result)


class TestCurrentsessionidGlobal(_TestCaseWithPoolCleanup):
    @classmethod
    def setUpClass(cls):
        cls.args = get_test_args()
        cls.pool = database.getpool(cls.args)
        _tracked_pools.append(cls.pool)

    def setUp(self):
        session.setcurrentsessionid(None)

    def tearDown(self):
        session.setcurrentsessionid(None)

    def test_currentsessionid_starts_as_none(self) -> None:
        self.assertIsNone(session.getcurrentsessionid())

    def test_set_sets_currentsessionid(self) -> None:
        session.setcurrentsessionid("my-session-id")
        self.assertEqual(session.getcurrentsessionid(), "my-session-id")

    def test_set_clears_currentsessionid(self) -> None:
        session.setcurrentsessionid("my-session-id")
        session.setcurrentsessionid(None)
        self.assertIsNone(session.getcurrentsessionid())


class TestGetmembersessionErrors(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    @patch("bbsengine6.session.member")
    def test_getmembersession_returns_none_when_moniker_is_none(
        self, mock_member: MagicMock
    ) -> None:
        mock_member.getcurrentmoniker.return_value = None

        result = session.getmembersession(self.mock_args)

        self.assertIsNone(result)
        mock_member.getcurrentmoniker.assert_called_once()

    @patch("bbsengine6.session.member")
    @patch("bbsengine6.session.io")
    def test_getmembersession_logs_error_when_moniker_is_none(
        self, mock_io: MagicMock, mock_member: MagicMock
    ) -> None:
        mock_member.getcurrentmoniker.return_value = None

        session.getmembersession(self.mock_args)

        mock_io.echo.assert_called()
        call_args = mock_io.echo.call_args
        assert call_args is not None
        self.assertIn("You do not exist", str(call_args))

    @patch("bbsengine6.session.member")
    def test_getmembersession_with_explicit_moniker_returns_session(
        self, mock_member: MagicMock
    ) -> None:
        mock_member.getcurrentmoniker.return_value = "testuser"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {
            "id": "test-session-id",
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": "testuser",
        }
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = session.getmembersession(self.mock_args, moniker="testuser", conn=mock_conn)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["moniker"], "testuser")

    @patch("bbsengine6.session.member")
    def test_getmembersession_returns_none_when_no_session_for_moniker(
        self, mock_member: MagicMock
    ) -> None:
        mock_member.getcurrentmoniker.return_value = "nonexistentuser"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = session.getmembersession(self.mock_args, conn=mock_conn)

        self.assertIsNone(result)


class TestBuildsessionErrors(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    @patch("bbsengine6.session.member")
    @patch("bbsengine6.session.io")
    def test_buildsession_returns_none_and_logs_error_when_no_moniker(
        self, mock_io: MagicMock, mock_member: MagicMock
    ) -> None:
        mock_member.getcurrentmoniker.return_value = None

        result = session.buildsession(self.mock_args)

        self.assertIsNone(result)
        mock_io.echo.assert_called()
        call_args = mock_io.echo.call_args
        assert call_args is not None
        self.assertIn("You do not exist", str(call_args))

    @patch("bbsengine6.session.member")
    @patch("bbsengine6.session.os")
    @patch("bbsengine6.session.database")
    def test_buildsession_creates_valid_session_with_moniker(
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


class TestSessionSetErrors(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    @patch("bbsengine6.session.member")
    @patch("bbsengine6.session.io")
    def test_set_returns_none_when_memberid_is_none(
        self, mock_io: MagicMock, mock_member: MagicMock
    ) -> None:
        session.setcurrentsessionid("test-session-id")
        mock_member.getcurrentid.return_value = None

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {
            "id": "test-session-id",
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": "testuser",
        }
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = session.set(self.mock_args, "key", "value", conn=mock_conn)

        self.assertIsNone(result)
        mock_io.echo.assert_called()
        call_args = mock_io.echo.call_args
        assert call_args is not None
        self.assertIn("You do not exist", str(call_args))

        session.setcurrentsessionid(None)

    @patch("bbsengine6.session.member")
    @patch("bbsengine6.session.io")
    def test_set_returns_false_when_session_expired(
        self, mock_io: MagicMock, mock_member: MagicMock
    ) -> None:
        session.setcurrentsessionid("test-session-id")
        mock_member.getcurrentid.return_value = 1

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {
            "id": "test-session-id",
            "expiry": datetime.now(timezone.utc) - timedelta(hours=1),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": "testuser",
        }
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = session.set(self.mock_args, "key", "value", conn=mock_conn)

        self.assertFalse(result)

        session.setcurrentsessionid(None)


class TestSessionStartErrors(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    @patch("bbsengine6.session.member")
    @patch("bbsengine6.session.io")
    def test_start_returns_false_when_buildsession_fails(
        self, mock_io: MagicMock, mock_member: MagicMock
    ) -> None:
        mock_member.getcurrentmoniker.return_value = None

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = session.start(self.mock_args, conn=mock_conn)

        self.assertFalse(result)

    @patch("bbsengine6.session.getmembersession")
    @patch("bbsengine6.session.buildsession")
    @patch("bbsengine6.session.database")
    def test_start_creates_new_session_when_none_exists(
        self, mock_database: MagicMock, mock_buildsession: MagicMock, mock_getmembersession: MagicMock
    ) -> None:
        session.setcurrentsessionid(None)
        mock_getmembersession.return_value = None
        mock_buildsession.return_value = {
            "id": "new-session-id",
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": "testuser",
        }
        mock_database.insert.return_value = "new-session-id"
        mock_database.Jsonb.side_effect = lambda x: x

        mock_pool = MagicMock()
        result = session.start(self.mock_args, pool=mock_pool)

        self.assertTrue(result)
        self.assertEqual(session.getcurrentsessionid(), "new-session-id")

        session.setcurrentsessionid(None)

    @patch("bbsengine6.session.getmembersession")
    @patch("bbsengine6.session.database")
    def test_start_returns_existing_session_when_valid(
        self, mock_database: MagicMock, mock_getmembersession: MagicMock
    ) -> None:
        session.setcurrentsessionid(None)
        mock_getmembersession.return_value = {
            "id": "existing-session-id",
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": "testuser",
        }

        mock_pool = MagicMock()
        result = session.start(self.mock_args, pool=mock_pool)

        self.assertTrue(result)
        self.assertEqual(session.getcurrentsessionid(), "existing-session-id")

        session.setcurrentsessionid(None)


class TestIsValid(unittest.TestCase):
    def test_is_valid_returns_false_for_none(self) -> None:
        result = session.is_valid(None)
        self.assertFalse(result)

    def test_is_valid_returns_false_for_non_dict(self) -> None:
        result = session.is_valid("not a dict")
        self.assertFalse(result)

    def test_is_valid_returns_false_when_no_expiry(self) -> None:
        result = session.is_valid({})
        self.assertFalse(result)

    def test_is_valid_returns_false_when_expiry_is_string(self) -> None:
        result = session.is_valid({"expiry": "some date string"})
        self.assertFalse(result)

    def test_is_valid_returns_false_when_expired(self) -> None:
        result = session.is_valid(
            {"expiry": datetime.now(timezone.utc) - timedelta(hours=1)}
        )
        self.assertFalse(result)

    def test_is_valid_returns_true_when_valid(self) -> None:
        result = session.is_valid(
            {"expiry": datetime.now(timezone.utc) + timedelta(hours=1)}
        )
        self.assertTrue(result)


class TestMemberLookupEdgeCases(unittest.TestCase):
    def setUp(self):
        self.mock_args = MagicMock()
        self.mock_args.debug = False

    @patch("bbsengine6.session.member")
    def test_getmembersession_returns_none_when_member_exists_but_moniker_is_null(
        self, mock_member: MagicMock
    ) -> None:
        mock_member.getcurrentmoniker.return_value = None

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {
            "id": "test-session-id",
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": None,
        }
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = session.getmembersession(self.mock_args, conn=mock_conn)

        self.assertIsNone(result)

    @patch("bbsengine6.session.member")
    @patch("bbsengine6.session.io")
    def test_getmembersession_logs_error_when_member_lookup_returns_none(
        self, mock_io: MagicMock, mock_member: MagicMock
    ) -> None:
        mock_member.getcurrentmoniker.return_value = None

        session.getmembersession(self.mock_args)

        error_calls = [str(call) for call in mock_io.echo.call_args_list]
        self.assertTrue(any("You do not exist" in c for c in error_calls))

    @patch("bbsengine6.session.member")
    @patch("bbsengine6.session.io")
    def test_buildsession_logs_error_when_member_lookup_returns_none(
        self, mock_io: MagicMock, mock_member: MagicMock
    ) -> None:
        mock_member.getcurrentmoniker.return_value = None

        session.buildsession(self.mock_args)

        error_calls = [str(call) for call in mock_io.echo.call_args_list]
        self.assertTrue(any("You do not exist" in c for c in error_calls))

    @patch("bbsengine6.session.member")
    @patch("bbsengine6.session.io")
    def test_set_logs_error_when_memberid_lookup_returns_none(
        self, mock_io: MagicMock, mock_member: MagicMock
    ) -> None:
        session.setcurrentsessionid("test-session-id")
        mock_member.getcurrentid.return_value = None

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {
            "id": "test-session-id",
            "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
            "lastactivity": datetime.now(timezone.utc),
            "data": {},
            "ipaddress": "127.0.0.1",
            "useragent": "test-agent",
            "datecreated": datetime.now(timezone.utc),
            "dateupdated": datetime.now(timezone.utc),
            "moniker": "testuser",
        }
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        session.set(self.mock_args, "key", "value", conn=mock_conn)

        error_calls = [str(call) for call in mock_io.echo.call_args_list]
        self.assertTrue(any("You do not exist" in c for c in error_calls))

        session.setcurrentsessionid(None)


if __name__ == "__main__":
    import sys

    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    _cleanup_pools()

    sys.stderr.flush()
    sys.stdout.flush()

    os._exit(0 if result.wasSuccessful() else 1)
