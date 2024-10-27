import copy

import argparse

#import psycopg2, psycopg2.extras
#from psycopg2.extras import Json
#from psycopg2.extensions import parse_dsn, make_dsn
from psycopg.types.json import Jsonb
from psycopg.rows import dict_row

import psycopg

from psycopg import sql

from psycopg_pool import ConnectionPool

from . import io

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

def make_dsn(**kw): # dbname=None, user=None, password=None, host=None, port=None):
    components = []

    for key, value in kw.items():
        if value is not None:  # Only add components where the value is provided
            components.append(f"{key}={value}")

    return ' '.join(components)

    if dbname:
        components.append(f"dbname={dbname}")
    if user:
        components.append(f"user={user}")
    if password:
        components.append(f"password={password}")
    if host:
        components.append(f"host={host}")
    if port:
        components.append(f"port={port}")

    return ' '.join(components)

pool = None
def getpool(args, **kwargs):
  global pool

  kwargs = buildkwargs(args, **kwargs)
  dsn = make_dsn(**kwargs)
  if args.debug is True:
    io.echo(f"{dsn=}", level="debug")

  if pool is None:
    pool = ConnectionPool(dsn, min_size=10, max_size=100, timeout=5, open=True)
  if args.debug is True:
    io.echo(f"{pool=}", level="debug")
  return pool

def transaction(conn, **kwargs):
  return conn.transaction(**kwargs)

#databasehandles = {}
def connect(args, **kwargs):
  if args.debug is True:
    io.echo(f"bbsengine6.database.connect.100: {args=}", level="debug")

#  kwargs = buildkwargs(args)
#  dsn = make_dsn(**kwargs)
#  io.echo(f"{dsn=}", level="debug")

#  if args.debug is True:
#    io.echo(f"bbsengine6.database.connect.120: {kw=} {dsn=}", level="debug")

  if "readonly" in kwargs:
    del kwargs["readonly"]
  pool = getpool(args, **kwargs)
  if args.debug is True:
    io.echo(f"{pool=}", level="debug")

  conn = pool.connection()

  conn.autocommit = False

#  readonly = kwargs.get("readonly", False)
#  if readonly is True:
#    conn.set_isolation_level(psycopg.ISOLATION_LEVEL_READ_ONLY)

#  conn.row_factory = psycopg.rows.dict_row

  return conn

def buildkwargs(args, **kwargs):
    # Set default values from args if not already present in kwargs
    if "dbname" not in kwargs and "databasename" in args:
        kwargs["dbname"] = args.databasename
    if "host" not in kwargs and "databasehost" in args:
        kwargs["host"] = args.databasehost
    if "user" not in kwargs and "databaseuser" in args:
        kwargs["user"] = args.databaseuser
    if "password" not in kwargs and "databasepassword" in args:
        kwargs["password"] = args.databasepassword
    if "port" not in kwargs and "databaseport" in args:
        kwargs["port"] = args.databaseport

    return kwargs

def update(args, table:str, pk:str, items:dict, primarykey="id", mogrify:bool=False, updatepk:bool=False) -> int:
  if args.debug is True:
    io.echo(f"bbsengine6.database.update.100: {items=}")
  with connect(args, readonly=False) as conn:
    with cursor(conn) as cur:
      for k, v in items.items():
        if k == "datecreatedepoch":
          continue
#          del items[k]

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

#      if mogrify is True:
#        io.echo(f"{mogrifysql(cur, sql, dat)=}", level="debug")
      return cur.rowcount

def insert(args, table:str, items:dict, **kwargs): # returnid:bool=True, primarykey:str="id", mogrify:bool=True):
  primarykey = kwargs.get("primarykey", "id")
  returnid = kwargs.get("returnid", True)
  mogrify = kwargs.get("mogrify", True)

  io.echo(f"bbsengine6.database.insert.100: {items=}", level="debug")

  try:
    with connect(args) as conn:
      with cursor(conn) as cur:
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
#        if mogrify is True:
#          io.echo(f"bbsengine5.insert.160: {mogrify(cur, sql, dat)=}", level="debug")
        cur.execute(sql, dat)
        if returnid is True:
          res = cur.fetchone()
          if primarykey in res:
            return res[primarykey]
          else:
            return None
  except Exception as e:
      io.echo(f"bbsengine6.database.insert.180: database error: {e}", level="error")
      raise

# @see https://soft-builder.com/how-to-list-all-schemas-in-postgresql/
# @since 20230510
def classexists(conn, name, mogrify=False):
  sql = "select to_regclass(%s) as class" # does not work with schemas
  dat = (name,)
  with conn:
#  with connect(args) as conn:
    with cursor(conn) as cur:
      cur.execute(sql, dat)
      if mogrify is True:
        io.echo("bbsengine6.database.classexists.120: {mogrifysql(cur, sql, dat)=}", level="debug")
      if cur.rowcount == 0:
        return False

      res = cur.fetchone()

      if args.debug is True:
        io.echo(f"clasexists.100: {res=}", level="debug")

      return res["class"] is not None

def schemaexists(args, name, mogrify=False):
  sql = "SELECT 't' as exists FROM information_schema.schemata where schema_name=%s"
  dat = (name,)

  with connect(args) as conn:
    with cursor(conn) as cur:
      if mogrify is True:
        io.echo(f"bbsengine6.database.schemaexists.100: mogrify={mogrifysql(cur, sql, dat)=}", level="debug")
      cur.execute(sql, dat)
      res = cur.fetchone()
      return res["exists"] is not None

# @since 20230510 copied from bbsengine5.py
def buildargs(parentparser:object, defaults:dict={}, label="database options", suppress=False):
    databasename = defaults["databasename"] if "databasename" in defaults else "zoid6"
    databasehost = defaults["databasehost"] if "databasehost" in defaults else "localhost"
    databaseport = defaults["databaseport"] if "databaseport" in defaults else "5432"
    databaseuser = defaults["databaseuser"] if "databaseuser" in defaults else None
    databasepassword = defaults["databasepassword"] if "databasepassword" in defaults else None
    databaseschema = defaults["databaseschema"] if "databaseschema" in defaults else None
    
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
def resultiter(cursor, arraysize=1000, filterfunc=None, **kw:dict):
    'An iterator which accepts a psycopg2 cursor to keep memory usage down'
    while True:
        results = cursor.fetchmany(arraysize)
        if not results:
            break
        for result in results:
          if filterfunc is None:
            yield result
          elif callable(filterfunc) is True and filterfunc(result, **kw) is True:
            yield result

def commit(args):
  io.echo("bbsengine6.database.commit.100: stub", level="warn")
  return False

  with connect(args) as conn:
    conn.commit()

# @since 20230715 used by empyre
def rollback(args):
  with connect(args) as conn:
    return conn.rollback()

def rolexists(args, rolname, mogrify=False):
  sql = "SELECT rolname FROM pg_roles where rolname=%s"
  dat = (rolname,)
  try:
    with connect(args, dbname="template1") as conn:
      with cursor(conn) as cur:
        cur.execute(sql, dat)
        if mogrify is True:
          io.echo("bbsengine6.database.rolexists.100: {mogrifysql(cur, sql, dat)=}", level="debug")
        result = cur.fetchone()
        return result is not None
  except psycopg.DatabaseError as e:
    io.echo(f"bbsengine6.database.rolexists.120: database error {e}", level="error")
    raise
   
def exists(args, databasename, mogrify=False):
  sql = "SELECT datname FROM pg_catalog.pg_database WHERE lower(datname) = lower(%s)"
  dat = (databasename,)
  try:
    with connect(args, database="template1") as conn:
      with cursor(conn) as cur:
        cur.execute(sql, dat)
        if mogrify is True:
          io.echo(f"bbsengine6.database.exists.100: {mogrifysql(cur, sql, dat)=}", level="debug")
        return cur.fetchone() is not None
  except psycopg.DatabaseError as e:
    io.echo(f"bbsengine6.database.exists.120: database error {e}", level="error")
    raise

def create(args, name):
  sql = f"create database %s"
  dat = (name,)
  try:
    with connect(args) as conn:
      with cursor(conn) as cur:
        cur.execute(sql)
        return True
  except psycopg.DatabaseError as e:
    io.echo(f"bbsengine6.database.create.100: database error {e}", level="error")
    raise

# generated by chatgpt.com 2024-10-14
def createrol(args, role_name):
    try:
        # Use 'with' to ensure the connection is properly closed
        with connect(args) as conn:
            # Use 'with' to ensure the cursor is properly closed
            with cursor(conn) as cur:
                # Call the PL/pgSQL function to create the role
                cur.execute("SELECT engine.createrol(%s) as result", (role_name,))

                # Fetch the result (True/False) from the function
                result = cur.fetchone()["result"]

                # Commit the transaction
                conn.commit() # database.commit(args)
                return result is not None

    except psycopg.DatabaseError as e:
        io.echo(f"bbsengine6.createrol.100: Error creating role: {e}", level="error")
        raise

def createschema(args, name):
    # Connect to the database using args
    try:
      with connect(args) as conn:
        with cursor(conn) as cur:
          # Call the stored procedure
          cur.execute("SELECT createschema(%s)", (name,))
    except psycopg.DatabaseError as e:
      io.echo(f"bbsengine6.database.createschema.100: database error: {e}")
      raise

    return True

def get_role_privs(args, rolname: str) -> dict:
  sql = "SELECT get_role_privs(%s);"
  try:
    with connect(args) as conn:
      with cursor(conn) as cur:
        cur.execute(sql, (rolname,))
        result = cur.fetchone()

        # Extract the JSONB result from the tuple
        if result and result[0]:
          return result[0]  # Return the JSON object as a dictionary
        else:
          return {}  # Return empty dict if no result
  except psycopg.DatabaseError as e:
    io.echo(f"Error retrieving role privileges: {e}", level="error")
    raise

def manage_role_privs(args, role_name, action, priv):
  try:
    with connect(args) as conn:
      with cursor(conn) as cur:
        sql = "select engine.manage_role_privs(%s, %s, %s)"
        dat = (role_name, action, priv)
        return cur.execute(sql, dat)
  except psycopg.DatabaseError as e:
    io.echo(f"bbsengine6.database.manage_role_privs.100: database error {e}", level="error")
    raise

def manage_secondary_role(args, role_name, action, secondary):
  try:
    with connect(args) as conn:
      with cursor(conn) as cur:
        sql = "select engine.manage_secondary_role(%s, %s, %s)"
        dat = (role_name, action, secondary)
        return cur.execute(sql, dat)
  except psycopg.DatabaseError as e:
    io.echo(f"bbsengine6.database.manage_secondary_role.100: database error {e}", level="error")
    raise

def cursor(conn, row_factory=dict_row, **kwargs):
    """
    Creates a cursor using the provided connection and applies the desired row factory.
    Source: generated by chatgpt.com 2024-10-16
    """
    return conn.cursor(row_factory=row_factory, **kwargs)
