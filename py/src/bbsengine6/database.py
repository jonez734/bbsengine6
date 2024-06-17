import copy

import argparse

import psycopg2, psycopg2.extras
from psycopg2.extras import Json
from psycopg2.extensions import parse_dsn, make_dsn

from . import io

#import ttyio6 as ttyio

databasehandles = {}
def connect(args, **kw):
  if args.debug is True:
    io.echo(f"bbsengine6.database.connect.100: {args=}", level="debug")

  if "databasename" in args:
#    ttyio.echo(f"buildkw.140: setting database to {args.databasename!r}", level="debug")
    kw["database"] = args.databasename
#    ttyio.echo("bbsengine6.database.buildkw.100: kw=%r" % (kw), level="debug", interpret=False)
  if "databasehost" in args:
    kw["host"] = args.databasehost
  if "databaseuser" in args:
    kw["user"] = args.databaseuser
  if "databasepassword" in args:
    kw["password"] = args.databasepassword
  if "databaseport" in args:
    kw["port"] = args.databaseport

#  res = buildkw(args)
#  ttyio.echo(f"bbsengine6.database.connect.140: res={res!r}", level="debug")

  dsn = make_dsn(**kw)

  if args.debug is True:
    io.echo(f"bbsengine6.database.connect.120: {kw=} {dsn=}", level="debug")

  if dsn in databasehandles:
    dbh = databasehandles[dsn]
    if dbh.closed == 0:
      return databasehandles[dsn]
#    else:
#      ttyio.echo("dbh handle closed")

  dbh = psycopg2.connect(connection_factory=psycopg2.extras.DictConnection, cursor_factory=psycopg2.extras.RealDictCursor, **kw)
  databasehandles[dsn] = dbh
  return dbh

def buildkw(args, **kwargs):
  kw = {}
#  ttyio.echo(f"bbsengine6.database.buildkw.120: args={args!r}", level="debug")
  if "databasename" in args:
#    ttyio.echo(f"buildkw.140: setting database to {args.databasename!r}", level="debug")
    kw["database"] = args.databasename
#    ttyio.echo("bbsengine6.database.buildkw.100: kw=%r" % (kw), level="debug", interpret=False)
  if "databasehost" in args:
    kw["host"] = args.databasehost
  if "databaseuser" in args:
    kw["user"] = args.databaseuser
  if "databasepassword" in args:
    kw["password"] = args.databasepassword
  if "databaseport" in args:
    kw["port"] = args.databaseport
  
  return kw

def update(args, table:str, pk:str, items:dict, primarykey="id", mogrify:bool=False, updatepk:bool=False) -> int:
  if args.debug is True:
    io.echo(f"bbsengine6.database.update.100: {items=}")
  dbh = connect(args)
  for k, v in items.items():
    if type(items[k]) is dict:
      items[k] = Json(items[k])
    if k == "datecreatedepoch":
      del items[k]

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

  cur = dbh.cursor()
  cur.execute(sql, dat)

  if mogrify is True:
    io.echo(f"{cur.mogrify(sql, dat)=}", level="debug")

  cur.close()
  return cur.rowcount

def insert(args, table:str, items:dict, returnid:bool=True, primarykey:str="id", mogrify:bool=False):
  dbh = connect(args)

  columns = items.keys()
#  if "" in columns:
#    del items[""]

  for k, v in items.items():
    if type(items[k]) is dict:
      items[k] = Json(items[k])
    if k == "datecreatedepoch":
      del items[k]

  if args.debug is True:
    io.echo(f"bbsengine6.database.insert.100: {columns=}", level="debug")
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
#    if type(items[k]) is dict:
#      items[k] = Json(items[k])

    dat.append(v)
  if returnid is True:
    sql += f" returning {table}.{primarykey}"
  # ttyio.echo("bbsengine.insert.100: sql=%s dat=%s" % (sql, dat), level="debug")
  cur = dbh.cursor()

  if mogrify is True:
    io.echo("bbsengine5.insert.100: %r" % (repr(cur.mogrify(sql, dat))), level="debug")
#    ttyio.echo(cur.mogrify(sql, [tuple(v.values() for v in dat)]), level="debug")
  cur.execute(sql, dat)
  if returnid is True:
    res = cur.fetchone()
    if primarykey in res:
      return res[primarykey]
  cur.close()
  return None

# @see https://soft-builder.com/how-to-list-all-schemas-in-postgresql/
# @since 20230510
def classexists(args, name, mogrify=False):
  sql = "select to_regclass(%s) as class" # does not work with schemas
  dat = (name,)
  dbh = connect(args)
  cur = dbh.cursor()
  cur.execute(sql, dat)
  if mogrify is True:
    io.echo("bbsengine6.database.classexists.120: {cur.mogrify(sql, dat)=}", level="debug")
  if cur.rowcount == 0:
    return False

  res = cur.fetchone()

  if args.debug is True:
    io.echo(f"clasexists.100: {res=}", level="debug")

  if res["class"] is None:
    return False
  return True

def schemaexists(args, name, mogrify=False):
  dbh = connect(args)
  sql = "SELECT 't' as exists FROM information_schema.schemata where schema_name=%s"
  dat = (name,)
  cur = dbh.cursor()
  cur.execute(sql, dat)
  if mogrify is True:
    io.echo(f"bbsengine6.database.schemaexists.100: mogrify={cur.mogrify(sql, dat)=}", level="debug")
  if cur.rowcount == 0:
    return False
  return True

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
  dbh = connect(args)
  return dbh.commit()

# @since 20230715 used by empyre
def rollback(args):
  dbh = connect(args)
  return dbh.rollback()

def rolexists(args, rolname, mogrify=False):
  sql = "SELECT rolname FROM pg_roles where rolname=%s"
  dat = (rolname,)
  dbh = connect(args, database="template1")
  cur = dbh.cursor()
  cur.execute(sql, dat)
  if mogrify is True:
    io.echo("bbsengine6.database.rolexists.100: mogrify={cur.mogrify(sql, dat)=}", level="debug")
  if cur.rowcount == 0:
    return False
  return True
   
def exists(args, databasename, mogrify=False):
  sql = "SELECT datname FROM pg_catalog.pg_database WHERE lower(datname) = lower(%s)"
  dat = (databasename,)
  dbh = connect(args, database="template1")
  cur = dbh.cursor()
  cur.execute(sql, dat)
  if mogrify is True:
    io.echo(f"bbsengine6.database.exists.100: mogrify={cur.mogrify(sql, dat)=}", level="debug")
  if cur.rowcount == 0:
    return False
  return True

def close(args, **kw):
  dsn = make_dsn(**buildkw(args, **kw))
  if dsn in databasehandles:
    dbh = databasehandles[dsn]
    dbh.close()
    del databasehandles[dsn]
    return True
  return False

# @since 20240328 copied from bbsengine5 for votingbooth
def postgres_to_python_list(arr:str) -> list:
  arr = arr.strip("}")
  arr = arr.strip("{")
  arr = arr.split(",")
  lst = [a.strip() for a in arr]
  return lst

def create(args, name):
  sql = f"create database {name}"
  # dat = (name,)
  dbh = connect(args)
  cur = dbh.cursor()
  cur.execute(sql)
  return True

def createrol(args, name):
  sql = f"create role {name}"
  # dat = (name,)
  dbh = connect(args)
  cur = dbh.cursor()
  cur.execute(sql)
  return True

def createschema(args, name):
  sql = f"create schema {name}"
  # dat = (name,)
  dbh = connect(args)
  cur = dbh.cursor()
  cur.execute(sql)
  return True
