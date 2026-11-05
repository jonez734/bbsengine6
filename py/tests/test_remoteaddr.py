"""getremoteaddr / remoteaddr_source: utmp first, the SSH environment as a sanity check and fallback."""

from unittest.mock import patch

import pytest

from bbsengine6 import util


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("SSH_CLIENT", "SSH_CONNECTION"):
        monkeypatch.delenv(var, raising=False)


def _utmp(addr):
    return patch("bbsengine6.utmp.current_origin", return_value=addr)


def test_utmp_wins_when_present(monkeypatch):
    monkeypatch.setenv("SSH_CLIENT", "203.0.113.9 50000 22")
    with _utmp("203.0.113.9"):
        assert util.getremoteaddr() == "203.0.113.9"
        assert util.remoteaddr_source() == "utmp"


def test_utmp_ipv6_is_returned(monkeypatch):
    monkeypatch.setenv("SSH_CONNECTION", "2001:db8::7 50000 2001:db8::1 22")
    with _utmp("2001:db8::7"):
        assert util.getremoteaddr() == "2001:db8::7"
        assert util.remoteaddr_source() == "utmp"


def test_mismatch_logs_and_keeps_utmp(monkeypatch):
    monkeypatch.setenv("SSH_CLIENT", "198.51.100.1 50000 22")
    with _utmp("203.0.113.9"), patch("bbsengine6.util.io.echo") as echo:
        assert util.getremoteaddr() == "203.0.113.9"
    assert echo.called
    assert "mismatch" in echo.call_args.args[0]
    assert echo.call_args.kwargs.get("level") == "warning"


def test_agreement_does_not_log(monkeypatch):
    monkeypatch.setenv("SSH_CLIENT", "203.0.113.9 50000 22")
    with _utmp("203.0.113.9"), patch("bbsengine6.util.io.echo") as echo:
        util.getremoteaddr()
    echo.assert_not_called()


def test_environment_used_when_utmp_has_nothing(monkeypatch):
    monkeypatch.setenv("SSH_CONNECTION", "203.0.113.9 50000 198.51.100.2 22")
    with _utmp(None):
        assert util.getremoteaddr() == "203.0.113.9"
        assert util.remoteaddr_source() == "ssh_env"


def test_ssh_client_used_before_connection_when_both_set(monkeypatch):
    monkeypatch.setenv("SSH_CLIENT", "203.0.113.9 50000 22")
    monkeypatch.setenv("SSH_CONNECTION", "203.0.113.9 50000 198.51.100.2 22")
    with _utmp(None):
        assert util.getremoteaddr() == "203.0.113.9"


def test_malformed_environment_is_ignored(monkeypatch):
    monkeypatch.setenv("SSH_CLIENT", "not-an-address 50000 22")
    with _utmp(None):
        assert util.getremoteaddr() is None
        assert util.remoteaddr_source() is None


def test_nothing_available_is_none(monkeypatch):
    with _utmp(None):
        assert util.getremoteaddr() is None
        assert util.remoteaddr_source() is None


def test_ipv6_environment_address_is_normalised(monkeypatch):
    monkeypatch.setenv("SSH_CLIENT", "2001:0DB8:0000::0007 50000 22")
    with _utmp(None):
        assert util.getremoteaddr() == "2001:db8::7"


def test_current_account_is_the_effective_user():
    import os
    import pwd

    assert util.current_account() == pwd.getpwuid(os.geteuid()).pw_name


def test_current_account_none_for_unknown_uid():
    with patch("os.geteuid", return_value=987654):
        assert util.current_account() is None
