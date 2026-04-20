import copy
from contextlib import contextmanager
from typing import Any, Generator, Iterator

import argparse

from psycopg.rows import dict_row
import psycopg
import psycopg.sql

from psycopg import sql
from psycopg.types.json import Jsonb  # noqa: F401

from psycopg_pool import ConnectionPool

from . import io, util

DEFAULTDATABASE = "postgres"


def convert_for_jsonb(v: Any) -> Any:
    """Recursively convert values for safe JSONB encoding.

    Wraps Python objects in psycopg3 Jsonb/Json types for database storage.

    Handles: type, datetime, dict, list, tuple, and other non-serializable types.
    Logs suspicious values (type objects, unknown types) at debug level.

    IMPORTANT: This function is called by database.update() and database.insert()
    when executing queries. Do NOT call json.dumps() before passing values to these
    functions - let this function handle the conversion.

    Example (correct):
        rec = {"flags": {"APPROVED": {"value": True}}}
        database.update(args, table, pk, rec)  # rec["flags"] is dict, not JSON string
        # database.update() calls convert_for_jsonb(rec["flags"]) internally

    Example (wrong):
        rec = {"flags": json.dumps({"APPROVED": {"value": True}})}  # Don't do this!
        # json.dumps() can't serialize Jsonb objects if convert_for_jsonb() is called on them
    """
    import datetime

    if isinstance(v, type):
##        io.echo(f"convert_for_jsonb: converting type {v}", level="debug")
        return str(v)
    if isinstance(v, Jsonb):
        return v
    if isinstance(v, datetime.datetime):
        return v.isoformat()
    if isinstance(v, dict):
        return Jsonb({k: convert_for_jsonb(val) for k, val in v.items()})
    elif isinstance(v, (list, tuple)):
        return Jsonb([convert_for_jsonb(item) for item in v])
    if v is not None and not isinstance(v, (str, int, float, bool)):
##        io.echo(
##            f"convert_for_jsonb: converting {type(v).__name__} to str", level="debug"
##        )
        return str(v)
    return v


def execute(cur: Any, query: Any, *params: Any) -> Any:
    """Execute query with auto-converted params for safe JSONB encoding.

    Use this instead of direct cur.execute() when params may contain
    dicts, lists, datetime objects, or type objects.

    Args:
        cur: Database cursor
        query: SQL query (sql.SQL or str)
        *params: Query parameters to convert

    Returns:
        Cursor result from cur.execute()
    """
    if not params or (len(params) == 1 and params[0] is None):
        return cur.execute(query)
    converted = [convert_for_jsonb(p) for p in params]
    return cur.execute(query, converted)


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


def query(sql_template: str, *params: Any, **kwargs: Any) -> sql.SQL:
    """Build a parameterized SQL query from readable string.

    Allows readable SQL like:
        cur.execute(database.query("SELECT * FROM $murdermotel.player WHERE moniker = :moniker", moniker=moniker))

    Security: Table/column names use sql.Identifier(), values use parameterized placeholders.

    Args:
        sql_template: SQL with $schema.table identifiers and :name or $1 placeholders
        *params: Values for positional placeholders ($1, $2...)
        **kwargs: Values for named placeholders (:name)

    Returns:
        sql.SQL object ready for cursor.execute()

    Example:
        cur.execute(database.query("SELECT * FROM $murdermotel.player WHERE moniker = $1", moniker))
        cur.execute(database.query("SELECT * FROM $murdermotel.player WHERE moniker = :moniker", moniker=moniker))
        cur.execute(database.query("SELECT * FROM $murdermotel.player p JOIN $murdermotel.room r ON p.room_id = r.id WHERE p.moniker = :moniker", moniker=moniker))
    """
    import re

    identifier_pattern = r"\$([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)"
    named_placeholder_pattern = r":([a-zA-Z_][a-zA-Z0-9_]*)"

    parts = []
    last_end = 0
    named_params = kwargs

    def replace_named(s: str) -> str:
        def replacer(match: re.Match) -> str:
            name = match.group(1)
            if name in named_params:
                return f"%({name})s"
            return match.group(0)

        return re.sub(named_placeholder_pattern, replacer, s)

    for match in re.finditer(identifier_pattern, sql_template):
        before = sql_template[last_end : match.start()]
        if before:
            processed = replace_named(before)
            parts.append(sql.SQL(processed))

        identifier = match.group(1)
        if "." in identifier:
            schema, table_name = identifier.split(".", 1)
            parts.append(sql.Identifier(schema, table_name))
        else:
            parts.append(sql.Identifier(identifier))
        last_end = match.end()

    if last_end < len(sql_template):
        remaining = sql_template[last_end:]
        processed = replace_named(remaining)
        if processed:
            parts.append(sql.SQL(processed))

    if not parts:
        return sql.SQL(sql_template)

    result = parts[0]
    for part in parts[1:]:
        result = result + part

    return result


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


_pool_cache: dict = {}


def getpool(args: Any, **kwargs: Any) -> ConnectionPool:
    """Get or create a connection pool to PostgreSQL.

    Args:
      args: Application args for DSN construction
      **kwargs: Optional DSN overrides

    Returns:
      ConnectionPool instance (min=10, max=100 connections)
    """
    dsn = make_dsn(args, **kwargs)

    if dsn not in _pool_cache or _pool_cache[dsn].closed:
        _pool_cache[dsn] = ConnectionPool(
            dsn, min_size=10, max_size=100, timeout=5, open=True
        )

    return _pool_cache[dsn]


def reset_pool_cache() -> None:
    """Reset the pool cache. Call this in tests."""
    global _pool_cache
    for pool in _pool_cache.values():
        try:
            pool.close()
        except Exception:
            io.echo_traceback("bbsengine6.database.234:")
    _pool_cache = {}


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


@contextmanager
def connect(
    args: Any, pool: Any = None, *, auto_commit: bool = True, **kwargs: Any
) -> Generator[Any, None, None]:
    """Context manager that safely gets a connection and returns it to the pool.

    Args:
      args: Application args (for logging, optional)
      pool: ConnectionPool instance
      auto_commit: If True (default), commits before returning connection to pool.
                   Set to False for multi-statement transactions.
      **kwargs: Additional arguments

    Yields:
      Connection from pool
    """
    if args and args.debug is True:
        io.echo(f"bbsengine6.database.connect.100: {args=}", level="debug")

    if "readonly" in kwargs:
        del kwargs["readonly"]

    if pool is None:
        io.echo("bbsengine6.database.connect.200: pool is None", level="error")
        raise ValueError("pool is None")

    if args and args.debug is True:
        io.echo(f"{pool=}", level="debug")

    try:
        conn: Any = pool.getconn()
        conn.autocommit = False
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.connect.300: {e}")
        raise

    try:
        yield conn
    finally:
        if auto_commit:
            conn.commit()
        pool.putconn(conn)


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
    commit = kwargs.get("commit", True)

    def _work(cur):
        _items = copy.deepcopy(items)
        if primarykey in _items and updatepk is False:
            del _items[primarykey]

        query = sql.SQL("update ") + _table_identifier(table) + sql.SQL(" set ")
        params = []
        dat = []
        for k, v in _items.items():
            params.append(sql.Identifier(k) + sql.SQL(" = %s"))
            dat.append(convert_for_jsonb(v))

        query = (
            query
            + sql.SQL(", ").join(params)
            + sql.SQL(" where ")
            + sql.Identifier(primarykey)
            + sql.SQL(" = %s")
        )
        dat.append(pk)

        if args.debug is True:
            io.echo(
                f"bbsengine6.database.update.150: dat types={[type(d).__name__ for d in dat]}",
                level="debug",
            )

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


def upsert(
    args: Any,
    table: str,
    items: dict,
    conflict_columns: list,
    update_columns: list | None = None,
    **kwargs,
) -> bool:
    """Insert or update a row (UPSERT) - atomic operation.

    Uses PostgreSQL INSERT ... ON CONFLICT ... DO UPDATE for atomic upsert.
    If row exists (based on conflict_columns), updates specified columns.
    If row doesn't exist, inserts it.

    Args:
        args: Application args (for debug logging)
        table: Table name (schema.table)
        items: Dict of column:value pairs to insert/update
        conflict_columns: List of column names that form the conflict key
                         (e.g., ["moniker", "name"] for unique constraint)
        update_columns: List of columns to update on conflict.
                       If None, updates all columns in items except conflict_columns.
        **kwargs: Optional - mogrify, commit, conn, pool

    Returns:
        True on success, False on error

    Example:
        # Upsert a flag: insert if not exists, update value if exists
        database.upsert(
            args,
            "engine.map_member_flag",
            {"moniker": "jonez", "name": "APPROVED", "value": True},
            conflict_columns=["moniker", "name"],
            update_columns=["value"],
            conn=conn
        )

    Note:
        - All columns in items should be valid for the table
        - conflict_columns must match a unique constraint in the database
        - Uses EXCLUDED pseudo-table to reference new values during update
    """
    mogrify = kwargs.get("mogrify", False)
    commit = kwargs.get("commit", True)
    conn = kwargs.get("conn", None)

    if not conflict_columns:
        io.echo(
            "bbsengine6.database.upsert.100: conflict_columns required", level="error"
        )
        return False

    # Determine which columns to update on conflict
    if update_columns is None:
        # Update all columns except the conflict columns
        update_columns = [k for k in items.keys() if k not in conflict_columns]

    def _work(conn):
        with cursor(conn) as cur:
            # Build column list and values
            columns = list(items.keys())
            values = [convert_for_jsonb(items[col]) for col in columns]

            # Build INSERT clause
            insert_clause = (
                sql.SQL("INSERT INTO ") + _table_identifier(table) + sql.SQL(" (")
            )
            insert_clause += sql.SQL(", ").join(
                [sql.Identifier(col) for col in columns]
            )
            insert_clause += sql.SQL(") VALUES (")
            insert_clause += sql.SQL(", ").join([sql.SQL("%s") for _ in columns])
            insert_clause += sql.SQL(")")

            # Build ON CONFLICT clause
            conflict_clause = sql.SQL(" ON CONFLICT (")
            conflict_clause += sql.SQL(", ").join(
                [sql.Identifier(col) for col in conflict_columns]
            )
            conflict_clause += sql.SQL(") DO UPDATE SET ")

            # Build UPDATE assignments using EXCLUDED
            update_assignments = []
            for col in update_columns:
                update_assignments.append(
                    sql.Identifier(col) + sql.SQL(" = EXCLUDED.") + sql.Identifier(col)
                )
            conflict_clause += sql.SQL(", ").join(update_assignments)

            # Combine full query
            upsert_query = insert_clause + conflict_clause

            if mogrify is True:
                io.echo(
                    f"bbsengine6.database.upsert.150: {mogrifysql(cur, str(upsert_query), values)}",
                    level="debug",
                )

            cur.execute(upsert_query, values)

        if commit is True:
            conn.commit()

        return True

    if args.debug is True:
        io.echo(
            f"bbsengine6.database.upsert.100: table={table}, items={items}, conflict={conflict_columns}",
            level="debug",
        )

    try:
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo(
                    "bbsengine6.database.upsert.200: conn and pool both None",
                    level="error",
                )
                return False
            with connect(args, pool=pool) as conn:
                return _work(conn)
        return _work(conn)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.upsert.300: {e}")
        return False


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
    commit = kwargs.get("commit", True)

    #  cur = kwargs.get("cur", None)

##    io.echo(f"bbsengine6.database.insert.100: {items=}", level="debug")

    if items is None:
        io.echo("bbsengine6.database.insert.120: no columns specified", level="error")
        return None

    columns = items.keys()
    if args.debug is True:
        io.echo(f"bbsengine6.database.insert.140: {columns=}", level="debug")

    for k in list(items.keys()):
        if k == "datecreatedepoch":
            del items[k]

    query = sql.SQL("insert into ") + _table_identifier(table) + sql.SQL("(")
    query = query + sql.SQL(", ").join([sql.Identifier(c) for c in columns])
    query = query + sql.SQL(") values (")

    params = []
    for x in range(len(columns)):
        params.append("%s")
    query = query + sql.SQL(", ").join([sql.SQL(p) for p in params])
    query = query + sql.SQL(")")

    dat = [convert_for_jsonb(v) for v in items.values()]
    if returnid is True:
        query = (
            query
            + sql.SQL(" returning ")
            + _table_identifier(table)
            + sql.SQL(".")
            + sql.Identifier(primarykey)
        )

    def _work(conn):
        with cursor(conn) as cur:
            cur.execute(query, dat)
            if returnid is True:
                res = cur.fetchone()
                if res is None:
                    returnval = False
                elif primarykey in res:
                    returnval = res[primarykey]
                else:
                    returnval = False
            else:
                returnval = True
        if commit is True:
            conn.commit()
        return returnval

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


def typeexists(args: Any, name: str, **kwargs: Any) -> bool:
    def _work(conn):
        mogrify = kwargs.get("mogrify", False)
        with cursor(conn) as cur:
            sql = "select to_regtype(%s) as type"
            dat = (name,)
            cur.execute(sql, dat)
            if mogrify is True:
                io.echo(
                    f"bbsengine6.database.typeexists.100: {mogrifysql(cur, sql, dat)=}",
                    level="debug",
                )
            if cur.rowcount == 0:
                return False
            res = cur.fetchone()
            return res["type"] is not None

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
        io.echo_traceback(f"bbsengine6.database.typeexists.200: {e}")
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
    databasehost = defaults.get("databasehost", "127.0.0.1")
    databaseport = defaults.get("databaseport", 5432)
    databaseuser = defaults.get("databaseuser", None)
    databasepassword = defaults.get("databasepassword", None)
    databaseschema = defaults.get("databaseschema", "engine")

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
                result = False if cur.rowcount == 0 else True
            conn.commit()
            return result
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
        stmt = sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(name))
        io.echo(f"bbsengine6.database.createschema.260: {stmt=}", level="debug")
        with cursor(conn) as cur:
            cur.execute(stmt)
        conn.commit()
        return True

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
