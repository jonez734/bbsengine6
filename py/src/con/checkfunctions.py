import psycopg
from bbsengine6 import io, database, util

from . import lib

def init(args, **kwargs) -> bool:
    return True

def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)

def access(args, op, **kwargs) -> bool:
    return True

def main(args, **kwargs):
  io.echo(f"con.checkfunctions.100: {kwargs=}", level="debug")
  stage = kwargs.pop("stage", 0)
  conn = kwargs.get("conn", None)
  def _work(conn):
    if stage == 0:
      funcs = ("public.get_role_privs", "public.manage_secondary_role", "public.manage_role_privs")
    else:
      funcs = ("engine.getflags",)
    io.echo(f"{stage=} {funcs=}", level="debug")
    for f in funcs:
      io.echo(f"{{var:labelcolor}}function {{var:valuecolor}}{f}{{var:labelcolor}}: {{var:valuecolor}}", end="")
      if database.functionexists(args, f, conn=conn) is False:
        io.echo("import ", end="")
        f = f.replace("engine.", "")
        f = f.replace("public.", "")
        if not f.endswith(".sql"):
          f += ".sql"
        if database.importsql(args, lib.SQLDIR, f, **kwargs) is False:
          io.echo("fail", level="error")
          conn.rollback()
        else:
          io.echo("ok", level="ok")
          conn.commit()
      else:
        io.echo("ok", level="ok")
    return True
  
  return _work(conn)
