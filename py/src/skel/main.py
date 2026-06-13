from bbsengine6 import util

# from . import lib


def init(args, **kwargs) -> bool:
    return True


def access(args, op: str, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    #    return lib.buildargs(args, **kw)
    return None


def main(args, **kwargs):
    util.heading("HEADER")
    return True
