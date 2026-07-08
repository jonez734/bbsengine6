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
def test_editflags_handles_getflags_returning_none(test_args) -> None:
    """editflags() must not crash when getflags() returns None.

    Previously the function did ``for ... in flags.items()`` on the
    return value of getflags(), which is None whenever pool= is
    missing (the add() path never threads pool= through). The fix
    coerces None to {} so the for-loop is a no-op.
    """
    with pytest.MonkeyPatch.context() as mp:
        def fake_getflags(args, moniker=None, **kwargs):
            return None

        mp.setattr(console_member.libmember, "getflags", fake_getflags)
        mp.setattr(console_member.io, "inputboolean", lambda *a, **kw: True)

        result = editflags(test_args, mode="add")

    assert result == {}, (
        "editflags() should treat None from getflags() as an empty "
        "flags dict and return {}"
    )


@pytest.mark.unit
def test_editflags_handles_getflags_returning_none_for_edit_mode(
    test_args,
) -> None:
    """Same coverage for the mode='edit' branch -- getflags() returns
    None there too when pool= is missing."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            console_member.libmember, "getflags",
            lambda args, moniker=None, **kwargs: None,
        )
        mp.setattr(console_member.io, "inputboolean", lambda *a, **kw: True)

        result = editflags(test_args, moniker="some_member", mode="edit")

    assert result == {}


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
def test_getflags_returns_empty_dict_when_pool_missing(test_args) -> None:
    """getflags() must return ``{}`` (not None) when ``pool=`` is
    missing. Callers like ``editflags()`` iterate the result with
    ``for ... in flags.items()``; a None result crashes the caller.

    This pins the fix at the source: getflags() never returns None,
    it returns an empty dict when it can't perform the lookup.
    """
    from bbsengine6.member import getflags

    flags = getflags(test_args, moniker="some_member")
    assert flags == {}, (
        f"getflags() must return {{}} when pool= is missing, got {flags!r}"
    )
    assert flags is not None, "getflags() must not return None"
