from bbsengine6 import io, database, module, bottombar


def buildargs(args, **kwargs):
    return None


# @since 20230630
def runmodule(args, submodule, package=".backend", **kwargs):
    return module.runmodule(args, submodule, package=package, **kwargs)


def setbottombar(args, buf, **kwargs) -> None:
    return bottombar.setbottombar(args, buf, **kwargs)


def checkroles(args, **kwargs):
    return runmodule(args, "checkroles", **kwargs)


def checkextensions(args, **kwargs):
    return runmodule(args, "checkextensions", **kwargs)


def checkdatabase(args, **kwargs):
    return runmodule(args, "checkdatabase", **kwargs)


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
