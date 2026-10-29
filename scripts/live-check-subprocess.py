#!/usr/bin/env python3
"""Live terminal check for subprocess commands (Phase 4).

Run this in a real terminal (gnome-terminal, xterm), not in a pipe or CI. It drives the
real code paths, one step at a time, and asks you what you saw after each step.

Steps:
  1. TERM refusal: with TERM=dumb the launcher must refuse and print a message.
  2. Child exit and redraw: run a short child that exits with status 3. Afterwards the
     bottom bar and the prompt must be redrawn, and the text you typed before the child
     must still be on the line.
  3. Full-screen child: run a full-screen program (default: worm) through the launcher.
     It must take the whole screen, and the shell screen must come back afterwards.

Usage:
    python3 scripts/live-check-subprocess.py [--program worm] [--log FILE]

Quitting: snake has no quit key; Ctrl-C ends it, and the launcher returns 130 (see
INTERRUPTED_STATUS). worm and atc also end on Ctrl-C. snake and robots need a
/var/games score file the opencode user cannot open here, so they exit at once with a
permission error; pick another program with --program.

Each answer is written to the log (default: captures/live-check-subprocess.log, in the
repo). Attach the log and, if useful, a capture from scripts/capture-session.sh.
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "py" / "src"))

from bbsengine6 import subprocess_command as sc  # noqa: E402
from bbsengine6 import screen  # noqa: E402
from bbsengine6.io.inputstring import inputstring  # noqa: E402


def _ask(question: str, log) -> bool:
    """Ask the operator a yes/no question, log the answer, and return it."""
    while True:
        answer = input(f"\n{question} [y/n/q] ").strip().lower()
        if answer in ("y", "n", "q"):
            break
    log.write(f"Q: {question}\nA: {answer}\n\n")
    log.flush()
    if answer == "q":
        raise SystemExit("stopped by operator")
    return answer == "y"


def _note(text: str, log) -> None:
    print(text)
    log.write(f"# {text}\n")
    log.flush()


def step_term_refusal(log) -> None:
    _note("Step 1: TERM refusal", log)
    saved = os.environ.get("TERM")
    os.environ["TERM"] = "dumb"
    try:
        sc.run_child(["sh", "-c", "echo SHOULD-NOT-RUN"], term=None)
        _note("launch was NOT refused", log)
        _ask("Did the launch run anyway? (should be n)", log)
    except sc.SubprocessCommandError as e:
        _note(f"refused as expected: {e}", log)
        _ask("Did the screen show a clear refusal message and stay usable?", log)
    finally:
        if saved is None:
            os.environ.pop("TERM", None)
        else:
            os.environ["TERM"] = saved


def step_child_exit_and_redraw(log) -> None:
    _note("Step 2: child exit and redraw", log)
    typed = inputstring("Type something, then press Enter: ")
    _note(f"typed before child: {typed!r}", log)
    screen.updatebottombar("live check: bottom bar")
    status = sc.run_child(
        ["sh", "-c", "printf 'child says hello\\n'; sleep 1; exit 3"],
        bottom_buf="live check: bottom bar",
    )
    _note(f"child exit status: {status}", log)
    _ask("Did the child's output appear, and then the screen clear for the shell?", log)
    # A real prompt after the child. Nothing reads input between the child and this
    # line, so this is the check that the shell can take input again.
    after = inputstring("Type a second line, then press Enter (new prompt after the child): ")
    _note(f"typed after child: {after!r}", log)
    _ask("Did the new prompt appear on a clean line, with the bottom bar on the last line?", log)
    _ask(f"Did the second prompt accept your typing and return {after!r}?", log)


def step_fullscreen(program: str, log) -> None:
    _note(f"Step 3: full-screen child: {program}", log)
    _ask(f"Ready? The program {program!r} will take the screen. Quit it normally.", log)
    status = sc.run_child([program], bottom_buf="live check: bottom bar")
    _note(f"{program} exit status: {status}", log)
    _ask(f"Did {program} take the whole screen?", log)
    # A real prompt after the program. Its line must be clean, with no game drawing left.
    after = inputstring("Type a line, then press Enter (prompt after the game): ")
    _note(f"typed after {program}: {after!r}", log)
    _ask("Is the screen free of leftover game drawing, with the prompt on a clean line?", log)
    _ask("Is the bottom bar drawn on the last line?", log)
    _ask(f"Did the prompt accept your typing and return {after!r}?", log)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--program", default="worm", help="full-screen program for step 3")
    ap.add_argument("--log", default=str(REPO / "captures" / "live-check-subprocess.log"))
    ap.add_argument("--skip", action="append", default=[], choices=["1", "2", "3"])
    args = ap.parse_args()

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("This check needs a real terminal (stdin and stdout must be a tty).")
        return 2

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as log:
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        log.write(f"== live check {stamp} TERM={os.environ.get('TERM')!r} "
                  f"size={os.get_terminal_size().columns}x{os.get_terminal_size().lines}\n")
        screen.init()
        try:
            if "1" not in args.skip:
                step_term_refusal(log)
            if "2" not in args.skip:
                step_child_exit_and_redraw(log)
            if "3" not in args.skip:
                step_fullscreen(args.program, log)
        except SystemExit as e:
            _note(str(e), log)
    print(f"\nLog written to {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
