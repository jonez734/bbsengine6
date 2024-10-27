from bbsengine6 import util, member, database, io

def init(args, **kw:dict) -> bool:
    return True

def access(args, op:str, **kw:dict) -> bool:
    return member.checkflag(args, "SYSOP", member.getcurrentid(args))

def buildargs(args, **kw:dict):
#    return lib.buildargs(args, **kw)
    return None

def main(args, **kw):
    util.heading("member approval")
    sql = "select id, moniker from engine.member where approvedbyid is null"
    dat = ()
    with database.connect(args) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                io.echo("no members waiting for approval")
                return True

            res = cur.fetchmany()
            for rec in res:
                memberid = rec["id"]
                m = member.getbymoniker(args, rec["moniker"])

                io.echo(f"{m=}")
                io.echo(f"{{labelcolor}}Moniker: {{valuecolor}}{m['moniker']} {{labelcolor}}({{valuecolor}}{m['loginid']}{{labelcolor}})")
                io.echo(f"{{labelcolor}}E-Mail:  {{valuecolor}}{m['email']} {{labelcolor}}", end="")
                if m["emailverified"] is True:
                    io.echo(" (verified by {{valuecolor}}{m['verifiedbyid']}{{labelcolor}} on {{valuecolor}}{util.datestamp(m['dateverified'])})")
                else:
                    io.echo(" (not verified)")
                util.hr()
                if io.inputboolean("{var:promptcolor}approve this member? {var:optioncolor}[Yn]{var:promptcolor}: {var:inputcolor}", "Y") is True:
                    m["approvedbyid"] = member.getcurrentmoniker(args)
                    m["dateapproved"] = "now()"
                    member.update(args, m, memberid)
    return True
