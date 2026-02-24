"""
Verify and initialize database schema.

Creates and validates the database schema including all necessary tables,
indexes, and constraints required for BBS engine operations.
"""

from bbsengine6 import io, database

from . import lib

def init(args, **kwargs) -> bool:
    return True

def buildargs(args, **kwargs):
    return None

def access(args, op, **kwargs) -> bool:
    return True

def main(args, **kwargs):
    io.echo(f"{{var:labelcolor}}schema {{var:valuecolor}}engine{{var:labelcolor}}: ", end="")
    conn = kwargs.get("conn", None)
    if database.schemaexists(args, "engine", conn=conn) is False:
      io.echo("import ", end="")
      res = database.importsql(args, "schema.sql", conn=conn)
      if res is False:
          io.echo("fail", level="error")
          return False
      elif res is True:
        io.echo(" ok ", level="ok")
        return True
    else:
      io.echo(" ok ", level="ok")

    failcount = 0
    io.echo(f"{{var:labelcolor}}schema {{var:valuecolor}}engine {{var:labelcolor}}privs: ", end="")
    for r in ("web", "term", "sysop"):
      if database.manage_schema_priv(args, "grant", "usage", "engine", r, **kwargs) is False:
        io.echo(f"fail", level="error")
        failcount += 1
      else:
        io.echo(f" ok ", level="ok")

    if failcount == 0:
      conn.commit()
      return True
    else:
      conn.rollback()
      return False
