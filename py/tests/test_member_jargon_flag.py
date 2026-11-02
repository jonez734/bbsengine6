"""The JARGON member flag: can_write_jargon allows a JARGON holder and any sysop, and refuses others.

checkflag and issysop are patched so the rule is tested without a database. The flag itself is
seeded in sql/flagdata.sql and checked in SQL by engine.checkmemberflag.
"""

from unittest.mock import patch

import pytest

from bbsengine6.member import lib as libmember


def _flags(**held):
    """Return a checkflag stub: True for each flag named in ``held``, False otherwise."""
    def fake(args, flag, moniker=None, **kwargs):
        return bool(held.get(flag.lower()))
    return fake


@pytest.mark.unit
def test_jargon_holder_may_write():
    with patch.object(libmember, "checkflag", side_effect=_flags(jargon=True)):
        assert libmember.can_write_jargon(object(), moniker="alice") is True


@pytest.mark.unit
def test_sysop_may_write_without_the_jargon_flag():
    with patch.object(libmember, "checkflag", side_effect=_flags(sysop=True)):
        assert libmember.can_write_jargon(object(), moniker="root") is True


@pytest.mark.unit
def test_member_without_the_flag_is_refused():
    with patch.object(libmember, "checkflag", side_effect=_flags()):
        assert libmember.can_write_jargon(object(), moniker="bob") is False


@pytest.mark.unit
def test_unknown_member_is_refused():
    """checkflag returns None when it cannot decide; that must not allow a write."""
    with patch.object(libmember, "checkflag", return_value=None):
        assert libmember.can_write_jargon(object(), moniker="ghost") is False


@pytest.mark.unit
def test_flag_is_seeded_in_flagdata_sql():
    from pathlib import Path
    seed = Path(libmember.__file__).parents[1] / "sql" / "flagdata.sql"
    assert "'JARGON'" in seed.read_text()
