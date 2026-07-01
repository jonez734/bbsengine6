import argparse

from bbsengine6 import module, database, io, bottombar

#buildargs = _console_lib.buildargs
#setbottombar = _console_lib.setbottombar


def setbottombar(args, buf, **kwargs) -> None:
    return bottombar.setbottombar(args, buf, **kwargs)


# @since 20230630
def runmodule(args, submodule, package="bbsengine6.startup", **kwargs):
    return module.run(args, submodule, package=package, **kwargs)

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
