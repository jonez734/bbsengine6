"""get_dsr() must not discard typed input that arrives around the cursor-position reply.

The bottom bar's {savecursor} sends ESC[6n and waits for the reply while the user may still
be typing. Keys read during that wait are typed input, so they go back on the input queue
in order. Keys already queued stay where they were.
"""

import importlib
import os
import pty
import threading
import time

import pytest

common = importlib.import_module("bbsengine6.io.common")


@pytest.fixture
def pty_input(monkeypatch):
    master, slave = pty.openpty()
    rs = os.fdopen(os.dup(slave), "r", buffering=1, encoding="utf-8")
    ws = os.fdopen(os.dup(slave), "w", buffering=1, encoding="utf-8")
    saved_in, saved_out = common._current_input_stream, common._current_output_stream
    common.set_input_stream(rs)
    common.set_output_stream(ws)
    queue = common._queue()
    saved_queue = list(queue)
    queue.clear()
    # Discard bytes left in the tty by an earlier test, so each test starts empty.
    import termios
    termios.tcflush(slave, termios.TCIFLUSH)
    yield master
    queue.clear()
    queue.extend(saved_queue)
    common.set_input_stream(saved_in)
    common.set_output_stream(saved_out)
    rs.close()
    ws.close()
    os.close(master)
    os.close(slave)


def _reply_after(master, pieces, delay=0.05):
    """Write `pieces` to the tty as if typed, then the cursor reply, from another thread.

    Returns the thread. The caller joins it, so no write lands after the test ends.
    """

    def run():
        for piece in pieces:
            time.sleep(delay)
            os.write(master, piece)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


@pytest.mark.unit
def test_keys_typed_around_the_reply_are_kept_in_order(pty_input):
    # "a" arrives before the reply, "b" after it. Neither may be dropped.
    writer = _reply_after(pty_input, [b"a", b"\x1b[3;7R", b"b"])
    row, col = common.get_cursor_position(timeout=2.0)
    assert (row, col) == (3, 7)
    # get_dsr returns at the reply. Keys typed after it are read by the next input call, so
    # check only what get_dsr itself kept: the key that arrived before the reply.
    writer.join(timeout=2.0)
    assert "".join(common._queue()) == "a"


@pytest.mark.unit
def test_queued_keys_stay_ahead_of_the_keys_read_with_the_reply(pty_input):
    common._queue().extend("x")
    _reply_after(pty_input, [b"y", b"\x1b[1;1R"])
    common.get_cursor_position(timeout=2.0)
    assert "".join(common._queue()) == "xy"


@pytest.mark.unit
def test_timeout_keeps_typed_keys(pty_input):
    # No reply arrives, only typing. The timeout must keep the keys, not discard them.
    _reply_after(pty_input, [b"k", b"e", b"y"])
    with pytest.raises(TimeoutError):
        common.get_cursor_position(timeout=0.5)
    assert "".join(common._queue()) == "key"
