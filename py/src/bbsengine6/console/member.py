"""Member admin: list/edit/add/configurerole/editflags/editui/setui."""

import copy

from bbsengine6 import io, database, util, bank, pgrole
from bbsengine6 import member as libmember

from . import lib
from . import showpgrole


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs):
    return True


def editflags(args, moniker=None, **kwargs):
    """Toggle each flag in memory; persistence is the caller's responsibility.

    Mutates ``flags`` dict in place to reflect the new desired state.
    Returns ``None``; the in-memory state is read out of ``member['flags']``
    by the caller and persisted only after the user confirms the surrounding
    add/edit operation. The local ``conn`` (if any) is **not** used to write
    here, even though it is accepted in ``kwargs`` for API symmetry with
    ``libmember.getflags``.
    """
    conn = kwargs.get("conn", None)
    pool = kwargs.get("pool", None)
    mode = kwargs.get("mode", "add")
    if mode == "add":
        flags = libmember.getflags(args, None, conn=conn, pool=pool)
    else:
        flags = libmember.getflags(args, moniker, conn=conn, pool=pool)
    io.echo(f"bbsengine.con.member.100: {flags=}", level="debug")

    for flag_name, flag_data in flags.items():
        description = flag_data["description"]
        current_value = flag_data["value"]
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
        flags[flag_name]["value"] = new_value
    return flags


def render_member(args, **kwargs):
    member = kwargs.get("member", {})
    _member = kwargs.get("_member", {})

    def _format_flags(flags):
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

    flags = member["flags"] or {}
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
    """Drive the per-field edit loop. Purely in-memory; no DB writes.

    All side-effecting operations (``libmember.insert``,
    ``libmember.update``, ``configurerole``, ``pgrole.*``,
    ``bank.add_funds``) are the caller's responsibility and must only be
    invoked after the user confirms the surrounding add/edit.
    """
    _member = copy.deepcopy(member)
    io.echo(f"con.member._edit.100: {kwargs=}", level="debug")

    util.heading(f"{mode} member")
    conn = kwargs.get("conn", None)
    done = False
    while not done:
        render_member(args, member=member, _member=_member)
        ch = io.inputchoice(
            f"{{var:promptcolor}}{mode} member {{var:optioncolor}}[MECPFURQ]{{var:promptcolor}}: {{var:inputcolor}}",
            "LMECPFURQ",
            "",
            help=render_member,
            member=member,
            _member=_member,
            **kwargs,
        )
        if ch == "M":
            io.echo("Moniker")
            _moniker = member["moniker"]
            moniker = io.inputstring("moniker:", _moniker, args=args)
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
            member["flags"] = editflags(
                args, member["moniker"], conn=conn, pool=kwargs.get("pool"), mode=mode
            )
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
            member["ui"] = editui(args, member["loginid"])
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
        elif ch == "A":
            io.echo("Alerts")
            # Alerts not yet implemented; the previous console/alert.py was
            # removed because it referenced undefined names. No DB or UI
            # action here; just acknowledge the choice.
        elif ch == "R":
            io.echo("Refcode")
            refcode = io.inputstring(
                "{var:promptcolor}refcode: {var:inputcolor}", member["refcode"]
            )
            if refcode == "":
                refcode = None
            member["refcode"] = refcode
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
        ui += ["web"]

    if (
        io.inputboolean(
            f"{{var:promptcolor}}allow {{var:valuecolor}}terminal{{var:promptcolor}} interface? {{var:optioncolor}}[Yn]{{var:promptcolor}}: {{var:inputcolor}}",
            "Y",
        )
        is True
    ):
        ui += ["term"]
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
        database.createrol(args, rolename, **kwargs)
        database.manage_role_privs(args, rolename, "grant", "login", **kwargs)
        database.manage_role_privs(args, rolename, "grant", "inherit", **kwargs)

    if sysop is True:
        database.manage_secondary_role(args, rolename, "grant", "sysop", **kwargs)
        database.manage_role_privs(args, rolename, "grant", "createdb", **kwargs)
        database.manage_role_privs(args, rolename, "grant", "createrole", **kwargs)
    else:
        database.manage_secondary_role(args, rolename, "revoke", "sysop", **kwargs)
        database.manage_role_privs(args, rolename, "revoke", "createdb", **kwargs)
        database.manage_role_privs(args, rolename, "revoke", "createrole", **kwargs)

    return True


def edit(args, **kwargs):
    """Edit an existing member. No DB writes happen before confirmation.

    Reads the row, drives the in-memory edit loop, prompts for
    confirmation, then commits all changes inside a single transaction.
    Loginid renames are refused.
    """
    io.echo(f"bbsengine.con.member.edit.100: {kwargs=}", level="debug")
    buf = io.inputstring(
        "{var:promptcolor}loginid or moniker: {var:inputcolor}", "", noneok=True
    )
    io.echo("{/all}")
    if buf is None:
        return None

    if "pool" not in kwargs or kwargs["pool"] is None:
        io.echo("bbsengine.con.member.edit.200: pool missing", level="error")
        return None

    with database.connect(args, pool=kwargs["pool"], auto_commit=False) as conn:
        with database.cursor(conn=conn) as cur:
            cur.execute(
                "select * from engine.__member where loginid=%s or moniker=%s",
                (buf, buf),
            )
            if cur.rowcount == 0:
                io.echo(f"{buf=} not found", level="error")
                return False
            rec = cur.fetchone()

        m = libmember.build(args, rec, conn=conn, **kwargs)
        _baseline_loginid = m["loginid"]
        _baseline_email = m["email"]
        _baseline_flags = {
            k: dict(v) for k, v in (m.get("flags") or {}).items()
        }
        _baseline_credits = m.get("credits")

        _edit(args, "edit", m, conn=conn, **kwargs)

        # Confirmation gate. The user can say No and the transaction
        # is rolled back with no DB state having changed.
        if not io.inputboolean(
            f"{{var:promptcolor}}save changes? {{var:optioncolor}}[Yn]{{var:promptcolor}}: {{var:inputcolor}}",
            "Y",
        ):
            io.echo("changes not saved.")
            return False

        # Loginid rename is not supported in the console: the psql
        # role (l_<loginid>) is named for the old loginid, and there
        # is no `database.renamerole` helper yet.
        if m["loginid"] != _baseline_loginid:
            io.echo(
                f"loginid rename from {_baseline_loginid!r} to {m['loginid']!r} "
                "is not supported in the console. Use psql to "
                "ALTER ROLE ... RENAME TO.",
                level="error",
            )
            # TODO: support rename via database.renamerole(args, old, new, conn=conn)
            return False

        # All side effects below run inside the open `with conn` block.
        # Any exception rolls back; on success we commit at the end.
        try:
            libmember.update(args, m, m["moniker"], conn=conn, **kwargs)

            for name, data in (m.get("flags") or {}).items():
                if data.get("value") != _baseline_flags.get(name, {}).get("value"):
                    libmember.setflag(
                        args,
                        name,
                        data["value"],
                        moniker=m["moniker"],
                        conn=conn,
                        **kwargs,
                    )

            if m["email"] != _baseline_email:
                libmember.setflag(
                    args,
                    "EMAILVERIFIED",
                    False,
                    moniker=m["moniker"],
                    conn=conn,
                    **kwargs,
                )

            libmember.setpassword(
                args, m["moniker"], m["password"], conn=conn, **kwargs
            )

            configurerole(
                args,
                m["loginid"],
                m.get("flags", {}).get("SYSOP", {}).get("value", False),
                conn=conn,
                **kwargs,
            )
            setui(args, m["loginid"], m["ui"], conn=conn, **kwargs)
            pgrole.ensure_role_for_member(
                args, m["loginid"], conn=conn, **kwargs
            )
            pgrole.sync_groups(args, m["loginid"], conn=conn, **kwargs)

            conn.commit()
        except Exception as e:
            io.echo_traceback(f"bbsengine6.console.member.edit: {e}")
            conn.rollback()
            return False
    return True


def add(args, **kwargs) -> bool:
    """Add a new member. No DB writes happen before confirmation.

    The user is asked to confirm the add before any side effects run.
    All operations (insert, setflag, setpassword, bank grant,
    configurerole, pgrole provisioning) share the same connection and
    commit atomically at the end.
    """
    io.echo(f"bbsengine.con.member.add.220: {kwargs=}", level="debug")
    if "pool" not in kwargs or kwargs["pool"] is None:
        io.echo("bbsengine.con.member.add.120: pool missing", level="error")
        return False

    with database.connect(args, pool=kwargs["pool"], auto_commit=False) as conn:
        _member = libmember.build(args, conn=conn, **kwargs)
        member = _edit(args, "add", _member, conn=conn, **kwargs)
        if member is None:
            io.echo("con.member.add.180: _edit returned None", level="error")
            return False

        member["datecreated"] = "now()"
        member["createdbymoniker"] = libmember.getcurrentmoniker(
            args, conn=conn, **kwargs
        )

        # Confirmation gate: no DB writes above this line on the
        # success path; everything below this line is a side effect
        # that is rolled back on user-cancel.
        if not io.inputboolean(
            f"{{var:promptcolor}}add member? {{var:optioncolor}}[Yn]: {{var:inputcolor}}",
            "Y",
        ):
            return False

        # All side effects run inside the open `with conn` block.
        # Any exception rolls back; on success we commit at the end.
        try:
            moniker = libmember.insert(
                args, member, primarykey="moniker", conn=conn, **kwargs
            )
            if not moniker:
                io.echo(
                    "con.member.add.200: libmember.insert returned no moniker",
                    level="error",
                )
                return False

            for name, data in (member.get("flags") or {}).items():
                libmember.setflag(
                    args,
                    name,
                    data["value"],
                    moniker=moniker,
                    conn=conn,
                    **kwargs,
                )

            if member.get("password"):
                libmember.setpassword(
                    args,
                    member["password"],
                    moniker,
                    conn=conn,
                    **kwargs,
                )

            bank_service = bank.BankService(args)
            bank_service.add_funds(
                moniker,
                100,
                transaction_type="initial",
                description="New member bonus",
                conn=conn,
            )

            configurerole(
                args,
                member["loginid"],
                member.get("flags", {}).get("SYSOP", {}).get("value", False),
                conn=conn,
                **kwargs,
            )
            pgrole.ensure_role_for_member(
                args, member["loginid"], conn=conn, **kwargs
            )
            pgrole.sync_groups(
                args, member["loginid"], conn=conn, **kwargs
            )

            conn.commit()
        except Exception as e:
            io.echo_traceback(f"bbsengine6.console.member.add: {e}")
            conn.rollback()
            return False
    return True


def main(args, **kwargs):
    parser = lib.buildargs(args, **kwargs)
    args = parser.parse_args()

    if "pool" not in kwargs or kwargs["pool"] is None:
        io.echo(f"bbsengine.con.member.main.120: pool missing", level="error")
        return False

    done = False
    while not done:
        util.heading("member")
        io.echo(
            f"{{f6}}{{var:labelcolor}}database: {{var:valuecolor}}{args.databasename} {{var:labelcolor}}host: {{var:valuecolor}}{args.databasehost}:{args.databaseport}{{f6}}"
        )
        io.echo(f"{{var:optioncolor}}[E]{{var:labelcolor}} Edit")
        io.echo(f"{{var:optioncolor}}[N]{{var:labelcolor}} New Member")
        io.echo(f"{{var:optioncolor}}[A]{{var:labelcolor}} Approvals")
        io.echo(f"{{var:optioncolor}}[P]{{var:labelcolor}} psql credentials")
        io.echo(f"{{f6}}{{var:optioncolor}}[Q]{{var:labelcolor}} Quit")
        ch = io.inputchoice(
            f"{{var:promptcolor}}member:{{var:inputcolor}} ",
            "NAEPQX",
            "Q",
            **kwargs,
        )
        if ch == "E":
            io.echo("Edit")
            if edit(args, **kwargs) is False:
                io.echo("edit aborted", level="error")
            else:
                io.echo("edit ok", level="ok")
        elif ch == "N":
            io.echo("New")
            if add(args, **kwargs) is False:
                io.echo("add aborted", level="error")
            else:
                io.echo("add ok", level="ok")
        elif ch == "A":
            io.echo("Approvals")
            if lib.runmodule(args, "memberapproval", **kwargs) is False:
                io.echo("approvals aborted", level="error")
        elif ch == "P":
            io.echo("psql credentials")
            if showpgrole.main(args, **kwargs) is False:
                io.echo("showpgrole failed", level="error")
        elif ch == "Q" or ch == "X":
            io.echo("Quit")
            done = True
