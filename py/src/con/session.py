import bbsengine6 as bbsengine
import ttyio6 as ttyio

def init(args, **kw):
    return True

def access(args, op, **kw):
    return True

def buildargs(args, **kw):
    return None

def main(args, **kw):
    bbsengine.util.heading("system sessions summary")

    dbh = bbsengine.database.connect(args)
    sql = "select * from engine.session order by datecreated"
    cur = dbh.cursor()
    cur.execute(sql)
    if cur.rowcount == 0:
        ttyio.echo("no sessions exist")
        return True

    for session in bbsengine.database.resultiter(cur):
        ttyio.echo(repr(session), level="debug")

    ttyio.echo("----")
