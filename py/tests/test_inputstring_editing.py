"""Editing keys and paste-related behavior in inputstring():

- Ctrl-W cuts the previous word; Ctrl-Y yanks it back (reader maps \\x17, \\x19).
- Typed input past max_len beeps; a paste that overflows beeps once.
- A bracketed paste (ESC[200~ ... ESC[201~) is one paste, with a newline ending the
  entry; the mode is enabled for the prompt and disabled on exit.
"""

import importlib
import os
import pty
import select
import threading
import time

import pytest

common = importlib.import_module("bbsengine6.io.common")
inp = importlib.import_module("bbsengine6.io.inputstring")
getch_mod = importlib.import_module("bbsengine6.io.getch")


@pytest.fixture
def term(monkeypatch):
    master, slave = pty.openpty()
    rs = os.fdopen(os.dup(slave), "r", buffering=1, encoding="utf-8")
    ws = os.fdopen(os.dup(slave), "w", buffering=1, encoding="utf-8")
    saved_in, saved_out = common._current_input_stream, common._current_output_stream
    common.set_input_stream(rs)
    common.set_output_stream(ws)
    monkeypatch.setattr(inp, "get_cursor_position", lambda timeout=1.0: (1, 1))
    out = bytearray()
    stop = threading.Event()

    def reader():
        while not stop.is_set():
            try:
                if select.select([master], [], [], 0.05)[0]:
                    out.extend(os.read(master, 4096))
            except OSError:
                return

    threading.Thread(target=reader, daemon=True).start()

    def run(writes, call, delay=0.25):
        def feed():
            for piece in writes:
                time.sleep(delay)
                os.write(master, piece)
        threading.Thread(target=feed, daemon=True).start()
        result = call()
        # Let the reader drain what the prompt wrote: wait until the output stops
        # growing, rather than sleeping a fixed time that a loaded machine can miss.
        last, quiet = -1, 0
        for _ in range(200):
            time.sleep(0.02)
            if len(out) == last:
                quiet += 1
                if quiet >= 3:
                    break
            else:
                quiet, last = 0, len(out)
        return result, bytes(out)

    yield run
    stop.set()
    common.set_input_stream(saved_in)
    common.set_output_stream(saved_out)
    rs.close()
    ws.close()
    os.close(master)
    os.close(slave)


def test_ctrl_w_cuts_word_and_ctrl_y_yanks_it_back(term):
    result, _ = term([b"foo bar", b"\x17", b"\x19", b"\r"], lambda: inp.inputstring("> "))
    assert result == "foo bar"


def test_typed_overflow_beeps_and_drops(term):
    result, out = term([b"abcdef", b"\r"], lambda: inp.inputstring("> ", max_len=3))
    assert result == "abc"
    assert out.count(b"\x07") == 1


def test_normal_typing_does_not_beep(term):
    result, out = term([b"abc", b"\r"], lambda: inp.inputstring("> ", max_len=10))
    assert result == "abc"
    assert out.count(b"\x07") == 0


def test_paste_overflow_beeps_once(term):
    result, out = term([b"abcdefgh\r"], lambda: inp.inputstring("> ", max_len=3), delay=0.3)
    assert result == "abc"
    assert out.count(b"\x07") == 1


def test_bracketed_paste_is_one_paste_then_typing_continues(term):
    result, out = term(
        [b"\x1b[200~hello world\x1b[201~", b"!\r"],
        lambda: inp.inputstring("> "),
        delay=0.3,
    )
    assert result == "hello world!"
    assert b"\x1b[?2004h" in out and b"\x1b[?2004l" in out


def test_bracketed_paste_newline_ends_entry_and_keeps_rest_queued(term):
    # A newline in a paste ends the entry (it is an Enter). The text after it is not
    # lost: it stays on the input queue for the next read, which is what a following
    # prompt on the same terminal should receive.
    result, _ = term([b"\x1b[200~ab\ncd\x1b[201~"], lambda: inp.inputstring("> "),
                     delay=0.3)
    assert result == "ab"
    assert list(common._input_queue) == ["c", "d"]
    common._input_queue.clear()  # the next prompt would consume these; reset for other tests


def test_reader_returns_paste_as_one_key():
    common._input_queue.clear()
    master, slave = pty.openpty()
    rs = os.fdopen(os.dup(slave), "r", buffering=1, encoding="utf-8")
    common.set_input_stream(rs)
    try:
        getch_mod.begin_raw_session()
        os.write(master, b"\x1b[200~hi there\x1b[201~z")
        time.sleep(0.1)
        first = getch_mod.getch_str(timeout=0.5, check_notifications=False)
        second = getch_mod.getch_str(timeout=0.5, check_notifications=False)
        assert first == "PASTE:hi there"
        assert second == "z"
    finally:
        getch_mod.end_raw_session()
        rs.close()
        os.close(master)
        os.close(slave)


def test_long_bracketed_paste_stays_on_one_row_and_is_complete(term):
    # The reported paste: longer than the 80-column row after the prompt. The entry must
    # be complete, every drawn cursor position must be on the row and inside the width,
    # and the visible text must never run past the right edge.
    text = ("Ctrl-W and Ctrl-Y are confirmed working in your gnome-terminal. I recorded "
            "that in the sidebar and in the handbook (ba51c2c, local only, not pushed).")
    # Pin the width so the test does not depend on the host's terminal size.
    monkeypatch_width = pytest.MonkeyPatch()
    monkeypatch_width.setenv("BBSENGINE_MAX_WIDTH", "80")
    try:
        result, out = term([b"\x1b[200~" + text.encode() + b"\x1b[201~", b"\r"],
                           lambda: inp.inputstring("> "), delay=0.3)
    finally:
        monkeypatch_width.undo()
    assert result == text
    import re
    width = 80
    for row, col in re.findall(rb"\x1b\[(\d+);(\d+)H", out):
        assert int(row) == 1, f"cursor left row 1: {row!r}"
        assert 1 <= int(col) <= width, f"cursor past width {width}: {col!r}"
    # Replay the drawn bytes onto a small row model: the final row must show the
    # tail of the paste exactly once (no leftovers from an earlier, longer draw).
    # Start the replay at this prompt's own output: the first mode request. Anything
    # earlier in the capture belongs to earlier output and would shift the model.
    start = out.find(b"\x1b[?2004h")
    assert start >= 0, "bracketed-paste mode request not seen"
    row = _replay_row1(out[start:].decode("utf-8", errors="replace"), width)
    assert row.count(text[-5:]) == 1, f"tail duplicated on screen: {row!r}"


def _replay_row1(data: str, width: int) -> str:
    """Minimal model of the escapes inputstring emits: cursor position, text,
    and blanks. Returns what is on row 1 after the bytes are applied."""
    import re as _re
    cells = [" "] * (width + 1)
    r, c = 1, 1
    token = _re.compile(r"\x1b\[(\d+);(\d+)H|\x1b\[[0-9;?$]*[A-Za-z]|\x1b\[[0-9;?$]*p")
    i = 0
    while i < len(data):
        m = token.match(data, i)
        if m:
            if m.group(1) is not None:
                r, c = int(m.group(1)), int(m.group(2))
            i = m.end()
            continue
        ch = data[i]
        if ch == "\n":
            r, c = r + 1, 1
        elif ch == "\r":
            c = 1
        elif ch >= " " and r == 1 and 1 <= c <= width:
            cells[c] = ch
            c += 1
        elif ch >= " ":
            c += 1
        i += 1
    return "".join(cells[1:]).rstrip()
