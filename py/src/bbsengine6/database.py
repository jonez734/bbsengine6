import copy
import json

import argparse

#import psycopg2, psycopg2.extras
#from psycopg2.extras import Json
#from psycopg2.extensions import parse_dsn, make_dsn
from psycopg.types.json import Jsonb
from psycopg.rows import dict_row
import psycopg, psycopg.sql

from psycopg import sql

from psycopg_pool import ConnectionPool

from . import io, util

DEFAULTDATABASE = "postgres"

def getoid(args, typ, cur=None):
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
    io.echo(f"bbsengine6.database.getoid.100: {e}", level="error")
    raise

#JSONB_OID = getoid("jsonb") # 3802
#JSON_OID = getoid("json") # 114

def mogrifysql(cur, query, params):
    # Create a SQL object using sql.SQL and format it with sql.Placeholder()
    formatted_query = sql.SQL(query).format(*[sql.Placeholder()] * len(params))

    # Manually interpolate the params into the query for logging/debugging
    formatted_query_str = formatted_query.as_string(cur.connection)

    # Replace placeholders with actual parameter values (escaping them correctly)
    formatted_query_with_values = formatted_query_str % params

    return formatted_query_with_values

def parse_dsn(dsn):
    params = {}
    for part in dsn.split():
        key, value = part.split('=', 1)
        params[key] = value
    return params

def make_dsn(args, **kwargs): # dbname=None, user=None, password=None, host=None, port=None):
    components = []
#    for key, value in kwargs.items():
#        if value is not None:  # Only add components where the value is provided
#            components.append(f"{key}={value}")
#
#    return ' '.join(components)

    defaults = {"dbname":args.databasename, "user":args.databaseuser, "password":args.databasepassword, "host":args.databasehost, "port":args.databaseport, "autocommit":False}
    for k in ("dbname", "user", "password", "host", "port"): # , "autocommit"):
      v = kwargs.get(k, defaults[k])
#      io.echo(f"make_dsn.100: {k=} {v=}", level="debug")
      if v is not None:
        components.append(f"{k}={v}")

    # io.echo(f"bbsengine.database.make_dsn.100: {kwargs=} {components=}", level="debug")
    return ' '.join(components)

def getpool(args, **kwargs):
  dsn = make_dsn(args, **kwargs)
  # io.echo(f"bbsengine.getpool.120: {dsn=}", level="debug")

  pool = ConnectionPool(dsn, min_size=10, max_size=100, timeout=5, open=True)
  # io.echo(f"bbsengine.getpool.100: {pool=}", level="debug")
  return pool

def transaction(conn, **kwargs):
  io.echo(f"database.transaction.100: {kwargs=}", level="debug")
  readonly = kwargs.get("readonly", None)
#  conn.read_only = readonly
  return conn.transaction()

#databasehandles = {}
def connect(args, **kwargs):
  # io.echo(f"bbsengine.database.connect.220: {kwargs=}", level="debug")

  pool = kwargs.pop("pool", None)
  if pool is None:
    io.echo(f"bbsengine6.database.connect.100: {pool=}", level="error")
    return None

  conn = pool.getconn()
  # io.echo(f"bbsengine.database.260: {conn=}", level="debug")
  return conn

#  conn = pool.connection()
#  autocommit = kwargs.pop("autocommit", False)
#  conn.autocommit = autocommit
#  with pool.connection() as conn:
#    io.echo(f"bbsengine.database.260: {conn=}", level="debug")
#    return conn
#  io.echo(f"bbsengine.database.connect.240: {conn=}", level="debug")
#  return conn
#  conn.autocommit = False
#  conn.read_only = True

#  readonly = kwargs.get("readonly", False)
#  if readonly is True:
#    conn.set_isolation_level(psycopg.ISOLATION_LEVEL_READ_ONLY)

#  conn.row_factory = psycopg.rows.dict_row

# this one is only truly useful when custom dumps and loads are needed
#  psycopg.types.json.register_json(conn, dumps=json.dumps, loads=json.loads, oids=[JSON_OID, JSONB_OID])
  return conn

#def buildkwargs(args, **kwargs):
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

def update(args, table:str, pk:str, items:dict, **kwargs) -> int: # primarykey="id", mogrify:bool=False, updatepk:bool=False, **kwargs) -> int:
  primarykey = kwargs.get("primarykey", "id")
  mogrify = kwargs.get("mogrify", False)
  updatepk = kwargs.get("updatepk", False)
  commit = kwargs.get("commit", False)

  def _work(cur):
    for k, v in items.items():
      if k == "datecreatedepoch":
        continue

    _items = copy.deepcopy(items)
    if primarykey in _items and updatepk is False:
      del _items[primarykey]

    sql = "update %s set " % (table)
    params = []
    dat = []
    for k, v in _items.items():
      params.append("%s=%%s" % (k),)
      dat.append(v)

    sql += ", ".join(params)
    sql += " where %s=%%s" % (primarykey)
    dat.append(pk)

    cur.execute(sql, dat)
    return cur.rowcount

  if args.debug is True:
    io.echo(f"bbsengine6.database.update.100: {items=}", level="debug")
  conn = kwargs.get("conn", None)
  if conn is None:
    io.echo(f"bbsengine.database.update.120: {conn=}", level="error")
    return False
  with cursor(conn) as cur:
    _work(cur)
    if commit is True:
      conn.commit()

def insert(args, table:str, items:dict, **kwargs): # returnid:bool=True, primarykey:str="id", mogrify:bool=True):
  def _work(conn):
    with cursor(conn) as cur:
      cur.execute(sql, dat)
      if returnid is True:
        res = cur.fetchone()
        if primarykey in res:
          return res[primarykey]
        else:
          return None

  primarykey = kwargs.get("primarykey", "id")
  returnid = kwargs.get("returnid", True)
  mogrify = kwargs.get("mogrify", True)

#  cur = kwargs.get("cur", None)

  io.echo(f"bbsengine6.database.insert.100: {items=}", level="debug")

  if items is None:
    io.echo("bbsengine6.database.insert.120: no columns specified", level="error")
    return None

  columns = items.keys()
  if args.debug is True:
    io.echo(f"bbsengine6.database.insert.140: {columns=}", level="debug")

  for k, v in items.items():
    if k == "datecreatedepoch":
      del items[k]

  sql = "insert into %s(" % (table)
  sql += ", ".join(columns)
  sql += ") values ("

  params = []
  for x in range(len(columns)):
    params.append("%s")
  sql += ", ".join(params)
  sql += ")"

  dat = []
  for v in items.values():
    dat.append(v)
  if returnid is True:
    sql += f" returning {table}.{primarykey}"

  try:
    conn = kwargs.get("conn", None)
    if conn is None:
      pool = kwargs.get("pool", None)
      if pool is None:
        io.echo(f"bbsengine.database.insert.200: {pool=}", level="error")
        return None
      with connect(args, pool=pool) as conn:
        return _work(conn)
    return _work(conn)
  except Exception as e:
    io.echo(f"bbsengine6.database.insert.180: database error: {e}", level="error")
    raise

# @see https://soft-builder.com/how-to-list-all-schemas-in-postgresql/
# @since 20230510
# tables, views, etc. NOT functions
def classexists(args, name, **kwargs):
  def _work(conn):
    mogrify = kwargs.get("mogrify", False)
    with cursor(conn) as cur:
      sql = "select to_regclass(%s) as class" # does not work with schemas
      dat = (name,)
      cur.execute(sql, dat)
      if mogrify is True:
        io.echo(f"bbsengine6.database.classexists.120: {mogrifysql(cur, sql, dat)=}", level="debug")
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
        return None
      with connect(args, pool=pool) as conn:
        return _work(conn)
    return _work(conn)
  except Exception as e:
    io.echo(f"bbsengine6.database.classexists.140: {e}", level="error")
    raise

def schemaexists(args, name, **kwargs):
  mogrify = kwargs.get("mogrify", False)

  def _work(conn):
    sql = "SELECT 't' as exists FROM information_schema.schemata where schema_name=%s"
    dat = (name,)
    if mogrify is True:
      io.echo(f"bbsengine6.database.schemaexists.100: {mogrifysql(cur, sql, dat)=}", level="debug")
    with cursor(conn) as cur:
      cur.execute(sql, dat)
      return False if cur.rowcount == 0 else True

  try:
    conn = kwargs.get("conn", None)
    if conn is None:
      pool = kwargs.get("pool", None)
      if pool is None:
        return None
      with connect(args, pool=pool) as conn:
        return _work(conn)
    return _work(conn)
  except Exception as e:
    io.echo(f"bbsengine6.database.schemaexists.120: error {e}", level="error")
    raise

# @since 20230510 copied from bbsengine5.py
def buildargs(parentparser:object, defaults:dict={}, label="database options", suppress=False):
    databasename = defaults.get("databasename", "zoid6")
    databasehost = defaults.get("databasehost", "localhost")
    databaseport = defaults.get("databaseport", 5432)
    databaseuser = defaults.get("databaseuser", None)
    databasepassword = defaults.get("databasepassword", None)
    databaseschema = defaults.get("databaseschema", None)
    
    group = parentparser.add_argument_group(label)
#    group = argparse.ArgumentParser("database", parents=[parentparser], add_help=False)
    if suppress is False:
      group.add_argument("--databasename", dest="databasename", action="store", default=databasename, type=str, help="database name (default: %(default)r)")
      group.add_argument("--databasehost", dest="databasehost", action="store", default=databasehost, type=str, help="database host (default: %(default)r)")
      group.add_argument("--databaseport", dest="databaseport", action="store", default=databaseport, type=int, help="database port (default: %(default)r)")
      group.add_argument("--databaseuser", dest="databaseuser", action="store", default=databaseuser, type=str, help="database user (default: %(default)r)")
      group.add_argument("--databasepassword", dest="databasepassword", action="store", default=databasepassword, type=str, help="database password (default: %(default)r)")

      group.add_argument("--databaseschema", dest="databaseschema", action="store", default=databaseschema, type=str, help="schema to use")
    else:
      group.add_argument("--databasename", dest="databasename", action="store", default=databasename, type=str, help=argparse.SUPPRESS)
      group.add_argument("--databasehost", dest="databasehost", action="store", default=databasehost, type=str, help=argparse.SUPPRESS) # "database host (default: %(default)r)")
      group.add_argument("--databaseport", dest="databaseport", action="store", default=databaseport, type=int, help=argparse.SUPPRESS) # "database port (default: %(default)r)")
      group.add_argument("--databaseuser", dest="databaseuser", action="store", default=databaseuser, type=str, help=argparse.SUPPRESS) # "database user (default: %(default)r)")
      group.add_argument("--databasepassword", dest="databasepassword", action="store", default=databasepassword, type=str, help=argparse.SUPPRESS) # "database password (default: %(default)r)")

    return

buildargdatabasegroup = buildargs
buildarggroup = buildargs

# @since 20211101
# @since 20230515 copied from bbsengine5
def resultiter(cur, arraysize:int=1000, filterfunc:callable=None, **kwargs:dict):
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

def commit(args, **kwargs):
  io.echo("bbsengine6.database.commit.100: stub", level="warn")
  return False

  with connect(args) as conn:
    conn.commit()

# @since 20230715 used by empyre
def rollback(args, conn=None, **kwargs):
  if conn is not None:
    return conn.rollback()

def createrol(args, name, **kwargs):
  # Map privilege keys to their SQL counterparts
  privilege_map = {
    "login": ("login", "nologin", False),
    "superuser": ("superuser", "nosuperuser", False),
    "createdb": ("createdb", "nocreatedb", False),
    "createrole": ("createrole", "nocreaterole", False),
    "inherit": ("inherit", "noinherit", False),
    "replication": ("replication", "noreplication", False)
  }

  options = []

  def _work(cur):
    for priv, (enabled, disabled, default) in privilege_map.items():
        value = kwargs.get(priv, default)
        options.append(enabled if value else disabled)

    # Handle password if provided
    if "password" in kwargs:
      options.append(f"password '{kwargs['password']}'")

    # Handle expiration if provided
    if "expiration" in kwargs:
      options.append(f"valid until '{kwargs['expiration']}'")

    sql = f"create role \"{name}\" with {' '.join(options)}"
    io.echo(f"bbsengine.database.createrol.100: {sql=}", level="debug")
    cur.execute(sql)
    return False if cur.rowcount == 0 else True

  try:
    conn = kwargs.get("conn", None)
    if conn is None:
      io.echo("bbsengine.database.createrol.140: {conn=}", level="error")
      return False
    with cursor(conn) as cur:
      return _work(cur)
  except psycopg.DatabaseError as e:
    io.echo(f"bbsengine6.createrol.100: Error creating role: {e}", level="error")
    raise

def rolexists(args, rolname, **kwargs):
  def _work(cur):
    sql = "SELECT rolname FROM pg_roles where rolname=%s"
    dat = (rolname,)
    cur.execute(sql, dat)
    if args.debug is True:
      io.echo(f"bbsengine6.database.rolexists.100: {mogrifysql(cur, sql, dat)=}", level="debug")
    return False if cur.rowcount == 0 else True

  mogrify = kwargs.get("mogrify", False)
  conn = kwargs.get("conn", None)
  if conn is None:
    io.echo(f"bbsengine.database.rolexists.100: {conn=}", level="error")
    return False

  try:
    with cursor(conn) as cur:
      return _work(cur)
  except psycopg.DatabaseError as e:
    io.echo(f"bbsengine6.database.rolexists.120: database error {e}", level="error")
    raise

def exists(args, databasename, **kwargs):
  mogrify = kwargs.get("mogrify", True)
  pool = kwargs.get("pool", None)
  if pool is None:
    io.echo("database.exists.200: no pool", level="error")
    return False

  try:
    with connect(args, database=DEFAULTDATABASE, pool=pool) as conn:
      sql = "SELECT datname FROM pg_catalog.pg_database WHERE lower(datname) = lower(%s)"
      dat = (databasename,)
      with cursor(conn) as cur:
        cur.execute(sql, dat)
        return False if cur.rowcount == 0 else True
  except psycopg.DatabaseError as e:
    io.echo(f"bbsengine6.database.exists.120: database error {e}", level="error")
    raise

def create(args, name, **kwargs):
  from psycopg.sql import SQL, Identifier

  def _work(cur):
    # Use psycopg.sql.Identifier to safely handle the database name
    try:
      sql = SQL("CREATE DATABASE {}").format(Identifier(name))
      cur.execute(sql)
    except Exception as e:
      io.echo(f"bbsengine.database.create.200: {e}", level="error")
      return False
    return True

  conn = kwargs.get("conn", None)
  if conn is None:
    io.echo(f"bbsengine.database.create.180: {conn=}", level="error")
    return False
  io.echo(f"{conn=}", level="debug")
  with cursor(conn) as cur:
    
    return _work(cur)

def createschema(args, name, **kwargs):
    io.echo(f"bbsengine.database.createschema.120: {name=}", level="debug")
    # Connect to the database using args
    def _work(conn):
      stmt = sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(name))
      io.echo(f"bbsengine6.database.createschema.260: {stmt=}", level="debug")
      with cursor(conn) as cur:
        cur.execute(stmt)

    try:
      io.echo(f"bbsengine6.database.createschema.220: {kwargs=}", level="debug")
      conn = kwargs.get("conn", None)
      if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
          io.echo(f"bbsengine6.database.createschema.200: pool is None", level="error")
          return False
        with connect(args, pool=pool) as conn:
          return _work(conn)
      return _work(conn)
    except psycopg.DatabaseError as e:
      io.echo(f"bbsengine6.database.createschema.100: database error: {e}")
      raise

def get_role_privs(args, rolname: str, cur=None, **kwargs) -> dict:
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

def manage_role_privs(args, role_name, action, priv, **kwargs):
  def _work(conn):
    sql = "select manage_role_privs(%s, %s, %s)"
    dat = (role_name, action, priv)
    with cursor(conn) as cur:
      return cur.execute(sql, dat)

  conn = kwargs.get("conn", None)
  if conn is None:
    pool = kwargs.get("pool", None)
    if pool is None:
      io.echo(f"bbsengine6.database.manage_role_privs.120: {pool=}", level="error")
      return False
    with connect(args, pool=pool) as conn:
      return _work(conn)
  return _work(conn)

def manage_secondary_role(args, role_name, action, secondary, **kwargs):
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
    io.echo(f"bbsengine6.database.manage_secondary_role.100: database error {e}", level="error")
    raise

def cursor(conn, row_factory=dict_row, **kwargs):
    """
    Creates a cursor using the provided connection and applies the desired row factory.
    @since 20241016
    """
    return conn.cursor(row_factory=row_factory)

def extensionavailable(args, ext, **kwargs):
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

def extensioninstalled(args, ext, **kwargs):
    def _work(cur):
        try:
            sql = "select * from pg_extension where extname=%s"
            dat = (ext,)
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return False
            return True
        except Exception as e:
            io.echo(f"exception while checking to see if {ext} is installed: {e}")
            return False
    cur = kwargs.get("cur", None)
    if cur is None:
      pool = kwargs.get("pool", None)
      with connect(args, pool=pool) as conn:
        with cursor(conn) as cur:
          return _work(cur)
    else:
        return _work(cur)

def creatextension(args, ext, **kwargs):
    def _work(cur):
        try:
            sql = psycopg.sql.SQL("CREATE EXTENSION IF NOT EXISTS {}").format(psycopg.sql.Identifier(ext))
#            sql = "create extension if not exists %s"
            cur.execute(sql)
        except psycopg.errors.InsufficientPrivilege:
            io.echo(f"error: permission denied creating extension {ext}", level="error")
            return False
        except psycopg.errors.UndefinedFile:
            io.echo(f"error: {ext} is not available", level="error")
            return False
        except Exception as e:
            io.echo(f"error: {e}", level="error")
            return False
        else:
            return True

    cur = kwargs.get("cur", None)
    if cur is None:
      pool = kwargs.get("pool", None)
      with connect(args, pool=pool) as conn:
        with database.cursor(conn) as cur:
          return _work(cur)
    else:
        return _work(cur)

# @since 20241212
def importsql(args, filename, **kwargs) -> bool:
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
          io.echo(f"fail", level="error")
          io.echo(f"sql execute: {e}")
          return False
    except Exception as e:
      io.echo(f"bbsengine.database.importsql.160: An error occurred: {e}", level="error")
      return False
    return True

  conn = kwargs.get("conn", None)
  if conn is None:
    pool = kwargs.get("pool", None)
    if pool is None:
      io.echo(f"importsql.100: no connection and no pool", level="error")
      return False
    with connect(pool) as conn:
      return _work(conn)
  return _work(conn)

def functionexists(args, name, **kwargs):
  mogrify = kwargs.get("mogrify", True)

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
    io.echo(f"bbsengine6.database.functionexists.140: {e}", level="error")
    raise

# @since 20250511
def manage_database_priv(args, action, priv, database_name, target_role, **kwargs):
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
      io.echo(f"bbsengine6.database.manage_database_priv.120: {pool=}", level="error")
      return False
    with connect(args, pool=pool) as conn:
      return _work(conn)
  return _work(conn)

# @since 20250511
def manage_schema_priv(args, action, priv, database_name, target_role, **kwargs):
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
      io.echo(f"bbsengine6.database.manage_schema_priv.120: {pool=}", level="error")
      return False
    with connect(args, pool=pool) as conn:
      return _work(conn)
  return _work(conn)
