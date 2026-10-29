"""A paste delivers several characters at once. inputstring() must insert them as
text: a tab must not start completion, a control byte must not move the cursor, and
a newline ends the entry like Enter.

Runs inputstring() on a pty with the whole paste written in one burst, before the
prompt reads, so the characters arrive together.
"""

import importlib
import os
import pty

import pytest

common = importlib.import_module("bbsengine6.io.common")
inp = importlib.import_module("bbsengine6.io.inputstring")


@pytest.fixture
def paste(monkeypatch):
    master, slave = pty.openpty()
    rs = os.fdopen(os.dup(slave), "r", buffering=1, encoding="utf-8")
    ws = os.fdopen(os.dup(slave), "w", buffering=1, encoding="utf-8")
    saved_in, saved_out = common._current_input_stream, common._current_output_stream
    common.set_input_stream(rs)
    common.set_output_stream(ws)
    monkeypatch.setattr(inp, "get_cursor_position", lambda timeout=1.0: (1, 1))

    def run(text: str, max_width: int = 200) -> str:
        os.write(master, text.encode())
        return inp.inputstring("> ", max_width=max_width)

    yield run
    common.set_input_stream(saved_in)
    common.set_output_stream(saved_out)
    rs.close()
    ws.close()
    os.close(master)
    os.close(slave)


def test_plain_paste_arrives_intact(paste):
    text = "The quick brown fox jumps over the lazy dog 0123456789"
    assert paste(text + "\r") == text


def test_paste_with_tab_keeps_following_text(paste):
    # A tab used to start completion and drop the rest of the paste.
    assert paste("a\tb\tc\r") == "a b c"


def test_paste_with_control_byte_is_dropped_not_run(paste):
    # \x01 is Ctrl-A (home). It must not move the cursor and reorder the text.
    assert paste("abc\x01def\r") == "abcdef"


def test_paste_utf8_intact(paste):
    text = "café naïve — ünïcödé ✓"
    assert paste(text + "\r") == text


def test_paste_respects_max_len(paste):
    # Longer than the field's max_width: truncated, not dropped mid-stream.
    assert paste("x" * 300 + "\r", max_width=255) == "x" * 255


def test_single_key_is_not_treated_as_paste(paste):
    # One character waiting is a keystroke, not a burst: the burst helper must
    # return None so the normal per-key path handles it.
    assert inp._take_paste_burst() is None
