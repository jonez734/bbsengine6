"""A DA reply that arrives after its probe timed out is dropped from the keys and recorded as late."""

import sys

import pytest

from bbsengine6.interaction import current_session
from bbsengine6.io import common, terminal

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_session():
    s = current_session()
    s.da_replies.clear()
    s.late_da_replies = []
    common._queue().clear()
    yield
    s.da_replies.clear()
    s.late_da_replies = []
    common._queue().clear()


def test_late_da_reply_is_removed_from_keys_and_marked_late():
    s = current_session()
    s.da_timed_out = {"da1"}
    common._queue().extend("x\x1b[?62;1;2cy")
    assert common.discard_da_replies() == 1
    assert "".join(common._queue()) == "xy"
    assert s.late_da_replies == [("da1", "\x1b[?62;1;2c")]


def test_discard_without_a_timed_out_request_is_not_late():
    s = current_session()
    common._queue().extend("\x1b[?62c")
    common.discard_da_replies()
    assert s.late_da_replies == []
    assert len(s.da_replies) == 1



needs_pty = pytest.mark.skipif(sys.platform == "win32", reason="needs a POSIX pty")
pexpect = pytest.importorskip("pexpect")


_LATE_CHILD = """
import sys, time, json
sys.path.insert(0, "src")
from bbsengine6.io import terminal
import importlib
getch = importlib.import_module("bbsengine6.io.getch")
from bbsengine6.interaction import current_session
# DA1 with a short timeout, and no reply: the probe times out and is marked.
reply = terminal.probe_da(timeout=0.2, block=True)
# The parent answers late, then types "q". getch reads the tty: the late reply is dropped from the
# keys and recorded, and the next key is what getch returns.
time.sleep(1.0)
key = getch.getch_str(timeout=2.0)
s = current_session()
state = {
    "reply": reply,
    "key": key,
    "late": s.late_da_replies,
    "timed": sorted(s.da_timed_out),
}
sys.stdout.write("LATE=" + json.dumps(state) + "\\n")
sys.stdout.flush()
"""


@needs_pty
def test_pty_late_da_reply_is_not_a_key_and_is_recorded_late():
    child = pexpect.spawn(
        "/bin/sh",
        ["-c", f"env -u COLORTERM TERM=xterm-256color {sys.executable} -c '{_LATE_CHILD}'"],
        timeout=20, encoding="utf-8",
    )
    try:
        child.expect_exact("\x1b[c")
        import time
        time.sleep(1.0)  # past the 0.2 s timeout and the 0.25 s settle window
        child.send("\x1b[?62;1;2c" + "q")
        child.expect(r"LATE=(\{[^\r\n]*\})")
        import json
        out = json.loads(child.match.group(1))
    finally:
        child.close(force=True)
    assert out["key"] == "q"
    assert out["late"] == [["da1", "\x1b[?62;1;2c"]]


def test_late_reply_is_not_shown_for_a_probe_that_was_not_sent(monkeypatch):
    # A late reply for a name only ever marks a record that was sent. A probe that did not run
    # (probing disabled, or RGB skipped by COLORTERM) keeps reply None.
    from bbsengine6.io import terminal as t

    s = current_session()
    s.late_da_replies = [("rgb", "\x1bP1+r524742=38\x1b\\")]
    monkeypatch.setenv("COLORTERM", "truecolor")
    monkeypatch.setattr(t, "probe_da", lambda timeout=None, block=True: None)
    monkeypatch.setattr(common, "query_terminal", lambda *a, **k: None)
    r = t.report(timeout=0.01)
    assert r["da"]["rgb"]["sent"] is False
    assert r["da"]["rgb"]["reply"] is None
    assert r["da"]["rgb"]["late"] is False
