"""XTGETTCAP RGB parsing and report source order (stubbed; no tty needed)."""

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


# --- report source order -----------------------------------------

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
    r = terminal.report()
    assert r["source"] == "query" and r["true_color"] is True


def test_query_invalid_is_false_and_not_overridden_by_colorterm(stub, monkeypatch):
    monkeypatch.setenv("COLORTERM", "truecolor")
    stub["rgb"] = "\x1bP0+r524742\x1b\\"
    r = terminal.report()
    assert r["source"] == "query" and r["true_color"] is False


def test_colorterm_used_when_query_silent(stub, monkeypatch):
    monkeypatch.setenv("COLORTERM", "24bit")
    r = terminal.report()
    assert r["source"] == "colorterm" and r["true_color"] is True


def test_unknown_when_silent_and_no_colorterm(stub):
    r = terminal.report()
    assert r["source"] == "unknown"
    assert r["true_color"] is None  # not False: silence is not evidence


def test_color_256_from_terminfo_even_without_truecolor(stub):
    r = terminal.report()
    assert r["colors"] == 256 and r["color_256"] is True and r["true_color"] is None


def test_color_256_false_for_small_palette(stub, monkeypatch):
    monkeypatch.setattr(terminal, "_terminfo_colors", lambda term: 8)
    r = terminal.report()
    assert r["color_256"] is False


def test_color_256_unknown_without_terminfo_or_truecolor(stub, monkeypatch):
    monkeypatch.setattr(terminal, "_terminfo_colors", lambda term: None)
    r = terminal.report()
    assert r["color_256"] is None


def test_truecolor_reports_colors_as_24bit_even_with_small_terminfo(stub, monkeypatch):
    # terminfo's colors for xterm is 8, but the terminal answered the RGB query: the two fields
    # must agree, so colors reports the 24-bit palette.
    monkeypatch.setattr(terminal, "_terminfo_colors", lambda term: 8)
    stub["rgb"] = "\x1bP1+r524742=38\x1b\\"
    r = terminal.report()
    assert r["colors"] == 16777216 and r["true_color"] is True and r["color_256"] is True


def test_no_truecolor_keeps_terminfo_colors(stub, monkeypatch):
    monkeypatch.setattr(terminal, "_terminfo_colors", lambda term: 8)
    r = terminal.report()
    assert r["colors"] == 8 and r["true_color"] is None


def test_truecolor_implies_color_256(stub, monkeypatch):
    monkeypatch.setattr(terminal, "_terminfo_colors", lambda term: None)
    stub["rgb"] = "\x1bP1+r524742=38\x1b\\"
    assert terminal.report()["color_256"] is True


def test_report_has_all_keys(stub):
    r = terminal.report()
    assert set(r) == {"term", "colors", "true_color", "color_256", "source", "ansi"}


def test_report_without_tty_is_safe(monkeypatch):
    monkeypatch.delenv("COLORTERM", raising=False)
    monkeypatch.setattr(common, "query_terminal", lambda *a, **k: (_ for _ in ()).throw(OSError("no tty")))
    r = terminal.report(timeout=0.01)
    assert r["source"] == "unknown" and r["true_color"] is None


# --- real pty: a child runs report; the parent answers each query --------

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
    report = terminal.report(timeout=0.4)
    sys.stdout.write("REPORT=" + json.dumps(report) + "\\n")
    sys.stdout.flush()
    """
)


def _run_report(answer_rgb, colorterm=None):
    """Run report on a pty. Answer DA1 with a VT220 reply, and the RGB query with
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
    assert r["colors"] == 16777216 and r["color_256"] is True
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



# --- generic XTGETTCAP query by capability name ----------------------------

def test_xtgettcap_request_encodes_any_name():
    assert terminal.xtgettcap_request("Tc") == "\x1bP+q5463\x1b\\"
    assert terminal.xtgettcap_request("RGB") == terminal.XTGETTCAP_RGB_REQUEST


@pytest.mark.parametrize("name", ["", "a b", "tc\x1b", "é"])
def test_xtgettcap_request_rejects_non_ascii_name(name):
    with pytest.raises(ValueError):
        terminal.xtgettcap_request(name)


def test_query_cap_returns_decoded_value(monkeypatch):
    # The terminal answers "Co" with value "256" (hex 323536).
    seen = {}

    def fake_query(request, reply_re, timeout=0.5):
        seen["request"] = request
        return "\x1bP1+r436f=323536\x1b\\"

    monkeypatch.setattr(common, "query_terminal", fake_query)
    assert terminal.query_cap("Co") == "256"
    assert seen["request"] == "\x1bP+q436f\x1b\\"


def test_query_cap_valid_without_value_is_true(monkeypatch):
    monkeypatch.setattr(common, "query_terminal", lambda *a, **k: "\x1bP1+r5463\x1b\\")
    assert terminal.query_cap("Tc") is True


def test_query_cap_invalid_is_false(monkeypatch):
    monkeypatch.setattr(common, "query_terminal", lambda *a, **k: "\x1bP0+r5463\x1b\\")
    assert terminal.query_cap("Tc") is False


def test_query_cap_silent_is_none(monkeypatch):
    monkeypatch.setattr(common, "query_terminal", lambda *a, **k: None)
    assert terminal.query_cap("Tc") is None


def test_query_cap_ignores_reply_for_another_name(monkeypatch):
    # The reply names a different capability: it is not the answer to this query.
    monkeypatch.setattr(common, "query_terminal", lambda *a, **k: "\x1bP1+r524742=38\x1b\\")
    assert terminal.query_cap("Tc") is None


# --- report()["term"] is the resolved terminal type ------------------------

def test_report_term_is_client_term_when_it_has_an_entry(stub, monkeypatch):
    monkeypatch.setenv("TERM", "xterm-256color")
    assert terminal.report()["term"] == "xterm-256color"


def test_report_term_falls_back_when_client_term_has_no_entry(stub, monkeypatch):
    # An unknown TERM is not reported as itself: report() describes the type the server uses.
    monkeypatch.setenv("TERM", "no-such-terminal-xyz")
    monkeypatch.setattr(terminal, "_terminfo_colors", lambda term: 8 if term == "xterm" else None)
    r = terminal.report()
    assert r["term"] == terminal.DEFAULT_TERM == "xterm"


def test_report_term_is_dumb_when_term_is_dumb(stub, monkeypatch):
    # dumb is reported as itself, for testing: resolve() refuses it for a full-screen program, but
    # the report describes what the process actually has.
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setattr(terminal, "_terminfo_colors", lambda term: None)
    assert terminal.report()["term"] == "dumb"


def test_report_colors_follow_the_resolved_term(stub, monkeypatch):
    # colors is looked up for the type report() names, so the two fields come from the same entry.
    monkeypatch.setenv("TERM", "no-such-terminal-xyz")
    seen = []
    monkeypatch.setattr(terminal, "_terminfo_colors", lambda term: seen.append(term) or 8)
    terminal.report()
    assert seen and set(seen) == {"xterm"}
