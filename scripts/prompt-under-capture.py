#!/usr/bin/env python3
"""One inputstring() prompt, for use under capture-session.sh.

Run from a checkout: the bbsengine6 source tree is found next to this script.
"""
import os, sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "py", "src")
sys.path.insert(0, os.path.abspath(SRC))
from bbsengine6.io.inputstring import inputstring  # noqa: E402

r = inputstring("> ", max_width=80)
print("GOT", repr(r), flush=True)
