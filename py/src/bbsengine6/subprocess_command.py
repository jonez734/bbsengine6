"""Run a full-screen program (a subprocess) as a command, then restore the shell's screen.

A subprocess command is a small module under the shell's command list. Its ``main()``
calls :func:`run_child`, so the command still goes through ``bbsengine6.module.run()``
and its ``access()`` check. The registry entry's ``spec`` names that module.

:func:`run_child` does three things:

1. Refuses to start when ``TERM`` cannot drive a full-screen program (unset, empty, or
   ``dumb``), unless the session turned ``subprocess_term_check`` off.
2. Leaves the shell's raw input session, so the child reads a cooked tty, and runs the
   child with ``subprocess.run``.
3. Afterwards, whatever happened, calls :func:`redraw_all`: the screen is reset, the
   scroll region and the bottom bar are drawn again, and the prompt redraws the line the
   user was typing.
"""

from __future__ import annotations

import os
import subprocess
from typing import Optional, Sequence

from .interaction import current_session

#: TERM values that cannot drive a full-screen program.
UNUSABLE_TERMS = ("", "dumb")


class SubprocessCommandError(Exception):
    """A subprocess command could not be started (for example, TERM is unusable)."""


def term_ok(term: Optional[str] = None) -> bool:
    """True if ``TERM`` (default: the environment's) can drive a full-screen program."""
    if term is None:
        term = os.environ.get("TERM", "")
    return term not in UNUSABLE_TERMS


def check_term(term: Optional[str] = None) -> None:
    """Raise SubprocessCommandError when the session's TERM check fails.

    Does nothing when the session has ``subprocess_term_check`` turned off.
    """
    if not current_session().subprocess_term_check:
        return
    if not term_ok(term):
        shown = os.environ.get("TERM", "") if term is None else term
        raise SubprocessCommandError(
            f"TERM is {shown!r}; a full-screen program needs a terminal type such as xterm"
        )


def redraw_all(bottom_buf: str = "") -> None:
    """Restore the shell's screen after a child program has used the terminal.

    Order matters: the screen is reset first, then the scroll region is set again (the
    child may have changed it), then the bottom bar is drawn. Finally the prompt line is
    marked dirty, so the next prompt read redraws the text the user had typed.

    ``bottom_buf`` is the left-hand text for the bottom bar (the shell passes its usual
    status). Nothing is drawn when there is no tty.
    """
    from . import screen
    from . import bottombar
    from .io import common
    from .io.echo import echo

    # Reset attributes and the cursor, then clear the screen the child left behind.
    echo("{/all}", end="", flush=True, raw=True)
    echo("\x1b[H\x1b[2J", end="", flush=True, raw=True)
    # Scroll region and bottom bar, as the shell sets them at start.
    bottombar.init()
    screen.updatebottombar(bottom_buf)
    # The prompt redraws on its next pass when the line is marked dirty.
    common._set_input_dirty(True)


def run_child(
    argv: Sequence[str],
    *,
    bottom_buf: str = "",
    term: Optional[str] = None,
    env: Optional[dict] = None,
) -> int:
    """Run ``argv`` on the terminal and return its exit status.

    Raises SubprocessCommandError (before anything runs) if the TERM check fails. Any
    other failure to start the program (missing binary) is raised as OSError after the
    screen has been restored.
    """
    check_term(term)

    from .io.common import end_raw_session

    # The child reads the tty itself, so leave the shell's raw session first. Nothing
    # needs restarting afterwards: the next prompt read starts its own raw session.
    end_raw_session()

    try:
        completed = subprocess.run(list(argv), env=env, check=False)
        return completed.returncode
    finally:
        redraw_all(bottom_buf)
