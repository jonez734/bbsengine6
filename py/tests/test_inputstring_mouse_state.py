"""inputstring() saves the terminal's mouse-reporting state, turns it off while
editing, and restores it on return, exception, and no-reply fallback.

A pty stands in for the terminal. A background thread plays the terminal:
it answers DECRQM queries (CSI ? mode $ p) and records every mode set/reset
(CSI ? mode h / l).
"""

import importlib
import os
import pty
import re
import threading
import time

import pytest

common = importlib.import_module("bbsengine6.io.common")
inp = importlib.import_module("bbsengine6.io.inputstring")

QUERY_RE = re.compile(rb"\x1b\[\?(\d+)\$p")
SET_RE = re.compile(rb"\x1b\[\?(\d+)([hl])")


class FakeTerminal:
    """Answers DECRQM from `modes` and records set/reset writes."""

    def __init__(self, master, modes, answer_queries=True):
        self.master = master
        self.modes = dict(modes)  # mode -> bool, current terminal state
        self.answer_queries = answer_queries
        self.log = []  # ("set"|"reset", mode)
        self._stop = threading.Event()
        self._buf = b""
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)

    def _run(self):
        while not self._stop.is_set():
            try:
                os.set_blocking(self.master, False)
                chunk = os.read(self.master, 4096)
            except (BlockingIOError, OSError):
                time.sleep(0.01)
                continue
            if not chunk:
                time.sleep(0.01)
                continue
            self._buf += chunk
            # Consume each request exactly once: answer queries and record set/reset
            # writes in stream order, then drop the bytes that were handled.
            pos = 0
            pattern = re.compile(rb"\x1b\[\?(\d+)(\$p|[hl])")
            for m in pattern.finditer(self._buf):
                pos = m.end()
                mode = int(m.group(1))
                if m.group(2) == b"$p":
                    if self.answer_queries and mode in self.modes:
                        status = 1 if self.modes[mode] else 2
                        os.write(self.master, f"\x1b[?{mode};{status}$y".encode())
                else:
                    self.modes[mode] = m.group(2) == b"h"
                    self.log.append(("set" if m.group(2) == b"h" else "reset", mode))
            # Keep only an unfinished tail (an incomplete request) for the next read.
            self._buf = self._buf[pos:] if pos else self._buf
            if len(self._buf) > 64:
                self._buf = self._buf[-64:]


MOUSE_MODES_SET = (1000, 1002, 1003, 1006)


def mouse_log(fake):
    """The fake terminal's log, restricted to mouse-reporting modes.

    Bracketed paste (2004) is written by the same prompt but is not mouse state,
    so it is excluded here.
    """
    return [(action, mode) for action, mode in fake.log if mode in MOUSE_MODES_SET]


@pytest.fixture
def terminal(monkeypatch):
    master, slave = pty.openpty()
    stream = os.fdopen(slave, "r", buffering=1, encoding="utf-8")
    saved_stream = common._current_input_stream
    saved_out = common._current_output_stream
    # Writes (mouse modes, redraws) must reach the same pty the fake reads.
    out = os.fdopen(os.dup(slave), "w", buffering=1, encoding="utf-8")
    common.set_input_stream(stream)
    common.set_output_stream(out)
    # A pty has no terminal emulator to answer the cursor-position query.
    monkeypatch.setattr(inp, "get_cursor_position", lambda timeout=1.0: (1, 1))
    saved_flag = common.MOUSE_STATE_MANAGED
    common.MOUSE_STATE_MANAGED = True
    holder = {}

    def make(modes, answer_queries=True):
        fake = FakeTerminal(master, modes, answer_queries=answer_queries)
        fake.start()
        holder["fake"] = fake
        return fake

    yield make
    if "fake" in holder:
        holder["fake"].stop()
    common.MOUSE_STATE_MANAGED = saved_flag
    common.set_input_stream(saved_stream)
    common.set_output_stream(saved_out)
    out.close()
    stream.close()
    os.close(master)


def _feed(master, data: bytes):
    os.write(master, data)


def test_mouse_modes_off_during_input_and_restored_on_return(terminal):
    fake = terminal({1000: True, 1002: True, 1003: False, 1006: True})
    master = fake.master
    threading.Timer(0.3, _feed, args=(master, b"ok\r")).start()
    result = inp.inputstring("> ")
    time.sleep(0.2)
    assert result == "ok"
    # Turned off on entry, then the saved state restored on exit.
    assert ("reset", 1000) in fake.log
    assert ("reset", 1006) in fake.log
    # Modes reported on are restored on. A mode reported off is never touched.
    final = {}
    for action, mode in fake.log:
        final[mode] = action == "set"
    assert final[1000] is True
    assert final[1002] is True
    assert final[1006] is True
    assert 1003 not in [m for _, m in fake.log], "a mode that was off must not be written"


def test_mouse_state_restored_when_body_raises(terminal):
    fake = terminal({1000: True, 1002: False, 1003: False, 1006: False})

    def boom(*a, **k):
        raise RuntimeError("simulated failure")

    # Force the body to fail after the push, with no keys needed.
    orig = inp._inputstring_body
    inp._inputstring_body = boom
    try:
        with pytest.raises(RuntimeError):
            inp.inputstring("> ")
    finally:
        inp._inputstring_body = orig
    time.sleep(0.2)
    final = {}
    for action, mode in fake.log:
        final[mode] = action == "set"
    assert final.get(1000) is True, "mouse 1000 must be restored after an exception"


def test_missing_decrqm_reply_leaves_modes_untouched(terminal):
    # No DECRQM answers means the terminal's state is unknown. The prompt must not
    # switch any mouse mode on or off, or it could disable tracking in a tab that
    # had it enabled.
    fake = terminal({1000: True, 1002: True, 1003: True, 1006: True}, answer_queries=False)
    master = fake.master
    threading.Timer(0.3, _feed, args=(master, b"x\r")).start()
    result = inp.inputstring("> ")
    time.sleep(0.2)
    assert result == "x"
    assert mouse_log(fake) == [], "unknown mouse state must not be written"


def test_reported_on_mode_is_reset_then_restored(terminal):
    # Mode 1000 is reported on: it is reset for the prompt and set back on exit.
    fake = terminal({1000: True, 1002: False, 1003: False, 1006: False})
    master = fake.master
    threading.Timer(0.3, _feed, args=(master, b"y\r")).start()
    result = inp.inputstring("> ")
    time.sleep(0.2)
    assert result == "y"
    assert mouse_log(fake) == [("reset", 1000), ("set", 1000)], fake.log


def test_managed_flag_false_leaves_mouse_alone(terminal):
    fake = terminal({1000: True, 1002: True, 1003: True, 1006: True})
    common.MOUSE_STATE_MANAGED = False
    master = fake.master
    threading.Timer(0.3, _feed, args=(master, b"y\r")).start()
    inp.inputstring("> ")
    time.sleep(0.2)
    assert mouse_log(fake) == [], "with the flag off, no mouse modes may be written"
