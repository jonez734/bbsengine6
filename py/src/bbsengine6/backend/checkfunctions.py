"""
Verify and initialize database functions (stored procedures).

Creates and validates all required PostgreSQL stored procedures and functions
that implement the business logic for the BBS engine.
"""

from bbsengine6 import io, database

from bbsengine6.backend import lib


# Functions whose CREATE lives in a differently-named .sql file. The
# default derivation (strip schema prefix + ".sql") assumes the file
# is named after the function; these are the exceptions. The three
# pgrole helpers all live in createrol.sql, so importing that file
# once provisions all of them.
SQL_FILE_OVERRIDES = {
    "engine.createpgrole": "createrol.sql",
    "engine.deletepgrole": "createrol.sql",
    "engine.syncpgrolegroups": "createrol.sql",
}


def init(args, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs) -> bool:
    return lib.issysop(args, **kwargs)


def main(args, **kwargs):
    stage = kwargs.pop("stage", 0)
    conn = kwargs.get("conn", None)

    def _work(conn):
        lib._ensure_autocommit_off(conn)
        if stage == 0:
            funcs = (
                "public.get_role_privs",
                "public.manage_secondary_role",
                "public.manage_role_privs",
                "public.manage_database_priv",
                "public.manage_schema_priv",
            )
        else:
            # public.* helpers are needed in the target DB too:
            # console/member.py calls manage_secondary_role and
            # manage_role_privs against args.databasename (zoid6),
            # not the admin DB. Stage 0 installs them in 'postgres';
            # stage 1 installs them in the target DB. PostgreSQL
            # functions are per-database, not cluster-wide.
            funcs = (
                "public.get_role_privs",
                "public.manage_secondary_role",
                "public.manage_role_privs",
                "public.manage_database_priv",
                "public.manage_schema_priv",
                "engine.getflags",
                "engine.checkmemberflag",
                # pgrole helpers (all defined in createrol.sql). See
                # SQL_FILE_OVERRIDES for the file mapping. Installed in
                # the target DB so console/member.py flag changes can
                # call engine.syncpgrolegroups().
                "engine.createpgrole",
                "engine.deletepgrole",
                "engine.syncpgrolegroups",
            )
        failcount = 0
        for f in funcs:
            sp_name = f
            io.echo(
                f"{{var:labelcolor}}function {{var:valuecolor}}{f}{{var:labelcolor}}: {{var:valuecolor}}",
                end="",
            )
            if database.functionexists(args, f, conn=conn) is False:
                io.echo("import ", end="")
                sp = lib._sanitize_sp(sp_name)
                with database.cursor(conn=conn) as cur:
                    cur.execute(f"SAVEPOINT {sp}")
                sql_file = SQL_FILE_OVERRIDES.get(sp_name)
                if sql_file is None:
                    sql_file = sp_name.replace("engine.", "").replace("public.", "")
                    if not sql_file.endswith(".sql"):
                        sql_file += ".sql"
                try:
                    ok = lib.retry_on_transient(
                        lambda: database.importsql(
                            args, sql_file, conn=conn, rollback=False
                        )
                    )
                except Exception as e:
                    io.echo_traceback(
                        f"checkfunctions: retry exhausted for {f}: {e}"
                    )
                    ok = False
                if ok is False:
                    with database.cursor(conn=conn) as cur:
                        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
                    io.echo("fail", level="error")
                    failcount += 1
                else:
                    with database.cursor(conn=conn) as cur:
                        cur.execute(f"RELEASE SAVEPOINT {sp}")
                    io.echo("ok", level="ok")
            else:
                io.echo("exists", level="ok")
        if failcount == 0:
            conn.commit()
        else:
            conn.rollback()
        return True if failcount == 0 else False

    return _work(conn)
