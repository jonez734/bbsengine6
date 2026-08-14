"""
Unit tests for ``bbsengine6.auth.access``.

Pins every (op, session, message) branch of the access decision
matrix. These are unit-only: no DB connection required. Run with
``pytest -m unit tests/test_auth_access.py``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bbsengine6.auth import access as auth_access


pytestmark = pytest.mark.unit


def _session(
    moniker: str | None = None,
    *,
    is_sysop: bool = False,
    session_id: str | None = None,
):
    """Build a session-like object with .moniker, .is_sysop, .session_id."""
    return SimpleNamespace(
        moniker=moniker,
        is_sysop=is_sysop,
        session_id=session_id,
    )


# ---------- module-load time ----------


def test_no_session_kwarg_returns_true():
    """bbsengine6.module.check() calls access() with no session kwarg at
    module-load time; access() must return True so the module loads."""
    assert auth_access(None, "run") is True


# ---------- login ----------


def test_login_allowed_for_unbound_session():
    s = _session(None)
    assert auth_access(None, "login", session=s, message={}) is True


def test_login_allowed_for_bound_non_sysop():
    s = _session("alice", is_sysop=False)
    assert auth_access(None, "login", session=s, message={}) is True


def test_login_allowed_for_sysop():
    s = _session("sysop", is_sysop=True)
    assert auth_access(None, "login", session=s, message={}) is True


def test_login_ignores_message_fields():
    """login is a free pass; the credential provider decides. access()
    does not read moniker/password/claims for login."""
    s = _session("alice")
    msg = {"type": "auth", "moniker": "alice", "password": "x"}
    assert auth_access(None, "login", session=s, message=msg) is True


# ---------- reconnect ----------


def test_reconnect_allowed_when_session_is_none():
    """A genuinely None session (no SessionState at all) = reconnect-
    after-restart path. Always passes."""
    msg = {"claims": {"moniker": "alice", "session_id": "s1"}}
    assert auth_access(None, "reconnect", session=None, message=msg) is True


def test_reconnect_denied_when_session_bound_without_moniker():
    """A session exists but has no moniker (degenerate state). The
    conservative default-deny rule fires because _moniker_eq cannot
    prove a match."""
    s = SimpleNamespace(moniker=None, is_sysop=False, session_id="s1")
    msg = {"claims": {"moniker": "alice", "session_id": "s1"}}
    assert auth_access(None, "reconnect", session=s, message=msg) is False


def test_reconnect_allowed_when_session_moniker_matches_token():
    s = _session("alice", is_sysop=False, session_id="s1")
    msg = {"claims": {"moniker": "alice", "session_id": "s1"}}
    assert auth_access(None, "reconnect", session=s, message=msg) is True


def test_reconnect_allowed_when_session_moniker_matches_case_insensitive():
    s = _session("Alice", is_sysop=False, session_id="s1")
    msg = {"claims": {"moniker": "alice", "session_id": "s1"}}
    assert auth_access(None, "reconnect", session=s, message=msg) is True


def test_reconnect_allowed_for_sysop_with_any_token():
    """A sysop session can reconnect anyone's token."""
    s = _session("sysop", is_sysop=True, session_id="s-sysop")
    msg = {"claims": {"moniker": "alice", "session_id": "s-alice"}}
    assert auth_access(None, "reconnect", session=s, message=msg) is True


def test_reconnect_denied_when_session_bound_to_different_moniker():
    """A non-sysop session bound to a different moniker cannot use
    someone else's token to reconnect."""
    s = _session("alice", is_sysop=False, session_id="s1")
    msg = {"claims": {"moniker": "bob", "session_id": "s2"}}
    assert auth_access(None, "reconnect", session=s, message=msg) is False


def test_reconnect_denied_when_token_moniker_missing():
    """If the token has no moniker claim, a non-sysop bound session
    cannot reconnect."""
    s = _session("alice", is_sysop=False, session_id="s1")
    msg = {"claims": {"session_id": "s1"}}
    assert auth_access(None, "reconnect", session=s, message=msg) is False


def test_reconnect_denied_when_message_has_no_claims():
    """If the message carries no claims dict at all, a non-sysop bound
    session cannot reconnect."""
    s = _session("alice", is_sysop=False, session_id="s1")
    assert auth_access(None, "reconnect", session=s, message={}) is False


def test_reconnect_denied_when_session_has_no_moniker():
    """A session without a moniker attribute cannot reconnect (unless
    sysop)."""
    s = SimpleNamespace(moniker=None, is_sysop=False, session_id="s1")
    msg = {"claims": {"moniker": "alice", "session_id": "s1"}}
    assert auth_access(None, "reconnect", session=s, message=msg) is False


# ---------- refresh ----------


def test_refresh_allowed_when_session_id_matches_token():
    s = _session("alice", is_sysop=False, session_id="s1")
    msg = {"claims": {"moniker": "alice", "session_id": "s1"}}
    assert auth_access(None, "refresh", session=s, message=msg) is True


def test_refresh_denied_when_session_id_differs():
    """Refresh on a different websocket is the canonical attack
    vector: this is the session-bound gate."""
    s = _session("alice", is_sysop=False, session_id="s1")
    msg = {"claims": {"moniker": "alice", "session_id": "s2"}}
    assert auth_access(None, "refresh", session=s, message=msg) is False


def test_refresh_denied_when_session_is_none():
    """No live websocket bound means refresh is impossible."""
    s = _session(None, session_id=None)
    msg = {"claims": {"moniker": "alice", "session_id": "s1"}}
    assert auth_access(None, "refresh", session=s, message=msg) is False


def test_refresh_denied_when_token_session_id_missing():
    s = _session("alice", is_sysop=False, session_id="s1")
    msg = {"claims": {"moniker": "alice"}}
    assert auth_access(None, "refresh", session=s, message=msg) is False


def test_refresh_denied_when_message_has_no_claims():
    s = _session("alice", is_sysop=False, session_id="s1")
    assert auth_access(None, "refresh", session=s, message={}) is False


def test_refresh_denied_even_for_sysop_when_session_id_differs():
    """The session-bound gate is not a sysop bypass. A sysop session
    bound to websocket A cannot refresh a token issued for websocket B."""
    s = _session("sysop", is_sysop=True, session_id="s-A")
    msg = {"claims": {"moniker": "alice", "session_id": "s-B"}}
    assert auth_access(None, "refresh", session=s, message=msg) is False


def test_refresh_allowed_for_sysop_when_session_id_matches():
    s = _session("sysop", is_sysop=True, session_id="s1")
    msg = {"claims": {"moniker": "sysop", "session_id": "s1"}}
    assert auth_access(None, "refresh", session=s, message=msg) is True


# ---------- revoke ----------


def test_revoke_allowed_for_unbound_session():
    """Revoke is a free pass once the handler has verified the
    signature; no live session required."""
    s = _session(None)
    msg = {"claims": {"moniker": "alice", "session_id": "s1"}}
    assert auth_access(None, "revoke", session=s, message=msg) is True


def test_revoke_allowed_for_bound_session():
    s = _session("alice", is_sysop=False, session_id="s1")
    msg = {"claims": {"moniker": "alice", "session_id": "s1"}}
    assert auth_access(None, "revoke", session=s, message=msg) is True


def test_revoke_allowed_for_sysop():
    s = _session("sysop", is_sysop=True, session_id="s-sysop")
    msg = {"claims": {"moniker": "alice", "session_id": "s-alice"}}
    assert auth_access(None, "revoke", session=s, message=msg) is True


def test_revoke_allowed_even_when_session_id_differs():
    """Revoke does not gate on session_id match -- it's a free pass
    on signature validity, which the handler has already verified."""
    s = _session("alice", is_sysop=False, session_id="s1")
    msg = {"claims": {"moniker": "alice", "session_id": "s2"}}
    assert auth_access(None, "revoke", session=s, message=msg) is True


# ---------- unknown op ----------


def test_unknown_op_denied():
    s = _session("alice", is_sysop=True, session_id="s1")
    assert auth_access(None, "totally-unknown-op", session=s, message={}) is False


# ---------- kwarg shape ----------


def test_session_kwarg_explicitly_none_denies_refresh():
    """Explicitly passing session=None must deny refresh even if the
    message carries claims."""
    msg = {"claims": {"moniker": "alice", "session_id": "s1"}}
    assert auth_access(None, "refresh", session=None, message=msg) is False


def test_message_kwarg_missing_treated_as_empty_dict():
    """A missing message kwarg is the same as message={} -- never
    raises, just returns False/True per the op's policy."""
    s = _session("alice", is_sysop=False, session_id="s1")
    assert auth_access(None, "refresh", session=s) is False
    assert auth_access(None, "login", session=s) is True


def test_message_kwarg_non_dict_treated_as_empty_dict():
    """A malformed message kwarg (not a dict) is treated as empty."""
    s = _session("alice", is_sysop=False, session_id="s1")
    assert auth_access(None, "refresh", session=s, message="not a dict") is False
    assert auth_access(None, "login", session=s, message=42) is True


def test_claims_subdict_non_dict_treated_as_empty():
    """message["claims"] that isn't a dict is treated as empty."""
    s = _session("alice", is_sysop=False, session_id="s1")
    msg = {"claims": "not a dict"}
    assert auth_access(None, "refresh", session=s, message=msg) is False
    assert auth_access(None, "reconnect", session=s, message=msg) is False


# ---------- arity ----------


def test_access_takes_args_op_and_keyword_only_kwargs():
    """access() must accept args and op positionally, then kwargs only.

    Pins the signature contract from bbsengine6.module._stub_access:
    def _stub_access(args, op, /, **kwargs) -> bool | None

    Calling it with extra positional args must raise.
    """
    import argparse

    args = argparse.Namespace()
    # Legal: args + op + kwargs
    assert callable(auth_access)
    # The positional-only `/` separator means a third positional
    # argument would be a TypeError, not silently ignored.
    with pytest.raises(TypeError):
        auth_access(args, "login", "extra-positional")  # type: ignore[misc]
