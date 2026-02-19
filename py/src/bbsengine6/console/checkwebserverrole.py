from bbsengine6 import database, io

def init(args, **kwargs):
    return True

def buildargs(args, **kwargs):
    return None

def access(args, op, **kwargs):
    return True

def main(args, **kwargs):
  io.echo(f"{{var:labelcolor}}role {{var:valuecolor}}www-data{{var:valuecolor}}: ", end="")
  if database.rolexists(args, "www-data", **kwargs) is False:
    io.echo(f"{{var:labelcolor}}create ")
    if database.createrol(args, "www-data", login=True, **kwargs) is False:
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
