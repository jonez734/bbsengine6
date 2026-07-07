__all__ = ["init", "access", "buildargs", "main"]

from . import lib


def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return True


def buildargs(args=None, **kwargs):
    return None


def main(args, **kwargs):
    lib.runmodule(args, "main")
