#!/usr/bin/env python3
"""Show, in order, every escape sequence and printable run a demo writes to the terminal.

Runs a bbsengine6 demo script on a pseudo-terminal and answers its terminal queries the way a
VT220-class terminal would (DA1, and the cursor and mode queries the engine sends). Each output
item is printed on its own line: an escape sequence in brackets, or a run of printable text in
quotes. Use it to find the bytes that come before a stray character on a terminal that cannot log.

Usage: python3 scripts/demo-escapes.py [demo_script.py] [--seconds N] [--term NAME] [--colorterm]
Default script: py/src/demo_box_inputstring.py, with TERM=xterm-256color (the default --term) and
COLORTERM unset, so the RGB query is sent. --colorterm sets COLORTERM=truecolor instead.
"""
import os
import pexpect
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT = os.path.join(ROOT, "py", "src", "demo_box_inputstring.py")

ESC_RE = re.compile(r"\x1b(?:\[[0-9;?>]*[ -/]*[@-~]|P[^\x1b]*\x1b\\|[()][0-9A-Za-z]|[78=>cDEHMNO]|\\)")


def classify(stream: str):
    """Split raw output into ("esc", seq) and ("text", run) items, in order."""
    items = []
    pos = 0
    for m in ESC_RE.finditer(stream):
        if m.start() > pos:
            items.append(("text", stream[pos:m.start()]))
        items.append(("esc", m.group(0)))
        pos = m.end()
    if pos < len(stream):
        items.append(("text", stream[pos:]))
    return items


def answer(child, data: str, state: dict) -> None:
    """Reply to the queries the engine sends, once each, as a VT220-class terminal."""
    if "\x1b[c" in data and not state.get("da1"):
        state["da1"] = True
        child.send("\x1b[?62;1;2c")
    if "\x1b[>c" in data and not state.get("da2"):
        state["da2"] = True
        child.send("\x1b[>1;2;0c")
    if "\x1b[6n" in data:
        child.send("\x1b[1;1R")
    if "\x1bP+q" in data and not state.get("rgb"):
        state["rgb"] = True  # no reply: a silent terminal, as the probe timeout expects


def main(argv):
    seconds = 8.0
    colorterm = False
    term = "xterm-256color"
    script = DEFAULT
    args = list(argv)
    if "--seconds" in args:
        i = args.index("--seconds")
        seconds = float(args[i + 1])
        del args[i:i + 2]
    if "--term" in args:
        i = args.index("--term")
        term = args[i + 1]
        del args[i:i + 2]
    if "--colorterm" in args:
        colorterm = True
        args.remove("--colorterm")
    if args:
        script = os.path.abspath(args[0])
    env = "COLORTERM=truecolor " if colorterm else "env -u COLORTERM "
    child = pexpect.spawn(
        "/bin/sh", ["-c", f"{env}TERM={term} {sys.executable} {script}"],
        cwd=os.path.dirname(script), timeout=seconds, encoding="utf-8", dimensions=(40, 120),
    )
    raw = ""
    state: dict = {}
    end = time.time() + seconds
    while time.time() < end:
        try:
            chunk = child.read_nonblocking(4096, timeout=0.3)
        except pexpect.TIMEOUT:
            continue
        except pexpect.EOF:
            break
        raw += chunk
        answer(child, chunk, state)
    child.close(force=True)
    for kind, value in classify(raw):
        if kind == "esc":
            print(f"[{value!r}]")
        else:
            print(f"{value!r}")


if __name__ == "__main__":
    main(sys.argv[1:])
