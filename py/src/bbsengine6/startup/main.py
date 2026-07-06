from bbsengine6 import io, util

from . import lib


def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def main(args, **kwargs) -> bool:
    util.heading("bbsengine6 startup")
    io.echo(f"bbsengine6.startup.main.100: {kwargs=}", level="debug")
    failcount = 0
    for s in ("stage_zero", "stage_one"):
        ## io.echo(f"{{labelcolor}}module {{valuecolor}}{s}{{labelcolor}}: ", end="")
        if lib.runmodule(args, s, package="bbsengine6.backend", **kwargs) is False:
            failcount += 1
            io.echo(f"bbsengine6.startup.200: module {s} failed ", level="error")
            break

    level = "ok" if failcount == 0 else "fail"
    io.echo(" bbsengine6 startup complete ", level=level)
    lib.hr(failcount)
    return True
