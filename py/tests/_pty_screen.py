"""Drive a bbsengine6 program on a real pty and read the screen with a terminal emulator.

Tests use this instead of matching raw escape bytes. The program's output is fed into
``pyte`` (a VT100 screen model), and tests assert on what is on screen and where the cursor
is, which is what a user sees.

The harness answers the cursor-position query (``ESC[6n``) the way a terminal does, so
prompts that wait for it do not time out.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Optional

import pexpect
import pyte

ROWS = 24
COLS = 80
PREFIX = "import sys; sys.path.insert(0, 'src')\n"


class Screen:
    """A program running on a pty, with its output modelled on a pyte screen."""

    def __init__(self, body: str, *, rows: int = ROWS, cols: int = COLS, timeout: float = 15.0):
        self.rows = rows
        self.cols = cols
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.ByteStream(self.screen)
        self.raw = bytearray()
        code = PREFIX + body
        self.child = pexpect.spawn(
            sys.executable,
            ["-c", code],
            timeout=timeout,
            env={**os.environ, "TERM": "xterm"},
            dimensions=(rows, cols),
        )

    # ---- reading -----------------------------------------------------------

    def pump(self, seconds: float = 0.2) -> None:
        """Read whatever the program writes for ``seconds``, answering cursor queries."""
        end = time.time() + seconds
        while time.time() < end:
            try:
                chunk = self.child.read_nonblocking(4096, timeout=0.05)
            except pexpect.TIMEOUT:
                continue
            except pexpect.EOF:
                return
            self.raw.extend(chunk)
            self.stream.feed(chunk)
            for _ in range(chunk.count(b"\x1b[6n")):
                self.child.send(b"\x1b[1;1R")

    def wait_for(self, text: str, seconds: float = 5.0) -> bool:
        """Pump until ``text`` is on screen (any row) or ``seconds`` pass."""
        end = time.time() + seconds
        while time.time() < end:
            if self.find(text) is not None:
                return True
            self.pump(0.05)
        return self.find(text) is not None

    def wait_for_raw(self, marker: bytes, seconds: float = 5.0) -> bool:
        """Pump until ``marker`` appears in the raw output (for things not drawn on screen)."""
        end = time.time() + seconds
        while time.time() < end:
            if marker in self.raw:
                return True
            self.pump(0.05)
        return marker in self.raw

    def wait_exit(self, seconds: float = 10.0) -> None:
        """Pump until the program exits."""
        end = time.time() + seconds
        while time.time() < end:
            if not self.child.isalive():
                self.pump(0.2)
                return
            self.pump(0.1)
        raise AssertionError("program did not exit; screen:\n" + self.text())

    # ---- writing -----------------------------------------------------------

    def type(self, data: str | bytes, pause: float = 0.05) -> None:
        """Send keys. A short pause between keys avoids the dropped-key gap after a child."""
        if isinstance(data, str):
            data = data.encode()
        self.child.send(data)
        self.pump(pause)

    def key(self, sequence: str | bytes, pause: float = 0.15) -> None:
        """Send one key or escape sequence, then let the program handle it."""
        self.type(sequence, pause=pause)

    # ---- reading the screen ------------------------------------------------

    def rows_text(self) -> list[str]:
        return [line.rstrip() for line in self.screen.display]

    def text(self) -> str:
        return "\n".join(f"{i + 1:2}|{r}" for i, r in enumerate(self.rows_text()) if r)

    def find(self, text: str) -> Optional[int]:
        """Row index (0-based) of the first row containing ``text``, or None."""
        for i, row in enumerate(self.rows_text()):
            if text in row:
                return i
        return None

    def row(self, index: int) -> str:
        return self.rows_text()[index]

    def cursor(self) -> tuple[int, int]:
        """Cursor position as (row, column), both 0-based."""
        return self.screen.cursor.y, self.screen.cursor.x

    def result(self, name: str = "RESULT") -> Optional[str]:
        """The repr of the value the program printed as ``RESULT=...``, or None."""
        import re

        m = re.search(rf"{name}=(.*)", self.raw.decode("utf-8", "replace"))
        return m.group(1).strip() if m else None

    def close(self) -> None:
        self.child.close(force=True)


def make_prompt_program(prompt: str = "name: ", *, prefix_code: str = "") -> str:
    """Program body: one inputstring prompt, then print its value as RESULT=..."""
    return (
        "from bbsengine6.io.inputstring import inputstring\n"
        f"{prefix_code}"
        f"v = inputstring({prompt!r})\n"
        "sys.stdout.write('\\nRESULT=%r\\n' % v); sys.stdout.flush()\n"
    )


