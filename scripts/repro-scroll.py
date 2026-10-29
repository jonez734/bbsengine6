#!/usr/bin/env python3
"""Drive a long paste into inputstring under capture-session.sh, then scroll left.

Answers the cursor-position query (ESC[6n) the way a terminal does, so the prompt
runs. Usage: repro_scroll.py [capture-session.sh path] [output dir]
"""
import os, sys, time, pexpect

HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "capture-session.sh")
OUT = sys.argv[2] if len(sys.argv) > 2 else "./captures"
PROMPT = os.environ.get("PROMPT_SCRIPT", os.path.join(HERE, "prompt-under-capture.py"))
TEXT = ("Ctrl-W and Ctrl-Y are confirmed working in your gnome-terminal. I recorded "
        "that in the sidebar and in the handbook (ba51c2c, local only, not pushed).")

child = pexpect.spawn(CAPTURE, ["-n", "scroll", "-o", OUT, "-c",
                                f"{sys.executable} {PROMPT}"],
                      encoding="utf-8", timeout=30, dimensions=(24, 80))

def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        try:
            chunk = child.read_nonblocking(4096, timeout=0.05)
        except pexpect.TIMEOUT:
            continue
        except pexpect.EOF:
            return
        if "\x1b[6n" in chunk:
            child.send("\x1b[1;1R")  # the cursor report a terminal sends

pump(1.0)
child.send("\x1b[200~" + TEXT + "\x1b[201~")   # bracketed paste
pump(0.8)
for _ in range(75):                             # left-arrow past the scroll edge
    child.send("\x1b[D")
    pump(0.05)
child.send("\r")
pump(2.0)
print("capture in", OUT)
