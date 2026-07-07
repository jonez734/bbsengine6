import argparse

from bbsengine6 import module, database, bottombar


def setbottombar(args, buf, **kwargs) -> None:
    return bottombar.setbottombar(args, buf, **kwargs)


# @since 20230630
def runmodule(args, submodule, package="bbsengine6.startup", **kwargs):
    return module.run(args, submodule, package=package, **kwargs)


# Stages whose implementation lives in bbsengine6.backend rather than
# bbsengine6.startup. This tuple is the single source of truth: the dict
# BACKEND_STAGES below is derived from it. The loop in startup.main.py
# iterates this tuple in order, so adding a stage here is sufficient.
#
# Python dicts preserve insertion order (3.7+ language guarantee).
BACKEND_STAGE_NAMES = ("stage_zero", "stage_one", "bank")

BACKEND_STAGES = {name: "bbsengine6.backend" for name in BACKEND_STAGE_NAMES}


def runstage(args, name, **kwargs):
    pkg = BACKEND_STAGES.get(name)
    if pkg is not None:
        kwargs.setdefault("package", pkg)
    return module.run(args, name, **kwargs)


# @since 20230518 copied from con
def buildargs(args=None, **kwargs):
    parser = argparse.ArgumentParser("startup")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {
        "databasename": "zoid6",
        "databasehost": "localhost",
        "databaseuser": None,
        "databaseport": 5432,
        "databasepassword": None,
    }
    database.buildargs(parser, defaults)

    return parser
