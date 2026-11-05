"""Tests for the ANSI probe: io.common.query_terminal, io.terminal.probe_da, has_ansi, and
configure_ansi_probe.

The reply rules are tested directly. The pty tests run a probe on a real pty through
``script`` (util-linux) and skip when it is missing.
"""

import shutil
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
    monkeypatch.setattr(terminal, "probe_da", lambda timeout=None: reply)
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
    monkeypatch.setattr(terminal, "probe_da", lambda timeout=None: reply)
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
