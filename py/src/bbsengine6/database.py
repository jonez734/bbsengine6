import copy

import psycopg2, psycopg2.extras
from psycopg2.extras import Json
from psycopg2.extensions import parse_dsn, make_dsn

import ttyio6 as ttyio

databasehandles = {}
def connect(args):
  ttyio.echo(f"bbsengine6.database.connect.100: args={args!r}", level="debug")
  kw = {}
  if "databasename" in args:
    kw["database"] = args.databasename
  if "databasehost" in args:
    kw["host"] = args.databasehost
  if "databaseuser" in args:
    kw["user"] = args.databaseuser
  if "databasepassword" in args:
    kw["password"] = args.databasepassword
  if "databaseport" in args:
    kw["port"] = args.databaseport

  dsn = make_dsn(**kw)

  ttyio.echo(f"bbsengine6.database.connect.120: kw={kw!r} dsn={dsn!r}", level="debug")

  if dsn in databasehandles:
    dbh = databasehandles[dsn]
    if dbh.closed == 0:
      return databasehandles[dsn]
#    else:
#      ttyio.echo("dbh handle closed")

  dbh = psycopg2.connect(connection_factory=psycopg2.extras.DictConnection, cursor_factory=psycopg2.extras.RealDictCursor, **kw)
  databasehandles[dsn] = dbh
  return dbh

def update(args, table, key, items:dict, primarykey="id", mogrify=False) -> int:
  dbh = connect(args)
  for k, v in items.items():
    if type(items[k]) == dict:
      items[k] = json.dumps(items[k])
    if k == "datecreatedepoch":
      del items[k]

  i = copy.deepcopy(items)
  if primarykey in i:
    del i[primarykey]

  sql = "update %s set " % (table)
  params = []
  dat = []
  for k, v in i.items():
    params.append("%s=%%s" % (k),)
    dat.append(v)

  sql += ", ".join(params)
  sql += " where %s=%%s" % (primarykey)
  dat.append(key)

  cur = dbh.cursor()
  cur.execute(sql, dat)

  if mogrify is True:
    ttyio.echo(cur.mogrify(sql, dat), level="debug")

  cur.close()
  return cur.rowcount

def insert(args, table:str, dict, returnid:bool=True, primarykey:str="id", mogrify:bool=False):
  dbh = connect(args)

  columns = dict.keys()
  sql = "insert into %s(" % (table)
  sql += ", ".join(columns)
  sql += ") values ("
  params = []
  for x in range(len(columns)):
    params.append("%s")
  sql += ", ".join(params)
  sql += ")"

  dat = []
  for v in dict.values():
    dat.append(v)
  if returnid is True:
    sql += " returning %s.%s" % (table, primarykey)
  # ttyio.echo("bbsengine.insert.100: sql=%s dat=%s" % (sql, dat), level="debug")
  cur = dbh.cursor()

#  if mogrify is True:
#    ttyio.echo("bbsengine5.insert.100: %r" % (cur.mogrify(sql, dat)), level="debug")
#      ttyio.echo(cur.mogrify(sql, [tuple(v.values() for v in dat)]), level="debug")
  cur.execute(sql, dat)
  if returnid is True:
    res = cur.fetchone()
    if primarykey in res:
      return res[primarykey]
  cur.close()
  return None

# @see https://soft-builder.com/how-to-list-all-schemas-in-postgresql/
# @since 20230510
def classexists(args, thing):
  dbh = connect(args)
  sql = "SELECT 't' as exists FROM information_schema.schemata where schema_name=%s"
  dat = (thing,)
  cur = dbh.cursor()
  cur.execute(sql, dat)
  if cur.rowcount == 1:
    res = cur.fetchone()
#    ttyio.echo(f"thing.120: res={res!r}")
    if res["exists"] is True:
      return True

  sql = "select to_regclass(%s) as class" # does not work with schemas
  dat = (thing,)
  cur = dbh.cursor()
  cur.execute(sql, dat)
  res = cur.fetchone()
#  ttyio.echo(f"thing.100: res={res!r}")
  if res["class"] is None:
    return False
  return True

# @since 20230510 copied from bbsengine5.py
def buildargdatabasegroup(parentparser:object, defaults:dict={}, label="database options"):
    databasename = defaults["databasename"] if "databasename" in defaults else "zoid6"
    databasehost = defaults["databasehost"] if "databasehost" in defaults else "localhost"
    databaseport = defaults["databaseport"] if "databaseport" in defaults else "5432"
    databaseuser = defaults["databaseuser"] if "databaseuser" in defaults else None
    databasepassword = defaults["databasepassword"] if "databasepassword" in defaults else None
    
    group = parentparser.add_argument_group(label)
#    group = argparse.ArgumentParser("database", parents=[parentparser], add_help=False)
    group.add_argument("--databasename", dest="databasename", action="store", default=databasename, type=str, help="database name (default: %(default)r)")
    group.add_argument("--databasehost", dest="databasehost", action="store", default=databasehost, type=str, help="database host (default: %(default)r)")
    group.add_argument("--databaseport", dest="databaseport", action="store", default=databaseport, type=int, help="database port (default: %(default)r)")
    group.add_argument("--databaseuser", dest="databaseuser", action="store", default=databaseuser, type=str, help="database user (default: %(default)r)")
    group.add_argument("--databasepassword", dest="databasepassword", action="store", default=databasepassword, type=str, help="database password (default: %(default)r)")
    return

# @since 20230510 copied from bbsengine5
def check(args, module, op="run", buildargs=False, **kw):
  if args.debug is True:
    ttyio.echo(f"bbsengine6.module.check.120: module={module!r}", level="debug")

  try:
    m = importlib.import_module(module)
  except Exception as e:
    if args.debug is True:
      ttyio.echo(repr(e), level="error")
    return False

  if args.debug is True:
    ttyio.echo("bbsengine6.module.check.100: m=%r" % (m), level="debug")

  # required
  if (hasattr(m, "init") and callable(m.init)) is False:
    if args.debug is True:
      ttyio.echo("no init function", level="warn")
    return False

  # optional
  if hasattr(m, "access") is False:
    if args.debug is True:
      ttyio.echo("no access function, returning True anyway")
    return True
  if (hasattr(m, "access") and callable(m.access)) is False:
    if args.debug is True:
      ttyio.echo("no callable access function", level="debug")
    return False

  if m.access(args, op) is True:
    if args.debug is True:
      ttyio.echo("access check passed", level="debug")
  else:
    ttyio.echo("access check failed", level="error")
    return False

  if (hasattr(m, "buildargs") and callable(m.buildargs)) is False:
    if args.debug is True:
      ttyio.echo("no callable buildargs function", level="debug")
    if buildargs is True:
      return False

  # required
  if (hasattr(m, "main") and callable(m.main)) is False:
    ttyio.echo("no main function", level="error")
    return False

  return True

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
