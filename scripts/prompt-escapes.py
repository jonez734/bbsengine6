#!/usr/bin/env python3
"""List every escape sequence an inputstring() prompt writes to the terminal.

With every switch off (the default), the prompt writes only cursor moves; with --keep-*
it also writes the mouse queries and resets, bracketed paste, and the bottom-bar save.
Drag still failed with all switches off, so the writes are not the blocker.

Runs one prompt on a pseudo-terminal with the same switches as drag-bisect.py
(all disabled by default). A pty-attached emulator answers the cursor query and
mouse-mode queries; the prompt is then fed "ok" and Enter. Prints each distinct
escape sequence with its count, so any mode the prompt sets is visible.

Usage: python3 scripts/prompt-escapes.py [--keep-mouse] [--keep-paste] [--keep-raw] [--keep-bar]
"""
import collections
import importlib
import os
import pty
import re
import select
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "py", "src"))

common = importlib.import_module("bbsengine6.io.common")
ins = importlib.import_module("bbsengine6.io.inputstring")

args = set(sys.argv[1:])
if "--keep-mouse" not in args:
    common.MOUSE_STATE_MANAGED = False
if "--keep-paste" not in args:
    common.BRACKETED_PASTE_MANAGED = False
if "--keep-raw" not in args:
    ins.begin_raw_session = lambda: None
    ins.end_raw_session = lambda: None
if "--keep-bar" not in args:
    ins._show_mode = lambda *a, **k: None
    ins._hide_mode = lambda *a, **k: None

master, slave = pty.openpty()
rs = os.fdopen(os.dup(slave), "r", buffering=1, encoding="utf-8")
ws = os.fdopen(os.dup(slave), "w", buffering=1, encoding="utf-8")
common.set_input_stream(rs)
common.set_output_stream(ws)
ins.get_cursor_position = lambda timeout=1.0: (1, 1)

out = bytearray()
stop = threading.Event()


def terminal():
    while not stop.is_set():
        try:
            if select.select([master], [], [], 0.02)[0]:
                data = os.read(master, 65536)
                out.extend(data)
                for m in re.finditer(rb"\x1b\[\?(\d+)\$p", data):
                    os.write(master, f"\x1b[?{int(m.group(1))};2$y".encode())
                if b"\x1b[6n" in data:
                    os.write(master, b"\x1b[1;1R")
        except OSError:
            return


threading.Thread(target=terminal, daemon=True).start()


def feed():
    time.sleep(0.5)
    os.write(master, b"ok\r")


threading.Thread(target=feed, daemon=True).start()
result = ins.inputstring("> ")
time.sleep(0.2)
stop.set()

seqs = collections.Counter(m.group(0).decode("ascii", "replace")
                           for m in re.finditer(rb"\x1b[\[\]()78=>][0-9;?]*[A-Za-z$@~=>78]?", bytes(out)))
print("RESULT", repr(result))
print("switches kept:", sorted(args) or "none")
for seq, n in sorted(seqs.items(), key=lambda kv: -kv[1]):
    print(f"{n:5d}  {seq!r}")
