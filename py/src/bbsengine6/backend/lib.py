from bbsengine6 import io, module, screen, util


def buildargs(args, **kwargs):
    return None


# @since 20230523
def runmodule(args, submodule, **kwargs):
    return module.runmodule(args, f"bbsengine6.backend.{submodule}", **kwargs)


# @since 20230523 copied from teos
def setbottombar(args, left, **kwargs):
    def right():
        help = " | F1: Help" if "help" in kwargs and kwargs["help"] is True else ""
        debug = " | debug" if args.debug is True else ""
        return f"con{debug}{help}"

    screen.setbottombar(left, right, **kwargs)
    return


def checkroles(args, **kwargs):
    return runmodule(args, "checkroles", **kwargs)


def checkextensions(args, **kwargs):
    return runmodule(args, "checkextensions", **kwargs)


def checkdatabase(args, **kwargs):
    return runmodule(args, "checkdatabase", **kwargs)


def checkcreatedb(args, **kwargs):
    return runmodule(args, "checkcreatedb", **kwargs)


def checksuperuser(args, **kwargs):
    return runmodule(args, "checksuperuser", **kwargs)


def createdatabase(args, **kwargs):
    return runmodule(args, "createdatabase", **kwargs)


def checkfunctions(args, **kwargs):
    return runmodule(args, "checkfunctions", **kwargs)


def checkclasses(args, **kwargs):
    return runmodule(args, "checkclasses", **kwargs)


def checkflag(args, **kwargs):
    return runmodule(args, "checkflag", **kwargs)


def checknotify(args, **kwargs):
    return runmodule(args, "checknotify", **kwargs)


def checknotifyd(args, **kwargs):
    return runmodule(args, "checknotifyd", **kwargs)


def checkwebserverrole(args, **kwargs):
    return runmodule(args, "checkwebserverrole", **kwargs)


def checkbank(args, **kwargs):
    return runmodule(args, "bank", **kwargs)


def ok():
    io.echo(f"{{level.ok}}  ok  {{/all}}")
    return


def fail():
    io.echo(f"{{level.fail}} fail {{/all}}")


# Historical note (2026-07-06): commit 8a5d1c0 removed {level.fail} and the
# level="fail" example from io/specs/echo_commands.spec on the assumption
# that no caller used them. backend.lib.fail() above emits {{level.fail}}
# fail {{/all}} and is called by checkdatabase, checkroles, checkwebserverrole,
# checkflag, checksuperuser, and bank. Commit 7115e77 restored both lines
# in the spec. If you ever consider removing {level.fail} again, also remove
# backend.lib.fail() and migrate those callers to io.echo(level="error")
# first; otherwise the spec will be out of sync with the live API.
util.logentry(
    "backend.lib: {level.fail} is in use by fail(); spec lists it",
    module="backend.lib",
    action="level_fail_in_use",
)


def hr(failcount: int = 0) -> None:
    color = "{boxcolor}" if failcount == 0 else "{/all}{red}"
    util.hr(color=color)
