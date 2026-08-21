"""
Ensure the dedicated ``zoid6`` role exists.

This role is the canonical owner of the five ``public.*`` SECURITY DEFINER
helpers (``manage_schema_priv``, ``manage_database_priv``,
``manage_role_privs``, ``manage_secondary_role``, ``get_role_privs``) and
nothing else. Decoupling ownership from the bootstrap principal
(``args.databaseuser`` / ``getpass.getuser()``, normally a login superuser)
keeps the trust surface stable across re-bootstraps and tightens the
allow-list enforced by ``database.verify_function_owner`` /
``backend.checkengine``.

Attributes: ``NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN INHERIT``. The
role is created with no password and cannot log in, so it cannot be used
as a credential entrypoint by an attacker even if the surrounding
``pg_hba.conf`` is misconfigured. The role exists only to own SQL
objects; mutating those objects is done from a superuser via
``ALTER FUNCTION ... OWNER TO zoid6`` (see ``checkzoid6owner``).

The module also asserts that an already-present ``zoid6`` role is
``NOSUPERUSER``. A ``rolsuper=True`` would silently break the trust
model (anyone able to create or replace the helpers inherits that
superuser). The check is hard-fail rather than warn so the misconfig
cannot be ignored in production.
"""

from bbsengine6 import database, io

from . import lib


ROLE_NAME = "zoid6"


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, **kwargs):
    return True


def main(args, **kwargs):
    failcount = 0
    conn = kwargs.get("conn", None)

    io.echo(
        f"{{var:labelcolor}}role {{var:valuecolor}}{ROLE_NAME}{{var:labelcolor}}: ",
        end="",
    )
    if database.rolexists(args, ROLE_NAME, conn=conn) is False:
        io.echo("{{var:labelcolor}}create ", end="")
        if (
            database.createrol(
                args,
                ROLE_NAME,
                conn=conn,
                superuser=False,
                login=False,
                createdb=False,
                createrole=False,
                inherit=True,
            )
            is False
        ):
            io.echo("{{var:level.error}} fail {{/all}}", level="error")
            failcount += 1
        else:
            io.echo("{{level.ok}}  ok  {{/all}}")
    else:
        io.echo("{{level.ok}}  ok  {{/all}}")

        # Hard guard: a `zoid6` with rolsuper=True breaks the trust
        # model. The verifier would still pass (a superuser can own
        # anything), but the role's purpose is to be unprivileged, and
        # silently accepting the override lets a misconfig slip
        # through. Refuse to continue and tell the operator how to fix.
        if failcount == 0:
            privs = database.get_role_privs(args, ROLE_NAME, conn=conn)
            if privs and privs.get("rolsuper") is True:
                io.echo(
                    f"{{var:labelcolor}}role '{{var:valuecolor}}{ROLE_NAME}"
                    f"{{var:labelcolor}}' has rolsuper=True; the dedicated "
                    f"owner role must be NOSUPERUSER. Run "
                    f"'ALTER ROLE {ROLE_NAME} WITH NOSUPERUSER;' and retry.",
                    level="error",
                )
                failcount += 1

    lib.hr(failcount)
    return True if failcount == 0 else False
