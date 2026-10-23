"""A key that arrives while getch_str runs its pre-wait notification check is not lost.

The notification check can be slow (a database read). If the tty is still in cooked mode during the
check, a key sent in that window waits in the line buffer until a newline, and getch_str times out
with None. The tty must be raw before the check, so the key is available to the wait.
"""

import importlib
import os
import pty
import threading
import time
from unittest.mock import patch

import pytest

common = importlib.import_module("bbsengine6.io.common")
g = importlib.import_module("bbsengine6.io.getch")


@pytest.fixture
def pty_stream():
    master, slave = pty.openpty()
    stream = os.fdopen(slave, "r", buffering=1, encoding="utf-8")
    saved = common._current_input_stream
    common.set_input_stream(stream)
    yield master
    common.set_input_stream(saved)
    stream.close()
    os.close(master)


@pytest.mark.unit
def test_key_sent_during_a_slow_precheck_is_returned(pty_stream):
    master = pty_stream

    def slow_check(*a, **k):
        time.sleep(0.5)
        return (False, 0)

    writer = threading.Thread(target=lambda: (time.sleep(0.2), os.write(master, b"a")), daemon=True)
    with patch.object(g, "_check_notifications", side_effect=slow_check), \
         patch.object(g, "_threadlocal") as tl:
        tl.moniker = "bob"
        writer.start()
        result = g.getch_str(timeout=2)
    writer.join(timeout=5)
    assert result == "a"
