from bbsengine6 import io, database, util

from . import lib

def init(args, **kwargs):
    return True

def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)

def access(args, op, **kwargs):
    return True

def main(args, **kwargs):
    util.heading("checking for database superuser")
    currentloginid = util.getcurrentloginid(args)
    privs = database.get_role_privs(args, currentloginid)
    io.echo(f"{privs=}", level="debug")
    if privs["rolsuper"] is True:
        io.echo(f"{{var:valuecolor}}{currentloginid}{{var:labelcolor}} has correct privs (superuser)")
        return True
    else:
        if privs["rolcreatedb"] is True and privs["rolcanlogin"] is True and privs["rolcreaterole"] is True:
            io.echo(f"{{var:valuecolor}}{currentloginid}{{var:labelcolor}} has correct privs (createdb, canlogin, createrole)")
            return True
    return False
