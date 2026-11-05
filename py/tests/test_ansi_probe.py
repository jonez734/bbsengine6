"""Tests for the ANSI probe: io.common.query_terminal, io.terminal.probe_da, has_ansi, and
configure_ansi_probe.

The reply rules are tested directly. The pty tests run a probe on a real pty through
``script`` (util-linux) and skip when it is missing.
"""

import shutil
import time
import subprocess
import sys
import textwrap

import pytest

from bbsengine6.io import common, terminal


@pytest.fixture(autouse=True)
def _reset_config():
    terminal.configure_ansi_probe(None)
    yield
    terminal.configure_ansi_probe(None)


# ---------------------------------------------------------------------------
# Approved replies
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reply",
    [
        "\x1b[?6c",  # VT102
        "\x1b[?1;2c",  # VT100 with AVO
        "\x1b[?62;1;2;6;8;9;15;22c",  # VT220
        "\x1b[?64;1;2;6;9;15;18;21;22c",  # modern xterm
        "\x1b[>0c",  # DA2 (VT240-style minimal reply)
        "\x1b[>41;0;0c",  # DA2 with version fields
    ],
)
def test_has_ansi_accepts_approved_replies(monkeypatch, reply):
    monkeypatch.setattr(terminal, "probe_da", lambda timeout=None, block=True: reply)
    assert terminal.has_ansi() is True


@pytest.mark.parametrize(
    "reply",
    [
        None,
        "",
        "\x1b[?6",  # truncated
        "hello",
        "\x1b[6c",  # no private marker
        "\x1b[?6cX",  # trailing text
        "\x1b[>?c",  # wrong marker order
        "\x1b[5n",  # a DSR status reply, not DA
    ],
)
def test_has_ansi_rejects_other_replies(monkeypatch, reply):
    monkeypatch.setattr(terminal, "probe_da", lambda timeout=None, block=True: reply)
    assert terminal.has_ansi() is False


# ---------------------------------------------------------------------------
# probe_da: DA1 first, DA2 fallback, config
# ---------------------------------------------------------------------------


def test_probe_da_tries_da2_when_da1_has_no_reply(monkeypatch):
    sent = []

    def fake_query(request, reply_re, timeout=0.5):
        sent.append(request)
        return "\x1b[>0c" if request == terminal.DA2_REQUEST else None

    monkeypatch.setattr(common, "query_terminal", fake_query)
    assert terminal.probe_da() == "\x1b[>0c"
    assert sent == [terminal.DA1_REQUEST, terminal.DA2_REQUEST]


def test_probe_da_stops_after_da1_reply(monkeypatch):
    sent = []

    def fake_query(request, reply_re, timeout=0.5):
        sent.append(request)
        return "\x1b[?62;1;2c"

    monkeypatch.setattr(common, "query_terminal", fake_query)
    assert terminal.probe_da() == "\x1b[?62;1;2c"
    assert sent == [terminal.DA1_REQUEST]


def test_probe_da_none_when_no_reply(monkeypatch):
    monkeypatch.setattr(common, "query_terminal", lambda *a, **k: None)
    assert terminal.probe_da() is None
    assert terminal.has_ansi() is False


def test_probe_da_disabled_writes_nothing(monkeypatch):
    called = []
    monkeypatch.setattr(common, "query_terminal", lambda *a, **k: called.append(a) or None)
    terminal.configure_ansi_probe({"ansi_probe": {"enabled": False}})
    assert terminal.probe_da() is None
    assert called == []
    assert terminal.has_ansi() is False


def test_probe_da_failure_returns_none(monkeypatch):
    def boom(*a, **k):
        raise OSError("no tty")

    monkeypatch.setattr(common, "query_terminal", boom)
    assert terminal.probe_da() is None


def test_timeout_from_config_is_used(monkeypatch):
    seen = []

    def fake_query(request, reply_re, timeout=0.5):
        seen.append(timeout)
        return None

    monkeypatch.setattr(common, "query_terminal", fake_query)
    terminal.configure_ansi_probe({"ansi_probe": {"timeout_seconds": 1.25}})
    terminal.probe_da()
    assert seen == [1.25, 1.25]


def test_explicit_timeout_overrides_config(monkeypatch):
    seen = []
    monkeypatch.setattr(
        common, "query_terminal", lambda r, p, timeout=0.5: seen.append(timeout) or None
    )
    terminal.configure_ansi_probe({"ansi_probe": {"timeout_seconds": 1.25}})
    terminal.probe_da(timeout=0.1)
    assert seen == [0.1, 0.1]


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


def test_defaults_when_no_config():
    terminal.configure_ansi_probe({})
    assert terminal._ANSI_PROBE_ENABLED is True
    assert terminal._ANSI_PROBE_TIMEOUT == 0.5


@pytest.mark.parametrize(
    "cfg",
    [
        {"ansi_probe": {"timeout_seconds": 0}},
        {"ansi_probe": {"timeout_seconds": -1}},
        {"ansi_probe": {"timeout_seconds": "slow"}},
        {"ansi_probe": {"timeout_seconds": True}},
        {"ansi_probe": {"enabled": "yes"}},
        {"ansi_probe": "on"},
    ],
)
def test_bad_config_raises(cfg):
    with pytest.raises(ValueError):
        terminal.configure_ansi_probe(cfg)


# ---------------------------------------------------------------------------
# query_terminal: reply matching and leftover keys (no tty needed)
# ---------------------------------------------------------------------------


def test_query_terminal_returns_none_without_a_tty(monkeypatch):
    class _NoTty:
        def fileno(self):
            raise OSError("not a tty")

        encoding = "utf-8"

    import bbsengine6.io.common as c

    monkeypatch.setattr(c, "_in_stream", lambda: _NoTty())
    with pytest.raises(Exception):
        common.query_terminal(terminal.DA1_REQUEST, terminal.DA1_REPLY_RE, timeout=0.05)
    # probe_da turns that failure into None.
    monkeypatch.setattr(c, "query_terminal", common.query_terminal)
    assert terminal.probe_da() is None


# ---------------------------------------------------------------------------
# Real pty: a child runs probe_da, and the parent answers the query on the master side
# ---------------------------------------------------------------------------

needs_script = pytest.mark.skipif(shutil.which("script") is None, reason="script not installed")

_PTY_CHILD = textwrap.dedent(
    """
    import sys
    sys.path.insert(0, "src")
    from bbsengine6.io import terminal
    ok = terminal.has_ansi()
    sys.stdout.write("\\nHAS_ANSI=" + str(ok) + "\\n")
    sys.stdout.flush()
    """
)


def _run_child_on_pty(reply: bytes | None):
    """Run the probe child on a pty. When ``reply`` is given, answer the DA1 query with it.

    Returns the child's text output.
    """
    import pexpect

    child = pexpect.spawn(sys.executable, ["-c", _PTY_CHILD], timeout=15, encoding="utf-8")
    try:
        if reply is not None:
            # The child writes ESC[c first. Answer it on the master side, as a terminal does.
            child.expect_exact("\x1b[c")
            child.send(reply.decode("latin-1"))
        child.expect(pexpect.EOF)
        return child.before
    finally:
        child.close(force=True)


@needs_script
def test_pty_terminal_that_answers_da1_is_detected():
    out = _run_child_on_pty(b"\x1b[?62;1;2c")
    assert "HAS_ANSI=True" in out, out


@needs_script
def test_pty_terminal_that_stays_silent_is_not_detected():
    out = _run_child_on_pty(None)
    assert "HAS_ANSI=False" in out, out


@needs_script
def test_pty_late_reply_inside_settle_window_is_consumed():
    """A DA1 reply that arrives after the timeout but inside the settle window is matched,
    so it is not echoed on screen or left in the tty for the input reader."""
    import pexpect

    src = textwrap.dedent(
        """
        import sys, time
        sys.path.insert(0, "src")
        from bbsengine6.io import terminal, common
        r = terminal.probe_da(timeout=0.3)
        sys.stdout.write("\\\\nRESULT=" + repr(r) + "\\\\n")
        time.sleep(0.6)
        common.drain_stream_to_queue(common._in_stream(), common._queue())
        sys.stdout.write("QUEUE=" + repr("".join(common._queue())) + "\\\\nDONE\\\\n")
        sys.stdout.flush()
        """
    )
    child = pexpect.spawn(sys.executable, ["-c", src], timeout=20, encoding="utf-8")
    try:
        child.expect_exact("\x1b[c")
        import time as _t
        _t.sleep(0.45)  # after the 0.3 s timeout, inside the 0.25 s settle window
        child.send("\x1b[?62;1;2c")
        child.expect("DONE")
        out = child.before
    finally:
        child.close(force=True)
    assert "RESULT='\\x1b[?62;1;2c'" in out, out
    assert "QUEUE=''" in out, out
    assert "^[[?62;1;2c" not in out, out


@needs_script
def test_pty_late_reply_then_key_returns_the_key():
    """A late DA reply in the input is discarded, and the next real keypress is returned.

    getch must not return None (a timeout) because the only bytes were a stale reply.
    """
    import pexpect

    src = textwrap.dedent(
        """
        import sys, time, importlib
        sys.path.insert(0, "src")
        from bbsengine6.io import terminal
        getch = importlib.import_module("bbsengine6.io.getch")
        terminal.probe_da(timeout=0.3)
        time.sleep(0.5)
        k = getch.getch_str(timeout=3.0)
        sys.stdout.write("\\\\nKEY=" + repr(k) + "\\\\n")
        sys.stdout.flush()
        """
    )
    child = pexpect.spawn(sys.executable, ["-c", src], timeout=20, encoding="utf-8")
    try:
        child.expect_exact("\x1b[c")
        child.expect_exact("\x1b[>c")
        time.sleep(1.0)
        child.send("\x1b[?62;1;2c")  # late DA1 reply
        time.sleep(0.3)
        child.send("q")
        child.expect(pexpect.EOF)
        out = child.before
    finally:
        child.close(force=True)
    assert "KEY='q'" in out, out


def test_nonblocking_probe_returns_at_once(monkeypatch):
    """probe_da(block=False) sends DA1 and returns without reading the tty."""
    sent = []
    monkeypatch.setattr(common, "write_current_output_stream", lambda s, flush=False: sent.append(s))
    called = []
    monkeypatch.setattr(common, "query_terminal", lambda *a, **k: called.append(a) or None)
    assert terminal.probe_da(block=False) is None
    assert sent == [terminal.DA1_REQUEST]
    assert called == []


def test_has_ansi_nonblocking_is_false_until_reply_is_collected(monkeypatch):
    monkeypatch.setattr(common, "write_current_output_stream", lambda s, flush=False: None)
    assert terminal.has_ansi(block=False) is False


def test_ansi_reply_pops_recorded_replies():
    from bbsengine6.interaction import current_session

    sess = current_session()
    sess.da_replies.clear()
    sess.da_replies.extend(["\x1b[?62;1;2c", "\x1b[>0c"])
    assert terminal.ansi_reply() == "\x1b[?62;1;2c"
    assert terminal.ansi_reply() == "\x1b[>0c"
    assert terminal.ansi_reply() is None


def test_discard_records_replies_in_the_session():
    from bbsengine6.interaction import current_session

    sess = current_session()
    sess.da_replies.clear()
    q = common._queue()
    q.clear()
    q.extend("\x1b[?6cx")
    assert common.discard_da_replies() == 1
    assert "".join(q) == "x"
    assert sess.da_replies == ["\x1b[?6c"]
    sess.da_replies.clear()
    q.clear()
