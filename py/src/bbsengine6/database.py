import copy
from typing import Any, Iterator

import argparse

from psycopg.rows import dict_row
import psycopg
import psycopg.sql

from psycopg import sql
from psycopg.types.json import Jsonb  # noqa: F401

from psycopg_pool import ConnectionPool

from . import io, util

DEFAULTDATABASE = "postgres"


def _table_identifier(table: str):
    """Create proper SQL identifier for schema-qualified table names.

    Args:
      table: Table name, optionally qualified with schema (e.g., 'empyre.__player')

    Returns:
      sql.Identifier for the table
    """
    if "." in table:
        schema, table_name = table.split(".", 1)
        return sql.Identifier(schema, table_name)
    return sql.Identifier(table)


def getoid(args: Any, typ: str, cur: Any = None) -> int | None:
    """Get the OID for a PostgreSQL type.

    Args:
      args: Application args (used to get connection if cur is None)
      typ: PostgreSQL type name (e.g., 'jsonb', 'varchar')
      cur: Optional cursor to use

    Returns:
      OID as int, or None if type not found
    """

    def _work(cur):
        sql = "SELECT oid FROM pg_type WHERE typname = %s"
        dat = (typ,)
        cur.execute(sql, dat)
        oid = cur.fetchone()
        if oid:
            return oid[0]
        else:
            return None

    try:
        if cur is None:
            with connect(args) as conn:
                with cursor(conn) as cur:
                    return _work(cur)
        else:
            return _work(cur)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.getoid.100: {e}")
        raise


# JSONB_OID = getoid("jsonb") # 3802
# JSON_OID = getoid("json") # 114


def mogrifysql(cur: Any, query: str, params: tuple) -> str:
    """Format a query with params for debugging/logging (safe for display only).

    Args:
      cur: Database cursor
      query: SQL query with %s placeholders
      params: Tuple of parameter values

    Returns:
      Formatted string with params interpolated safely
    """
    escaped = []
    for p in params:
        if p is None:
            escaped.append("NULL")
        elif isinstance(p, (bool, int, float)):
            escaped.append(str(p))
        else:
            escaped.append("'" + str(p).replace("'", "''") + "'")

    try:
        return query % tuple(escaped)
    except (ValueError, TypeError):
        return query + " [param interpolation failed]"


def parse_dsn(dsn: str) -> dict[str, str]:
    """Parse a PostgreSQL DSN string into a dict.

    Args:
      dsn: DSN string like 'host=localhost dbname=test'

    Returns:
      Dict with keys like 'host', 'dbname', etc.
    """
    params = {}
    for part in dsn.split():
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        params[key] = value
    return params


def make_dsn(args: Any, **kwargs: Any) -> str:
    """Build a PostgreSQL DSN string from args or kwargs.

    Args:
      args: Application args with database* attributes
      **kwargs: Optional overrides for dbname, user, password, host, port

    Returns:
      DSN string like 'dbname=test user=admin'
    """
    components = []

    try:
        defaults = {
            "dbname": args.databasename,
            "user": args.databaseuser,
            "password": args.databasepassword,
            "host": args.databasehost,
            "port": args.databaseport,
            "autocommit": False,
        }
    except AttributeError:
        io.echo_traceback("bbsengine6.database.make_dsn.100:")
        defaults = {
            "dbname": None,
            "user": None,
            "password": None,
            "host": None,
            "port": 5432,
            "autocommit": False,
        }

    for k in ("dbname", "user", "password", "host", "port"):
        v = kwargs.get(k, defaults.get(k))
        if v not in (None, ""):
            components.append(f"{k}={v}")

    return " ".join(components)


def getpool(args: Any, **kwargs: Any) -> ConnectionPool:
    """Create a connection pool to PostgreSQL.

    Args:
      args: Application args for DSN construction
      **kwargs: Optional DSN overrides

    Returns:
      ConnectionPool instance (min=10, max=100 connections)
    """
    dsn = make_dsn(args, **kwargs)

    pool = ConnectionPool(dsn, min_size=10, max_size=100, timeout=5, open=True)
    return pool


def transaction(conn: Any, **kwargs: Any) -> Any:
    """Create a transaction context manager.

    Args:
      conn: Database connection
      **kwargs: Optional arguments

    Returns:
      Transaction context manager
    """
    io.echo(f"database.transaction.100: {kwargs=}", level="debug")
    return conn.transaction()


def connect(args, pool=None, **kwargs):
    if args.debug is True:
        io.echo(f"bbsengine6.database.connect.100: {args=}", level="debug")

    try:
        pool = getpool(args, **kwargs)
    except AttributeError as e:
        io.echo_traceback(f"bbsengine6.database.connect.200: {e}")
        raise
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.connect.210: {e}")
        raise

    if args.debug is True:
        io.echo(f"{pool=}", level="debug")

    try:
        conn = pool.connection()
        conn.autocommit = False
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.connect.300: {e}")
        raise
    return conn


# def buildkwargs(args, **kwargs):
#    # Set default values from args if not already present in kwargs
#    if "dbname" not in kwargs and "databasename" in args:
#        kwargs["dbname"] = args.databasename
#    if "host" not in kwargs and "databasehost" in args:
#        kwargs["host"] = args.databasehost
#    if "user" not in kwargs and "databaseuser" in args:
#        kwargs["user"] = args.databaseuser
#    if "password" not in kwargs and "databasepassword" in args:
#        kwargs["password"] = args.databasepassword
#    if "port" not in kwargs and "databaseport" in args:
#        kwargs["port"] = args.databaseport
#
#    return kwargs


def update(args: Any, table: str, pk: str, items: dict, **kwargs) -> bool:
    """Update rows in a table.

    Args:
      args: Application args (for debug logging)
      table: Table name
      pk: Primary key value to match
      items: Dict of column:value pairs to update
      **kwargs: Optional - primarykey, mogrify, updatepk, commit

    Returns:
      True on success, False on connection error, raises on database error
    """
    primarykey = kwargs.get("primarykey", "id")
    _mogrify = kwargs.get("mogrify", False)
    updatepk = kwargs.get("updatepk", False)
    commit = kwargs.get("commit", False)

    def _work(cur):
        _items = copy.deepcopy(items)
        if primarykey in _items and updatepk is False:
            del _items[primarykey]

        query = sql.SQL(f"update {_table_identifier(table)} set ")
        params = []
        dat = []
        for k, v in _items.items():
            params.append(sql.SQL(f"{sql.Identifier(k)} = %s"))
            dat.append(v)

        query += sql.SQL(", ").join(params)
        query = sql.SQL(f"{query} where {sql.Identifier(primarykey)} = %s")
        dat.append(pk)

        cur.execute(query, dat)
        return cur.rowcount

    if args.debug is True:
        io.echo(f"bbsengine6.database.update.100: {items=}", level="debug")
    conn = kwargs.get("conn", None)
    if conn is None:
        io.echo(f"bbsengine.database.update.120: {conn=}", level="error")
        return False
    try:
        with cursor(conn) as cur:
            _work(cur)
            if commit is True:
                conn.commit()
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.update.200: {e}")
        return False
    return True


def insert(args: Any, table: str, items: dict, **kwargs: Any) -> int | bool:
    """Insert a row into a table.

    Args:
      args: Application args (for debug logging)
      table: Table name
      items: Dict of column:value pairs to insert
      **kwargs: Optional - primarykey, returnid, mogrify, conn, pool

    Returns:
      Inserted ID if returnid=True, True on success, False on error
    """

    primarykey = kwargs.get("primarykey", "id")
    returnid = kwargs.get("returnid", True)
    _mogrify = kwargs.get("mogrify", True)

    #  cur = kwargs.get("cur", None)

    io.echo(f"bbsengine6.database.insert.100: {items=}", level="debug")

    if items is None:
        io.echo("bbsengine6.database.insert.120: no columns specified", level="error")
        return None

    columns = items.keys()
    if args.debug is True:
        io.echo(f"bbsengine6.database.insert.140: {columns=}", level="debug")

    for k in list(items.keys()):
        if k == "datecreatedepoch":
            del items[k]

    query = sql.SQL(f"insert into {_table_identifier(table)}(")
    query = query + sql.SQL(", ").join([sql.Identifier(c) for c in columns])
    query = query + sql.SQL(") values (")

    params = []
    for x in range(len(columns)):
        params.append("%s")
    query = query + sql.SQL(", ").join([sql.SQL(p) for p in params])
    query = query + sql.SQL(")")

    dat = []
    for v in items.values():
        if type(v) is dict:
            dat.append(Jsonb(v))
        elif type(v) is list:
            dat.append(Jsonb(v))
        else:
            dat.append(v)
    if returnid is True:
        query = sql.SQL(
            f"{query} returning {_table_identifier(table)}.{sql.Identifier(primarykey)}"
        )

    def _work(conn):
        with cursor(conn) as cur:
            cur.execute(query, dat)
            if returnid is True:
                res = cur.fetchone()
                if res is None:
                    return False
                if primarykey in res:
                    return res[primarykey]
                else:
                    return False
        return True

    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo(f"bbsengine.database.insert.200: {pool=}", level="error")
                return False
            with connect(args, pool=pool) as conn:
                return _work(conn)
        return _work(conn)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.insert.200: {e}")
        return False


# @see https://soft-builder.com/how-to-list-all-schemas-in-postgresql/
# @since 20230510
# tables, views, etc. NOT functions
def classexists(args: Any, name: str, **kwargs: Any) -> bool:
    def _work(conn):
        mogrify = kwargs.get("mogrify", False)
        with cursor(conn) as cur:
            sql = "select to_regclass(%s) as class"  # does not work with schemas
            dat = (name,)
            cur.execute(sql, dat)
            if mogrify is True:
                io.echo(
                    f"bbsengine6.database.classexists.120: {mogrifysql(cur, sql, dat)=}",
                    level="debug",
                )
            if cur.rowcount == 0:
                return False

            res = cur.fetchone()

            return res["class"] is not None

    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo(f"bbsengine6.classexists.200: {pool=}", level="error")
                return False
            with connect(args, pool=pool) as conn:
                return _work(conn)
        return _work(conn)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.classexists.200: {e}")
        return False


def schemaexists(args: Any, name: str, **kwargs: Any) -> bool:
    mogrify = kwargs.get("mogrify", False)

    def _work(conn):
        sql = (
            "SELECT 't' as exists FROM information_schema.schemata where schema_name=%s"
        )
        dat = (name,)
        with cursor(conn) as cur:
            if mogrify is True:
                io.echo(
                    f"bbsengine6.database.schemaexists.100: {mogrifysql(cur, sql, dat)=}",
                    level="debug",
                )
            cur.execute(sql, dat)
            return False if cur.rowcount == 0 else True

    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                return False
            with connect(args, pool=pool) as conn:
                return _work(conn)
        return _work(conn)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.schemaexists.200: {e}")
        return False


def tableexists(args: Any, schema: str, table: str, **kwargs: Any) -> bool:
    mogrify = kwargs.get("mogrify", False)

    def _work(conn):
        sql = "SELECT 't' as exists FROM information_schema.tables where table_schema=%s and table_name=%s"
        dat = (schema, table)
        with cursor(conn) as cur:
            if mogrify is True:
                io.echo(
                    f"bbsengine6.database.tableexists.100: {mogrifysql(cur, sql, dat)=}",
                    level="debug",
                )
            cur.execute(sql, dat)
            return False if cur.rowcount == 0 else True

    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                return False
            with connect(args, pool=pool) as conn:
                return _work(conn)
        return _work(conn)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.tableexists.200: {e}")
        return False


# @since 20230510 copied from bbsengine5.py
def buildargs(
    parentparser: Any,
    defaults: dict | None = None,
    label: str = "database options",
    suppress: bool = False,
) -> None:
    if defaults is None:
        defaults = {}
    databasename = defaults.get("databasename", "zoid6")
    databasehost = defaults.get("databasehost", "")
    databaseport = defaults.get("databaseport", 5432)
    databaseuser = defaults.get("databaseuser", None)
    databasepassword = defaults.get("databasepassword", None)
    databaseschema = defaults.get("databaseschema", None)

    group = parentparser.add_argument_group(label)
    #    group = argparse.ArgumentParser("database", parents=[parentparser], add_help=False)
    if suppress is False:
        group.add_argument(
            "--databasename",
            dest="databasename",
            action="store",
            default=databasename,
            type=str,
            help="database name (default: %(default)r)",
        )
        group.add_argument(
            "--databasehost",
            dest="databasehost",
            action="store",
            default=databasehost,
            type=str,
            help="database host (default: %(default)r)",
        )
        group.add_argument(
            "--databaseport",
            dest="databaseport",
            action="store",
            default=databaseport,
            type=int,
            help="database port (default: %(default)r)",
        )
        group.add_argument(
            "--databaseuser",
            dest="databaseuser",
            action="store",
            default=databaseuser,
            type=str,
            help="database user (default: %(default)r)",
        )
        group.add_argument(
            "--databasepassword",
            dest="databasepassword",
            action="store",
            default=databasepassword,
            type=str,
            help="database password (default: %(default)r)",
        )

        group.add_argument(
            "--databaseschema",
            dest="databaseschema",
            action="store",
            default=databaseschema,
            type=str,
            help="schema to use",
        )
    else:
        group.add_argument(
            "--databasename",
            dest="databasename",
            action="store",
            default=databasename,
            type=str,
            help=argparse.SUPPRESS,
        )
        group.add_argument(
            "--databasehost",
            dest="databasehost",
            action="store",
            default=databasehost,
            type=str,
            help=argparse.SUPPRESS,
        )  # "database host (default: %(default)r)")
        group.add_argument(
            "--databaseport",
            dest="databaseport",
            action="store",
            default=databaseport,
            type=int,
            help=argparse.SUPPRESS,
        )  # "database port (default: %(default)r)")
        group.add_argument(
            "--databaseuser",
            dest="databaseuser",
            action="store",
            default=databaseuser,
            type=str,
            help=argparse.SUPPRESS,
        )  # "database user (default: %(default)r)")
        group.add_argument(
            "--databasepassword",
            dest="databasepassword",
            action="store",
            default=databasepassword,
            type=str,
            help=argparse.SUPPRESS,
        )  # "database password (default: %(default)r)")

    return


buildargdatabasegroup = buildargs
buildarggroup = buildargs


# @since 20211101
# @since 20230515 copied from bbsengine5
def resultiter(
    cur: Any, arraysize: int = 1000, filterfunc: callable = None, **kwargs: dict
) -> Iterator:
    "An iterator which accepts a psycopg3 cursor to keep memory usage down"
    while True:
        results = cur.fetchmany(arraysize)
        if not results:
            break
        for result in results:
            if filterfunc is None:
                yield result
            elif callable(filterfunc) is True and filterfunc(result, **kwargs) is True:
                yield result


def commit(args: Any, conn: Any = None, **kwargs: Any) -> bool:
    """Commit the current transaction.

    Args:
      args: Application args (for logging)
      conn: Database connection
      **kwargs: Additional arguments

    Returns:
      True on success, False if no connection
    """
    if conn is not None:
        conn.commit()
        return True
    io.echo("bbsengine6.database.commit.100: no connection", level="error")
    return False


def rollback(args: Any, conn: Any = None, **kwargs: Any) -> None:
    """Roll back the current transaction.

    Args:
      args: Application args (for logging)
      conn: Database connection
      **kwargs: Additional arguments
    """
    if conn is not None:
        return conn.rollback()


def createrol(args: Any, name: str, **kwargs: Any) -> bool:
    # Map privilege keys to their SQL counterparts
    privilege_map = {
        "login": ("login", "nologin", False),
        "superuser": ("superuser", "nosuperuser", False),
        "createdb": ("createdb", "nocreatedb", False),
        "createrole": ("createrole", "nocreaterole", False),
        "inherit": ("inherit", "noinherit", False),
        "replication": ("replication", "noreplication", False),
    }

    options = []

    def _work(cur):
        for priv, (enabled, disabled, default) in privilege_map.items():
            value = kwargs.get(priv, default)
            options.append(enabled if value else disabled)

        if "password" in kwargs:
            query = sql.SQL(
                f"create role {sql.Identifier(name)} with {sql.SQL(' ').join([sql.SQL(o) for o in options])} password %s"
            )
            io.echo(f"bbsengine.database.createrol.100: {query=}", level="debug")
            cur.execute(query, (kwargs["password"],))
        elif "expiration" in kwargs:
            query = sql.SQL(
                f"create role {sql.Identifier(name)} with {sql.SQL(' ').join([sql.SQL(o) for o in options])} valid until %s"
            )
            io.echo(f"bbsengine.database.createrol.100: {query=}", level="debug")
            cur.execute(query, (kwargs["expiration"],))
        else:
            query = sql.SQL(
                f"create role {sql.Identifier(name)} with {sql.SQL(' ').join([sql.SQL(o) for o in options])}"
            )
            io.echo(f"bbsengine.database.createrol.100: {query=}", level="debug")
            cur.execute(query)
        return False if cur.rowcount == 0 else True

    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            io.echo("bbsengine.database.createrol.140: {conn=}", level="error")
            return False
        with cursor(conn) as cur:
            return _work(cur)
    except psycopg.DatabaseError as e:
        io.echo_traceback(f"bbsengine6.database.createrol.200: {e}")
        return False


def rolexists(args: Any, rolname: str, **kwargs: Any) -> bool:
    _mogrify = kwargs.get("mogrify", False)

    def _work(cur):
        sql = "SELECT rolname FROM pg_roles where rolname=%s"
        dat = (rolname,)
        cur.execute(sql, dat)
        if args.debug is True:
            io.echo(
                f"bbsengine6.database.rolexists.100: {mogrifysql(cur, sql, dat)=}",
                level="debug",
            )
        return False if cur.rowcount == 0 else True

    conn = kwargs.get("conn", None)
    if conn is None:
        io.echo(f"bbsengine.database.rolexists.100: {conn=}", level="error")
        return False

    try:
        with cursor(conn) as cur:
            return _work(cur)
    except psycopg.DatabaseError as e:
        io.echo_traceback(f"bbsengine6.database.rolexists.200: {e}")
        return False


def exists(args: Any, databasename: str, **kwargs: Any) -> bool:
    _mogrify = kwargs.get("mogrify", True)
    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo("database.exists.200: no pool", level="error")
        return False

    try:
        with connect(args, pool=pool) as conn:
            sql = "SELECT datname FROM pg_catalog.pg_database WHERE lower(datname) = lower(%s)"
            dat = (databasename,)
            with cursor(conn) as cur:
                cur.execute(sql, dat)
                return False if cur.rowcount == 0 else True
    except psycopg.DatabaseError as e:
        io.echo_traceback(f"bbsengine6.database.exists.200: {e}")
        return False


def create(args: Any, name: str, **kwargs: Any) -> bool:
    from psycopg.sql import SQL, Identifier

    def _work(cur):
        # Use psycopg.sql.Identifier to safely handle the database name
        try:
            sql = SQL(f"CREATE DATABASE {Identifier(name)}")
            cur.execute(sql)
        except Exception as e:
            io.echo_traceback(f"bbsengine6.database.create.200: {e}")
            return False
        return True

    conn = kwargs.get("conn", None)
    if conn is None:
        io.echo(f"bbsengine.database.create.180: {conn=}", level="error")
        return False
    io.echo(f"{conn=}", level="debug")
    with cursor(conn) as cur:
        return _work(cur)


def createschema(args: Any, name: str, **kwargs: Any) -> bool:
    io.echo(f"bbsengine.database.createschema.120: {name=}", level="debug")

    # Connect to the database using args
    def _work(conn):
        stmt = sql.SQL(f"CREATE SCHEMA {sql.Identifier(name)}")
        io.echo(f"bbsengine6.database.createschema.260: {stmt=}", level="debug")
        with cursor(conn) as cur:
            cur.execute(stmt)

    try:
        io.echo(f"bbsengine6.database.createschema.220: {kwargs=}", level="debug")
        conn = kwargs.get("conn", None)
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo(
                    f"bbsengine6.database.createschema.200: pool is None", level="error"
                )
                return False
            with connect(args, pool=pool) as conn:
                return _work(conn)
        return _work(conn)
    except psycopg.DatabaseError as e:
        io.echo_traceback(f"bbsengine6.database.createschema.200: {e}")
        return False


def get_role_privs(
    args: Any, rolname: str, cur: Any = None, **kwargs: Any
) -> dict | bool:
    def _work(cur):
        sql = "SELECT get_role_privs(%s);"
        cur.execute(sql, (rolname,))
        result = cur.fetchone()
        return result["get_role_privs"] if "get_role_privs" in result else {}

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            return False

        with connect(args, pool=pool) as conn:
            with cursor(conn) as cur:
                return _work(cur)
    else:
        with cursor(conn) as cur:
            return _work(cur)


def manage_role_privs(
    args: Any, role_name: str, action: str, priv: str, **kwargs: Any
) -> Any:
    def _work(conn):
        sql = "select manage_role_privs(%s, %s, %s)"
        dat = (role_name, action, priv)
        with cursor(conn) as cur:
            return cur.execute(sql, dat)

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(
                f"bbsengine6.database.manage_role_privs.120: {pool=}", level="error"
            )
            return False
        with connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(conn)


def manage_secondary_role(
    args: Any, role_name: str, action: str, secondary: str, **kwargs: Any
) -> Any:
    conn = kwargs.get("conn", None)
    if conn is None:
        io.echo(f"bbsengine.database.manage_secondary_role.100: {conn=}", level="error")
        return False

    def _work(cur):
        sql = "select manage_secondary_role(%s, %s, %s)"
        dat = (role_name, action, secondary)
        return cur.execute(sql, dat)

    try:
        with cursor(conn) as cur:
            return _work(cur)
    except psycopg.DatabaseError as e:
        io.echo_traceback(f"bbsengine6.database.manage_secondary_role.200: {e}")
        return False


def cursor(conn: Any, row_factory: Any = dict_row, **kwargs: Any) -> Any:
    """Create a cursor with the specified row factory.

    Args:
      conn: Database connection
      row_factory: Row factory (default: dict_row for dict results)
      **kwargs: Additional arguments

    Returns:
      Cursor instance
    """
    return conn.cursor(row_factory=row_factory)


def extensionavailable(args: Any, ext: str, **kwargs: Any) -> bool:
    def _work(cur):
        sql = "select * from pg_available_extensions where name=%s"
        dat = (ext,)
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            return False
        return True

    cur = kwargs.get("cur", None)
    if cur is None:
        pool = kwargs.get("pool", None)
        with connect(args, pool=pool) as conn:
            with cursor(conn) as cur:
                return _work(cur)
    else:
        return _work(cur)


def extensioninstalled(args: Any, ext: str, **kwargs: Any) -> bool:
    def _work(cur):
        try:
            sql = "select * from pg_extension where extname=%s"
            dat = (ext,)
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return False
            return True
        except Exception as e:
            io.echo_traceback(f"bbsengine6.database.extensioninstalled.200: {e}")
            return False

    cur = kwargs.get("cur", None)
    if cur is None:
        pool = kwargs.get("pool", None)
        with connect(args, pool=pool) as conn:
            with cursor(conn) as cur:
                return _work(cur)
    else:
        return _work(cur)


def creatextension(args: Any, ext: str, **kwargs: Any) -> bool:
    def _work(cur):
        try:
            sql = psycopg.sql.SQL(
                f"CREATE EXTENSION IF NOT EXISTS {psycopg.sql.Identifier(ext)}"
            )
            #            sql = "create extension if not exists %s"
            cur.execute(sql)
        except psycopg.errors.InsufficientPrivilege:
            io.echo(f"error: permission denied creating extension {ext}", level="error")
            return False
        except psycopg.errors.UndefinedFile:
            io.echo(f"error: {ext} is not available", level="error")
            return False
        except Exception as e:
            io.echo_traceback(f"bbsengine6.database.creatextension.200: {e}")
            return False
        else:
            return True

    cur = kwargs.get("cur", None)
    if cur is None:
        pool = kwargs.get("pool", None)
        with connect(args, pool=pool) as conn:
            with cursor(conn) as cur:
                return _work(cur)
    else:
        return _work(cur)


# @since 20241212
def importsql(args: Any, filename: str, **kwargs: Any) -> bool:
    def _work(conn):
        #    io.echo(f"bbsengine.database.importsql.140: {conn=}", level="debug")
        #    fullpath = util.get_safe_path(args, *components, **kwargs)
        #    io.echo(f"bbsengine.database.importsql.120: {fullpath=}", level="debug")

        try:
            package = kwargs.get("package", None)
            sql_script = util.load_sql(args, filename, package=package)
            #      with open(fullpath, 'r') as file:
            #        sql_script = file.read()
            with cursor(conn) as cur:
                try:
                    cur.execute(sql_script)
                except psycopg.errors.Error as e:
                    io.echo_traceback(f"bbsengine6.database.importsql.200: {e}")
                    return False
        except Exception as e:
            io.echo_traceback(f"bbsengine6.database.importsql.300: {e}")
            return False
        return True

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(f"importsql.100: no connection and no pool", level="error")
            return False
        with connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(conn)


def functionexists(args: Any, name: str, **kwargs: Any) -> bool:

    def _work(conn):
        if "." in name:
            schema, function_name = name.split(".", 1)
        else:
            schema, function_name = "public", name
        #    io.echo(f"bbsengine.database.functionexists.100: {schema=} {function_name=}", level="debug")
        sql = "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE p.proname = %s AND n.nspname = %s"
        dat = (function_name, schema)
        with cursor(conn) as cur:
            cur.execute(sql, dat)
            #    io.echo(f"bbsengine6.database.functionexists.120: {mogrifysql(cur, sql, dat)=} {cur.rowcount=}", level="debug")
            return True if cur.rowcount > 0 else False

    try:
        conn = kwargs.get("conn", None)
        io.echo(f"bbsengine.database.functionexists.100: {conn=}", level="debug")
        if conn is None:
            return False
        return _work(conn)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.functionexists.200: {e}")
        return False


# @since 20250511
def manage_database_priv(
    args: Any,
    action: str,
    priv: str,
    database_name: str,
    target_role: str,
    **kwargs: Any,
) -> bool:
    def _work(conn):
        sql = "select manage_database_priv(%s, %s, %s, %s)"
        dat = (action, priv, database_name, target_role)
        with cursor(conn) as cur:
            cur.execute(sql, dat)
            return True if cur.rowcount > 0 else False

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(
                f"bbsengine6.database.manage_database_priv.120: {pool=}", level="error"
            )
            return False
        with connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(conn)


# @since 20250511
def manage_schema_priv(
    args: Any,
    action: str,
    priv: str,
    database_name: str,
    target_role: str,
    **kwargs: Any,
) -> bool:
    def _work(conn):
        sql = "select manage_schema_priv(%s, %s, %s, %s)"
        dat = (action, priv, database_name, target_role)
        with cursor(conn) as cur:
            cur.execute(sql, dat)
            return True if cur.rowcount > 0 else False

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(
                f"bbsengine6.database.manage_schema_priv.120: {pool=}", level="error"
            )
            return False
        with connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(conn)
