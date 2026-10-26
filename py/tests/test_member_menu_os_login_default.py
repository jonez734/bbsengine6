"""The [O] OS login line shows the value the [O] prompt will default to.

[L] loginid is the member's login name. [O] OS login is the OS username stored in engine.pgrole.
With no stored OS login, [O] defaults to the loginid, so the menu line shows that default.
"""

import pytest

from bbsengine6.console import member as cm


def _osline(member):
    import io as _io
    from unittest.mock import patch

    out = []
    with patch.object(cm.io, "echo", side_effect=lambda *a, **k: out.append(str(a[0]) if a else "")):
        cm.render_member(None, member=member, _member=dict(member))
    return next(line for line in out if "[O]" in line)


@pytest.mark.unit
def test_no_stored_os_login_shows_the_loginid():
    line = _osline({"moniker": "lo_test", "loginid": "lo_test", "osuser": None,
                    "email": "e", "credits": 1, "flags": {}, "ui": ["term"], "password": None, "tz": None, "attrs": {}, "datecreated": None})
    assert "lo_test" in line
    assert "(none)" not in line


@pytest.mark.unit
def test_the_loginid_wins_over_a_stored_os_login():
    line = _osline({"moniker": "lo_test", "loginid": "lo_test", "osuser": "opsbob",
                    "email": "e", "credits": 1, "flags": {}, "ui": ["term"], "password": None, "tz": None, "attrs": {}, "datecreated": None})
    assert "lo_test" in line
    assert "opsbob" not in line


@pytest.mark.unit
def test_no_loginid_and_no_os_login_shows_none():
    line = _osline({"moniker": "x", "loginid": None, "osuser": None,
                    "email": "e", "credits": 1, "flags": {}, "ui": ["term"], "password": None, "tz": None, "attrs": {}, "datecreated": None})
    assert "(none)" in line
