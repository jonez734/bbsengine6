import argparse

import lib


def init(args: argparse.Namespace, **kwargs) -> bool | None:
    return True


def access(args: argparse.Namespace, op: str, **kwargs) -> bool | None:
    return True


def buildargs(args: argparse.Namespace = None, **kwargs) -> argparse.ArgumentParser | None:
    return None


def main(args: argparse.Namespace, **kwargs) -> bool | None:
    return lib.runmodule("main", **kwargs)
