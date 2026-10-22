"""The session idle window is configurable; the default is 15 minutes.

updatelastactivity extends a session's expiry by the idle window. The window
is set by session.configure(idle_minutes=...) from the host application, the
same way message.configure is used. The buildsession creation window (2 hours)
is separate and not changed.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.session import lib as session_lib


@pytest.fixture(autouse=True)
def restore_window():
    before = session_lib.get_idle_minutes()
    yield
    session_lib.configure(idle_minutes=before)


@pytest.mark.unit
def test_default_idle_window_is_15_minutes():
    session_lib.configure(idle_minutes=None)
    assert session_lib.get_idle_minutes() == 15


@pytest.mark.unit
def test_configure_sets_idle_window():
    session_lib.configure(idle_minutes=30)
    assert session_lib.get_idle_minutes() == 30


@pytest.mark.unit
@pytest.mark.parametrize("bad", [0, -5, "15", 1.5, True])
def test_configure_rejects_bad_values(bad):
    with pytest.raises(ValueError):
        session_lib.configure(idle_minutes=bad)


@pytest.mark.unit
def test_updatelastactivity_uses_configured_window():
    session_lib.configure(idle_minutes=30)
    args = MagicMock(debug=False)
    conn = MagicMock()
    session = {"id": "s1", "expiry": datetime.now(timezone.utc)}
    written = {}
    with patch.object(session_lib, "read", return_value=session), \
         patch.object(session_lib, "write", side_effect=lambda a, s, sid, **kw: written.update(s)):
        session_lib.updatelastactivity(args, "s1", conn=conn)
    remaining = written["expiry"] - datetime.now(timezone.utc)
    assert timedelta(minutes=29) < remaining <= timedelta(minutes=30)


@pytest.mark.unit
def test_buildsession_creation_window_unchanged():
    session_lib.configure(idle_minutes=5)
    assert "hours=2" in open(session_lib.__file__).read()
