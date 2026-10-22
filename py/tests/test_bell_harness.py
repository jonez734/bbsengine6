"""scripts/bell_harness.py: a logged-in terminal session that shows the notification bell.

The harness logs a member in with member.checkpassword, sets the session moniker
the way the login path does, and then waits for keys with getch_str, which rings
the bell when unread messages exist for that moniker.
"""

import importlib.util
import pathlib
from unittest.mock import MagicMock, patch

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "bell_harness.py"


@pytest.fixture(scope="module")
def harness():
    spec = importlib.util.spec_from_file_location("bell_harness", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_login_returns_moniker_on_success(harness):
    with patch.object(harness, "member") as m:
        m.checkpassword.return_value = True
        assert harness.login(MagicMock(), "alice", "pw") == "alice"
        m.checkpassword.assert_called_once()


@pytest.mark.unit
def test_login_refused_on_bad_password(harness):
    with patch.object(harness, "member") as m:
        m.checkpassword.return_value = False
        assert harness.login(MagicMock(), "alice", "wrong") is None


@pytest.mark.unit
def test_login_sets_session_moniker_for_the_bell(harness):
    with patch.object(harness, "member") as m, patch.object(harness, "_threadlocal") as tl:
        m.checkpassword.return_value = True
        harness.login(MagicMock(), "bob", "pw")
    assert tl.moniker == "bob"


@pytest.mark.unit
def test_loop_stops_on_quit_key(harness):
    keys = iter([None, None, "q"])
    with patch.object(harness, "getch_str", side_effect=lambda **kw: next(keys)):
        seen = harness.wait_loop(timeout=0.01, max_iterations=10)
    assert seen == 3


@pytest.mark.unit
def test_loop_is_bounded(harness):
    with patch.object(harness, "getch_str", return_value=None):
        assert harness.wait_loop(timeout=0.01, max_iterations=4) == 4


@pytest.mark.unit
def test_password_not_echoed(harness, capsys):
    with patch.object(harness, "member") as m, patch.object(harness, "_threadlocal"):
        m.checkpassword.return_value = True
        harness.login(MagicMock(), "alice", "very-secret-pw-123")
    out = capsys.readouterr()
    assert "very-secret-pw-123" not in out.out and "very-secret-pw-123" not in out.err
