import copy
import os
from contextlib import contextmanager
import threading
from typing import Any, Generator, Iterator, Literal

import argparse

from psycopg.rows import dict_row
import psycopg
import psycopg.sql

from psycopg import sql
from psycopg.types.json import Jsonb  # noqa: F401

from psycopg_pool import ConnectionPool

from . import io, util

DEFAULTDATABASE = "postgres"

# CONVENTION: Connection and cursor objects are passed via **kwargs, NOT as positional or
# keyword arguments. All database functions accept **kwargs and extract conn/cur from it.
# Example: database.cursor(conn=conn) not database.cursor(**kwargs) or database.cursor(conn)


def convert_for_jsonb(v: Any, *, wrap: bool = True) -> Any:
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

    Note: Only the top-level dict/list is wrapped in Jsonb. Inner dicts/lists
    are returned as plain dicts/lists to avoid "Object of type Jsonb is not JSON
    serializable" when psycopg calls json.dumps() on the outer Jsonb wrapper.
    The ``wrap`` parameter controls this and is intended for internal recursion;
    callers should use the default (wrap=True).
    """
    import datetime

    if isinstance(v, type):
        return str(v)
    if isinstance(v, Jsonb):
        return v
    if isinstance(v, datetime.datetime):
        return v.isoformat()
    if isinstance(v, dict):
        inner = {k: convert_for_jsonb(val, wrap=False) for k, val in v.items()}
        return Jsonb(inner) if wrap else inner
    if isinstance(v, (list, tuple)):
        inner = [convert_for_jsonb(item, wrap=False) for item in v]
        return Jsonb(inner) if wrap else inner
    if v is not None and not isinstance(v, (str, int, float, bool)):
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


def executemany(cur: Any, operation: str, seq_of_params: list) -> None:
    """Execute operation against all parameter sequences with auto-conversion.

    Auto-converts params through convert_for_jsonb() for consistency with execute().

    Args:
        cur: Database cursor
        operation: SQL operation to execute
        seq_of_params: Sequence of parameter tuples/lists
    """
    for params in seq_of_params:
        converted = [convert_for_jsonb(p) for p in params]
        cur.execute(operation, converted)


def _table_identifier(table: str, args: Any = None):
    """Create proper SQL identifier for schema-qualified table names.

    Args:
      table: Table name, optionally qualified with schema (e.g., 'empyre.__player')
      args: Optional application args. When provided, a bare schema of 'engine'
            is rewritten to args.databaseschema so callers do not have to know
            the active schema at the call site.

    Returns:
      sql.Identifier for the table
    """
    if "." in table:
        schema, table_name = table.split(".", 1)
        if schema == "engine" and args is not None:
            try:
                schema = args.databaseschema
            except AttributeError:
                pass
        return sql.Identifier(schema, table_name)
    return sql.Identifier(table)


def query(sql_template: str, *params: Any, **kwargs: Any) -> sql.SQL:
    """Build a parameterized SQL query from readable string.

    Allows readable SQL like:
        cur.execute(database.query("SELECT * FROM $engine.member WHERE moniker = :moniker", moniker=moniker))

    Security: Table/column names use sql.Identifier(), values are interpolated using sql.Literal().

    Args:
        sql_template: SQL with $schema.table identifiers and :name placeholders
        *params: Values for positional placeholders ($1, $2...)
        **kwargs: Values for named placeholders (:name)

    Returns:
        sql.SQL object ready for cursor.execute()

    Example:
        cur.execute(database.query("SELECT * FROM $engine.member WHERE moniker = $1", moniker))
        cur.execute(database.query("SELECT * FROM $engine.member WHERE moniker = :moniker", moniker=moniker))
        cur.execute(database.query("SELECT * FROM $engine.member p JOIN $engine.room r ON p.room_id = r.id WHERE p.moniker = :moniker", moniker=moniker))
    """
    import re

    identifier_pattern = r"\$([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)"
    named_placeholder_pattern = r":([a-zA-Z_][a-zA-Z0-9_]*)"
    positional_placeholder_pattern = r"\$(\d+)"

    parts = []
    last_end = 0
    named_params = kwargs
    positional_params = params

    def process_text(s: str) -> list:
        result = []
        pos = 0

        # Handle both named (:name) and positional ($N) placeholders
        # Combined pattern has groups: (1=:name_name, 2=$N_N)
        combined_pattern = (
            f"{named_placeholder_pattern}|{positional_placeholder_pattern}"
        )
        for match in re.finditer(combined_pattern, s):
            if match.start() > pos:
                result.append(sql.SQL(s[pos : match.start()]))  # type: ignore[arg-type]

            # Check which pattern matched
            if match.lastindex == 1:  # named placeholder (:name)
                name = match.group(1)
                if name in named_params:
                    result.append(sql.Literal(named_params[name]))  # type: ignore[index]
                else:
                    result.append(sql.SQL(match.group(0)))  # type: ignore
            elif match.lastindex == 2:  # positional placeholder ($N)
                idx = int(match.group(2))
                if 0 < idx <= len(positional_params):
                    result.append(sql.Literal(positional_params[idx - 1]))  # type: ignore[index]
                else:
                    result.append(sql.SQL(match.group(0)))  # type: ignore[arg-type]

            pos = match.end()
        if pos < len(s):
            result.append(sql.SQL(s[pos:]))  # type: ignore
        return result

    for match in re.finditer(identifier_pattern, sql_template):
        before = sql_template[last_end : match.start()]
        if before:
            parts.extend(process_text(before))

        identifier = match.group(1)
        if "." in identifier:
            schema, table_name = identifier.split(".", 1)
            parts.append(sql.Identifier(schema, table_name))
        else:
            parts.append(sql.Identifier(identifier))
        last_end = match.end()

    if last_end < len(sql_template):
        remaining = sql_template[last_end:]
        parts.extend(process_text(remaining))

    if not parts:
        return sql.SQL(sql_template)  # type: ignore

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
                with cursor(conn=conn) as cur:
                    return _work(cur)
        else:
            return _work(cur)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.getoid.100: {e}")
        raise


# JSONB_OID = getoid("jsonb") # 3802
# JSON_OID = getoid("json") # 114


def mogrifysql(cur: Any, query: str, params: list[Any] | tuple[Any, ...]) -> str:
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
      **kwargs: Optional overrides for dbname/database, user, password, host, port.
                Supports both 'database' and 'dbname' for backward compatibility;
                'database' takes precedence.

    Returns:
      DSN string like 'dbname=test user=admin'

    Raises:
      ValueError: If args is None and required database parameters are not provided via kwargs.
    """
    if "database" in kwargs and "dbname" not in kwargs:
        kwargs["dbname"] = kwargs.pop("database")
    elif "database" in kwargs and "dbname" in kwargs:
        kwargs.pop("database")

    components = []

    if args is None:
        defaults = {
            "dbname": None,
            "user": None,
            "password": None,
            "host": None,
            "port": 5432,
            "autocommit": False,
        }
        if not any(kwargs.get(k) for k in ("dbname", "user", "password", "host")):
            raise ValueError(
                "make_dsn: args is None and no database parameters provided via kwargs. "
                "Cannot build DSN."
            )
    else:
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
                "port": None,
                "autocommit": False,
            }

    for k in ("dbname", "user", "password", "host", "port"):
        v = kwargs.get(k, defaults.get(k))
        if v not in (None, ""):
            components.append(f"{k}={v}")

    return " ".join(components)


_pool_cache: dict = {}
_pool_cache_lock = threading.Lock()


def getpool(args: Any, **kwargs: Any) -> ConnectionPool:
    """Get or create a connection pool to PostgreSQL.

    Args:
      args: Application args for DSN construction
      **kwargs: Optional DSN overrides. Supports both 'database' and 'dbname'
                for backward compatibility; 'database' takes precedence.

    Returns:
      ConnectionPool instance (min=10, max=100 connections)

    Raises:
      ValueError: If DSN is empty or invalid (no connection parameters)
    """
    databasename = kwargs.pop("database", kwargs.pop("dbname", None))

    if databasename is not None:
        dsn = make_dsn(args, dbname=databasename, **kwargs)
    else:
        dsn = make_dsn(args, **kwargs)

    if not dsn or dsn == "port=5432":
        raise ValueError(
            "bbsengine6.database.getpool: empty or invalid DSN. "
            "Database connection parameters are required."
        )

    with _pool_cache_lock:
        if dsn not in _pool_cache or _pool_cache[dsn].closed:
            _pool_cache[dsn] = ConnectionPool(
                dsn, min_size=10, max_size=100, timeout=5, open=True
            )

        return _pool_cache[dsn]


def reset_pool_cache() -> None:
    """Reset the pool cache. Call this in tests."""
    global _pool_cache
    with _pool_cache_lock:
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
    args: Any,
    pool: Any = None,
    *,
    auto_commit: bool = True,
    wrapper: bool = False,
    **kwargs: Any,
) -> Generator[Any, None, None]:
    """Context manager that safely gets a connection and returns it to the pool.

    Args:
      args: Application args (for logging, optional)
      pool: ConnectionPool instance
      auto_commit: If True (default), commits before returning connection to pool.
                   Set to False for multi-statement transactions.
      wrapper: If True, yields DatabaseConnection wrapper with method-style API.
      **kwargs: Additional arguments

    Yields:
      Connection from pool (raw or DatabaseConnection wrapper if wrapper=True)
    """
    import traceback

    _debug = args and getattr(args, "debug", False) is True
    if _debug:
        stack = "".join(traceback.format_stack()[-15:])
        io.echo(
            f"database.connect: entering, args.debug={getattr(args, 'debug', 'MISSING')}, auto_commit={auto_commit}, pool={id(pool) if pool else None}",
            level="debug",
        )
        io.echo(f"database.connect: call stack:\n{stack}", level="debug")

    if "readonly" in kwargs:
        del kwargs["readonly"]

    if pool is None:
        # CONN_POOL_PATTERN fallback: try to get pool from args
        if args is not None and hasattr(args, "databasename"):
            try:
                pool = getpool(args)
            except Exception:
                io.echo("bbsengine6.database.connect.200: pool is None", level="error")
                raise ValueError("pool is None")
        else:
            io.echo("bbsengine6.database.connect.200: pool is None", level="error")
            raise ValueError("pool is None")

    conn: Any = None
    try:
        conn = pool.getconn()
        conn.autocommit = False
        if _debug:
            io.echo(
                f"database.connect: got conn id={id(conn)}, autocommit={conn.autocommit}, status={conn.pgconn.transaction_status}",
                level="debug",
            )
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.connect.300: {e}")
        raise

    exception_occurred = False
    try:
        if wrapper:
            yield DatabaseConnection(conn, pool)
        else:
            yield conn
    except BaseException as e:
        exception_occurred = True
        io.echo_traceback(f"bbsengine6.database.connect.400: {e}")
        conn.rollback()
        raise
    finally:
        if conn is not None:
            conn_id = id(conn)
            pool_id = id(pool)
            try:
                tx_status = conn.pgconn.transaction_status
            except Exception:
                tx_status = "unknown"
            if _debug:
                io.echo(
                    f"database.connect: finally for conn id={conn_id} ({hex(conn_id)}), pool id={pool_id}, status={tx_status}, auto_commit={auto_commit}, exception={exception_occurred}",
                    level="debug",
                )
            if auto_commit and not exception_occurred:
                conn.commit()
                if _debug:
                    io.echo(
                        f"database.connect: after commit conn id={conn_id} ({hex(conn_id)}), pool id={pool_id}, status={conn.pgconn.transaction_status}",
                        level="debug",
                    )
            pool.putconn(conn)
            if _debug:
                io.echo(
                    f"database.connect: putconn done conn id={conn_id} ({hex(conn_id)}), pool id={pool_id}, tx_status before={tx_status}",
                    level="debug",
                )


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

        query = sql.SQL("update ") + _table_identifier(table, args) + sql.SQL(" set ")
        params = []
        dat = []
        for k, v in _items.items():
            params.append(sql.Identifier(k) + sql.SQL(" = %s"))  # type: ignore
            dat.append(convert_for_jsonb(v))

        query = (
            query
            + sql.SQL(", ").join(params)  # type: ignore
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
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(f"bbsengine.database.update.120: {pool=}", level="error")
            return False
        with connect(args, pool=pool) as conn:
            try:
                with cursor(conn=conn) as cur:
                    _work(cur)
                    if commit is True:
                        conn.commit()
            except Exception as e:
                io.echo_traceback(f"bbsengine6.database.update.200: {e}")
                return False
            return True
    try:
        with cursor(conn=conn) as cur:
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
            conn=conn,
        )
        # The 'engine' schema is rewritten to args.databaseschema.

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

    def _build_conflict_clause() -> sql.Composable:
        """Build the ON CONFLICT clause."""
        conflict_clause = sql.SQL(" ON CONFLICT (") + sql.SQL(", ").join(
            [sql.Identifier(col) for col in conflict_columns]
        )

        if update_columns:
            # Build UPDATE assignments using EXCLUDED
            conflict_clause = conflict_clause + sql.SQL(") DO UPDATE SET ")
            update_assignments = []
            for col in update_columns:
                update_assignments.append(
                    sql.Identifier(col) + sql.SQL(" = EXCLUDED.") + sql.Identifier(col)
                )
            conflict_clause = conflict_clause + sql.SQL(", ").join(update_assignments)  # type: ignore
        else:
            conflict_clause = conflict_clause + sql.SQL(") DO NOTHING")

        return conflict_clause

    def _work(conn):
        with cursor(conn=conn) as cur:
            # Build column list and values
            columns = list(items.keys())
            values = [convert_for_jsonb(items[col]) for col in columns]

            # Build INSERT clause
            insert_clause = (
                sql.SQL("INSERT INTO ") + _table_identifier(table, args) + sql.SQL(" (")
            )
            insert_clause += sql.SQL(", ").join(
                [sql.Identifier(col) for col in columns]
            )
            insert_clause += sql.SQL(") VALUES (")
            insert_clause += sql.SQL(", ").join([sql.SQL("%s") for _ in columns])
            insert_clause += sql.SQL(")")

            # Build ON CONFLICT clause
            conflict_clause = _build_conflict_clause()

            # Combine full query
            upsert_query = insert_clause + conflict_clause

            if mogrify is True:
                io.echo(
                    f"bbsengine6.database.upsert.150: {mogrifysql(cur, str(upsert_query), values)}",  # type: ignore[arg-type]
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

    items_copy = copy.copy(items)
    columns = items_copy.keys()
    if args.debug is True:
        io.echo(f"bbsengine6.database.insert.140: {columns=}", level="debug")

    for k in list(items_copy.keys()):
        if k == "datecreatedepoch":
            del items_copy[k]

    query = sql.SQL("insert into ") + _table_identifier(table, args) + sql.SQL("(")
    query = query + sql.SQL(", ").join([sql.Identifier(c) for c in columns])
    query = query + sql.SQL(") values (")

    params = []
    for x in range(len(columns)):
        params.append("%s")
    query = query + sql.SQL(", ").join([sql.SQL(p) for p in params])
    query = query + sql.SQL(")")

    dat = [convert_for_jsonb(v) for v in items_copy.values()]
    if returnid is True:
        query = (
            query
            + sql.SQL(" returning ")
            + _table_identifier(table, args)
            + sql.SQL(".")
            + sql.Identifier(primarykey)
        )

    def _work(conn):
        with cursor(conn=conn) as cur:
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
            with connect(args, pool=pool) as managed_conn:
                return _work(managed_conn)
        return _work(conn)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.database.insert.200: {e}")
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        return False


# @see https://soft-builder.com/how-to-list-all-schemas-in-postgresql/
# @since 20230510
# tables, views, etc. NOT functions
def classexists(args: Any, name: str, **kwargs: Any) -> bool:
    def _work(conn):
        mogrify = kwargs.get("mogrify", False)
        with cursor(conn=conn) as cur:
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
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def schemaexists(args: Any, name: str, **kwargs: Any) -> bool:
    mogrify = kwargs.get("mogrify", False)

    def _work(conn):
        sql = (
            "SELECT 't' as exists FROM information_schema.schemata where schema_name=%s"
        )
        dat = (name,)
        with cursor(conn=conn) as cur:
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
        with cursor(conn=conn) as cur:
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
        with cursor(conn=conn) as cur:
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
    databasename = defaults.get(
        "databasename", os.environ.get("BBSENGINE6_DBNAME", "zoid6")
    )
    databasehost = defaults.get(
        "databasehost", os.environ.get("BBSENGINE6_DBHOST", "localhost")
    )
    databaseport = int(
        defaults.get(
            "databaseport", os.environ.get("BBSENGINE6_DBPORT", "5432")
        )
    )
    databaseuser = defaults.get(
        "databaseuser", os.environ.get("BBSENGINE6_DBUSER", None)
    )
    databasepassword = defaults.get(
        "databasepassword", os.environ.get("BBSENGINE6_DBPASSWORD", None)
    )
    databaseschema = defaults.get(
        "databaseschema", os.environ.get("BBSENGINE6_DBSCHEMA", "engine")
    )

    group = parentparser.add_argument_group(label)
    #    group = argparse.ArgumentParser("database", parents=[parentparser], add_help=False)
    if suppress is False:
        group.add_argument(
            "--databasename",
            "--database",
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
) -> Literal[Iterator[Any]]:  # type: ignore
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

        options_sql = sql.SQL(" ").join([sql.SQL(o) for o in options])

        if "password" in kwargs:
            query = sql.SQL(  # type: ignore
                "create role {} with {} password %s"
            ).format(sql.Identifier(name), options_sql)
            io.echo(f"bbsengine.database.createrol.100: {query=}", level="debug")
            cur.execute(query, (kwargs["password"],))
        elif "expiration" in kwargs:
            query = sql.SQL(  # type: ignore
                "create role {} with {} valid until %s"
            ).format(sql.Identifier(name), options_sql)
            io.echo(f"bbsengine.database.createrol.100: {query=}", level="debug")
            cur.execute(query, (kwargs["expiration"],))
        else:
            query = sql.SQL(  # type: ignore
                "create role {} with {}"
            ).format(sql.Identifier(name), options_sql)
            io.echo(f"bbsengine.database.createrol.100: {query=}", level="debug")
            cur.execute(query)
        return False if cur.rowcount == 0 else True

    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            io.echo("bbsengine.database.createrol.140: {conn=}", level="error")
            return False
        with cursor(conn=conn) as cur:
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
        with cursor(conn=conn) as cur:
            return _work(cur)
    except psycopg.DatabaseError as e:
        io.echo_traceback(f"bbsengine6.database.rolexists.200: {e}")
        return False


def exists(args: Any, databasename: str, **kwargs: Any) -> bool:
    """Check whether a PostgreSQL database exists in the cluster.

    The check is cluster-wide (queries ``pg_database``) and case-insensitive
    (matches PostgreSQL's unquoted-identifier folding). The caller may pass
    either a connection (``conn=...``) or a pool (``pool=...``); if neither
    is provided, the function returns ``False`` and logs an error. This
    mirrors the pattern used by ``schemaexists``, ``tableexists``, etc.

    Args:
        args: Application args (for logging).
        databasename: Database name to look up.
        **kwargs: ``conn`` (caller-supplied connection) and/or ``pool``
                  (used as a fallback when ``conn`` is not provided).

    Returns:
        ``True`` if the database exists, ``False`` otherwise (including
        when the connection fails or the lookup raises).
    """
    query = (
        "SELECT 1 FROM pg_database WHERE lower(datname) = lower(%s)"
    )
    dat = (databasename,)

    def _work(conn: Any) -> bool:
        with cursor(conn=conn) as cur:
            cur.execute(query, dat)
            return cur.fetchone() is not None

    conn = kwargs.get("conn", None)
    if conn is not None:
        try:
            return _work(conn)
        except psycopg.DatabaseError as e:
            io.echo_traceback(f"bbsengine6.database.exists.200: {e}")
            return False

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo(
            "bbsengine6.database.exists.180: conn and pool both None",
            level="error",
        )
        return False
    try:
        with connect(args, pool=pool) as conn:
            return _work(conn)
    except psycopg.DatabaseError as e:
        io.echo_traceback(f"bbsengine6.database.exists.200: {e}")
        return False


def create(
    args: Any,
    name: str,
    *,
    owner: str | None = None,
    template: str | None = None,
    encoding: str | None = None,
    lc_collate: str | None = None,
    lc_ctype: str | None = None,
    **kwargs: Any,
) -> bool:
    """Create a new PostgreSQL database.

    IMPORTANT - AUTOCOMMIT CONTRACT:
        PostgreSQL rejects ``CREATE DATABASE`` inside an explicit transaction
        block. When called with a caller-supplied ``conn``, the connection MUST
        have ``conn.autocommit = True``. This function does NOT modify
        autocommit for the caller-supplied ``conn`` path. If you obtained your
        connection through ``database.connect()`` (which forces autocommit
        off), flip it before calling, e.g.::

            conn.autocommit = True
            database.create(args, "mydb", conn=conn)
            conn.autocommit = False

        Failure to do so will surface a server-side "CREATE DATABASE cannot
        run inside a transaction block" error, which this function catches
        and reports as a return value of ``False`` (see below).

    DUPLICATE-NAME BEHAVIOR:
        PostgreSQL has no ``CREATE DATABASE IF NOT EXISTS``. If ``name``
        already exists, the server raises ``psycopg.errors.DuplicateDatabase``
        (SQLSTATE ``42P04``). This function catches that (and any other
        exception), logs the traceback via ``io.echo_traceback``, and returns
        ``False``. Callers wanting idempotent behavior should pre-check with
        ``database.exists(args, name, pool=pool)``.

    Args:
        args: Application args (for debug logging).
        name: Database name to create. Forwarded via ``sql.Identifier`` for
              safe quoting.
        owner: Optional role name to own the new database. ``sql.Identifier``.
        template: Optional template database name. ``sql.Identifier``.
        encoding: Optional character set encoding (e.g. ``"UTF8"``). Forwarded
                  via ``sql.Literal`` (server-side string, not an identifier).
        lc_collate: Optional LC_COLLATE locale. ``sql.Literal``.
        lc_ctype: Optional LC_CTYPE locale. ``sql.Literal``.
        **kwargs: Optional ``conn`` (caller-supplied connection, must be
                  autocommit) and/or ``pool`` (used as a fallback when
                  ``conn`` is not provided; the function will temporarily
                  set ``autocommit = True`` on the pooled connection and
                  restore the prior value on exit).

    Returns:
        ``True`` on success, ``False`` on any caught failure (including
        duplicate names and the "cannot run inside a transaction block"
        error when the autocommit contract is violated).
    """

    def _work(cur):
        clauses = [
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name))
        ]
        opts: list[sql.Composable] = []
        if owner is not None:
            opts.append(sql.SQL("OWNER = {}").format(sql.Identifier(owner)))
        if template is not None:
            opts.append(sql.SQL("TEMPLATE = {}").format(sql.Identifier(template)))
        if encoding is not None:
            opts.append(sql.SQL("ENCODING = {}").format(sql.Literal(encoding)))
        if lc_collate is not None:
            opts.append(sql.SQL("LC_COLLATE = {}").format(sql.Literal(lc_collate)))
        if lc_ctype is not None:
            opts.append(sql.SQL("LC_CTYPE = {}").format(sql.Literal(lc_ctype)))
        if opts:
            clauses.append(sql.SQL("WITH"))
            clauses.append(sql.SQL(" ").join(opts))
        stmt = sql.SQL(" ").join(clauses)
        try:
            cur.execute(stmt)
        except psycopg.Error as e:
            # Catch only DB-level errors. A broad `except Exception`
            # would also swallow programming errors (TypeError when
            # sql.Identifier rejects a name, etc.) and report them as
            # "database create failed", which is misleading.
            io.echo_traceback(f"bbsengine6.database.create.200: {e}")
            return False
        return True

    if args and getattr(args, "debug", False) is True:
        io.echo(
            f"bbsengine6.database.create.100: name={name}, owner={owner}, "
            f"template={template}, encoding={encoding}",
            level="debug",
        )

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(
                "bbsengine6.database.create.180: conn and pool both None",
                level="error",
            )
            return False
        # Pool path: temporarily flip autocommit on for the duration of the
        # call, then restore. This is the ONLY path in this function that
        # modifies autocommit, per the documented autocommit contract.
        prev_autocommit: Any = None
        had_conn = False
        try:
            with connect(args, pool=pool) as conn:
                had_conn = True
                prev_autocommit = conn.autocommit
                conn.autocommit = True
                with cursor(conn=conn) as cur:
                    return _work(cur)
        finally:
            if had_conn and prev_autocommit is not None:
                try:
                    conn.autocommit = prev_autocommit
                except Exception:
                    pass
        return False

    if args and getattr(args, "debug", False) is True:
        io.echo(
            f"bbsengine6.database.create.100: using caller conn id={id(conn)}, "
            f"autocommit={conn.autocommit} (must be True)",
            level="debug",
        )

    with cursor(conn=conn) as cur:
        return _work(cur)


def createschema(args: Any, name: str, **kwargs: Any) -> bool:
    io.echo(f"bbsengine.database.createschema.120: {name=}", level="debug")

    # Connect to the database using args
    def _work(conn):
        stmt = sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(name))
        io.echo(f"bbsengine6.database.createschema.260: {stmt=}", level="debug")
        with cursor(conn=conn) as cur:
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
) -> dict | None:
    """Return the role-privs dict for ``rolname`` or ``None`` on failure.

    The return type is normalized to ``dict | None``: callers can use
    ``if not privs:`` to detect both "no privs" and "lookup failed",
    avoiding the previous ``dict | bool`` ambiguity where the
    no-conn/no-pool path returned ``False`` and a successful empty
    privs lookup returned ``{}`` (which are different things).
    """

    def _work(cur):
        sql = "SELECT get_role_privs(%s);"
        cur.execute(sql, (rolname,))
        result = cur.fetchone()
        if result is None:
            return None
        privs = result.get("get_role_privs")
        return privs if isinstance(privs, dict) else None

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            return None

        with connect(args, pool=pool) as conn:
            with cursor(conn=conn) as cur:
                return _work(cur)
    else:
        with cursor(conn=conn) as cur:
            return _work(cur)


def manage_role_privs(
    args: Any, role_name: str, action: str, priv: str, **kwargs: Any
) -> Any:
    def _work(conn):
        sql = "select manage_role_privs(%s, %s, %s)"
        dat = (role_name, action, priv)
        with cursor(conn=conn) as cur:
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
        with cursor(conn=conn) as cur:
            return _work(cur)
    except psycopg.DatabaseError as e:
        io.echo_traceback(f"bbsengine6.database.manage_secondary_role.200: {e}")
        return False


def cursor(conn: Any = None, row_factory: Any = dict_row, **kwargs: Any) -> Any:
    """Create a cursor with the specified row factory.

    Args:
      conn: Database connection (can be passed as arg or via kwargs)
      row_factory: Row factory (default: dict_row for dict results)
      **kwargs: Additional arguments (conn can be passed here)

    Returns:
      Cursor instance
    """
    if conn is None:
        conn = kwargs.get("conn", None)
    return conn.cursor(row_factory=row_factory)


class DatabaseCursor:
    """Wrapper around psycopg Cursor with auto-conversion and DB-API methods."""

    def __init__(self, cursor: Any, connection: Any = None):
        self._cursor = cursor
        self._connection = connection

    @property
    def description(self) -> Any:
        return self._cursor.description

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def arraysize(self) -> int:
        return self._cursor.arraysize

    @arraysize.setter
    def arraysize(self, value: int) -> None:
        self._cursor.arraysize = value

    @property
    def rownumber(self) -> int | None:
        return self._cursor.rownumber

    @property
    def connection(self) -> Any:
        return self._connection

    def execute(self, operation: str, params: Any = None) -> None:
        if params:
            converted = [convert_for_jsonb(p) for p in params]
            self._cursor.execute(operation, converted)
        else:
            self._cursor.execute(operation)

    def executemany(self, operation: str, seq_of_params: list) -> None:
        for params in seq_of_params:
            converted = [convert_for_jsonb(p) for p in params]
            self._cursor.execute(operation, converted)

    def fetchone(self) -> Any:
        return self._cursor.fetchone()

    def fetchmany(self, size: int | None = None) -> Any:
        if size is None:
            return self._cursor.fetchmany()
        return self._cursor.fetchmany(size)

    def fetchall(self) -> Any:
        return self._cursor.fetchall()

    def scroll(self, value: int, mode: str = "relative") -> None:
        self._cursor.scroll(value, mode)

    def nextset(self) -> bool | None:
        return self._cursor.nextset()

    def close(self) -> None:
        self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)


class DatabaseConnection:
    """Wrapper around psycopg Connection providing DB-API compatible method interface."""

    def __init__(self, conn: Any, pool: Any = None):
        self._conn = conn
        self._pool = pool

    def cursor(self, row_factory: Any = dict_row) -> DatabaseCursor:
        return DatabaseCursor(self._conn.cursor(row_factory=row_factory), self)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        if self._pool:
            self._pool.putconn(self._conn)

    @property
    def autocommit(self) -> bool:
        return self._conn.autocommit

    @autocommit.setter
    def autocommit(self, value: bool) -> None:
        self._conn.autocommit = value


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
            with cursor(conn=conn) as cur:
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
            with cursor(conn=conn) as cur:
                return _work(cur)
    else:
        return _work(cur)


def creatextension(args: Any, ext: str, **kwargs: Any) -> bool:
    def _work(cur):
        try:
            sql = psycopg.sql.SQL(  # type: ignore
                "CREATE EXTENSION IF NOT EXISTS {}"
            ).format(psycopg.sql.Identifier(ext))
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
            with cursor(conn=conn) as cur:
                return _work(cur)
    else:
        return _work(cur)


# @since 20241212
def importsql(
    args: Any, filename: str, *, rollback: bool = True, **kwargs: Any
) -> bool:
    # SECURITY: validate `package` against an allowlist. `package` is
    # forwarded to util.load_sql, which uses it to resolve the on-disk
    # SQL directory. An attacker (or buggy caller) that can pass
    # `package="../../etc"` or similar would be able to read arbitrary
    # .sql resources and execute them as the connecting DB role.
    package = kwargs.get("package", None)
    _ALLOWED_PACKAGES = {
        None,
        "bbsengine6",
        "bbsengine6.backend",
        "bbsengine6.startup",
        "bbsengine6.engine",
    }
    if package not in _ALLOWED_PACKAGES:
        io.echo(
            f"bbsengine6.database.importsql.050: refusing to load SQL from "
            f"package={package!r} (not in allowlist)",
            level="error",
        )
        return False

    def _work(conn):
        #    io.echo(f"bbsengine.database.importsql.140: {conn=}", level="debug")
        #    fullpath = util.get_safe_path(args, *components, **kwargs)
        #    io.echo(f"bbsengine.database.importsql.120: {fullpath=}", level="debug")

        try:
            sql_script = util.load_sql(args, filename, package=package)
            #      with open(fullpath, 'r') as file:
            #        sql_script = file.read()
            with cursor(conn=conn) as cur:
                try:
                    cur.execute(sql_script)
                except psycopg.errors.Error as e:
                    io.echo_traceback(f"bbsengine6.database.importsql.200: {e}")
                    if rollback:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    return False
        except Exception as e:
            io.echo_traceback(f"bbsengine6.database.importsql.300: {e}")
            if rollback:
                try:
                    conn.rollback()
                except Exception:
                    pass
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


def verify_function_owner(
    args: Any,
    name: str,
    expected_owners: tuple[str, ...] | str,
    **kwargs: Any,
) -> bool:
    """Check that the function ``name`` exists and is owned by one of
    ``expected_owners``.

    ``expected_owners`` may be a single role name (string) or a
    tuple of acceptable role names. Returns True on success, False
    otherwise (including the function not existing or the owner not
    matching). Logs a clear error message when the check fails.

    This is intended to gate calls to SECURITY DEFINER functions
    installed by the BBS engine. If the function has been replaced
    or its owner changed (e.g. by an attacker who obtained DDL on
    the database), calls to it would execute as the new owner and
    could escalate privileges. The check is a runtime guard
    complement to the install-time checks in checkengine.py.
    """

    def _work(conn):
        if "." in name:
            schema, function_name = name.split(".", 1)
        else:
            schema, function_name = "public", name
        sql = (
            "SELECT r.rolname AS owner "
            "FROM pg_proc p "
            "JOIN pg_namespace n ON p.pronamespace = n.oid "
            "JOIN pg_roles r ON p.proowner = r.oid "
            "WHERE p.proname = %s AND n.nspname = %s"
        )
        with cursor(conn=conn) as cur:
            cur.execute(sql, (function_name, schema))
            row = cur.fetchone()
        if row is None:
            io.echo(
                f"bbsengine6.database.verify_function_owner.100: "
                f"function {name!r} does not exist",
                level="error",
            )
            return False
        owner = row["owner"] if isinstance(row, dict) else row[0]
        if isinstance(expected_owners, str):
            ok = owner == expected_owners
        else:
            ok = owner in expected_owners
        if not ok:
            io.echo(
                f"bbsengine6.database.verify_function_owner.200: "
                f"function {name!r} is owned by {owner!r}, expected one of "
                f"{expected_owners!r}. Refusing to call it. "
                f"Reinstall the function or update the expected owner.",
                level="error",
            )
            return False
        return True

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(
                f"bbsengine6.database.verify_function_owner.300: "
                f"no conn or pool supplied for {name!r}",
                level="error",
            )
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
        with cursor(conn=conn) as cur:
            cur.execute(sql, dat)
            #    io.echo(f"bbsengine6.database.functionexists.120: {mogrifysql(cur, sql, dat)=} {cur.rowcount=}", level="debug")
            return True if cur.rowcount > 0 else False

    try:
        conn = kwargs.get("conn", None)
##        io.echo(f"bbsengine.database.functionexists.140: {conn=}", level="debug")
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
        with cursor(conn=conn) as cur:
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
        with cursor(conn=conn) as cur:
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


# ============================================================
# ASYNC DATABASE SUPPORT
# @since 20250622
# ============================================================

import asyncio
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool


_async_pools: dict[str, AsyncConnectionPool] = {}


async def get_async_pool(
    args: Any, database: str | None = None, dbname: str | None = None
) -> AsyncConnectionPool:
    """Get or create an async connection pool.

    Args:
        args: Application args for DSN construction
        database: Optional database name override (preferred)
        dbname: Optional database name override (legacy, for backward compatibility)

    Returns:
        AsyncConnectionPool instance (min=2, max=10 connections)
    """
    db = database or dbname
    key = db or getattr(args, "databasename", None) or DEFAULTDATABASE
    dsn = make_dsn(args, **(dict(database=db) if db else {}))

    # Return existing pool if valid
    if key in _async_pools and not _async_pools[key].closed:
        return _async_pools[key]

    # Close and remove stale pool if exists
    if key in _async_pools:
        try:
            await _async_pools[key].close()
        except Exception:
            pass
        del _async_pools[key]

    _async_pools[key] = AsyncConnectionPool(
        dsn,
        min_size=2,
        max_size=10,
        timeout=30.0,
        open=False,
    )
    await _async_pools[key].open()

    return _async_pools[key]


async def reset_async_pool_cache() -> None:
    """Reset the async pool cache. Call this in tests."""
    global _async_pools
    for pool in _async_pools.values():
        try:
            await pool.close()
        except Exception:
            io.echo_traceback("bbsengine6.database.reset_async_pool_cache:")
    _async_pools = {}


class AsyncDBConnection:
    """Async wrapper for database connection."""

    def __init__(self, conn: Any):
        self._conn = conn

    @property
    def cursor(self):
        return AsyncCursor(self._conn)

    async def __aenter__(self) -> "AsyncDBConnection":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._conn.close()


class AsyncCursor:
    """Async cursor wrapper."""

    def __init__(self, conn: Any):
        self._conn = conn
        self._cur = None

    async def execute(self, query: Any, params: dict | None = None) -> "AsyncCursor":
        self._cur = self._conn.cursor(row_factory=dict_row)
        if params:
            await self._cur.execute(query, params)
        else:
            await self._cur.execute(query)
        return self

    async def fetchone(self) -> dict | None:
        row = await self._cur.fetchone()
        return dict(row) if row else None

    async def fetchall(self) -> list[dict]:
        rows = await self._cur.fetchall()
        return [dict(row) for row in rows] if rows else []

    async def __aenter__(self) -> "AsyncCursor":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._cur:
            await self._cur.close()


@asynccontextmanager
async def async_connect(
    args: Any,
    pool: AsyncConnectionPool | None = None,
    *,
    auto_commit: bool = True,
    database: str | None = None,
    dbname: str | None = None,
) -> AsyncDBConnection:
    """Async context manager for database connections.

    Args:
        args: Application args
        pool: AsyncConnectionPool instance (optional)
        auto_commit: If True (default), commits before returning connection
        database: Optional database name (preferred)
        dbname: Optional database name (legacy, for backward compatibility)

    Yields:
        AsyncDBConnection wrapper

    Note:
        In psycopg-pool 3.3.0+, pool.connection() returns an AsyncIterator context manager,
        not an awaitable. This function handles both old (3.1.x) and new (3.3.0+) APIs.
    """
    if pool is None:
        pool = await get_async_pool(args, database, dbname)

    # psycopg-pool 3.3.0+ changed pool.connection() to return an async context manager
    # Handle both old (3.1.x) and new (3.3.0+) APIs
    try:
        # Try new 3.3.0+ API: async with pool.connection() as conn
        async with pool.connection() as conn:
            yield AsyncDBConnection(conn)
    except TypeError:
        # Fall back to old 3.1.x API: conn = await pool.connection()
        conn = await pool.connection()
        yield AsyncDBConnection(conn)


async def async_query(
    args: Any,
    sql: str,
    pool: AsyncConnectionPool | None = None,
    *,
    database: str | None = None,
    dbname: str | None = None,
    **params: Any,
) -> list[dict]:
    """Async query helper - executes SQL and returns list of dicts.

    Args:
        args: Application args
        sql: SQL query with named parameters (:param)
        pool: Optional async pool
        database: Optional database name (preferred)
        dbname: Optional database name (legacy, for backward compatibility)
        **params: Query parameters

    Returns:
        List of result rows as dicts
    """
    sql_processed = query(sql, **params) if params else query(sql)
    async with async_connect(args, pool, database=database, dbname=dbname) as db_conn:
        async with db_conn.cursor as cur:
            await cur.execute(sql_processed)
            return await cur.fetchall()
