#!/usr/bin/env python3
# ed.py
# Terminal-based visual editor

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Visual editor")
    parser.add_argument("filepath", nargs="?", help="File to edit (optional)")
    parser.add_argument(
        "--mode",
        choices=["visual", "line"],
        default="visual",
        help="Editor mode (default: visual)",
    )
    args = parser.parse_args()

    from bbsengine6 import ed

    class MockArgs:
        pass

    mock_args = MockArgs()
    mock_args.debug = False

    result = ed.run(mock_args, moniker="", mode=args.mode, filepath=args.filepath)

    if result is not None:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
