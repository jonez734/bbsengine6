"""Member admin: list/edit/add/configurerole/editflags/editui/setui."""

import copy

import psycopg

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

    # [P] changes the password, so it is always offered. The value is never shown: only whether
    # a new password has been entered in this edit.
    if member.get("password"):
        io.echo("  {var:optioncolor}[P]{var:labelcolor} Password: {var:valuecolor}(set, not shown){/all}")
    else:
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
    # io.echo(f"{ui=} {_ui=}", level="debug")  # noisy: printed ui=None on every menu draw
    if ui is None or len(ui) == 0:
        # Print the empty UI line and keep drawing the rest of the menu. Returning here
        # cut the menu off, so [F], [R], [D] and [X] never showed.
        io.echo(f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: None", end="")
        if _ui is not None:
            _ui.sort()
            io.echo(f" (was: {', '.join(_ui)})")
        else:
            io.echo()
    else:
        if ui is not None:
            ui.sort()
        if _ui is not None:
            _ui.sort()

    if ui is None or len(ui) == 0:
        pass  # the empty UI line was printed above
    elif ui != _ui:
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

    psqlrole = member.get("psqlrole")
    io.echo(
        f"  {{var:optioncolor}}[D]{{var:labelcolor}} Data role:{{var:valuecolor}} {psqlrole or '(none)'}"
    )


def _load_psql(conn, m: dict) -> None:
    """Put the member's data role into the edit dict (the loginid is the OS login).

    Without this an existing member's [D] menu starts blank. A member with no tracking row
    gets None.
    """
    with database.cursor(conn=conn) as cur:
        cur.execute(
            "SELECT rolname FROM engine.pgrole WHERE membermoniker = %s",
            (m["moniker"],),
        )
        row = cur.fetchone()
    if row is None or not isinstance(row, (dict, tuple, list)):
        m["psqlrole"] = None
        return
    m["psqlrole"] = row.get("rolname") if isinstance(row, dict) else row[0]

def _stored_psqlrole(conn, moniker: str):
    """The data role already recorded for this member in engine.pgrole, or None."""
    with database.cursor(conn=conn) as cur:
        cur.execute(
            "SELECT rolname FROM engine.pgrole WHERE membermoniker = %s",
            (moniker,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return row["rolname"] if isinstance(row, dict) else row[0]


def _ask_psqlrole_menu(args, moniker: str, stored, *, conn):
    """[D] menu option: name the data role, then check it exists. Writes nothing.

    An existing data role is not renamed here (the same rule as the loginid): the stored
    name is kept and the sysop is told so. A new name is checked and created on exit.
    """
    default = stored or pgrole.role_name_for(moniker)
    name = io.inputstring(
        f"{{var:promptcolor}}data role{{var:promptcolor}} (default {{var:valuecolor}}{default}{{var:promptcolor}}): {{var:inputcolor}}",
        default,
        noneok=True,
    )
    name = (name or "").strip() or default
    if stored is not None and name != stored:
        io.echo(
            f"{{var:labelcolor}}data role {{var:valuecolor}}{stored}{{var:labelcolor}} already exists for this "
            f"member; it is not renamed from the menu.",
            level="error",
        )
        return stored
    if database.rolexists(args, name, conn=conn) is False:
        io.echo(
            f"{{var:labelcolor}}data role {{var:valuecolor}}{name}{{var:labelcolor}} "
            f"does not exist yet; it is created when you exit the menu."
        )
    return name


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
            f"{{var:promptcolor}}{mode} member {{var:optioncolor}}[MECPFDURQX]{{var:promptcolor}}: {{var:inputcolor}}",
            "LMECPFDURQX",
            "",
            help=render_member,
            member=member,
            _member=_member,
            **kwargs,
        )
        if ch == "D":
            io.echo("Data role (psql role)")
            member["psqlrole"] = _ask_psqlrole_menu(
                args, member["moniker"], _stored_psqlrole(conn, member["moniker"]), conn=conn
            )
        elif ch == "M":
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
        elif ch in ("Q", "X"):
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


def configurerole(
    args,
    rolename: str,
    sysop=False,
    *,
    psqlrole=None,
    menu_answered: bool = False,
    **kwargs: dict,
) -> bool:
    """Apply a member's psql role configuration.

    menu_answered=True means the [D] menu already asked the sysop and checked
    existence; psqlrole is then applied without
    prompting again. Otherwise the prompts run here, as before.
    """
    conn = kwargs.get("conn", None)
    io.echo(f"con.member.configurerole.100: {conn=}", level="debug")
    if conn is None:
        return False

    moniker = kwargs.get("moniker")
    if not moniker:
        io.echo(
            f"con.member.configurerole.110: no moniker for {rolename=}",
            level="error",
        )
        return False

    # The role is m_<moniker>, created by pgrole.ensure_login_role. That path also grants
    # 'member' and writes the engine.pgrole tracking row, which the request path needs.
    # A bare CREATE ROLE <loginid> here skipped both, so the member was refused at login.
    target = pgrole.role_name_for(moniker)
    # When the [D] menu answered, those were checked right after input and the sysop
    # was already asked. Only the bare path (no menu answers) prompts here.
    # preexisting is read once: the prompt check on the bare path, otherwise a single check.
    if not menu_answered:
        io.echo(f"{{var:labelcolor}}checking for role {{var:valuecolor}}{target}")
        exists = database.rolexists(args, target, conn=conn)
        preexisting = exists is True
        if exists is False:
            if (
                io.inputboolean(
                    f"{{var:promptcolor}}role {{var:valuecolor}}{target}{{var:promptcolor}} does not exist. create it? {{var:optioncolor}}[Yn]{{var:promptcolor}}: {{var:inputcolor}}",
                    "Y",
                )
                is False
            ):
                io.echo("role not created.")
                return False


    if menu_answered:
        preexisting = database.rolexists(args, psqlrole or target, conn=conn) is True
    rolname = pgrole.ensure_login_role(args, moniker, conn=conn, rolname=psqlrole)
    if not rolname:
        io.echo(
            f"{{var:labelcolor}}could not provision a psql role for {{var:valuecolor}}{rolename}",
            level="error",
        )
        return False

    privs = database.get_role_privs(args, rolname, conn=conn)
    if privs is not None and privs.get("rolsuper") is True:
        io.echo(
            f"{{var:valuecolor}}{rolname}{{var:labelcolor}} has "
            f"SUPERUSER; skipping login/inherit/createdb/createrole sync "
            f"(zoid6 cannot ALTER a SUPERUSER role). Leave SUPERUSER in "
            f"place.",
            level="warning",
        )
    else:
        if sysop is True:
            database.manage_role_privs(args, rolname, "grant", "createdb", **kwargs)
            database.manage_role_privs(args, rolname, "grant", "createrole", **kwargs)
        else:
            # Revoke only a privilege the role actually holds. An ALTER ROLE on a role that holds
            # nothing is redundant, and manage_role_privs runs as zoid6, which cannot alter a role
            # it did not create (InsufficientPrivilege). Privileges come from the role itself.
            if privs is None:
                io.echo(
                    f"{{var:labelcolor}}could not read privileges for {{var:valuecolor}}{rolname}; "
                    f"not changing createdb/createrole this time.",
                    level="warning",
                )
            holds = privs or {}
            if holds.get("rolcreatedb") is True:
                database.manage_role_privs(args, rolname, "revoke", "createdb", **kwargs)
            if holds.get("rolcreaterole") is True:
                database.manage_role_privs(args, rolname, "revoke", "createrole", **kwargs)

    if sysop is True:
        database.manage_secondary_role(args, rolname, "grant", "sysop", **kwargs)
    else:
        database.manage_secondary_role(args, rolname, "revoke", "sysop", **kwargs)

    return _apply_login_role(args, rolname, rolename, **kwargs)


def _apply_login_role(args, rolname: str, loginid: str, **kwargs) -> bool:
    """Ensure the login role for this member's loginid exists and may SET ROLE to the data role.

    The loginid is the OS login: the login role is named for it, and ident maps the OS user to
    it. Runs only after every prompt has been answered. Failures return False with a message.
    """
    conn = kwargs.get("conn")
    if not loginid:
        io.echo("{var:labelcolor}no loginid, so no login role is set up for this member.")
        return True

    ok = pgrole.ensure_os_login_role(args, loginid, rolname, conn=conn)
    if not ok:
        io.echo(
            f"{{var:labelcolor}}could not create or grant login role {{var:valuecolor}}{loginid}",
            level="error",
        )
        return False
    io.echo(f"{{var:okcolor}}login role {loginid} may SET ROLE {rolname}.")
    return True


def _edit_write(args, m, *, _baseline_flags, _baseline_email, conn, **kwargs) -> bool:
    """Update and provision an existing member. One transaction: commit on success, roll back on failure.

    A failed step prints one readable line naming it. The full traceback goes through
    io.echo_traceback and is kept. Nothing is saved after a failure.
    """
    step = "update"
    try:
        if libmember.update(args, m, m["moniker"], conn=conn, **kwargs) is False:
            io.echo(
                f"could not update member {m.get('moniker')!r}: the member record was not saved. "
                f"No changes were saved.",
                level="error",
            )
            conn.rollback()
            return False

        step = "flags"
        for name, data in (m.get("flags") or {}).items():
            if data.get("value") != _baseline_flags.get(name, {}).get("value"):
                libmember.setflag(args, name, data["value"], moniker=m["moniker"], conn=conn, **kwargs)

        if m["email"] != _baseline_email:
            step = "email verification flag"
            libmember.setflag(args, "EMAILVERIFIED", False, moniker=m["moniker"], conn=conn, **kwargs)

        step = "password"
        libmember.setpassword(args, m["password"], m["moniker"], conn=conn, **kwargs)

        step = "psql roles"
        configurerole(
            args, m["loginid"],
            m.get("flags", {}).get("SYSOP", {}).get("value", False),
            conn=conn, moniker=m["moniker"],
            psqlrole=m.get("psqlrole"),
            menu_answered=True, **kwargs,
        )
        step = "user interface"
        setui(args, m["loginid"], m["ui"], conn=conn, **kwargs)
        step = "psql role record"
        pgrole.ensure_login_role(args, m["moniker"], conn=conn, **kwargs)
        step = "group sync"
        pgrole.sync_groups(args, m["loginid"], conn=conn, **kwargs)

        step = "commit"
        conn.commit()
        return True
    except Exception as e:
        io.echo_traceback(f"bbsengine6.console.member.edit.{step}: {e}")
        io.echo(
            f"could not update member {m.get('moniker')!r}: failed at {step} ({type(e).__name__}). "
            f"No changes were saved.",
            level="error",
        )
        conn.rollback()
        return False


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
        _load_psql(conn, m)
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
        # role (m_<moniker>) is named for the moniker, and there
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

        return _edit_write(args, m, _baseline_flags=_baseline_flags, _baseline_email=_baseline_email, conn=conn, **kwargs)
    return True


def _add_write(args, member, *, conn, **kwargs) -> bool:
    """Insert and provision a new member. One transaction: commit on success, roll back on any failure.

    A failed step prints one readable line naming it, and the full traceback through
    io.echo_traceback (kept, not dropped). The menu stays usable.
    """
    step = "insert"
    try:
        moniker = libmember.insert(
            args, member, primarykey="moniker", conn=conn, **kwargs
        )
        if not moniker:
            io.echo(
                f"could not insert member {member.get('moniker')!r}: insert returned no moniker. "
                f"No changes were saved.",
                level="error",
            )
            conn.rollback()
            return False

        step = "flags"
        for name, data in (member.get("flags") or {}).items():
            libmember.setflag(args, name, data["value"], moniker=moniker, conn=conn, **kwargs)

        step = "password"
        if member.get("password"):
            libmember.setpassword(args, member["password"], moniker, conn=conn, **kwargs)

        step = "bank account"
        bank_service = bank.BankService(args)
        starting = bank.get_starting_balance()
        bank_service.add_funds(
            moniker, starting, transaction_type="initial",
            description="New member bonus", conn=conn,
        )

        step = "psql roles"
        configurerole(
            args, member["loginid"],
            member.get("flags", {}).get("SYSOP", {}).get("value", False),
            conn=conn, moniker=moniker,
            psqlrole=member.get("psqlrole"),
            menu_answered=True, **kwargs,
        )
        pgrole.ensure_login_role(args, moniker, conn=conn, **kwargs)
        pgrole.sync_groups(args, member["loginid"], conn=conn, **kwargs)

        step = "commit"
        conn.commit()
        return True
    except Exception as e:
        io.echo_traceback(f"bbsengine6.console.member.add.{step}: {e}")
        io.echo(
            f"could not add member {member.get('moniker')!r}: failed at {step} ({type(e).__name__}). "
            f"No changes were saved.",
            level="error",
        )
        conn.rollback()
        return False


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

        return _add_write(args, member, conn=conn, **kwargs)
    return True


def main(args, **kwargs):
    parser = lib.buildargs(args, **kwargs)
    args = parser.parse_args()

    if "pool" not in kwargs or kwargs["pool"] is None:
        io.echo(f"bbsengine.con.member.main.120: pool missing", level="error")
        return False

    done = False
    while not done:
        try:
            done = _menu_once(args, **kwargs)
        except _DatabaseLost as e:
            io.echo(
                f"{{var:labelcolor}}the database connection was lost ({e}); the member menu is closing. "
                f"Nothing from the interrupted action was saved.",
                level="error",
            )
            return False
    return True


class _DatabaseLost(Exception):
    """The server closed the session while the member menu was running."""


def _menu_once(args, **kwargs) -> bool:
    """One pass of the member menu. Returns True when the user chose to quit."""
    done = False
    try:
        return _menu_pass(args, **kwargs)
    except (psycopg.OperationalError, psycopg.InterfaceError) as e:
        raise _DatabaseLost(str(e)) from e


def _menu_pass(args, **kwargs) -> bool:
    done = False
    if True:
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
    return done
