import psycopg
from bbsengine6 import io, database, util

from . import lib

def init(*args, **kwargs):
    return True

def buildargs(*args, **kwargs):
    return lib.buildargs(*args, **kwargs)

def access(args, op, **kwargs):
    return True

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
        with database.connect(args) as conn:
            with database.cursor(conn) as cur:
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
        with database.connect(args) as conn:
            with database.cursor(conn) as cur:
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
        with database.connect(args) as conn:
            with database.cursor(conn) as cur:
                return _work(cur)
    else:
        return _work(cur)

def main(args, **kwargs):
    util.heading("checking for required database extensions")
    # SELECT * FROM pg_available_extensions WHERE name = 'citext';
    # SELECT * FROM pg_extension WHERE extname = 'citext';
    # CREATE EXTENSION IF NOT EXISTS citext;
    with database.connect(args) as conn:
        with database.cursor(conn) as cur:
            for ext in ("pgcrypto", "ltree", "citext"):
                if extensionavailable(args, ext, cur=cur) is True:
                    if extensioninstalled(args, ext, cur=cur) is False:
                        if creatextension(args, ext, cur=cur) is False:
                            io.echo(f"{{var:labelcolor}}unable to create extension {{var:valuecolor}}{ext}{{var:labelcolor}}")
                        else:
                            io.echo(f"{{var:labelcolor}}installed extension {{var:valuecolor}}{ext}{{var:labelcolor}}")
                    else:
                        io.echo(f"{{var:labelcolor}}extension {{var:valuecolor}}{ext}{{var:labelcolor}} has already been installed")
                else:
                    io.echo(f"{{var:labelcolor}}extension {{var:valuecolor}}{ext}{{var:labelcolor}} is not available")
