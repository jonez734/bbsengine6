"""
Verify and initialize system flags.

Validates that all required system flags and configuration flags exist
in the database with correct default values.
"""

from bbsengine6 import io, database

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs) -> bool:
    return True


def main(args, **kwargs):
    failcount = 0
    conn = kwargs.get("conn", None)
    pool = kwargs.get("pool", None)
    io.echo(f"{{var:labelcolor}}class {{var:valuecolor}}engine.member_flag: ", end="")
    if database.classexists(args, "engine.member_flag", conn=conn) is False:
        io.echo("import ", end="")
        if database.importsql(args, "member_flag.sql", conn=conn, pool=pool) is False:
            failcount += 1
            io.echo(" fail ", level="error")
            return False
        else:
            io.echo(" ok ", level="ok")
    else:
        io.echo(" ok ", level="ok")

    io.echo(
        f"{{var:labelcolor}}class {{var:valuecolor}}engine.map_member_flag: ", end=""
    )
    if database.classexists(args, "engine.map_member_flag", conn=conn) is False:
        io.echo("import ", end="")
        if database.importsql(args, "map_member_flag.sql", conn=conn, pool=pool) is False:
            io.echo(" fail ", level="error")
            failcount += 1
        else:
            io.echo(" ok ", level="ok")
    else:
        io.echo(" ok ", level="ok")

    io.echo(f"{{var:labelcolor}}flagdata: ", end="")
    sql = "select count(name) from engine.member_flag"
    with database.cursor(conn=conn) as cur:
        cur.execute(sql)
        if cur.rowcount == 0:
            io.echo("fail")
            failcount += 1
        elif cur.rowcount == 1:
            count = cur.fetchone()["count"]
            if count == 0:
                io.echo("import ", end="")
                if database.importsql(args, "flagdata.sql", conn=conn, pool=pool) is False:
                    failcount += 1
                    io.echo("fail", level="error")
                else:
                    io.echo(" ok ", level="ok")
            else:
                io.echo(" ok ", level="ok")

    return True if failcount == 0 else False
