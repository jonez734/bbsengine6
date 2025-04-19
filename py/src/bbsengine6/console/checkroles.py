from bbsengine6 import database, io, util
from . import lib

def init(args, **kwargs):
    return True

def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)

def access(args, op, **kwargs):
    return True

def main(args, **kwargs):
  roles = ("web", "sysop", "term") # , "www-data")
  io.echo(f"con.checkroles.100: {kwargs=}", level="debug")
  for r in roles:
    io.echo(f"{{var:labelcolor}}role {{var:valuecolor}}{r!s}{{var:labelcolor}}: ", end="")
    if database.rolexists(args, r, **kwargs) is False:
      io.echo("create ", end="")
      if database.createrol(args, r, superuser=False, login=False, **kwargs) is False:
        io.echo("fail", level="error")
        return False
      else:
        io.echo("ok", level="ok")
    else:
      io.echo("ok", level="ok")

  io.echo(f"{{var:labelcolor}}role {{var:valuecolor}}www-data{{var:valuecolor}}: ", end="")
  if database.rolexists(args, "www-data", **kwargs) is False:
    io.echo(f"{{var:labelcolor}}create ")
    if database.createrol(args, "www-data", login=True) is False:
      io.echo(f"{{var:labelcolor}}error")
      return False
    else:
      io.echo(f"ok")
  else:
    io.echo("ok")
  
  io.echo(f"{{var:labelcolor}}granting {{var:valuecolor}}login{{var:labelcolor}} to role {{var:valuecolor}}www-data{{var:labelcolor}}: ", end="")
  if database.manage_role_privs(args, "www-data", "grant", "login", **kwargs) is False:
#    io.echo(f"{{var:labelcolor}}failed")
    return False
  else:
    io.echo("ok")
    return True
