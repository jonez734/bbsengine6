"""Display active system sessions.

Shows information about currently active user sessions, including
login times, idle times, and IP addresses.
"""

import time
import dateutil.tz

from datetime import datetime

from bbsengine6 import io, util, database


def init(args, **kwargs):
    return True


def access(args, op, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def main(args, **kwargs):
    util.heading("system sessions summary")

    time.tzset()
    localtz = dateutil.tz.tzlocal()

    if "pool" not in kwargs or kwargs["pool"] is None:
        io.echo(
            "bbsengine.con.session.main.100: pool missing from kwargs",
            level="error",
        )
        return False

    try:
        with database.connect(args, **kwargs) as conn:
            with database.cursor(conn) as cur:
                sql = "select * from engine.session order by datecreated"
                cur.execute(sql)
                if cur.rowcount == 0:
                    io.echo("there are no sessions.")
                    return True

                for sess in database.resultiter(cur):
                    io.echo(
                        f"bbsengine.con.session.100: {sess['moniker']=}",
                        level="debug",
                    )
                    la = util.timedeltastr(
                        datetime.now(tz=localtz) - sess["lastactivity"]
                    )
                    ex = util.timedeltastr(sess["expiry"] - datetime.now(tz=localtz))

                    io.echo(
                        f"{{var:labelcolor}}Moniker:    {{var:valuecolor}}{sess['moniker']}"
                    )
                    io.echo(
                        f"{{var:labelcolor}}Created:    {{var:valuecolor}}{util.datestamp(sess['datecreated'])}"
                    )
                    io.echo(
                        f"{{var:labelcolor}}Expiry:     {{var:valuecolor}}{util.datestamp(sess['expiry'])} {{var:labelcolor}}({{var:valuecolor}}{ex}{{var:labelcolor}})"
                    )
                    io.echo(
                        f"{{var:labelcolor}}Actvity:    {{var:valuecolor}}{util.datestamp(sess['lastactivity'])} {{var:labelcolor}}({{var:valuecolor}}{la}{{var:labelcolor}})"
                    )
                    io.echo(
                        f"{{var:labelcolor}}User Agent: {{var:valuecolor}}{sess['useragent']}"
                    )
    except Exception as e:
        io.echo_traceback(f"bbsengine6.console.session.main: {e}")

    io.echo("----")
    return True
