#!/usr/bin/env python3
"""bbsengine6 inputstring / getch / tab-completion checks.

Runs on a pseudo-terminal, so it needs NO real terminal and NO database.
Each check feeds keystrokes to inputstring() and compares the result.

REQUIREMENTS
  * Python 3.10 or newer, on Linux or another POSIX system (uses ptys and termios).
  * The bbsengine6 package, either:
      - installed in the active environment (e.g. pip install -e .), or
      - present as a source tree: pass --src PATH (the directory that CONTAINS
        the "bbsengine6" package, e.g. .../bbsengine6/py/src).
  * pytest, only for --pytest mode. The default mode needs nothing beyond
    the standard library and bbsengine6.
  * Not needed: a display, gnome-terminal, ssh, PostgreSQL. Tests that need
    a database are not part of this script.

USAGE
  python3 run_inputstring_tests.py                      # all checks, uses installed bbsengine6
  python3 run_inputstring_tests.py --src /path/to/src   # use a source checkout
  python3 run_inputstring_tests.py --only tab           # one group: tab | noneok | allowed | filter | paste | mouse
  python3 run_inputstring_tests.py --pytest --src ...   # run as pytest (needs pytest)
  python3 run_inputstring_tests.py --interactive        # manual prompt in THIS terminal

EXIT STATUS
  0 = every check passed; 1 = at least one failed; 2 = bbsengine6 could not be imported.

Each FAIL line prints the expected and actual result so the failure is visible.
"""

from __future__ import annotations

import argparse
import importlib
import os
import pty
import sys
import threading
import time

# --------------------------------------------------------------------------
# Locate and import bbsengine6
# --------------------------------------------------------------------------


def _import_bbsengine6(src: str | None):
    """Import bbsengine6.io and report which copy was used.

    With --src, the directory must exist and must contain the bbsengine6 package;
    otherwise an installed copy could be tested by mistake.
    """
    if src:
        src = os.path.abspath(src)
        if not os.path.isfile(os.path.join(src, "bbsengine6", "__init__.py")):
            print(
                f"ERROR: --src {src} does not contain a 'bbsengine6' package directory.\n"
                "Give the directory that CONTAINS bbsengine6, e.g. .../bbsengine6/py/src",
                file=sys.stderr,
            )
            sys.exit(2)
        sys.path.insert(0, src)
    try:
        common = importlib.import_module("bbsengine6.io.common")
        inp = importlib.import_module("bbsengine6.io.inputstring")
        ii = importlib.import_module("bbsengine6.io.inputinteger")
    except Exception as exc:  # report clearly; do not hide the cause
        print("ERROR: cannot import bbsengine6.io:", repr(exc), file=sys.stderr)
        print(
            "Install bbsengine6 in this environment, or pass --src PATH where PATH\n"
            "contains the 'bbsengine6' package directory.",
            file=sys.stderr,
        )
        sys.exit(2)
    where = os.path.dirname(os.path.dirname(os.path.abspath(inp.__file__)))
    print(f"Testing bbsengine6 from: {where}")
    return common, inp, ii


WORDS = ["apple", "apricot", "banana", "blueberry", "cherry"]


def completer(word, curpos=0, **kwargs):
    """Test completer: words starting with the word under the cursor."""
    return [w for w in WORDS if w.startswith(word)]


# --------------------------------------------------------------------------
# Pty harness
# --------------------------------------------------------------------------


class Term:
    """Runs inputstring() on a fresh pty and writes keystrokes to it."""

    def __init__(self, common, inp):
        self.common = common
        self.inp = inp

    def run(self, writes, call, delay=0.25):
        master, slave = pty.openpty()
        rs = os.fdopen(os.dup(slave), "r", buffering=1, encoding="utf-8")
        ws = os.fdopen(os.dup(slave), "w", buffering=1, encoding="utf-8")
        saved_in = self.common._current_input_stream
        saved_out = self.common._current_output_stream
        saved_pos = self.inp.get_cursor_position
        self.common.set_input_stream(rs)
        self.common.set_output_stream(ws)
        # A pty has no terminal emulator to answer the cursor-position query.
        self.inp.get_cursor_position = lambda timeout=1.0: (1, 1)
        try:
            def feed():
                for piece in writes:
                    time.sleep(delay)
                    os.write(master, piece)

            threading.Thread(target=feed, daemon=True).start()
            return call()
        finally:
            self.inp.get_cursor_position = saved_pos
            self.common.set_input_stream(saved_in)
            self.common.set_output_stream(saved_out)
            rs.close()
            ws.close()
            os.close(master)
            os.close(slave)


# --------------------------------------------------------------------------
# Checks: (group, name, keystrokes, call-factory, expected)
# call-factory receives (inp, ii) and returns a zero-argument callable.
# --------------------------------------------------------------------------


def checks(inp, ii):
    tc = {"completer": completer}
    return [
        # --- tab completion
        ("tab", "unambiguous prefix completes",
         [b"ban", b"\t", b"\r"], lambda: inp.inputstring("> ", **tc), "banana"),
        ("tab", "ambiguous prefix stays as typed",
         [b"ap", b"\t", b"\r"], lambda: inp.inputstring("> ", **tc), "ap"),
        ("tab", "no match leaves text unchanged",
         [b"zz", b"\t", b"\r"], lambda: inp.inputstring("> ", **tc), "zz"),
        ("tab", "completion then more typing",
         [b"ban", b"\t", b"!", b"\r"], lambda: inp.inputstring("> ", **tc), "banana!"),
        ("tab", "backspace after completion",
         [b"ban", b"\t", b"\x7f", b"\r"], lambda: inp.inputstring("> ", **tc), "banan"),
        ("tab", "second word completes",
         [b"hello ban", b"\t", b"\r"], lambda: inp.inputstring("> ", **tc), "hello banana"),
        ("tab", "second word mid-line",
         [b"hello cher", b"\t", b"\r"], lambda: inp.inputstring("> ", **tc), "hello cherry"),
        ("tab", "empty input: Tab Tab leaves text empty",
         [b"\t", b"\t", b"\r"], lambda: inp.inputstring("> ", **tc), ""),
        ("tab", "no completer: Tab is ignored",
         [b"ban", b"\t", b"\r"], lambda: inp.inputstring("> "), "ban"),
        # --- noneok
        ("noneok", "default accepts empty Enter",
         [b"\r"], lambda: inp.inputstring("> "), ""),
        ("noneok", "noneok=False reprompts, then accepts text",
         [b"\r", b"ab\r"], lambda: inp.inputstring("> ", noneok=False), "ab"),
        # --- allowed
        ("allowed", "typed: disallowed letters dropped",
         [b"1", b"x", b"2", b"y", b"3", b"\r"],
         lambda: inp.inputstring("> ", allowed="0123456789"), "123"),
        ("allowed", "pasted: disallowed letters dropped",
         [b"a1b2c3\r"], lambda: inp.inputstring("> ", allowed="0123456789"), "123"),
        ("allowed", "allowed=None accepts everything",
         [b"a1-", b"\r"], lambda: inp.inputstring("> "), "a1-"),
        # --- filter
        ("filter", "rejects on Enter, accepts after fix",
         [b"-", b"\r", b"\x7f", b"5", b"\r"],
         lambda: inp.inputstring("> ", filter=r"^-?\d+$"), "5"),
        ("filter", "accepts a matching value",
         [b"-12", b"\r"], lambda: inp.inputstring("> ", filter=r"^-?\d+$"), "-12"),
        ("filter", "partial value typeable (checked on Enter only)",
         [b"-", b"1", b"\r"], lambda: inp.inputstring("> ", filter=r"^-?\d+$"), "-1"),
        # --- inputinteger uses allowed + filter
        ("filter", "inputinteger drops letters",
         [b"4", b"a", b"2", b"b", b"\r"], lambda: ii.inputinteger("n> "), 42),
        ("filter", "inputinteger rejects 007, then accepts 42",
         [b"007", b"\r", b"\x7f", b"\x7f", b"\x7f", b"42", b"\r"],
         lambda: ii.inputinteger("n> "), 42),
        # --- paste
        ("paste", "plain paste arrives intact",
         [b"The quick brown fox 0123456789\r"], lambda: inp.inputstring("> "),
         "The quick brown fox 0123456789"),
        ("paste", "tab in paste becomes a space",
         [b"a\tb\tc\r"], lambda: inp.inputstring("> ", completer=None), "a b c"),
        ("paste", "tab in paste kept with insert_tabs=True",
         [b"a\tb\r"], lambda: inp.inputstring("> ", insert_tabs=True), "a\tb"),
        ("paste", "control byte dropped from paste",
         [b"abc\x01def\r"], lambda: inp.inputstring("> ", completer=None), "abcdef"),
        ("paste", "UTF-8 paste intact",
         ["café naïve ✓\r".encode()], lambda: inp.inputstring("> "), "café naïve ✓"),
        ("paste", "paste longer than max_width is truncated at max_len",
         [b"x" * 300 + b"\r"], lambda: inp.inputstring("> ", max_width=400, max_len=255),
         "x" * 255),
    ]


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------


def run_checks(common, inp, ii, only: str | None, delay: float) -> int:
    term = Term(common, inp)
    failures = 0
    total = 0
    for group, name, keys, call, expected in checks(inp, ii):
        if only and group != only:
            continue
        total += 1
        try:
            got = term.run(keys, call, delay=delay)
        except Exception as exc:
            got = f"<exception: {exc!r}>"
        ok = got == expected
        if not ok:
            failures += 1
        print(f"{'PASS' if ok else 'FAIL'}  [{group}] {name}")
        if not ok:
            print(f"        expected: {expected!r}")
            print(f"        got:      {got!r}")
    print(f"\n{total - failures}/{total} passed")
    return 0 if failures == 0 else 1


def run_interactive(inp) -> int:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("ERROR: --interactive needs a terminal: run it directly in a terminal tab,",
              "not with input redirected or piped.", file=sys.stderr)
        return 2
    print("Interactive check, in THIS terminal.")
    print("Try: a word then Tab (completion), Tab Tab on an empty line (lists all),")
    print("Enter on an empty line with noneok=False (reprompts), typing letters with")
    print("allowed='0123456789' (dropped), and a paste (Ctrl-Shift-V).")
    print("Ctrl-C quits.\n")
    while True:
        try:
            r = inp.inputstring(
                "try> ",
                completer=completer,
                noneok=False,
                allowed=None,
            )
        except KeyboardInterrupt:
            print()
            return 0
        print(f"you entered: {r!r}\n")


# Pytest imports this file as its own module, separate from the one that runs
# main(). Shared state therefore lives on the module the test is collected from:
# run_pytest() sets the environment variables below, and the collected module
# reads them to build its cases. This needs no import-time state.
_ENV_SRC = "BBSENGINE6_CHECK_SRC"
_ENV_ONLY = "BBSENGINE6_CHECK_ONLY"


def _pytest_cases():
    src = os.environ.get(_ENV_SRC) or None
    only = os.environ.get(_ENV_ONLY) or None
    common, inp, ii = _import_bbsengine6(src)
    return common, inp, ii, [c for c in checks(inp, ii) if not only or c[0] == only]


def pytest_generate_tests(metafunc):
    if "group" in metafunc.fixturenames:
        _, _, _, cases = _pytest_cases()
        metafunc.parametrize(
            "group,name,keys,call,expected",
            cases,
            ids=[f"{g}:{n}" for g, n, *_ in cases],
        )


def test_check(group, name, keys, call, expected):
    """One bbsengine6 check; the parameters come from pytest_generate_tests."""
    common, inp, _, _ = _pytest_cases()
    assert Term(common, inp).run(keys, call) == expected


def run_pytest(src: str | None, only: str | None) -> int:
    """Run the same checks as pytest tests (one test per check)."""
    try:
        import pytest
    except ImportError:
        print("ERROR: --pytest needs pytest installed in this environment.", file=sys.stderr)
        return 2
    _import_bbsengine6(src)  # fail early with a clear message
    if src:
        os.environ[_ENV_SRC] = os.path.abspath(src)
    if only:
        os.environ[_ENV_ONLY] = only
    return int(pytest.main(["-q", "-p", "no:cacheprovider", os.path.abspath(__file__)]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="bbsengine6 inputstring/getch/tab checks on a pseudo-terminal.",
        epilog="See the docstring at the top of this file for requirements.",
    )
    ap.add_argument("--src", metavar="PATH",
                    help="directory that CONTAINS the bbsengine6 package (source checkout)")
    ap.add_argument("--only", metavar="GROUP",
                    choices=["tab", "noneok", "allowed", "filter", "paste"],
                    help="run one group of checks")
    ap.add_argument("--delay", type=float, default=0.25,
                    help="seconds between keystrokes (default 0.25; raise on a slow machine)")
    ap.add_argument("--pytest", action="store_true", help="run through pytest instead")
    ap.add_argument("--interactive", action="store_true",
                    help="open one prompt in this terminal for manual checks")
    args = ap.parse_args(argv)

    if args.pytest:
        return run_pytest(args.src, args.only)

    common, inp, ii = _import_bbsengine6(args.src)
    if args.interactive:
        return run_interactive(inp)
    return run_checks(common, inp, ii, args.only, args.delay)


if __name__ == "__main__":
    sys.exit(main())
