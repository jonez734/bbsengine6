import argparse

import lib


def init(args: argparse.Namespace, **kwargs) -> bool | None:
    return True


def access(args: argparse.Namespace, op: str, **kwargs) -> bool | None:
    return True


def buildargs(
    args: argparse.Namespace = None, **kwargs
) -> argparse.ArgumentParser | None:
    return None


def main(args: argparse.Namespace, **kwargs) -> bool | None:
    return lib.runmodule(args, "main", **kwargs)


# Module ABI Pattern:
# ==================
# __init__.py must have:
#   - init(args, **kwargs) -> bool
#   - access(args, op, **kwargs) -> bool
#   - buildargs(args, **kwargs) -> ArgumentParser | None
#   - main(args, **kwargs) -> bool
#
# main() delegates to lib.runmodule(args, "main", **kwargs)
#
# lib.py must have:
#   - PACKAGENAME = "packagename"
#   - runmodule(args, modulename, **kwargs) that calls
#     module.runmodule(args, f"{PACKAGENAME}.{modulename}", **kwargs)
