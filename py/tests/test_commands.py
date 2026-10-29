"""Command registry: tiers, collision rules, extend/replace, and resolve outcomes."""

import importlib

import pytest

c = importlib.import_module("bbsengine6.commands")


def _shell(mode=c.MODE_EXTEND):
    r = c.CommandRegistry(mode=mode)
    r.register("logout", c.TIER_PROTECTED, aliases=("lo", "quit", "q", "o", "o!"))
    r.register("message", c.TIER_PROTECTED)
    r.use_default([c.Entry("exit", c.TIER_DEFAULT), c.Entry("murdermotel", c.TIER_DEFAULT)])
    return r


def _seated(state):
    return bool(state and state.get("seat"))


# ---- resolve ----------------------------------------------------------

def test_exact_name_wins():
    kind, entry = _shell().resolve("exit", {})
    assert (kind, entry.name) == (c.RESOLVE_EXACT, "exit")


def test_exact_alias_wins():
    kind, entry = _shell().resolve("lo", {})
    assert (kind, entry.name) == (c.RESOLVE_EXACT, "logout")


def test_unique_prefix_resolves():
    kind, entry = _shell().resolve("murd", {})
    assert (kind, entry.name) == (c.RESOLVE_UNIQUE, "murdermotel")


def test_ambiguous_prefix_runs_nothing():
    r = _shell()
    r.register("mail", c.TIER_DEFAULT)
    r.register("message2", c.TIER_SESSION)
    kind, entry = r.resolve("m", {})
    assert kind == c.RESOLVE_AMBIGUOUS
    assert entry is None


def test_unknown_name_is_none():
    assert _shell().resolve("nosuch", {}) == (c.RESOLVE_NONE, None)


def test_empty_text_is_none():
    assert _shell().resolve("", {}) == (c.RESOLVE_NONE, None)


def test_unavailable_entry_takes_no_part_in_matching():
    r = _shell()
    r.register("hit", c.TIER_SESSION, available=_seated)
    r.register("stand", c.TIER_SESSION, available=_seated)
    # Not seated: "h" is nothing, not an ambiguous or unique match.
    assert r.resolve("h", {"seat": False}) == (c.RESOLVE_NONE, None)
    # Seated: "h" is unique.
    kind, entry = r.resolve("h", {"seat": True})
    assert (kind, entry.name) == (c.RESOLVE_UNIQUE, "hit")


def test_unavailable_exact_name_does_not_run():
    r = _shell()
    r.register("hit", c.TIER_SESSION, available=_seated)
    assert r.resolve("hit", {"seat": False}) == (c.RESOLVE_NONE, None)


def test_st_resolves_to_stand_when_seated():
    r = _shell()
    r.register("stand", c.TIER_SESSION, available=_seated)
    r.register("status", c.TIER_SESSION, available=_seated)
    assert r.resolve("sta", {"seat": True})[0] == c.RESOLVE_AMBIGUOUS
    assert r.resolve("stan", {"seat": True})[1].name == "stand"


def test_resolve_never_returns_candidates():
    # Ambiguous: the payload is None, never a list of names.
    r = _shell()
    r.register("mail", c.TIER_DEFAULT)
    kind, payload = r.resolve("m", {})
    assert kind == c.RESOLVE_AMBIGUOUS
    assert payload is None


def test_candidates_are_for_display_and_respect_availability():
    r = _shell()
    r.register("hit", c.TIER_SESSION, available=_seated)
    assert "hit" not in r.candidates("h", {"seat": False})
    assert "hit" in r.candidates("h", {"seat": True})


def test_broken_predicate_hides_entry_and_does_not_raise():
    r = _shell()
    r.register("boom", c.TIER_SESSION, available=lambda s: 1 / 0)
    assert r.resolve("boom", {}) == (c.RESOLVE_NONE, None)


# ---- tiers and protection ---------------------------------------------

def test_protected_cannot_be_unregistered():
    with pytest.raises(c.CommandError):
        _shell().unregister("logout")


def test_protected_alias_cannot_be_unregistered():
    with pytest.raises(c.CommandError):
        _shell().unregister("q")


def test_protected_cannot_be_overridden_by_name():
    with pytest.raises(c.CommandError):
        _shell().register("logout", c.TIER_SESSION)


def test_protected_alias_cannot_be_overridden():
    with pytest.raises(c.CommandError):
        _shell().register("quit", c.TIER_SESSION)


def test_default_cannot_be_overridden_by_default():
    with pytest.raises(c.CommandError):
        _shell().register("exit", c.TIER_DEFAULT)


def test_unknown_tier_is_rejected():
    with pytest.raises(c.CommandError):
        _shell().register("x", "base")


def test_protected_entries_survive_a_session_replace():
    r = _shell(mode=c.MODE_REPLACE)
    assert {e.name for e in r.entries() if e.tier == c.TIER_PROTECTED} == {"logout", "message"}
    assert c.protected_entry_names(r) == ["logout", "message"]


# ---- override: a session replaces a name and its aliases together -------

def test_session_overrides_default_exit_in_extend_mode():
    r = _shell(mode=c.MODE_EXTEND)
    r.register("exit", c.TIER_SESSION, spec={"action": "leave_casino"})
    kind, entry = r.resolve("exit", {})
    assert (kind, entry.tier, entry.spec) == (c.RESOLVE_EXACT, c.TIER_SESSION, {"action": "leave_casino"})


def test_override_replaces_aliases_together():
    r = _shell()
    # The default exit has no aliases; the session entry brings "bye" as its alias.
    r.register("exit", c.TIER_SESSION, aliases=("bye",), spec={"action": "leave"})
    assert r.lookup("exit").spec == {"action": "leave"}
    assert r.lookup("bye").name == "exit"
    assert r.lookup("bye").tier == c.TIER_SESSION


def test_override_drops_the_old_entrys_other_names():
    r = _shell()
    r.register("exit", c.TIER_SESSION, aliases=("bye",))
    # The new entry owns "exit" and "bye"; no default entry remains under either name.
    assert r.lookup("exit").tier == c.TIER_SESSION
    assert r.lookup("bye").tier == c.TIER_SESSION


def test_session_overrides_session_entry():
    r = _shell()
    r.register("snake", c.TIER_SESSION, spec={"v": 1})
    r.register("snake", c.TIER_SESSION, spec={"v": 2})
    assert r.lookup("snake").spec == {"v": 2}


def test_replace_mode_session_entry_has_no_default_to_override():
    r = _shell(mode=c.MODE_REPLACE)
    assert r.lookup("murdermotel") is None
    r.register("murdermotel", c.TIER_SESSION, spec={"prg": "casino_mm"})
    assert r.lookup("murdermotel").tier == c.TIER_SESSION


def test_invalid_mode_is_rejected():
    with pytest.raises(ValueError):
        c.CommandRegistry(mode="merge")


# ---- independence: registries do not share state -----------------------

def test_two_registries_do_not_share_entries():
    a = _shell()
    b = _shell()
    b.register("hit", c.TIER_SESSION)
    assert a.lookup("hit") is None
    assert b.lookup("hit") is not None


def test_listing_is_sorted_by_name():
    names = [e.name for e in _shell().visible({})]
    assert names == sorted(names)


# ---- default list loading ---------------------------------------------

def test_replace_mode_does_not_load_default_list():
    r = c.CommandRegistry(mode=c.MODE_REPLACE)
    r.use_default([c.Entry("murdermotel", c.TIER_DEFAULT), c.Entry("exit", c.TIER_DEFAULT)])
    assert r.lookup("murdermotel") is None
    assert r.lookup("exit") is None


def test_replace_mode_refuses_registering_a_default_entry():
    r = c.CommandRegistry(mode=c.MODE_REPLACE)
    with pytest.raises(c.CommandError):
        r.register("murdermotel", c.TIER_DEFAULT)


def test_extend_mode_loads_default_list():
    r = c.CommandRegistry(mode=c.MODE_EXTEND)
    r.use_default([c.Entry("murdermotel", c.TIER_DEFAULT)])
    assert r.lookup("murdermotel").tier == c.TIER_DEFAULT


def test_replace_mode_still_holds_protected_and_session_entries():
    r = c.CommandRegistry(mode=c.MODE_REPLACE)
    r.register("logout", c.TIER_PROTECTED, aliases=("lo",))
    r.register("snake", c.TIER_SESSION)
    assert r.lookup("lo").name == "logout"
    assert r.lookup("snake").tier == c.TIER_SESSION
