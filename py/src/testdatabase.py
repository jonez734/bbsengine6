import argparse
import getpass
import unittest
from unittest.mock import MagicMock

from psycopg import sql

from bbsengine6 import database


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
    def test_connect_with_no_pool(self):
        mock_args = MagicMock()
        mock_pool = None

        with database.connect(mock_args, pool=mock_pool) as result:
            self.assertIsNone(result)

    def test_connect_with_pool(self):
        mock_args = MagicMock()
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        with database.connect(mock_args, pool=mock_pool) as result:
            self.assertEqual(result, mock_conn)


class TestTransaction(unittest.TestCase):
    def test_transaction_returns_context_manager(self):
        mock_conn = MagicMock()
        mock_tx = MagicMock()
        mock_conn.transaction.return_value = mock_tx

        result = database.transaction(mock_conn)
        self.assertEqual(result, mock_tx)


class TestDatabaseIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args = get_real_args()
        cls.pool = database.getpool(cls.args)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "pool"):
            cls.pool.close()

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


class TestTCPConnection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tcp_args = get_tcp_args()
        cls.tcp_pool = database.getpool(cls.tcp_args)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "tcp_pool"):
            cls.tcp_pool.close()

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


if __name__ == "__main__":
    unittest.main()
