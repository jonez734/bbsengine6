import time
import dateutil.tz

from datetime import datetime

from bbsengine6 import io, util, database, member

def init(args, **kwargs):
    return True

def access(args, op, **kwargs):
    return True

def buildargs(args, **kwargs):
    return None

def main(args, **kwargs):
    util.heading("system sessions summary")

    time.tzset()
    # tz = datetime.tzinfo("US/Pacific") # .tzname # ("US/Pacific")
    localtz = dateutil.tz.tzlocal()

    # conn = kwargs.get("conn", None)
    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo(f"bbsengine.con.session.main.100: {pool=}", level="error")
        return False

    try:
        with database.connect(args, **kwargs) as conn:
            with database.cursor(conn) as cur:
                sql = "select * from engine.session order by datecreated"
                cur.execute(sql)
                if cur.rowcount == 0:
                    io.echo("there are no sessions.")
                    return True

                for session in database.resultiter(cur):
                    io.echo(f"bbsengine.con.session.100: {session['moniker']=}", level="debug")
                    m = member.getbymoniker(args, session["moniker"], conn=conn, **kwargs)
                    io.echo(f"bbsengine.con.session.120: {m=}", level="debug")

#                    if m is None:
#                        continue
                    la = util.timedelta(datetime.now(tz=localtz) - session["lastactivity"])
                    ex = util.timedelta(session["expiry"] - datetime.now(tz=localtz))

                    io.echo(f"{{var:labelcolor}}Moniker:    {{var:valuecolor}}{session['moniker']}")
                    io.echo(f"{{var:labelcolor}}Created:    {{var:valuecolor}}{util.datestamp(session['datecreated'])}")
                    io.echo(f"{{var:labelcolor}}Expiry:     {{var:valuecolor}}{util.datestamp(session['expiry'])} {{var:labelcolor}}({{var:valuecolor}}{ex}{{var:labelcolor}})")
                    io.echo(f"{{var:labelcolor}}Actvity:    {{var:valuecolor}}{util.datestamp(session['lastactivity'])} {{var:labelcolor}}({{var:valuecolor}}{la}{{var:labelcolor}})")
                    io.echo(f"{{var:labelcolor}}User Agent: {{var:valuecolor}}{session['useragent']}")
    except Exception as e:
        io.echo(f"exception {e=}", level="error")

    io.echo("----")
