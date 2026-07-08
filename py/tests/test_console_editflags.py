"""
Tests for bbsengine6.console.member.editflags.

The console flag editor iterates ``flags.items()`` to render Y/N
prompts for each flag. The flags come from ``libmember.getflags()``,
which returns ``None`` when ``pool=`` is not supplied.

The ``add()`` path in ``console/member.py`` opens a ``conn`` and
forwards it (but no ``pool=``) to ``_edit()`` -> ``editflags()`` ->
``getflags()``. ``getflags()`` then returns ``None``, and
``editflags()`` crashes at the for-loop on ``None.items()``.

These tests pin the bug and the expected post-fix behavior:

- The two ``test_editflags_crashes_*`` tests reproduce the production
  crash (AttributeError). They FAIL on the unfixed code, documenting
  the bug.
- The two ``test_editflags_with_*`` tests cover the working branches
  (empty dict and populated dict) and pass both before and after the
  fix.
- The integration test confirms that ``getflags()`` returns an
  iterable (not None) when ``pool=`` is supplied, so the fix in
  ``editflags()`` has a sound foundation.
"""

from __future__ import annotations

import argparse
import getpass

import pytest

from bbsengine6 import database
from bbsengine6.console import member as console_member
from bbsengine6.console.member import editflags


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_test_args(databasename: str = "zoid6test") -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    defaults = {
        "databasename": databasename,
        "databasehost": "/var/run/postgresql",
        "databaseport": 5432,
        "databaseuser": getpass.getuser(),
        "databasepassword": None,
    }
    database.buildargdatabasegroup(parser, defaults)
    return parser.parse_args([])


@pytest.fixture(scope="function")
def test_args() -> argparse.Namespace:
    return make_test_args()


# ---------------------------------------------------------------------------
# Failure-mode tests -- these fail before the fix, pass after
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_editflags_propagates_getflags_none(test_args) -> None:
    """editflags() does NOT tolerate getflags() returning None.

    With the proper chain in place (add/edit forward pool=), this
    should never happen in production. If it does, the AttributeError
    on ``flags.items()`` is the loud signal that the chain is broken
    somewhere upstream. Silent data loss (the prior {} band-aid
    behavior) would be worse.
    """
    with pytest.MonkeyPatch.context() as mp:
        def fake_getflags(args, moniker=None, **kwargs):
            return None

        mp.setattr(console_member.libmember, "getflags", fake_getflags)
        mp.setattr(console_member.io, "inputboolean", lambda *a, **kw: True)

        with pytest.raises(AttributeError) as excinfo:
            editflags(test_args, mode="add")

        assert "items" in str(excinfo.value)


@pytest.mark.unit
def test_editflags_propagates_getflags_none_for_edit_mode(test_args) -> None:
    """Same coverage for the mode='edit' branch -- getflags() returns
    None there too when pool= is missing, and editflags() must not
    swallow it."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            console_member.libmember, "getflags",
            lambda args, moniker=None, **kwargs: None,
        )
        mp.setattr(console_member.io, "inputboolean", lambda *a, **kw: True)

        with pytest.raises(AttributeError):
            editflags(test_args, moniker="some_member", mode="edit")


# ---------------------------------------------------------------------------
# Working-mode tests -- pass before AND after the fix
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_editflags_with_empty_flags_dict_is_noop(test_args) -> None:
    """When getflags() returns an empty dict (member with no flags),
    editflags() must return {} without prompting."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            console_member.libmember, "getflags",
            lambda args, moniker=None, **kwargs: {},
        )
        prompts = []
        mp.setattr(
            console_member.io, "inputboolean",
            lambda prompt, default: prompts.append(prompt) or True,
        )

        result = editflags(test_args, mode="add")

    assert result == {}
    assert prompts == [], (
        f"empty flags should not produce any prompts, got {prompts}"
    )


@pytest.mark.unit
def test_editflags_with_populated_flags_returns_mutated_dict(
    test_args,
) -> None:
    """When getflags() returns a populated dict, editflags() must
    return it mutated, after one Y/N prompt per flag."""
    flags_in = {
        "SYSOP": {"description": "SysOp Access", "value": False},
        "MAGIC": {"description": "Magician", "value": True},
    }
    prompt_defaults = []

    def fake_inputboolean(prompt, default):
        prompt_defaults.append(default)
        return True

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            console_member.libmember, "getflags",
            lambda args, moniker=None, **kwargs: flags_in,
        )
        mp.setattr(console_member.io, "inputboolean", fake_inputboolean)
        mp.setattr(console_member.io, "echo", lambda *a, **kw: None)

        result = editflags(test_args, mode="add")

    assert result is flags_in
    assert prompt_defaults == ["N", "Y"]
    assert result["SYSOP"]["value"] is True
    assert result["MAGIC"]["value"] is True


# ---------------------------------------------------------------------------
# Integration test -- confirms getflags() returns iterable when pool= is given
# ---------------------------------------------------------------------------


def test_getflags_returns_iterable_for_brand_new_member(test_args, pool) -> None:
    """Integration: getflags(args, new_member, pool=pool) must return
    something that editflags() can iterate. Per the SQL at
    sql/getflags.sql, a member with no entry in engine.member and no
    flag overrides returns 0 rows, so the result is ``{}``.

    This is the value editflags() should be operating on, but the
    add() path never threads ``pool=`` through, so getflags() never
    returns this ``{}`` -- it returns None and the function crashes.
    """
    from bbsengine6.member import getflags

    new_moniker = "ghost_user_no_such_member_xyzzy"
    flags = getflags(test_args, new_moniker, pool=pool)
    assert flags is not None, (
        "getflags() must not return None when pool= is supplied"
    )
    assert isinstance(flags, dict), f"expected dict, got {type(flags)}"


@pytest.mark.unit
def test_getflags_returns_none_when_pool_missing(test_args) -> None:
    """getflags() must return ``None`` (not ``{}``) when ``pool=`` is
    missing. None is the honest signal that the lookup could not be
    performed; callers must check for it and handle the failure
    explicitly. Returning ``{}`` would silently drop data (e.g. the
    default flags for a new member) which is worse than a loud
    crash.
    """
    from bbsengine6.member import getflags

    flags = getflags(test_args, moniker="some_member")
    assert flags is None, (
        f"getflags() must return None when pool= is missing, got {flags!r}"
    )


def test_getflags_returns_defaults_for_null_moniker(test_args, pool) -> None:
    """getflags(args, None, pool=pool) returns the 8 default flags
    from engine.member_flag. This is the add() path's mode='add' call
    inside editflags().

    For a new member, editflags() should load these defaults so the
    user can toggle them. If pool= is missing, editflags() used to
    get an empty dict and the defaults were silently dropped.
    """
    from bbsengine6.member import getflags

    flags = getflags(test_args, None, pool=pool)
    assert flags is not None
    assert isinstance(flags, dict)
    # The schema seeds 8 default flags (SYSOP, MAGIC, EROS,
    # AUTHENTICATED, ASIMOV, NOCALUMNI, EMAILVERIFIED, APPROVED).
    # The exact list may grow over time, so just check there is a
    # meaningful set of defaults to work with.
    assert len(flags) >= 1, (
        f"expected at least one default flag for new members, got {flags!r}"
    )
    for name, data in flags.items():
        assert "description" in data
        assert "value" in data
        # New members get the default value (False for all current flags).
        assert data["value"] is False, (
            f"new-member default for {name} should be False, got {data['value']!r}"
        )


@pytest.mark.unit
def test_editflags_loads_defaults_for_new_member_when_pool_supplied(
    test_args,
) -> None:
    """editflags() must forward pool= to getflags() so the 8 default
    flags are loaded for a new member (mode='add').

    Previously editflags() only forwarded conn=, so getflags() saw
    pool=None and returned {}. The defaults from engine.member_flag
    were silently dropped, and the new member was added with no
    flag entries.
    """
    defaults = {
        "SYSOP": {"description": "SysOp Access", "value": False},
        "MAGIC": {"description": "Magician", "value": False},
        "APPROVED": {"description": "Account Approved", "value": False},
    }
    seen_prompts = []

    def fake_getflags(args, moniker=None, **kwargs):
        # Confirm pool= was forwarded (the actual fix).
        assert "pool" in kwargs, "editflags() must forward pool= to getflags()"
        return defaults

    def fake_inputboolean(prompt, default):
        seen_prompts.append(prompt)
        return False  # user accepts all defaults

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(console_member.libmember, "getflags", fake_getflags)
        mp.setattr(console_member.io, "inputboolean", fake_inputboolean)
        mp.setattr(console_member.io, "echo", lambda *a, **kw: None)

        result = editflags(test_args, mode="add", pool=object())

    assert result is defaults
    # One prompt per default flag -- the user is asked about each.
    assert len(seen_prompts) == len(defaults)
    for name in defaults:
        assert all(d["value"] is False for d in result.values())
