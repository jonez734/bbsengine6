import json
import copy
import argparse

from bbsengine6 import io, database, util
from bbsengine6 import member as libmember

from . import lib


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs):
    return True


def editflags(args, moniker=None, **kwargs):
    """Edits flags for a member.

    Args:
        args: An argparse.ArgumentParser object.
        moniker (optional): The unique identifier of the member.
            If None, returns the flags with default values.
    """

    conn = kwargs.get("conn", None)
    mode = kwargs.get("mode", "add")
    if mode == "add":
        flags = libmember.getflags(args, None, conn=conn)
    else:
        flags = libmember.getflags(args, moniker, conn=conn)
    io.echo(f"bbsengine.con.member.100: {flags=}", level="debug")
    updated_flags = {
        flag_name: {"value": flag_data["value"]}
        for flag_name, flag_data in flags.items()
    }

    for flag_name, flag_data in flags.items():
        description = flag_data["description"]
        current_value = flag_data["value"]
        #        default_value = "Y" if util.tobool(current_value) else "N"
        io.echo(f"{current_value=}", level="debug")
        prompt = f"{{var:promptcolor}}{description} "
        if current_value is True:
            prompt += (
                f"[{{var:currentoptioncolor}}Y{{var:optioncolor}}n{{var:promptcolor}}]"
            )
        else:
            prompt += (
                f"[{{var:optioncolor}}y{{var:currentoptioncolor}}N{{var:promptcolor}}]"
            )
        prompt += f"{{promptcolor}}: {{var:inputcolor}}"
        default = "Y" if current_value is True else "N"
        new_value = io.inputboolean(prompt, default=default)
        io.echo("{/all}", end="")
        if new_value != current_value:
            # TODO: Implement logic to update the flag in the database
            io.echo(
                f"{{var:labelcolor}}Updating flag '{{var:valuecolor}}{flag_name}{{var:labelcolor}}' to {{var:valuecolor}}{new_value}{{/all}}"
            )
            updated_flags[flag_name] = {"value": new_value}
    return updated_flags


def showui(args, ui, _ui):
    io.echo(f"{ui=} {_ui=}", level="debug")
    if ui is None or len(ui) == 0:
        io.echo(f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: None", end="")
        if _ui is not None:
            _ui.sort()
            io.echo(f" (was: {', '.join(_ui)})")
        else:
            io.echo()
        return

    if ui is not None:
        ui.sort()
    if _ui is not None:
        _ui.sort()

    if ui != _ui:
        if _ui is None:
            io.echo(
                f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: {', '.join(ui)} (was: None)"
            )
        else:
            io.echo(
                f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: {', '.join(ui)} (was: {', '.join(_ui)})"
            )
    else:
        io.echo(f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: {', '.join(ui)}")
    return


def help(args, **kwargs):
    member = kwargs.get("member", {})
    _member = kwargs.get("_member", {})
    conn = kwargs.get("conn", None)

    def _format_flags(flags):
        """
        Formats the flag names based on their values.
        If the value is True, the name is wrapped with '**'.
        If the value is False, the name is returned as is.

        Args:
            flags (dict): A dictionary of flags with 'description' and 'value' keys.

        Returns:
            str: A formatted string of flag names.
        """
        formatted_flags = []
        for name, flag in flags.items():
            if flag["value"]:
                formatted_flags.append(f":checkmark: {name}")
            else:
                formatted_flags.append(f":crossmark: {name}")
        return " ".join(formatted_flags)

    if member["moniker"] is None:
        io.echo(f"{{red}} *{{var:optioncolor}}[M]{{var:labelcolor}} Moniker")
    elif member["moniker"] != _member["moniker"]:
        io.echo(
            f"{{red}} *{{var:optioncolor}}[M]{{var:labelcolor}} Moniker: {{var:valuecolor}}{member['moniker']} {{var:labelcolor}}(was: {{var:valuecolor}}{_member['moniker']}{{var:labelcolor}})"
        )
    else:
        io.echo(
            f"{{red}} *{{var:optioncolor}}[M]{{var:labelcolor}} Moniker: {{var:valuecolor}}{member['moniker']}"
        )

    if member["loginid"] is None:
        io.echo(f"{{red}} *{{var:optioncolor}}[L]{{var:labelcolor}} Loginid{{/all}}")
    elif member["loginid"] != _member["loginid"]:
        io.echo(
            f"{{red}} *{{var:optioncolor}}[L]{{var:labelcolor}} Loginid: {{var:valuecolor}}{member['loginid']} {{var:labelcolor}}(was: {{var:labelcolor}}{_member['loginid']}{{var:labelcolor}})"
        )
    else:
        io.echo(
            f"{{red}} *{{var:optioncolor}}[L]{{var:labelcolor}} Loginid: {{var:valuecolor}}{member['loginid']}"
        )

    if member["email"] is None:
        io.echo(f"{{red}} *{{var:optioncolor}}[E]{{var:labelcolor}} Email")
    elif member["email"] != _member["email"]:
        io.echo(
            f"{{red}} *{{var:optioncolor}}[E]{{var:labelcolor}} Email: {{var:valuecolor}}{member['email']} {{var:labelcolor}}(was: {{var:valuecolor}}{_member['email']})"
        )
    else:
        io.echo(
            f"{{red}} *{{var:optioncolor}}[E]{{var:labelcolor}} Email: {member['email']}"
        )

    if member["password"] is None:
        io.echo("  {var:optioncolor}[P]{var:labelcolor} Password{/all}")

    if member["credits"] is None:
        io.echo(f"  {{var:optioncolor}}[C]{{var:labelcolor}} Credits")
    elif member["credits"] != _member["credits"]:
        io.echo(
            f"  {{var:optioncolor}}[C]{{var:labelcolor}} Credits: {{var:valuecolor}}{member['credits']} (was: {_member['credits']})"
        )
    else:
        io.echo(
            f"  {{var:optioncolor}}[C]{{var:labelcolor}} Credits: {{var:valuecolor}}{member['credits']}"
        )

    ui = member["ui"]
    _ui = _member["ui"]
    io.echo(f"{ui=} {_ui=}", level="debug")
    if ui is None or len(ui) == 0:
        io.echo(f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: None", end="")
        if _ui is not None:
            _ui.sort()
            io.echo(f" (was: {', '.join(_ui)})")
        else:
            io.echo()

    if ui is not None:
        ui.sort()
    if _ui is not None:
        _ui.sort()

    if ui != _ui:
        if _ui is None:
            io.echo(
                f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: {', '.join(ui)} (was: None)"
            )
        else:
            io.echo(
                f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: {', '.join(ui)} (was: {', '.join(_ui)})"
            )
    else:
        io.echo(f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: {', '.join(ui)}")

    flags = member["flags"] or {}
    # io.echo(f"bbsengine.con.member.help.100: {flags=} {member['flags']=}", level="debug")
    # set_flags = [flag for flag, data in flags.items() if data["value"] is True]
    set_flags = _format_flags(flags)
    if len(set_flags) > 0:
        io.echo(
            f"  {{var:optioncolor}}[F]{{var:labelcolor}} Flags:{{var:valuecolor}} {set_flags}"
        )
    else:
        io.echo(f"  {{var:optioncolor}}[F]{{var:labelcolor}} Flags{{var:valuecolor}}")

    if "refcode" not in member:
        member["refcode"] = None
    if "refcode" not in _member:
        _member["refcode"] = None

    if member["refcode"] is None:
        io.echo(f"  {{var:optioncolor}}[R]{{var:labelcolor}} Refcode", end="")
        if _member["refcode"] is not None:
            io.echo(
                f"  {{var:labelcolor}} (was: {{var:valuecolor}}{_member['refcode']}{{var:labelcolor}})"
            )
        else:
            io.echo()
    elif member["refcode"] != _member["refcode"]:
        io.echo(
            f"  {{var:optioncolor}}[R]{{var:labelcolor}} Refcode: {member['refcode']} {{var:labelcolor}}(was: {{var:valuecolor}}{_member['refcode']}{{var:labelcolor}})"
        )
    else:
        io.echo(
            f"  {{var:optioncolor}}[R]{{var:labelcolor}} Refcode: {member['refcode']}"
        )


def _edit(args, mode, member, **kwargs):
    #  cur = kwargs.get("cur", None)
    _member = copy.deepcopy(member)
    io.echo(f"con.member._edit.100: {kwargs=}", level="debug")

    util.heading(f"{mode} member")
    conn = kwargs.get("conn", None)
    done = False
    while not done:
        help(args, member=member, _member=_member)
        #    flags = member["flags"]
        ch = io.inputchoice(
            f"{{var:promptcolor}}{mode} member {{var:optioncolor}}[MECPFURQ]{{var:promptcolor}}: {{var:inputcolor}}",
            "LMECPFURQ",
            "",
            help=help,
            member=member,
            _member=_member,
        )
        if ch == "M":
            io.echo("Moniker")
            _moniker = member["moniker"]
            moniker = io.inputstring(
                "moniker:", _moniker, args=args
            )  # verify=bbsengine.member.verifyMemberFound, args=args)
            if _moniker != moniker:
                if (
                    libmember.verifyMemberFound(
                        args, moniker, column="moniker", **kwargs
                    )
                    is True
                ):
                    io.echo(f"{moniker} is already in use.", level="error")
                else:
                    member["moniker"] = moniker
        elif ch == "F":
            io.echo("Flags")
            member["flags"] = editflags(args, member["moniker"], conn=conn, mode=mode)
        elif ch == "L":
            io.echo("Loginid")
            member["loginid"] = io.inputstring(
                "{var:promptcolor}loginid: {var:inputcolor}",
                member["loginid"],
                args=args,
            )
        elif ch == "C":
            io.echo("Credits")
            member["credits"] = io.inputinteger(
                "{var:promptcolor}credits: {var:inputcolor}",
                member["credits"],
                args=args,
            )
        elif ch == "U":
            io.echo("User Interface")
            member["ui"] = editui(
                args, member["loginid"]
            )  # io.inputstring("{var:promptcolor}ui: {var:inputcolor}", member["ui"], args=args, multiple=True)
        elif ch == "P":
            io.echo("Password")
            member["password"] = util.inputpassword("Password: ")
        elif ch == "E":
            io.echo("E-mail address")
            member["email"] = io.inputstring(
                "{var:promptcolor}e-mail address: {var:inputcolor}"
            )
            if member["email"] != _member["email"]:
                io.echo("FIXME: set emailverified flag to false", level="info")
        #        member["emailverified"] = False
        #        member["emailverifiedbymoniker"] = None
        #        member["dateemailverified"] = None
        elif ch == "A":
            io.echo("Alerts")
            alerts(args)
        elif ch == "R":
            io.echo("Refcode")
            refcode = io.inputstring(
                "{var:promptcolor}refcode: {var:inputcolor}", member["refcode"]
            )
            if refcode == "":
                refcode = None
            member["refcode"] = refcode
            done = False
        elif ch == "Q":
            io.echo("Quit")

            errcount = 0
            for f in ("loginid", "moniker", "email"):
                if member[f] is None or member[f] == "":
                    io.echo(f"{{valuecolor}}{f} {{labelcolor}}is a required field")
                    errcount += 1
            if errcount > 0:
                if (
                    io.inputboolean(
                        f"{{var:promptcolor}}go back and fix it? {{optioncolor}}[{{currentoptioncolor}}Y{{optioncolor}}n]{{promptcolor}}: {{var:inputcolor}}",
                        "Y",
                    )
                    is False
                ):
                    done = True
                    break
            else:
                done = True

    return member


def editui(args, rolename):
    ui = []
    if (
        io.inputboolean(
            f"{{var:promptcolor}}allow {{var:valuecolor}}web{{var:promptcolor}} interface? {{var:optioncolor}}[Yn]{{var:promptcolor}}: {{var:inputcolor}}",
            "Y",
        )
        is True
    ):
        #    database.manage_secondary_role(args, rolename, "add", "web")
        ui += ["web"]
    #  else:
    #    database.manage_secondary_role(args, rolename, "remove", "web")

    if (
        io.inputboolean(
            f"{{var:promptcolor}}allow {{var:valuecolor}}terminal{{var:promptcolor}} interface? {{var:optioncolor}}[Yn]{{var:promptcolor}}: {{var:inputcolor}}",
            "Y",
        )
        is True
    ):
        #    database.manage_secondary_role(args, rolename, "add", "term")
        ui += ["term"]
    #  else:
    #    database.manage_secondary_role(args, rolename, "remove", "term")
    return ui


def setui(args, rolname, ui, **kwargs):
    io.echo(f"bbsengine.con.setui.100: {kwargs=}", level="debug")
    if ui is None:
        ui = []
    if "term" in ui:
        database.manage_secondary_role(args, rolname, "grant", "term", **kwargs)
    else:
        database.manage_secondary_role(args, rolname, "revoke", "term", **kwargs)

    if "web" in ui:
        database.manage_secondary_role(args, rolname, "grant", "web", **kwargs)
    else:
        database.manage_secondary_role(args, rolname, "revoke", "web", **kwargs)


def configurerole(args, rolename: str, sysop=False, **kwargs: dict) -> bool:
    conn = kwargs.get("conn", None)
    io.echo(f"con.member.configurerole.100: {conn=}", level="debug")
    if conn is None:
        return False

    io.echo(f"{{var:labelcolor}}checking for role {{var:valuecolor}}{rolename}")
    io.echo(f"con.member.configurerole.100: {kwargs=}", level="debug")
    if database.rolexists(args, rolename, **kwargs) is False:
        if (
            io.inputboolean(
                f"{{var:promptcolor}}role {{var:valuecolor}}{rolename}{{var:promptcolor}} does not exist. create it? {{var:optioncolor}}[Yn]{{var:promptcolor}}: {{var:inputcolor}}",
                "Y",
            )
            is False
        ):
            io.echo("role not created.")
            return False
        io.echo(
            f"bbsengine.con.configurerole.120: trying to create role", level="debug"
        )
        database.createrol(args, rolename, **kwargs)

        io.echo(
            f"bbsengine.con.configurerole.140: calling manage_role_privs()",
            level="debug",
        )
        database.manage_role_privs(args, rolename, "grant", "login", **kwargs)
        database.manage_role_privs(args, rolename, "grant", "inherit", **kwargs)

    if sysop is True:
        database.manage_secondary_role(args, rolename, "grant", "sysop", **kwargs)
        database.manage_role_privs(args, rolename, "grant", "createdb", **kwargs)
        # database.manage_role_privs(args, loginid, "grant", "superuser", **kwargs)
        database.manage_role_privs(args, rolename, "grant", "createrole", **kwargs)
    else:
        database.manage_secondary_role(args, rolename, "revoke", "sysop", **kwargs)
        database.manage_role_privs(args, rolename, "revoke", "createdb", **kwargs)
        # database.manage_role_privs(args, loginid, "revoke", "superuser")
        database.manage_role_privs(args, rolename, "revoke", "createrole", **kwargs)

    io.echo(f"con.member.configurerole.160: done", level="debug")
    return True


def edit(args, **kwargs):
    io.echo(f"bbsengine.con.member.100: {kwargs=}", level="debug")
    buf = io.inputstring(
        "{var:promptcolor}loginid or moniker: {var:inputcolor}", "", noneok=True
    )
    io.echo("{/all}")
    if buf is None:
        return None

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo("bbsengine.con.member.200: {pool=}", level="error")
        return None

    with database.connect(args, **kwargs) as conn:
        sql = "select * from engine.__member where loginid=%s or moniker=%s"
        dat = (buf, buf)

        with database.cursor(conn, **kwargs) as cur:
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                io.echo(f"{buf=} not found", level="error")
                return False

            rec = cur.fetchone()

            m = libmember.build(args, rec, conn=conn, **kwargs)

            io.echo(f"bbsengine6.con.member.edit.120: {rec=} {m=}", level="debug")

            _m = _edit(args, "edit", m, conn=conn)

            loginid = m["loginid"]
            moniker = m["moniker"]
            #      memberid = m["id"]
            password = m["password"]
            ui = m["ui"]

            configurerole(args, loginid, conn=conn, **kwargs)

            io.echo(f"con.member.edit.100: calling setui()", level="debug")
            setui(args, loginid, ui, conn=conn, **kwargs)

            if _m["email"] != m["email"]:
                libmember.setflag(
                    args, "EMAILVERIFIED", False, moniker=m["moniker"], mogrify=True
                )

            libmember.update(args, m, moniker, conn=conn, **kwargs)
            libmember.setpassword(args, moniker, password, conn=conn, **kwargs)

    if io.inputboolean(
        f"{{var:promptcolor}}save changes? {{var:optioncolor}}[Yn]{{var:promptcolor}}: {{var:inputcolor}}",
        "Y",
    ):
        io.echo("commiting member.")
        conn.commit()
    else:
        io.echo("changes not saved.")
        conn.rollback()

        return True


def add(args, **kwargs) -> bool:
    io.echo(f"bbsengine.con.member.add.220: {kwargs=}", level="debug")
    pool = kwargs.get("pool", None)
    io.echo(f"bbsengine.con.member.200: {pool=}", level="debug")
    if pool is None:
        return False

    with database.connect(args, pool=pool) as conn:
        _member = libmember.build(args, conn=conn, **kwargs)

        member = _edit(args, "add", _member, conn=conn, **kwargs)
        io.echo(f"con.member.add.140: {member=}", level="debug")
        if member is None:
            io.echo(f"con.member.add.180: _edit returned None", level="error")
            return False

        # pool = kwargs.get("pool", None)
        member["datecreated"] = "now()"
        member["createdbymoniker"] = libmember.getcurrentmoniker(
            args, conn=conn, **kwargs
        )
        io.echo(f"con.member.add.100: {member=}", level="debug")

        if args.debug is True:
            io.echo(f"con.member.add.120: {member=}", level="debug")

        moniker = libmember.insert(
            args, member, primarykey="moniker", conn=conn, **kwargs
        )  # =member, mogrify=True, returnid=True, primarykey="moniker")
        if args.debug is True:
            io.echo(f"{moniker=}", level="debug")

        for name, data in member["flags"].items():
            io.echo(f"{name=} {data=}", level="debug")
            libmember.setflag(
                args, name, data["value"], moniker=moniker, conn=conn, **kwargs
            )

        #    setui(args, member["loginid"], member["ui"], conn=conn, **kwargs)

        #  for name, data in flags.items():
        #    io.echo(f"{name=} {data=}", level="debug")
        #    libmember.setflag(args, name, data["value"], membermoniker)

        #    libmember.setattrs(args, {}, moniker, reset=True, conn=conn, **kwargs)
        if member["password"] is not None and member["password"] != "":
            libmember.setpassword(
                args, member["password"], moniker, conn=conn, **kwargs
            )
        libmember.setcredits(args, member["credits"], moniker, conn=conn, **kwargs)

        configurerole(
            args,
            member["loginid"],
            member["flags"]["SYSOP"]["value"],
            conn=conn,
            **kwargs,
        )

        if (
            io.inputboolean(
                f"{{var:promptcolor}}add member? {{var:optioncolor}}[Yn]: {{var:inputcolor}}",
                "Y",
            )
            is False
        ):
            conn.rollback()
            return False

        conn.commit()
        io.echo("{/all}member added.")
    return True


def main(args, **kwargs):
    parser = lib.buildargs(args, **kwargs)
    args = parser.parse_args()

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo(f"bbsengine.con.member.main.120: {pool=}", level="error")
        return False
    #    conn = kwargs.get("conn", None)
    #    io.echo(f"bbsengine.con.member.100: {conn=}", level="debug")

    done = False
    while not done:
        util.heading("member")
        io.echo(
            f"{{f6}}{{var:labelcolor}}database: {{var:valuecolor}}{args.databasename} {{var:labelcolor}}host: {{var:valuecolor}}{args.databasehost}:{args.databaseport}{{f6}}"
        )
        io.echo(f"{{var:optioncolor}}[E]{{var:labelcolor}} Edit")
        io.echo(f"{{var:optioncolor}}[N]{{var:labelcolor}} New Member")
        io.echo(f"{{var:optioncolor}}[A]{{var:labelcolor}} Approvals")
        io.echo(f"{{f6}}{{var:optioncolor}}[Q]{{var:labelcolor}} Quit")
        ch = io.inputchoice(
            f"{{var:promptcolor}}member:{{var:inputcolor}} ", "NAEQX", "Q"
        )
        if ch == "E":
            io.echo("Edit")
            if edit(args, **kwargs) is False:
                io.echo(f"edit aborted", level="error")
            else:
                io.echo("edit ok", level="ok")
        elif ch == "N":
            io.echo("New")
            if add(args, **kwargs) is False:
                io.echo(f"add aborted", level="error")
            else:
                io.echo(f"add ok", level="ok")
        elif ch == "Q" or ch == "X":
            io.echo("Quit")
            done = True
            break
