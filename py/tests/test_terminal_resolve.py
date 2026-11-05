"""Tests for bbsengine6.io.terminal.resolve and resolve_notice: the terminal-type order."""

import pytest

from bbsengine6.io import terminal, terminfo


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("TERMINFO", raising=False)
    monkeypatch.delenv("TERMINFO_DIRS", raising=False)
    terminfo.clear_cache()
    yield
    terminfo.clear_cache()


def _known(monkeypatch, names):
    """Make has_entry true for exactly ``names``; everything else is unknown."""
    monkeypatch.setattr(terminfo, "has_entry", lambda n: n in names)


def test_client_term_wins_when_it_has_an_entry(monkeypatch):
    _known(monkeypatch, {"vt100", "xterm"})
    assert terminal.resolve(stored="xterm", client="vt100") == ("vt100", "client")


def test_stored_used_when_client_unknown(monkeypatch):
    _known(monkeypatch, {"vt100"})
    assert terminal.resolve(stored="vt100", client="nope") == ("vt100", "stored")


def test_default_when_client_and_stored_unknown(monkeypatch):
    _known(monkeypatch, set())
    assert terminal.resolve(stored="nope", client="nope") == ("xterm", "default")


def test_default_when_nothing_given(monkeypatch):
    _known(monkeypatch, set())
    assert terminal.resolve(stored=None, client="") == ("xterm", "default")


@pytest.mark.parametrize("client", ["", "dumb"])
def test_unusable_client_is_not_resolved_to_itself(monkeypatch, client):
    _known(monkeypatch, {"dumb", ""})
    assert terminal.resolve(stored="vt100", client=client)[1] != "client"


def test_client_read_from_environment(monkeypatch):
    _known(monkeypatch, {"vt100"})
    monkeypatch.setenv("TERM", "vt100")
    assert terminal.resolve() == ("vt100", "client")


def test_notice_when_client_term_has_no_entry(monkeypatch):
    _known(monkeypatch, {"xterm"})
    notice = terminal.resolve_notice(stored=None, client="bogus-term")
    assert "'bogus-term'" in notice
    assert "'xterm'" in notice


def test_no_notice_when_client_term_is_valid(monkeypatch):
    _known(monkeypatch, {"xterm"})
    assert terminal.resolve_notice(stored=None, client="xterm") is None


def test_no_notice_for_unset_or_dumb(monkeypatch):
    _known(monkeypatch, set())
    assert terminal.resolve_notice(stored=None, client="") is None
    assert terminal.resolve_notice(stored=None, client="dumb") is None
