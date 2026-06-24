from bbsengine6 import util

from . import lib


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def init(args, **kwargs) -> bool:
    return True


def access(args, op: str, **kwargs) -> bool:
    return True


def main(args, **kwargs):
    util.heading("HEADER")
    return True
