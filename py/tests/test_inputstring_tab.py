"""Tab handling in inputstring(): a typed Tab completes; a tab inside a paste is
text, shown as a space by default and inserted when insert_tabs=True (for an
editor that needs real tabs).
"""

import importlib
import os
import pty
import threading
import time

import pytest

common = importlib.import_module("bbsengine6.io.common")
inp = importlib.import_module("bbsengine6.io.inputstring")

WORDS = ["apple", "apricot", "banana"]


def completer(buffer, curpos=0, **kwargs):
    return [w for w in WORDS if w.startswith(buffer)]


@pytest.fixture
def term(monkeypatch):
    master, slave = pty.openpty()
    rs = os.fdopen(os.dup(slave), "r", buffering=1, encoding="utf-8")
    ws = os.fdopen(os.dup(slave), "w", buffering=1, encoding="utf-8")
    saved_in, saved_out = common._current_input_stream, common._current_output_stream
    common.set_input_stream(rs)
    common.set_output_stream(ws)
    monkeypatch.setattr(inp, "get_cursor_position", lambda timeout=1.0: (1, 1))

    def run(writes, delay=0.3, **kwargs):
        def feed():
            for piece in writes:
                time.sleep(delay)
                os.write(master, piece)
        threading.Thread(target=feed, daemon=True).start()
        return inp.inputstring("> ", **kwargs)

    yield run
    common.set_input_stream(saved_in)
    common.set_output_stream(saved_out)
    rs.close()
    ws.close()
    os.close(master)
    os.close(slave)


def test_typed_tab_completes_unambiguous_prefix(term):
    assert term([b"ban", b"\t", b"\r"], completer=completer) == "banana"


def test_typed_tab_on_ambiguous_prefix_does_not_complete(term):
    # Two matches: the prefix is left as typed.
    assert term([b"ap", b"\t", b"\r"], completer=completer) == "ap"


def test_pasted_tab_becomes_space_by_default(term):
    # The paste arrives in one burst so the tab is text, not a keypress.
    assert term([b"a\tb\tc\r"], delay=0.3) == "a b c"


def test_pasted_tab_inserted_when_insert_tabs(term):
    assert term([b"a\tb\r"], delay=0.3, insert_tabs=True) == "a\tb"
