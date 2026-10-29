"""bbsengine6.command_runner: dispatch outcomes, messages, and launch through module.run()."""

import argparse

import pytest

from bbsengine6 import command_runner as cr
from bbsengine6 import commands as c


def _shell():
    r = c.CommandRegistry(mode=c.MODE_EXTEND)
    r.register("logout", c.TIER_PROTECTED, aliases=("lo", "q"))
    r.register("message", c.TIER_PROTECTED)
    r.use_default([
        c.Entry("stats", c.TIER_DEFAULT, spec={"prg": "stats"}),
        c.Entry("snake", c.TIER_DEFAULT, spec={"prg": "snake"}),
        c.Entry("sort", c.TIER_DEFAULT, spec={"prg": "sort"}),
        # name differs from prg: launch must use prg, not the typed name.
        c.Entry("hi", c.TIER_DEFAULT, spec={"prg": "highscores"}),
    ])
    return r


# ---- dispatch outcomes -------------------------------------------------

def test_exact_name_runs():
    d = cr.dispatch(_shell(), "logout", {})
    assert (d.outcome, d.entry.name) == (cr.OUTCOME_RUN, "logout")
    assert d.message == ""


def test_exact_alias_runs():
    d = cr.dispatch(_shell(), "lo", {})
    assert (d.outcome, d.entry.name) == (cr.OUTCOME_RUN, "logout")


def test_unique_prefix_runs():
    d = cr.dispatch(_shell(), "sta", {})
    assert (d.outcome, d.entry.name) == (cr.OUTCOME_RUN, "stats")


def test_unknown_name_is_not_found_with_one_line_message():
    d = cr.dispatch(_shell(), "zzz", {})
    assert d.outcome == cr.OUTCOME_NOT_FOUND
    assert d.entry is None
    assert d.message == "command not found zzz"


def test_ambiguous_prefix_runs_nothing_and_says_so_without_candidates():
    d = cr.dispatch(_shell(), "s", {})  # snake, sort, stats
    assert d.outcome == cr.OUTCOME_AMBIGUOUS
    assert d.entry is None
    assert d.message == "ambiguous command s"
    assert "snake" not in d.message and "sort" not in d.message


def test_hidden_entry_takes_no_part():
    r = _shell()
    r.lookup("snake").available = lambda state: False
    d = cr.dispatch(r, "sn", {})
    assert d.outcome == cr.OUTCOME_NOT_FOUND


def test_dispatch_does_not_launch_or_check(monkeypatch):
    """Dispatch only decides; it never reaches module.run() or access()."""
    import bbsengine6.module as module

    calls = []
    monkeypatch.setattr(module, "run", lambda *a, **k: calls.append(("run", a)))
    monkeypatch.setattr(module, "check", lambda *a, **k: calls.append(("check", a)))
    cr.dispatch(_shell(), "stats", {})
    assert calls == []


# ---- launch ------------------------------------------------------------

def test_launch_calls_module_run_with_prg_and_argv(monkeypatch):
    import bbsengine6.module as module

    seen = {}

    def fake_run(args, modulename, **kwargs):
        seen["args"] = args
        seen["modulename"] = modulename
        seen["kwargs"] = kwargs
        return True

    monkeypatch.setattr(module, "run", fake_run)
    args = argparse.Namespace(debug=False)
    entry = _shell().lookup("stats")
    result = cr.launch(entry, args, ["stats", "-v"], pool="P")
    assert result is True
    assert seen["modulename"] == "stats"
    assert seen["kwargs"] == {"argv": ["stats", "-v"], "pool": "P"}


def test_launch_uses_prg_not_the_typed_name(monkeypatch):
    import bbsengine6.module as module

    seen = []
    monkeypatch.setattr(module, "run", lambda args, modulename, **k: seen.append(modulename))
    entry = _shell().lookup("hi")
    cr.launch(entry, argparse.Namespace(debug=False), ["hi"])
    assert seen == ["highscores"]


def test_launch_without_prg_fails_before_running(monkeypatch):
    import bbsengine6.module as module

    calls = []
    monkeypatch.setattr(module, "run", lambda *a, **k: calls.append(a))
    entry = c.Entry("broken", c.TIER_DEFAULT, spec={})
    with pytest.raises(KeyError):
        cr.launch(entry, argparse.Namespace(debug=False), ["broken"])
    assert calls == []


def test_launch_propagates_access_refusal_from_module_run(monkeypatch):
    """module.run() returning False (access refused) is passed back, not swallowed."""
    import bbsengine6.module as module

    monkeypatch.setattr(module, "run", lambda *a, **k: False)
    entry = _shell().lookup("stats")
    assert cr.launch(entry, argparse.Namespace(debug=False), ["stats"]) is False
