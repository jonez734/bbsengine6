#!/usr/bin/env python3
# demo_ed.py
# Demo script to run the visual editor from the shell

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Demo line editor")
    parser.add_argument("filepath", nargs="?", help="File to edit (optional)")
    parser.add_argument(
        "--mode",
        choices=["visual", "line"],
        default="line",
        help="Editor mode (default: line)",
    )
    args = parser.parse_args()

    from bbsengine6 import ed

    class MockArgs:
        pass

    mock_args = MockArgs()
    mock_args.debug = False

    result = ed.run(mock_args, moniker="demo", mode=args.mode, filepath=args.filepath)

    if result is not None:
        print("\n--- Editor content ---\n")
        print(result)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
