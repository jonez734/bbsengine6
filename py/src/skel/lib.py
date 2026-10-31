import argparse

from bbsengine6 import module


PACKAGENAME = "skel"


def checkmodule(args: argparse.Namespace, modulename: str, **kwargs) -> bool:
    return module.check(args, f"{PACKAGENAME}.{modulename}", **kwargs)


def runmodule(args: argparse.Namespace, modulename: str, **kwargs) -> bool | None:
    return module.runmodule(args, f"{PACKAGENAME}.{modulename}", **kwargs)


def buildargs(args: argparse.Namespace, **kwargs) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(PACKAGENAME)
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    return parser
