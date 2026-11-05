"""run_child passes the resolved TERM to the child and keeps the dumb/empty refusal."""

import pytest

from bbsengine6 import subprocess_command as sc
from bbsengine6.io import terminal


class _Sess:
    subprocess_term_check = True


@pytest.fixture
def captured(monkeypatch):
    calls = {}

    class _Done:
        returncode = 0

    def fake_run(argv, env=None, check=False):
        calls["env"] = env
        return _Done()

    monkeypatch.setattr(sc.subprocess, "run", fake_run)
    monkeypatch.setattr(sc, "current_session", lambda: _Sess())
    monkeypatch.setattr(sc, "redraw_all", lambda *a, **k: None)
    monkeypatch.setattr(terminal, "resolve", lambda stored=None, client=None: ("vt100", "stored"))
    import bbsengine6.io.common as common

    monkeypatch.setattr(common, "end_raw_session", lambda: None)
    return calls


def test_child_env_gets_resolved_term(captured, monkeypatch):
    monkeypatch.setenv("TERM", "xterm")
    sc.run_child(["true"], stored_term="vt100")
    assert captured["env"]["TERM"] == "vt100"


def test_child_env_does_not_mutate_callers_env(captured, monkeypatch):
    monkeypatch.setenv("TERM", "xterm")
    base = {"PATH": "/bin", "TERM": "xterm"}
    sc.run_child(["true"], env=base, stored_term="vt100")
    assert base == {"PATH": "/bin", "TERM": "xterm"}
    assert captured["env"]["TERM"] == "vt100"
    assert captured["env"]["PATH"] == "/bin"


def test_dumb_term_still_refused(monkeypatch):
    monkeypatch.setattr(sc, "current_session", lambda: _Sess())
    monkeypatch.setenv("TERM", "dumb")
    with pytest.raises(sc.SubprocessCommandError):
        sc.run_child(["true"])
