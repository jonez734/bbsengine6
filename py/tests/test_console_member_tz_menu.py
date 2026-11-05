"""[T] time zone menu option in the member console.

The answer is checked against pg_timezone_names before it is kept. A blank answer clears the stored
zone so the member uses the configured default. Nothing is written by the menu itself; the member
dict carries the choice and the normal update saves it.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import member as libmember
from bbsengine6.console import member as console_member


def _member(**over):
    m = {"moniker": "lo_test", "loginid": "lo_test", "email": "x@y", "ui": None,
         "credits": 0, "refcode": None, "flags": {}, "password": None,
         "psqlrole": None, "tz": None}
    m.update(over)
    return m


def _conn(known: bool):
    """A connection whose pg_timezone_names lookup finds the name only when ``known``."""
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,) if known else None
    return conn


def _run_edit(choices, member, *, conn, answers=()):
    seq = iter(choices)
    ans = iter(answers)
    cursor = conn.cursor.return_value.__enter__.return_value
    with patch.object(console_member.io, "inputchoice", side_effect=lambda *a, **k: next(seq)), \
         patch.object(console_member.io, "inputstring", side_effect=lambda *a, **k: next(ans, "")), \
         patch.object(console_member.util, "heading"), \
         patch("bbsengine6.console.member.io.echo"), \
         patch.object(console_member, "render_member"), \
         patch.object(console_member.database, "cursor") as cur_factory:
        cur_factory.return_value.__enter__.return_value = cursor
        return console_member._edit(object(), "edit", member, conn=conn)


@pytest.mark.unit
def test_tz_option_is_offered_in_the_menu_keys():
    """The T key is on the menu's input choice set, next to the other single-letter options."""
    import inspect
    src = inspect.getsource(console_member._edit)
    assert '"LMECPFDTYURQX"' in src and "[MECPFDTYURQX]" in src


@pytest.mark.unit
def test_known_zone_is_stored_on_the_member():
    m = _member()
    out = _run_edit(["T", "Q"], m, conn=_conn(known=True), answers=["Europe/Paris"])
    assert out["tz"] == "Europe/Paris"


@pytest.mark.unit
def test_unknown_zone_is_refused_and_the_stored_value_is_kept():
    m = _member(tz="America/Chicago")
    out = _run_edit(["T", "Q"], m, conn=_conn(known=False), answers=["Not/AZone"])
    assert out["tz"] == "America/Chicago"


@pytest.mark.unit
def test_blank_answer_clears_to_the_default():
    m = _member(tz="America/Chicago")
    out = _run_edit(["T", "Q"], m, conn=_conn(known=True), answers=[""])
    assert out["tz"] is None


@pytest.mark.unit
def test_default_is_the_configured_value_and_defaults_to_est5edt(monkeypatch):
    monkeypatch.setattr(libmember.lib, "_DEFAULT_TZ", "America/New_York")
    assert libmember.default_tz() == "America/New_York"
    libmember.configure_default_tz("Europe/Paris")
    try:
        assert libmember.default_tz() == "Europe/Paris"
    finally:
        libmember.configure_default_tz("America/New_York")


@pytest.mark.unit
def test_configure_default_tz_refuses_a_blank_value():
    with pytest.raises(ValueError):
        libmember.configure_default_tz("   ")


@pytest.mark.unit
def test_build_loads_tz_with_the_configured_default_when_absent(monkeypatch):
    monkeypatch.setattr(libmember.lib, "_DEFAULT_TZ", "America/New_York")
    pool = object()
    with patch.object(libmember, "getflags", return_value={}):
        m = libmember.build(object(), {"moniker": "x"}, pool=pool)
    assert m["tz"] == "America/New_York"
