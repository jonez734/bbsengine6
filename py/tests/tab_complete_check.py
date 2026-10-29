#!/usr/bin/env python3
"""Run tab-completion checks for bbsengine6.io.inputstring.

Automated mode (default) drives inputstring() on a pseudo-terminal and checks
the result of each case:

    python3 tests/tab_complete_check.py

Interactive mode runs one prompt in the current terminal (for example your
gnome-terminal tab). Press Tab to complete; Enter prints what was entered:

    python3 tests/tab_complete_check.py --interactive

Exit status is 0 when every automated case passes, 1 otherwise.
"""

import os
import pty
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, SRC)

import importlib  # noqa: E402

common = importlib.import_module("bbsengine6.io.common")
inp_mod = importlib.import_module("bbsengine6.io.inputstring")

inputstring = inp_mod.inputstring

WORDS = ["apple", "apricot", "banana", "blueberry", "cherry"]


def completer(buffer, curpos=0, **kwargs):
    """Return words starting with the text before the cursor (empty = all)."""
    return [w for w in WORDS if w.startswith(buffer)]


# (name, keystrokes written in order, expected result, extra kwargs)
CASES = [
    (
        "unambiguous prefix completes",
        [b"ban", b"\t", b"\r"],
        "banana",
        {},
    ),
    (
        "ambiguous prefix stays as typed",
        [b"ap", b"\t", b"\r"],
        "ap",
        {},
    ),
    (
        "no match leaves text unchanged",
        [b"zz", b"\t", b"\r"],
        "zz",
        {},
    ),
    (
        "completion then more typing",
        [b"ban", b"\t", b"!", b"\r"],
        "banana!",
        {},
    ),
    (
        "backspace after completion",
        [b"ban", b"\t", b"\x7f", b"\r"],
        "banan",
        {},
    ),
    (
        "tab mid-line completes the word under the cursor",
        [b"cher", b"\t", b"\r"],
        "cherry",
        {},
    ),
    (
        "typed Tab does not insert a tab character",
        [b"blu", b"\t", b"\r"],
        "blueberry",
        {},
    ),
    (
        "second word completes",
        [b"hello ban", b"\t", b"\r"],
        "hello banana",
        {},
    ),
    (
        "second word mid-line completes the word under the cursor",
        [b"hello cher", b"\t", b"\r"],
        "hello cherry",
        {},
    ),
    (
        "second word ambiguous stays as typed",
        [b"hello ap", b"\t", b"\r"],
        "hello ap",
        {},
    ),
    (
        "empty input: double Tab lists all completions (result unchanged)",
        [b"\t", b"\t", b"\r"],
        "",
        {},
    ),
    (
        "no completer: Tab is ignored",
        [b"ban", b"\t", b"\r"],
        "ban",
        {"completer": None},
    ),
]


def run_case(keystrokes, extra, delay=0.25):
    """Feed keystrokes to inputstring() on a fresh pty; return its result."""
    master, slave = pty.openpty()
    rs = os.fdopen(os.dup(slave), "r", buffering=1, encoding="utf-8")
    ws = os.fdopen(os.dup(slave), "w", buffering=1, encoding="utf-8")
    saved_in = common._current_input_stream
    saved_out = common._current_output_stream
    common.set_input_stream(rs)
    common.set_output_stream(ws)
    saved_pos = inp_mod.get_cursor_position
    inp_mod.get_cursor_position = lambda timeout=1.0: (1, 1)
    try:
        def feed():
            for piece in keystrokes:
                time.sleep(delay)
                os.write(master, piece)

        threading.Thread(target=feed, daemon=True).start()
        kwargs = {"completer": completer}
        kwargs.update(extra)
        return inputstring("> ", **kwargs)
    finally:
        inp_mod.get_cursor_position = saved_pos
        common.set_input_stream(saved_in)
        common.set_output_stream(saved_out)
        rs.close()
        ws.close()
        os.close(master)
        os.close(slave)


def run_automated():
    failures = 0
    for name, keys, expected, extra in CASES:
        try:
            got = run_case(keys, extra)
        except Exception as exc:  # report and keep going
            got = f"<error: {exc!r}>"
        ok = got == expected
        failures += 0 if ok else 1
        status = "PASS" if ok else "FAIL"
        print(f"{status}  {name}")
        if not ok:
            print(f"      expected {expected!r}")
            print(f"      got      {got!r}")
    total = len(CASES)
    print(f"\n{total - failures}/{total} passed")
    return 0 if failures == 0 else 1


def run_interactive():
    print("Tab completion, interactive.")
    print("Words: " + ", ".join(WORDS))
    print("Type a prefix and press Tab. Enter finishes. Ctrl-C quits.\n")
    while True:
        try:
            result = inputstring("complete> ", completer=completer)
        except KeyboardInterrupt:
            print()
            return 0
        print(f"you entered: {result!r}\n")


def main(argv):
    if "--interactive" in argv:
        return run_interactive()
    return run_automated()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
