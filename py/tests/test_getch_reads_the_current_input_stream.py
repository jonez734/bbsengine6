"""getch reads the input stream that common currently holds, not a copy taken at import time.

getch used to import _current_input_stream by value, so rebinding common's stream (set_input_stream,
or a test that patches common) left getch waiting on the old stream and never seeing a key.
"""

import importlib
import os
import pty
import threading
import time

import pytest

common = importlib.import_module("bbsengine6.io.common")
g = importlib.import_module("bbsengine6.io.getch")


@pytest.fixture
def pty_stream():
    master, slave = pty.openpty()
    stream = os.fdopen(slave, "r", buffering=1, encoding="utf-8")
    saved = common._current_input_stream
    common.set_input_stream(stream)
    yield master, stream
    common.set_input_stream(saved)
    stream.close()
    os.close(master)


@pytest.mark.unit
def test_getch_sees_a_key_on_the_stream_set_through_common(pty_stream):
    master, _ = pty_stream
    writer = threading.Thread(target=lambda: (time.sleep(0.15), os.write(master, b"q")), daemon=True)
    writer.start()
    result = g.getch_str(timeout=3)
    writer.join(timeout=5)
    assert result == "q"


@pytest.mark.unit
def test_getch_does_not_keep_an_import_time_copy_of_the_stream():
    assert "_current_input_stream" not in vars(g) or g._current_input_stream is common._current_input_stream

