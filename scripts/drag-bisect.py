"""Run one inputstring() prompt with selected parts of its terminal setup disabled.

Usage: python3 scripts/drag-bisect.py [--no-mouse] [--no-paste] [--no-raw] [--no-bar]
Run from bbsengine6/py/src (or with bbsengine6 installed). Type text, press Enter.
While the prompt waits, try a button-1 drag, then note whether it selected.
"""
import importlib
import sys

common = importlib.import_module("bbsengine6.io.common")
ins = importlib.import_module("bbsengine6.io.inputstring")

args = set(sys.argv[1:])
if "--no-mouse" in args:
    common.MOUSE_STATE_MANAGED = False
if "--no-paste" in args:
    common.BRACKETED_PASTE_MANAGED = False
if "--no-raw" in args:
    ins.begin_raw_session = lambda: None
    ins.end_raw_session = lambda: None
if "--no-bar" in args:
    ins._show_mode = lambda *a, **k: None
    ins._hide_mode = lambda *a, **k: None

print("disabled:", sorted(args) or "none", flush=True)
print("RESULT", repr(ins.inputstring("> ")), flush=True)
