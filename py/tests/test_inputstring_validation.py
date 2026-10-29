"""inputstring() input rules: noneok (empty Enter), allowed (characters accepted
while typing and pasting), and filter (whole-buffer regex checked on Enter).
Each case runs on a pty; the keys are written with small delays so each one is
read on its own, as typing is.
"""

import importlib
import os
import pty
import threading
import time

import pytest

common = importlib.import_module("bbsengine6.io.common")
inp = importlib.import_module("bbsengine6.io.inputstring")
ii = importlib.import_module("bbsengine6.io.inputinteger")


@pytest.fixture
def term(monkeypatch):
    master, slave = pty.openpty()
    rs = os.fdopen(os.dup(slave), "r", buffering=1, encoding="utf-8")
    ws = os.fdopen(os.dup(slave), "w", buffering=1, encoding="utf-8")
    saved_in, saved_out = common._current_input_stream, common._current_output_stream
    common.set_input_stream(rs)
    common.set_output_stream(ws)
    monkeypatch.setattr(inp, "get_cursor_position", lambda timeout=1.0: (1, 1))

    def run(writes, call, delay=0.25):
        def feed():
            for piece in writes:
                time.sleep(delay)
                os.write(master, piece)
        threading.Thread(target=feed, daemon=True).start()
        return call()

    yield run
    common.set_input_stream(saved_in)
    common.set_output_stream(saved_out)
    rs.close()
    ws.close()
    os.close(master)
    os.close(slave)


# --- noneok ---------------------------------------------------------------

def test_noneok_default_accepts_empty_enter(term):
    assert term([b"\r"], lambda: inp.inputstring("> ")) == ""


def test_noneok_false_reprompts_on_empty_enter(term):
    # The first Enter is rejected; the text typed after it is the answer.
    assert term([b"\r", b"ab\r"], lambda: inp.inputstring("> ", noneok=False)) == "ab"


# --- allowed --------------------------------------------------------------

def test_allowed_drops_disallowed_typed_characters(term):
    assert term([b"1", b"x", b"2", b"y", b"3", b"\r"],
                lambda: inp.inputstring("> ", allowed="0123456789")) == "123"


def test_allowed_drops_disallowed_pasted_characters(term):
    assert term([b"a1b2c3\r"], lambda: inp.inputstring("> ", allowed="0123456789"),
                delay=0.3) == "123"


def test_allowed_none_accepts_everything(term):
    assert term([b"a1-", b"\r"], lambda: inp.inputstring("> ")) == "a1-"


# --- filter ---------------------------------------------------------------

def test_filter_rejects_then_accepts_after_fix(term):
    # "-" fails the pattern on Enter; backspace and a digit make it valid.
    assert term([b"-", b"\r", b"\x7f", b"5", b"\r"],
                lambda: inp.inputstring("> ", filter=r"^-?\d+$")) == "5"


def test_filter_accepts_matching_value(term):
    assert term([b"-12", b"\r"], lambda: inp.inputstring("> ", filter=r"^-?\d+$")) == "-12"


def test_filter_is_not_applied_while_typing(term):
    # A partial value ("-") must be typeable; only Enter checks the whole buffer.
    assert term([b"-", b"1", b"\r"], lambda: inp.inputstring("> ", filter=r"^-?\d+$")) == "-1"


# --- inputinteger uses both -----------------------------------------------

def test_inputinteger_drops_letters(term):
    assert term([b"4", b"a", b"2", b"b", b"\r"], lambda: ii.inputinteger("n> ")) == 42


def test_inputinteger_rejects_leading_zero_then_accepts(term):
    assert term([b"007", b"\r", b"\x7f", b"\x7f", b"\x7f", b"42", b"\r"],
                lambda: ii.inputinteger("n> ")) == 42
