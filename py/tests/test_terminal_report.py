"""XTGETTCAP RGB parsing and terminal_report source order (stubbed; no tty needed)."""

import pytest

from bbsengine6.io import common, terminal


# --- parser ---------------------------------------------------------------

@pytest.mark.parametrize(
    "reply, valid, name, value",
    [
        ("\x1bP1+r524742=38\x1b\\", True, "RGB", "8"),  # VTE, verified
        ("\x1bP1+r524742\x1b\\", True, "RGB", None),  # present, no value
        ("\x1bP0+r524742\x1b\\", False, "RGB", None),  # invalid
        ("\x1bP1+r524742=3F\x1b\\", True, "RGB", "?"),  # hex is case-insensitive
    ],
)
def test_parse_valid_and_invalid(reply, valid, name, value):
    p = terminal.parse_xtgettcap_reply(reply)
    assert p == {"valid": valid, "name": name, "value": value}


@pytest.mark.parametrize(
    "reply",
    [None, "", "\x1b[?6c", "\x1bP1+r52474\x1b\\", "\x1bP1+rZZ\x1b\\", "\x1bP2+r524742\x1b\\",
     "\x1bP1+r524742=3\x1b\\"],  # odd-length hex value
)
def test_not_an_xtgettcap_reply(reply):
    assert terminal.parse_xtgettcap_reply(reply) is None


@pytest.mark.parametrize(
    "reply, expected",
    [
        ("\x1bP1+r524742=38\x1b\\", True),  # value "8"
        ("\x1bP1+r524742=38\x1b\\".replace("38", "3" + "8"), True),
        ("\x1bP1+r524742=37\x1b\\", False),  # value "7"
        ("\x1bP1+r524742\x1b\\", True),
        ("\x1bP0+r524742\x1b\\", False),
        ("\x1bP1+r5847=38\x1b\\", None),  # a different capability
    ],
)
def test_rgb_from_reply(reply, expected):
    assert terminal.rgb_from_reply(terminal.parse_xtgettcap_reply(reply)) is expected


def test_rgb_request_is_dcs_plus_q_hex_rgb():
    assert terminal.XTGETTCAP_RGB_REQUEST == "\x1bP+q524742\x1b\\"


# --- terminal_report source order -----------------------------------------

@pytest.fixture
def stub(monkeypatch):
    """Replace probe_da and the query; return a setter for the RGB reply."""
    state = {"rgb": None, "queries": []}
    monkeypatch.setattr(terminal, "probe_da", lambda timeout=None, block=True: "\x1b[?62c")

    def fake_query(request, reply_re, timeout=0.5):
        state["queries"].append(request)
        return state["rgb"]

    monkeypatch.setattr(common, "query_terminal", fake_query)
    monkeypatch.setattr(terminal, "_terminfo_colors", lambda term: 256)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("COLORTERM", raising=False)
    return state


def test_query_answer_wins(stub, monkeypatch):
    monkeypatch.setenv("COLORTERM", "truecolor")
    stub["rgb"] = "\x1bP1+r524742=38\x1b\\"
    r = terminal.terminal_report()
    assert r["source"] == "query" and r["true_color"] is True


def test_query_invalid_is_false_and_not_overridden_by_colorterm(stub, monkeypatch):
    monkeypatch.setenv("COLORTERM", "truecolor")
    stub["rgb"] = "\x1bP0+r524742\x1b\\"
    r = terminal.terminal_report()
    assert r["source"] == "query" and r["true_color"] is False


def test_colorterm_used_when_query_silent(stub, monkeypatch):
    monkeypatch.setenv("COLORTERM", "24bit")
    r = terminal.terminal_report()
    assert r["source"] == "colorterm" and r["true_color"] is True


def test_unknown_when_silent_and_no_colorterm(stub):
    r = terminal.terminal_report()
    assert r["source"] == "unknown"
    assert r["true_color"] is None  # not False: silence is not evidence


def test_color_256_from_terminfo_even_without_truecolor(stub):
    r = terminal.terminal_report()
    assert r["colors"] == 256 and r["color_256"] is True and r["true_color"] is None


def test_color_256_false_for_small_palette(stub, monkeypatch):
    monkeypatch.setattr(terminal, "_terminfo_colors", lambda term: 8)
    r = terminal.terminal_report()
    assert r["color_256"] is False


def test_color_256_unknown_without_terminfo_or_truecolor(stub, monkeypatch):
    monkeypatch.setattr(terminal, "_terminfo_colors", lambda term: None)
    r = terminal.terminal_report()
    assert r["color_256"] is None


def test_truecolor_implies_color_256(stub, monkeypatch):
    monkeypatch.setattr(terminal, "_terminfo_colors", lambda term: None)
    stub["rgb"] = "\x1bP1+r524742=38\x1b\\"
    assert terminal.terminal_report()["color_256"] is True


def test_report_has_all_keys(stub):
    r = terminal.terminal_report()
    assert set(r) == {"term", "colors", "true_color", "color_256", "source", "ansi"}


def test_report_without_tty_is_safe(monkeypatch):
    monkeypatch.delenv("COLORTERM", raising=False)
    monkeypatch.setattr(common, "query_terminal", lambda *a, **k: (_ for _ in ()).throw(OSError("no tty")))
    r = terminal.terminal_report(timeout=0.01)
    assert r["source"] == "unknown" and r["true_color"] is None


# --- real pty: a child runs terminal_report; the parent answers each query --------

import shutil
import sys
import textwrap

pexpect = pytest.importorskip("pexpect")
needs_pty = pytest.mark.skipif(sys.platform == "win32", reason="needs a POSIX pty")

_REPORT_CHILD = textwrap.dedent(
    """
    import sys, json
    sys.path.insert(0, "src")
    from bbsengine6.io import terminal
    report = terminal.terminal_report(timeout=0.4)
    sys.stdout.write("REPORT=" + json.dumps(report) + "\\n")
    sys.stdout.flush()
    """
)


def _run_report(answer_rgb, colorterm=None):
    """Run terminal_report on a pty. Answer DA1 with a VT220 reply, and the RGB query with
    ``answer_rgb`` (or stay silent when None)."""
    import json
    import time

    env_prefix = f"COLORTERM={colorterm} " if colorterm else "env -u COLORTERM "
    child = pexpect.spawn(
        "/bin/sh", ["-c", f"{env_prefix}TERM=xterm-256color {sys.executable} -c '{_REPORT_CHILD}'"],
        timeout=20, encoding="utf-8",
    )
    try:
        child.expect_exact("\x1b[c")
        child.send("\x1b[?62;1;2c")
        child.expect_exact("\x1bP+q524742\x1b\\")
        if answer_rgb is not None:
            time.sleep(0.05)
            child.send(answer_rgb)
        child.expect(r"REPORT=(\{[^\r\n]*\})")
        return json.loads(child.match.group(1))
    finally:
        child.close(force=True)


@needs_pty
def test_pty_query_valid_reports_true_color():
    r = _run_report("\x1bP1+r524742=38\x1b\\")
    assert r["source"] == "query" and r["true_color"] is True
    assert r["colors"] == 256 and r["color_256"] is True
    assert r["ansi"] == "\x1b[?62;1;2c"


@needs_pty
def test_pty_query_invalid_reports_false_even_with_colorterm():
    r = _run_report("\x1bP0+r524742\x1b\\", colorterm="truecolor")
    assert r["source"] == "query" and r["true_color"] is False


@needs_pty
def test_pty_silent_query_falls_back_to_colorterm():
    r = _run_report(None, colorterm="truecolor")
    assert r["source"] == "colorterm" and r["true_color"] is True


@needs_pty
def test_pty_silent_and_no_colorterm_is_unknown():
    r = _run_report(None)
    assert r["source"] == "unknown" and r["true_color"] is None

