import argparse
import atexit
import datetime
import getpass
import os
import unittest
from unittest.mock import MagicMock, patch

from psycopg import sql
from psycopg.types.json import Jsonb

from bbsengine6 import database

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


def get_real_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    defaults = {
        "databasename": "zoid6",
        "databasehost": "",  # Empty string - defaults to Unix socket
        "databaseport": 5432,
        "databaseuser": getpass.getuser(),
        "databasepassword": None,
    }
    database.buildargdatabasegroup(parser, defaults)
    args = parser.parse_args([])
    return args


def get_tcp_args():
    """Args for TCP connection to localhost."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    defaults = {
        "databasename": "zoid6",
        "databasehost": "localhost",
        "databaseport": 5432,
        "databaseuser": getpass.getuser(),
        "databasepassword": None,
    }
    database.buildargdatabasegroup(parser, defaults)
    args = parser.parse_args([])
    return args


class TestTableIdentifier(unittest.TestCase):
    def test_simple_table_name(self):
        result = database._table_identifier("users")
        self.assertIsInstance(result, sql.Identifier)
        self.assertEqual(result.as_string(), '"users"')

    def test_schema_qualified_table_name(self):
        result = database._table_identifier("public.users")
        self.assertIsInstance(result, sql.Identifier)
        self.assertEqual(result.as_string(), '"public"."users"')

    def test_custom_schema_table_name(self):
        result = database._table_identifier("myschema.mytable")
        self.assertIsInstance(result, sql.Identifier)
        self.assertEqual(result.as_string(), '"myschema"."mytable"')


class TestMogrifySQL(unittest.TestCase):
    def setUp(self):
        self.mock_cursor = MagicMock()

    def test_none_value(self):
        result = database.mogrifysql(
            self.mock_cursor, "SELECT * FROM t WHERE x = %s", (None,)
        )
        self.assertEqual(result, "SELECT * FROM t WHERE x = NULL")

    def test_integer_value(self):
        result = database.mogrifysql(
            self.mock_cursor, "SELECT * FROM t WHERE id = %s", (42,)
        )
        self.assertEqual(result, "SELECT * FROM t WHERE id = 42")

    def test_float_value(self):
        result = database.mogrifysql(
            self.mock_cursor, "SELECT * FROM t WHERE val = %s", (3.14,)
        )
        self.assertEqual(result, "SELECT * FROM t WHERE val = 3.14")

    def test_boolean_value(self):
        result = database.mogrifysql(
            self.mock_cursor, "SELECT * FROM t WHERE active = %s", (True,)
        )
        self.assertEqual(result, "SELECT * FROM t WHERE active = True")

    def test_string_value(self):
        result = database.mogrifysql(
            self.mock_cursor, "SELECT * FROM t WHERE name = %s", ("test",)
        )
        self.assertEqual(result, "SELECT * FROM t WHERE name = 'test'")

    def test_string_with_single_quote(self):
        result = database.mogrifysql(
            self.mock_cursor, "SELECT * FROM t WHERE name = %s", ("O'Brien",)
        )
        self.assertEqual(result, "SELECT * FROM t WHERE name = 'O''Brien'")

    def test_string_with_multiple_quotes(self):
        result = database.mogrifysql(
            self.mock_cursor,
            "SELECT * FROM t WHERE name = %s",
            ("it's a test's value",),
        )
        self.assertEqual(result, "SELECT * FROM t WHERE name = 'it''s a test''s value'")

    def test_multiple_params(self):
        result = database.mogrifysql(
            self.mock_cursor, "SELECT * FROM t WHERE a = %s AND b = %s", (1, "test")
        )
        self.assertEqual(result, "SELECT * FROM t WHERE a = 1 AND b = 'test'")

    def test_invalid_format_string(self):
        result = database.mogrifysql(self.mock_cursor, "SELECT * FROM t", (1,))
        self.assertEqual(result, "SELECT * FROM t [param interpolation failed]")


class TestParseDSN(unittest.TestCase):
    def test_simple_dsn(self):
        result = database.parse_dsn("host=localhost dbname=test")
        self.assertEqual(result, {"host": "localhost", "dbname": "test"})

    def test_full_dsn(self):
        result = database.parse_dsn(
            "host=localhost dbname=test user=admin password=secret port=5432"
        )
        self.assertEqual(
            result,
            {
                "host": "localhost",
                "dbname": "test",
                "user": "admin",
                "password": "secret",
                "port": "5432",
            },
        )

    def test_dsn_with_empty_values(self):
        result = database.parse_dsn("host=localhost dbname=")
        self.assertEqual(result, {"host": "localhost", "dbname": ""})

    def test_dsn_with_value_containing_equals(self):
        result = database.parse_dsn(
            "host=localhost dbname=test connection=host=1.2.3.4"
        )
        self.assertEqual(
            result,
            {"host": "localhost", "dbname": "test", "connection": "host=1.2.3.4"},
        )

    def test_dsn_with_missing_value(self):
        result = database.parse_dsn("host localhost")
        self.assertEqual(result, {})

    def test_empty_dsn(self):
        result = database.parse_dsn("")
        self.assertEqual(result, {})

    def test_dsn_with_only_spaces(self):
        result = database.parse_dsn("   ")
        self.assertEqual(result, {})


class TestMakeDSN(unittest.TestCase):
    def test_make_dsn_with_all_args(self):
        args = MagicMock()
        args.databasename = "testdb"
        args.databaseuser = "testuser"
        args.databasepassword = "testpass"
        args.databasehost = "localhost"
        args.databaseport = 5432

        result = database.make_dsn(args)
        self.assertIn("dbname=testdb", result)
        self.assertIn("user=testuser", result)
        self.assertIn("password=testpass", result)
        self.assertIn("host=localhost", result)
        self.assertIn("port=5432", result)

    def test_make_dsn_with_kwargs_override(self):
        args = MagicMock()
        args.databasename = "testdb"
        args.databaseuser = "testuser"
        args.databasepassword = "testpass"
        args.databasehost = "localhost"
        args.databaseport = 5432

        result = database.make_dsn(args, dbname="overridedb")
        self.assertIn("dbname=overridedb", result)
        self.assertNotIn("dbname=testdb", result)

    def test_make_dsn_missing_attributes(self):
        args = MagicMock(spec=[])  # No database attributes
        args.databasename = "defaultdb"
        args.databaseuser = None
        args.databasepassword = None
        args.databasehost = None
        args.databaseport = 5432

        result = database.make_dsn(args)
        self.assertIn("dbname=defaultdb", result)
        self.assertIn("port=5432", result)
        self.assertNotIn("user=", result)
        self.assertNotIn("password=", result)
        self.assertNotIn("host=", result)


class TestBuildArgs(unittest.TestCase):
    def test_buildargs_returns_none(self):
        parser = argparse.ArgumentParser()
        result = database.buildargs(parser)
        self.assertIsNone(result)

    def test_buildargs_adds_database_group(self):
        parser = argparse.ArgumentParser()
        database.buildargs(parser)
        args = parser.parse_args([])
        self.assertEqual(args.databasename, "zoid6")
        self.assertEqual(args.databaseport, 5432)

    def test_buildargs_with_defaults(self):
        parser = argparse.ArgumentParser()
        defaults = {"databasename": "customdb", "databasehost": "remotehost"}
        database.buildargs(parser, defaults=defaults)
        args = parser.parse_args([])
        self.assertEqual(args.databasename, "customdb")
        self.assertEqual(args.databasehost, "remotehost")

    def test_buildargs_suppress_help(self):
        parser = argparse.ArgumentParser()
        database.buildargs(parser, suppress=True)
        args = parser.parse_args(["--databasename", "test"])
        self.assertEqual(args.databasename, "test")

    def test_buildargs_custom_label(self):
        parser = argparse.ArgumentParser()
        database.buildargs(parser, label="custom label")
        groups = [g.title for g in parser._action_groups]
        self.assertIn("custom label", groups)


class TestResultIter(unittest.TestCase):
    def test_resultiter_with_no_filter(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchmany.side_effect = [[(1, "a"), (2, "b")], [(3, "c")], []]

        results = list(database.resultiter(mock_cursor))
        self.assertEqual(results, [(1, "a"), (2, "b"), (3, "c")])
        self.assertEqual(mock_cursor.fetchmany.call_count, 3)

    def test_resultiter_with_filter(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchmany.side_effect = [[(1, "a"), (2, "b"), (3, "c")], []]

        def filter_func(row, **kwargs):
            return row[0] > 1

        results = list(database.resultiter(mock_cursor, filterfunc=filter_func))
        self.assertEqual(results, [(2, "b"), (3, "c")])

    def test_resultiter_empty_cursor(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchmany.return_value = []

        results = list(database.resultiter(mock_cursor))
        self.assertEqual(results, [])

    def test_resultiter_custom_arraysize(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchmany.return_value = [(1,)]
        mock_cursor.fetchmany.side_effect = [[(1,)], [(2,)], []]

        results = list(database.resultiter(mock_cursor, arraysize=1))
        self.assertEqual(len(results), 2)
        mock_cursor.fetchmany.assert_called_with(1)


class TestCommit(unittest.TestCase):
    def test_commit_with_connection(self):
        mock_conn = MagicMock()
        mock_args = MagicMock()
        result = database.commit(mock_args, conn=mock_conn)
        self.assertTrue(result)
        mock_conn.commit.assert_called_once()

    def test_commit_without_connection(self):
        mock_args = MagicMock()
        result = database.commit(mock_args, conn=None)
        self.assertFalse(result)


class TestRollback(unittest.TestCase):
    def test_rollback_with_connection(self):
        mock_conn = MagicMock()
        mock_args = MagicMock()
        database.rollback(mock_args, conn=mock_conn)
        mock_conn.rollback.assert_called_once()

    def test_rollback_without_connection(self):
        mock_args = MagicMock()
        database.rollback(mock_args, conn=None)


class TestCursor(unittest.TestCase):
    def test_cursor_with_default_row_factory(self):
        from psycopg.rows import dict_row

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        database.cursor(mock_conn)
        mock_conn.cursor.assert_called_once_with(row_factory=dict_row)


class TestConnect(unittest.TestCase):
    @patch("bbsengine6.database.getpool")
    def test_connect_works_as_context_manager(self, mock_getpool):
        mock_args = MagicMock()
        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_getpool.return_value = mock_pool

        with database.connect(mock_args, pool=mock_pool) as conn:
            self.assertEqual(conn, mock_conn)
        mock_pool.putconn.assert_called_once_with(mock_conn)

    @patch("bbsengine6.database.getpool")
    def test_connect_autocommit_false(self, mock_getpool):
        mock_args = MagicMock()
        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_getpool.return_value = mock_pool

        with database.connect(mock_args, pool=mock_pool) as conn:
            self.assertEqual(conn, mock_conn)
        self.assertFalse(mock_conn.autocommit)

    @patch("bbsengine6.database.getpool")
    def test_connect_removes_readonly_kwarg(self, mock_getpool):
        mock_args = MagicMock()
        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_getpool.return_value = mock_pool

        with database.connect(mock_args, pool=mock_pool, readonly=True):
            pass
        mock_getpool.assert_not_called()


class TestTransaction(unittest.TestCase):
    def test_transaction_returns_context_manager(self):
        mock_conn = MagicMock()
        mock_tx = MagicMock()
        mock_conn.transaction.return_value = mock_tx

        result = database.transaction(mock_conn)
        self.assertEqual(result, mock_tx)


class TestDatabaseIntegration(_TestCaseWithPoolCleanup):
    @classmethod
    def setUpClass(cls):
        cls.args = get_real_args()
        cls.pool = database.getpool(cls.args)
        _tracked_pools.append(cls.pool)

    def test_connect_to_real_database(self):
        with database.connect(self.args, pool=self.pool) as conn:
            self.assertIsNotNone(conn)

    def test_make_dsn_empty_host_omitted(self):
        dsn = database.make_dsn(self.args)
        self.assertNotIn("host=", dsn)
        self.assertIn("dbname=zoid6", dsn)
        self.assertIn("user=opencode", dsn)

    def test_make_dsn_with_explicit_host(self):
        tcp_args = get_tcp_args()
        dsn = database.make_dsn(tcp_args)
        self.assertIn("host=localhost", dsn)
        self.assertIn("dbname=zoid6", dsn)

    def test_cursor_creation(self):
        with database.connect(self.args, pool=self.pool) as conn:
            with database.cursor(conn) as cur:
                cur.execute("SELECT 1 as val")
                result = cur.fetchone()
                self.assertEqual(result["val"], 1)

    def test_insert_and_select(self):
        with database.connect(self.args, pool=self.pool) as conn:
            with database.cursor(conn) as cur:
                cur.execute("SELECT relname FROM pg_class WHERE relkind = 'r' LIMIT 1")
                row = cur.fetchone()
                self.assertIsNotNone(row)
                self.assertIn("relname", row)

    def test_schema_exists(self):
        result = database.schemaexists(self.args, "public", pool=self.pool)
        self.assertTrue(result)

    def test_schema_not_exists(self):
        result = database.schemaexists(
            self.args, "nonexistent_schema_xyz", pool=self.pool
        )
        self.assertFalse(result)

    def test_table_exists(self):
        result = database.tableexists(
            self.args, "pg_catalog", "pg_class", pool=self.pool
        )
        self.assertTrue(result)

    def test_table_not_exists(self):
        result = database.tableexists(
            self.args, "public", "nonexistent_table_xyz", pool=self.pool
        )
        self.assertFalse(result)

    def test_rolexists(self):
        result = database.rolexists(self.args, "postgres", conn=self.pool.getconn())
        self.assertTrue(result)
        self.pool.putconn(self.pool.getconn())

    def test_rolexists_nonexistent(self):
        with database.connect(self.args, pool=self.pool) as conn:
            result = database.rolexists(self.args, "nonexistent_role_xyz", conn=conn)
            self.assertFalse(result)

    def test_exists_database(self):
        result = database.exists(self.args, "zoid6", pool=self.pool)
        self.assertTrue(result)

    def test_exists_database_false(self):
        result = database.exists(self.args, "nonexistent_database_xyz", pool=self.pool)
        self.assertFalse(result)

    def test_commit_with_real_connection(self):
        with database.connect(self.args, pool=self.pool) as conn:
            result = database.commit(self.args, conn=conn)
            self.assertTrue(result)

    def test_rollback_with_real_connection(self):
        with database.connect(self.args, pool=self.pool) as conn:
            database.rollback(self.args, conn=conn)

    def test_transaction_real_connection(self):
        with database.connect(self.args, pool=self.pool) as conn:
            tx = database.transaction(conn)
            self.assertIsNotNone(tx)

    def test_getoid(self):
        with database.connect(self.args, pool=self.pool) as conn:
            cur = conn.cursor()
            oid = database.getoid(self.args, "int4", cur=cur)
            self.assertIsNotNone(oid)
            self.assertIsInstance(oid, int)
            cur.close()

    def test_parse_dsn_real(self):
        dsn = "host=/var/run/postgresql port=5432 dbname=zoid6 user=opencode"
        result = database.parse_dsn(dsn)
        self.assertEqual(result["host"], "/var/run/postgresql")
        self.assertEqual(result["dbname"], "zoid6")
        self.assertEqual(result["user"], "opencode")

    def test_resultiter_real(self):
        with database.connect(self.args, pool=self.pool) as conn:
            with database.cursor(conn) as cur:
                cur.execute("SELECT generate_series(1, 5) as num")
                results = list(database.resultiter(cur))
                self.assertEqual(len(results), 5)
                self.assertEqual(results[0]["num"], 1)
                self.assertEqual(results[4]["num"], 5)


class TestTCPConnection(_TestCaseWithPoolCleanup):
    @classmethod
    def setUpClass(cls):
        cls.tcp_args = get_tcp_args()
        cls.tcp_pool = database.getpool(cls.tcp_args)
        _tracked_pools.append(cls.tcp_pool)

    def test_tcp_connect_to_database(self):
        with database.connect(self.tcp_args, pool=self.tcp_pool) as conn:
            self.assertIsNotNone(conn)

    def test_tcp_cursor_query(self):
        with database.connect(self.tcp_args, pool=self.tcp_pool) as conn:
            with database.cursor(conn) as cur:
                cur.execute("SELECT 1 as val")
                result = cur.fetchone()
                self.assertEqual(result["val"], 1)

    def test_tcp_schema_exists(self):
        result = database.schemaexists(self.tcp_args, "public", pool=self.tcp_pool)
        self.assertTrue(result)

    def test_tcp_rolexists(self):
        with database.connect(self.tcp_args, pool=self.tcp_pool) as conn:
            result = database.rolexists(self.tcp_args, "postgres", conn=conn)
            self.assertTrue(result)

    def test_tcp_resultiter(self):
        with database.connect(self.tcp_args, pool=self.tcp_pool) as conn:
            with database.cursor(conn) as cur:
                cur.execute("SELECT generate_series(1, 3) as num")
                results = list(database.resultiter(cur))
                self.assertEqual(len(results), 3)


class TestUnixSocketDefault(unittest.TestCase):
    def test_make_dsn_empty_string_host_omitted(self):
        args = get_real_args()
        dsn = database.make_dsn(args)
        self.assertNotIn("host=", dsn)
        self.assertIn("dbname=zoid6", dsn)
        self.assertNotIn("password=", dsn)

    def test_make_dsn_none_host_omitted(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true", default=False)
        defaults = {
            "databasename": "testdb",
            "databasehost": None,
            "databaseport": 5432,
            "databaseuser": "testuser",
            "databasepassword": None,
        }
        database.buildargdatabasegroup(parser, defaults)
        args = parser.parse_args([])
        dsn = database.make_dsn(args)
        self.assertNotIn("host=", dsn)
        self.assertIn("dbname=testdb", dsn)


class TestSQLInjectionParseDSN(unittest.TestCase):
    def test_parse_dsn_malicious_host(self):
        dsn = "host=localhost'; DROP TABLE users;--"
        result = database.parse_dsn(dsn)
        self.assertIsInstance(result, dict)
        self.assertIn("host", result)

    def test_parse_dsn_injection_in_dbname(self):
        dsn = "dbname=zoid6'; DELETE FROM users;--"
        result = database.parse_dsn(dsn)
        self.assertIsInstance(result, dict)
        self.assertIn("dbname", result)

    def test_parse_dsn_no_key_value(self):
        dsn = "just some text without equals"
        result = database.parse_dsn(dsn)
        self.assertEqual(result, {})

    def test_parse_dsn_equals_in_value(self):
        dsn = "host=localhost port=5432 connection=host=1.2.3.4"
        result = database.parse_dsn(dsn)
        self.assertEqual(result["host"], "localhost")
        self.assertEqual(result["connection"], "host=1.2.3.4")

    def test_parse_dsn_empty_value_handled(self):
        dsn = "host= dbname=test"
        result = database.parse_dsn(dsn)
        self.assertEqual(result.get("host"), "")


class TestSQLInjectionMogrify(unittest.TestCase):
    def test_mogrifysql_escapes_single_quotes(self):
        result = database.mogrifysql(
            MagicMock(),
            "SELECT * FROM t WHERE x = %s",
            ("'; DROP TABLE users;--",),
        )
        self.assertIn("''", result)
        self.assertIn("DROP TABLE users", result)

    def test_mogrifysql_or_injection(self):
        result = database.mogrifysql(
            MagicMock(),
            "SELECT * FROM t WHERE x = %s",
            ("' OR '1'='1",),
        )
        self.assertIn("'' OR ''", result)

    def test_mogrifysql_double_quotes(self):
        result = database.mogrifysql(
            MagicMock(),
            "SELECT * FROM t WHERE x = %s",
            ('Robert"); DROP TABLE users;--',),
        )
        self.assertIsInstance(result, str)
        self.assertIn("DROP TABLE users", result)

    def test_mogrifysql_multiple_quotes(self):
        result = database.mogrifysql(
            MagicMock(),
            "SELECT * FROM t WHERE x = %s",
            ("user's name''; DELETE--",),
        )
        self.assertNotIn("DELETE--',", result)


class TestSQLInjectionTableIdentifier(unittest.TestCase):
    def test_table_identifier_quotes_malicious_name(self):
        malicious = "users; DROP TABLE"
        result = database._table_identifier(malicious)
        self.assertIn('"', result.as_string())
        self.assertIn("DROP TABLE", result.as_string())

    def test_table_identifier_schema_injection(self):
        malicious = "public'; DROP TABLE users;--"
        result = database._table_identifier(malicious)
        self.assertIn('"', result.as_string())

    def test_table_identifier_double_quote_attempt(self):
        malicious = 'users" DROP TABLE'
        result = database._table_identifier(malicious)
        self.assertIn('"', result.as_string())


class TestSQLInjectionIntegration(_TestCaseWithPoolCleanup):
    @classmethod
    def setUpClass(cls):
        cls.args = get_real_args()
        cls.pool = database.getpool(cls.args)
        _tracked_pools.append(cls.pool)

    def test_classexists_malicious_name(self):
        malicious = "'; DROP TABLE pg_class;--"
        result = database.classexists(self.args, malicious, pool=self.pool)
        self.assertFalse(result)
        self.assertTrue(
            database.tableexists(self.args, "pg_catalog", "pg_class", pool=self.pool)
        )

    def test_schemaexists_malicious_name(self):
        malicious = "'; DELETE FROM pg_class;--"
        result = database.schemaexists(self.args, malicious, pool=self.pool)
        self.assertFalse(result)
        self.assertTrue(database.schemaexists(self.args, "public", pool=self.pool))

    def test_tableexists_malicious_schema(self):
        malicious_schema = "pg_catalog'; DROP TABLE users"
        result = database.tableexists(
            self.args, malicious_schema, "pg_class", pool=self.pool
        )
        self.assertFalse(result)

    def test_tableexists_malicious_table(self):
        malicious_table = "pg_class'; DELETE FROM users"
        result = database.tableexists(
            self.args, "pg_catalog", malicious_table, pool=self.pool
        )
        self.assertFalse(result)

    def test_insert_malicious_column_names(self):
        malicious_columns = {
            "id'; DROP TABLE users;--": 1,
            "name'; DELETE FROM users;--": "test",
        }
        result = database.insert(
            self.args,
            "pg_class",
            malicious_columns,
            pool=self.pool,
            returnid=False,
        )
        self.assertFalse(result)
        self.assertTrue(
            database.tableexists(self.args, "pg_catalog", "pg_class", pool=self.pool)
        )


class TestConvertForJsonb(unittest.TestCase):
    def test_passthrough_strings(self):
        self.assertEqual(database.convert_for_jsonb("test"), "test")
        self.assertEqual(database.convert_for_jsonb(""), "")

    def test_passthrough_numbers(self):
        self.assertEqual(database.convert_for_jsonb(42), 42)
        self.assertEqual(database.convert_for_jsonb(3.14), 3.14)

    def test_passthrough_booleans(self):
        self.assertEqual(database.convert_for_jsonb(True), True)
        self.assertEqual(database.convert_for_jsonb(False), False)

    def test_passthrough_none(self):
        self.assertIsNone(database.convert_for_jsonb(None))

    def test_convert_type_to_string(self):
        result = database.convert_for_jsonb(int)
        self.assertEqual(result, "<class 'int'>")

    def test_convert_type_nested_in_dict(self):
        result = database.convert_for_jsonb({"key": int, "other": "value"})
        self.assertIsInstance(result, Jsonb)
        self.assertEqual(result.obj["key"], "<class 'int'>")
        self.assertEqual(result.obj["other"], "value")

    def test_convert_type_nested_in_list(self):
        result = database.convert_for_jsonb([int, "string", 123])
        self.assertIsInstance(result, Jsonb)
        self.assertEqual(result.obj[0], "<class 'int'>")
        self.assertEqual(result.obj[1], "string")
        self.assertEqual(result.obj[2], 123)

    def test_convert_type_nested_in_tuple(self):
        result = database.convert_for_jsonb((int, "string"))
        self.assertIsInstance(result, Jsonb)
        self.assertEqual(result.obj[0], "<class 'int'>")
        self.assertEqual(result.obj[1], "string")

    def test_convert_datetime_to_isoformat(self):
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.timezone.utc)
        result = database.convert_for_jsonb(dt)
        self.assertEqual(result, "2024-01-15T10:30:00+00:00")

    def test_convert_datetime_in_dict(self):
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.timezone.utc)
        result = database.convert_for_jsonb({"timestamp": dt})
        self.assertIsInstance(result, Jsonb)
        self.assertEqual(result.obj["timestamp"], "2024-01-15T10:30:00+00:00")

    def test_convert_dict_with_mixed_values(self):
        data = {
            "string": "value",
            "number": 42,
            "nested": {"inner": int, "datetime": datetime.datetime.now()},
            "list": [str, 1, True],
        }
        result = database.convert_for_jsonb(data)
        self.assertIsInstance(result, Jsonb)
        self.assertEqual(result.obj["string"], "value")
        self.assertEqual(result.obj["number"], 42)
        # Inner dict is a plain dict (not wrapped in Jsonb) so we index
        # it directly rather than via .obj.
        nested = result.obj["nested"]
        self.assertIsInstance(nested, dict)
        self.assertEqual(nested["inner"], "<class 'int'>")
        self.assertIsInstance(nested["datetime"], str)
        # Inner list is also plain (not wrapped in Jsonb).
        lst = result.obj["list"]
        self.assertIsInstance(lst, list)
        self.assertEqual(lst[0], "<class 'str'>")

    def test_convert_datetime_naive(self):
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0)
        result = database.convert_for_jsonb(dt)
        self.assertEqual(result, "2024-01-15T10:30:00")

    def test_convert_datetime_with_timezone(self):
        tz = datetime.timezone(datetime.timedelta(hours=-5))
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=tz)
        result = database.convert_for_jsonb(dt)
        self.assertEqual(result, "2024-01-15T10:30:00-05:00")

    def test_jsonb_passthrough(self):
        original = Jsonb({"key": "value"})
        result = database.convert_for_jsonb(original)
        self.assertEqual(result, original)

    def test_convert_unknown_type_to_string(self):
        class CustomClass:
            pass

        obj = CustomClass()
        result = database.convert_for_jsonb(obj)
        self.assertIsInstance(result, str)


class TestExecute(_TestCaseWithPoolCleanup):
    @classmethod
    def setUpClass(cls):
        cls.args = get_real_args()
        cls.pool = database.getpool(cls.args)
        _tracked_pools.append(cls.pool)

    def test_execute_with_simple_params(self):
        with database.connect(self.args, pool=self.pool) as conn:
            with database.cursor(conn) as cur:
                database.execute(cur, "SELECT 1 as val, 'test' as name")
                result = cur.fetchone()
                self.assertEqual(result["val"], 1)
                self.assertEqual(result["name"], "test")

    def test_execute_with_type_object(self):
        with database.connect(self.args, pool=self.pool) as conn:
            with database.cursor(conn) as cur:
                query = "SELECT %s::text as type_name"
                database.execute(cur, query, int)
                result = cur.fetchone()
                self.assertEqual(result["type_name"], "<class 'int'>")

    def test_execute_with_datetime(self):
        with database.connect(self.args, pool=self.pool) as conn:
            with database.cursor(conn) as cur:
                query = "SELECT %s::timestamptz as ts"
                dt = datetime.datetime(
                    2024, 1, 15, 10, 30, 0, tzinfo=datetime.timezone.utc
                )
                database.execute(cur, query, dt)
                result = cur.fetchone()
                self.assertIn("2024-01-15", result["ts"].isoformat())

    def test_execute_with_dict_param(self):
        with database.connect(self.args, pool=self.pool) as conn:
            with database.cursor(conn) as cur:
                query = "SELECT (%s::jsonb)->'key' as value"
                database.execute(cur, query, {"key": "value"})
                result = cur.fetchone()
                self.assertEqual(result["value"], "value")

    def test_execute_with_dict_containing_type(self):
        with database.connect(self.args, pool=self.pool) as conn:
            with database.cursor(conn) as cur:
                query = "SELECT (%s::jsonb)->>'type_key' as type_str"
                database.execute(cur, query, {"type_key": int})
                result = cur.fetchone()
                self.assertEqual(result["type_str"], "<class 'int'>")


if __name__ == "__main__":
    import sys

    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    _cleanup_pools()

    sys.stderr.flush()
    sys.stdout.flush()

    os._exit(0 if result.wasSuccessful() else 1)
