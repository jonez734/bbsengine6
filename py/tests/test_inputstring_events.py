"""inputstring() fires key events, and F1/F2 arrive as KEY_HELP and KEY_MESSAGES.

Regression: inputstring passed fire_events=False, so handlers saw nothing during a prompt,
and escape keys taken from the queue returned without pushing events at all.
"""

import importlib
import os
import pty
import threading
import time

import pytest

common = importlib.import_module("bbsengine6.io.common")
g = importlib.import_module("bbsengine6.io.getch")
inp = importlib.import_module("bbsengine6.io.inputstring")


@pytest.fixture
def term(monkeypatch):
    master, slave = pty.openpty()
    rs = os.fdopen(os.dup(slave), "r", buffering=1, encoding="utf-8")
    ws = os.fdopen(os.dup(slave), "w", buffering=1, encoding="utf-8")
    saved_in, saved_out = common._current_input_stream, common._current_output_stream
    common.set_input_stream(rs)
    common.set_output_stream(ws)
    monkeypatch.setattr(inp, "get_cursor_position", lambda timeout=1.0: (1, 1))
    seen = []
    g.register_key_event_handler("test-events", lambda e: seen.append((e.stage, e.processed_key)))
    g.start_event_dispatcher()

    def run(writes, call, delay=0.3):
        def feed():
            for piece in writes:
                time.sleep(delay)
                os.write(master, piece)
        threading.Thread(target=feed, daemon=True).start()
        result = call()
        time.sleep(0.2)
        return result, [e for e in seen if e[0] == "processed"]

    yield run
    g.stop_event_dispatcher()
    g.unregister_key_event_handler("test-events")
    common.set_input_stream(saved_in)
    common.set_output_stream(saved_out)
    rs.close()
    ws.close()
    os.close(master)
    os.close(slave)


def test_f1_and_f2_arrive_as_help_and_messages_during_prompt(term):
    result, processed = term([b"\x1bOP", b"\x1bOQ", b"a", b"\r"],
                             lambda: inp.inputstring("> ", f1_help="help"))
    assert result == "a"
    names = [p[1] for p in processed]
    assert "KEY_HELP" in names and "KEY_MESSAGES" in names
    assert names.index("KEY_HELP") < names.index("KEY_MESSAGES") < names.index("a")


def test_returned_key_names_are_unchanged(term):
    # The reader still returns KEY_F1 / KEY_F2; only the event name is aliased.
    common._input_queue.clear()
    master, slave = pty.openpty()
    rs = os.fdopen(os.dup(slave), "r", buffering=1, encoding="utf-8")
    common.set_input_stream(rs)
    try:
        g.begin_raw_session()
        os.write(master, b"\x1bOP")
        time.sleep(0.1)
        assert g.getch_str(timeout=0.5, check_notifications=False) == "KEY_F1"
    finally:
        g.end_raw_session()
        rs.close()
        os.close(master)
        os.close(slave)
