import argparse

from bbsengine6 import util

from . import lib


def buildargs(args: argparse.Namespace, **kwargs) -> argparse.ArgumentParser | None:
    return lib.buildargs(args, **kwargs)


def init(args: argparse.Namespace, **kwargs) -> bool | None:
    return True


def access(args: argparse.Namespace, op: str, **kwargs) -> bool | None:
    return True


def main(args: argparse.Namespace, **kwargs) -> bool | None:
    util.heading("HEADER")
    return True
