"""
Integration tests for ``bbsengine6.bank.api.handler._check_auth``.

Verifies that the WebSocket dispatch entry point delegates
authorization to ``bbsengine6.bank.access`` rather than to its own
inline checks. These are unit-only: no DB connection, no live
websocket. Run with ``pytest -m unit tests/test_bank_handler_auth.py``.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from bbsengine6.bank.api.handler import _check_auth
from bbsengine6.session import SessionManager


pytestmark = pytest.mark.unit


class _FakeBankService:
    """Stand-in for BankService: records calls so we can assert on them."""

    def __init__(self):
        self.calls = []
        self.account = _FakeAccount()

    def get_balance(self, moniker):
        self.calls.append(("get_balance", moniker))
        return 100

    def add_funds(self, moniker, amount, **kw):
        self.calls.append(("add_funds", moniker, amount))
        return {"success": True, "new_balance": 200}

    def remove_funds(self, moniker, amount, **kw):
        self.calls.append(("remove_funds", moniker, amount))
        return {"success": True, "new_balance": 50}

    def transfer(self, frm, to, amount, requested_by):
        self.calls.append(("transfer", frm, to, amount, requested_by))
        return {"success": True, "transfer_id": 7}

    def approve_transfer(self, tid, responded_by):
        self.calls.append(("approve_transfer", tid, responded_by))
        return {"success": True, "from_balance": 0, "to_balance": 200}

    def reject_transfer(self, tid, responded_by):
        self.calls.append(("reject_transfer", tid, responded_by))
        return {"success": True}

    def get_pending_transfers(self, moniker, is_sysop):
        self.calls.append(("get_pending_transfers", moniker, is_sysop))
        return []

    def get_history(self, moniker, limit):
        self.calls.append(("get_history", moniker, limit))
        return []


class _FakeAccount:
    def get(self, moniker):
        return {"maxtransfer": 1000}


@pytest.fixture
def sessions():
    return SessionManager()


# ---------- _check_auth unit tests ----------


@pytest.mark.parametrize(
    "msg_type",
    [
        "bank_balance", "bank_add", "bank_remove", "bank_history",
        "bank_pending", "bank_transfer_request", "bank_transfer_approve",
        "bank_transfer_reject", "bank_list_all",
    ],
)
def test_check_auth_denies_unbound_websocket(msg_type, sessions):
    """No SessionManager entry for the session id -> forbidden."""
    err = _check_auth(None, msg_type, 999, {"moniker": "alice"}, sessions)
    assert err == {"type": "error", "code": "forbidden", "message": "not authorized"}


def test_check_auth_denies_other_users_account():
    sessions = SessionManager()
    sessions.register_session(1, "alice", is_sysop=False)
    err = _check_auth(None, "bank_balance", 1, {"moniker": "bob"}, sessions)
    assert err["code"] == "forbidden"


def test_check_auth_allows_self_account():
    sessions = SessionManager()
    sessions.register_session(1, "alice", is_sysop=False)
    assert _check_auth(None, "bank_balance", 1, {"moniker": "alice"}, sessions) is None


def test_check_auth_allows_sysop_any_account():
    sessions = SessionManager()
    sessions.register_session(1, "root", is_sysop=True)
    assert _check_auth(None, "bank_balance", 1, {"moniker": "alice"}, sessions) is None


def test_check_auth_denies_non_sysop_list_all():
    sessions = SessionManager()
    sessions.register_session(1, "alice", is_sysop=False)
    err = _check_auth(None, "bank_list_all", 1, {}, sessions)
    assert err["code"] == "forbidden"


def test_check_auth_allows_sysop_list_all():
    sessions = SessionManager()
    sessions.register_session(1, "root", is_sysop=True)
    assert _check_auth(None, "bank_list_all", 1, {}, sessions) is None


def test_check_auth_denies_transfer_from_other_users_account():
    sessions = SessionManager()
    sessions.register_session(1, "alice", is_sysop=False)
    err = _check_auth(
        None, "bank_transfer_request", 1,
        {"from": "bob", "to": "carol", "amount": 10, "requested_by": "alice"},
        sessions,
    )
    assert err["code"] == "forbidden"


def test_check_auth_allows_own_transfer():
    sessions = SessionManager()
    sessions.register_session(1, "alice", is_sysop=False)
    assert _check_auth(
        None, "bank_transfer_request", 1,
        {"from": "alice", "to": "bob", "amount": 10, "requested_by": "alice"},
        sessions,
    ) is None


def test_check_auth_denies_zero_transfer_id():
    sessions = SessionManager()
    sessions.register_session(1, "bob", is_sysop=False)
    err = _check_auth(
        None, "bank_transfer_approve", 1,
        {"transfer_id": 0}, sessions,
    )
    assert err["code"] == "forbidden"


def test_check_auth_denies_unknown_message_type():
    sessions = SessionManager()
    sessions.register_session(1, "alice", is_sysop=False)
    err = _check_auth(None, "not_a_bank_op", 1, {}, sessions)
    assert err == {"type": "error", "code": "unknown_operation"}


def test_check_auth_passes_through_claims_when_present():
    """A sysop claim lifts the ownership gate even if the session
    in-memory state says non-sysop. Pins that the handler delegates
    to bank_access and does not second-guess."""
    sessions = SessionManager()
    sessions.register_session(1, "alice", is_sysop=False)
    msg = {
        "moniker": "bob",
        "claims": {"moniker": "root", "is_sysop": True},
    }
    assert _check_auth(None, "bank_balance", 1, msg, sessions) is None


# ---------- handle_message integration ----------


class _WS:
    """Plain websocket stand-in. id(self) is the session key."""
    pass


def test_handle_message_denies_when_session_unbound(monkeypatch, sessions):
    """handle_message returns the forbidden envelope when the websocket
    has no session_manager entry."""
    from bbsengine6.bank.api.handler import BankServiceHandler

    handler = BankServiceHandler(SimpleNamespace(), sessions)
    fake_bank = _FakeBankService()
    monkeypatch.setattr(handler, "bank_service", fake_bank)

    ws = _WS()
    result = asyncio.run(
        handler.handle_message(
            None, ws, "/bank",
            {"type": "bank_balance", "moniker": "alice"},
        )
    )
    assert result == {"type": "error", "code": "forbidden", "message": "not authorized"}
    assert fake_bank.calls == []


def test_handle_message_passes_through_on_allowed(monkeypatch, sessions):
    from bbsengine6.bank.api.handler import BankServiceHandler

    ws = _WS()
    sessions.register_session(id(ws), "alice", is_sysop=False)

    handler = BankServiceHandler(SimpleNamespace(), sessions)
    fake_bank = _FakeBankService()
    monkeypatch.setattr(handler, "bank_service", fake_bank)

    result = asyncio.run(
        handler.handle_message(
            None, ws, "/bank",
            {"type": "bank_balance", "moniker": "alice"},
        )
    )
    assert result["type"] == "bank_balance"
    assert result["moniker"] == "alice"
    assert fake_bank.calls == [("get_balance", "alice")]


# ---------- token-claims path (existing token reused on bank ops) ----------
#
# When the auth handler (bed/api/auth.py) verifies a bearer token for
# an incoming bank message, it stashes the decoded claims under
# ``message["claims"]``. The bank WS handler must forward those claims
# unchanged into ``bank_access`` so that the claim-derived
# ``moniker`` / ``is_sysop`` take precedence over the in-memory
# session attributes (which can be stale or tampered with).


def test_handle_message_uses_existing_token_claims_for_self_op(monkeypatch, sessions):
    """The live session belongs to 'mallory', but the message carries
    a verified token whose claims say 'alice' owns the target. The
    bank handler must authorize on the claims, not the session."""
    from bbsengine6.bank.api.handler import BankServiceHandler

    ws = _WS()
    sessions.register_session(id(ws), "mallory", is_sysop=False)

    handler = BankServiceHandler(SimpleNamespace(), sessions)
    fake_bank = _FakeBankService()
    monkeypatch.setattr(handler, "bank_service", fake_bank)

    msg = {
        "type": "bank_balance",
        "moniker": "alice",
        "claims": {"moniker": "alice", "is_sysop": False, "session_id": "tok-1"},
    }
    result = asyncio.run(handler.handle_message(None, ws, "/bank", msg))

    assert result["type"] == "bank_balance"
    assert fake_bank.calls == [("get_balance", "alice")]


def test_handle_message_token_sysop_overrides_non_sysop_session(monkeypatch, sessions):
    """A token whose claims say is_sysop=True must lift the
    ownership gate even when the in-memory session is non-sysop.
    This is the 'existing sysop token' path."""
    from bbsengine6.bank.api.handler import BankServiceHandler

    ws = _WS()
    sessions.register_session(id(ws), "root", is_sysop=False)

    handler = BankServiceHandler(SimpleNamespace(), sessions)
    fake_bank = _FakeBankService()
    monkeypatch.setattr(handler, "bank_service", fake_bank)

    msg = {
        "type": "bank_balance",
        "moniker": "alice",
        "claims": {"moniker": "root", "is_sysop": True, "session_id": "tok-root"},
    }
    result = asyncio.run(handler.handle_message(None, ws, "/bank", msg))

    assert result["type"] == "bank_balance"
    assert fake_bank.calls == [("get_balance", "alice")]


def test_handle_message_token_authorizes_list_all_for_sysop(monkeypatch, sessions):
    """An existing sysop token on the message must unlock list_all
    even when the in-memory session is not sysop (e.g., demoted).
    Patches out the DB read since list_all queries bank.__account."""
    from bbsengine6.bank.api.handler import BankServiceHandler

    ws = _WS()
    sessions.register_session(id(ws), "root", is_sysop=False)

    handler = BankServiceHandler(SimpleNamespace(), sessions)

    class _Ctx:
        def __enter__(self_inner):
            class _Cur:
                def __enter__(self_cur):
                    return self_cur

                def __exit__(self_cur, *exc):
                    return False

                def execute(self_cur, *a, **kw):
                    return self_cur

                def __iter__(self_cur):
                    return iter([])

            return _Cur()

        def __exit__(self_inner, *exc):
            return False

    monkeypatch.setattr("bbsengine6.bank.api.handler.database.connect", lambda *a, **kw: _Ctx())
    monkeypatch.setattr("bbsengine6.bank.api.handler.database.cursor", lambda conn: _Ctx())

    msg = {"type": "bank_list_all", "claims": {"moniker": "root", "is_sysop": True}}
    result = asyncio.run(handler.handle_message(None, ws, "/bank", msg))

    assert result["type"] == "bank_list_all"


def test_handle_message_token_authorizes_transfer_from_own_account(monkeypatch, sessions):
    """A transfer whose ``from`` matches the token's moniker is
    allowed even when the in-memory session was tampered to a
    different moniker. Pins that claims are forwarded into
    bank_access unchanged."""
    from bbsengine6.bank.api.handler import BankServiceHandler

    ws = _WS()
    sessions.register_session(id(ws), "mallory", is_sysop=False)

    handler = BankServiceHandler(SimpleNamespace(), sessions)
    fake_bank = _FakeBankService()
    monkeypatch.setattr(handler, "bank_service", fake_bank)

    msg = {
        "type": "bank_transfer_request",
        "from": "alice",
        "to": "bob",
        "amount": 1,
        "claims": {"moniker": "alice", "is_sysop": False, "session_id": "tok-1"},
    }
    result = asyncio.run(handler.handle_message(None, ws, "/bank", msg))

    assert result["type"] == "bank_transfer_request"
    assert fake_bank.calls == [("transfer", "alice", "bob", 1, "mallory")]


def test_handle_message_token_denies_transfer_from_other_account(monkeypatch, sessions):
    """If the session says 'alice' but the token's claims say 'bob',
    a transfer from alice is denied. The claim wins."""
    from bbsengine6.bank.api.handler import BankServiceHandler

    ws = _WS()
    sessions.register_session(id(ws), "alice", is_sysop=False)

    handler = BankServiceHandler(SimpleNamespace(), sessions)
    fake_bank = _FakeBankService()
    monkeypatch.setattr(handler, "bank_service", fake_bank)

    msg = {
        "type": "bank_transfer_request",
        "from": "alice",
        "to": "bob",
        "amount": 1,
        "claims": {"moniker": "bob", "is_sysop": False, "session_id": "tok-bob"},
    }
    result = asyncio.run(handler.handle_message(None, ws, "/bank", msg))

    assert result == {"type": "error", "code": "forbidden", "message": "not authorized"}
    assert fake_bank.calls == []


def test_handle_message_token_demoted_to_non_sysop_blocks_other_account(monkeypatch, sessions):
    """If the token was demoted (claims say is_sysop=False) but the
    stale session is still sysop, the claim wins and ops against an
    unrelated account are denied. Pins that claims are the source of
    truth, not the in-memory session."""
    from bbsengine6.bank.api.handler import BankServiceHandler

    ws = _WS()
    sessions.register_session(id(ws), "alice", is_sysop=True)

    handler = BankServiceHandler(SimpleNamespace(), sessions)
    fake_bank = _FakeBankService()
    monkeypatch.setattr(handler, "bank_service", fake_bank)

    msg = {
        "type": "bank_balance",
        "moniker": "bob",
        "claims": {"moniker": "alice", "is_sysop": False, "session_id": "tok-1"},
    }
    result = asyncio.run(handler.handle_message(None, ws, "/bank", msg))

    assert result == {"type": "error", "code": "forbidden", "message": "not authorized"}
    assert fake_bank.calls == []


def test_handle_message_no_claims_falls_back_to_session(monkeypatch, sessions):
    """When the message carries no claims dict (the auth handler did
    not verify a token for this message -- e.g., a fresh login
    followed immediately by a bank op), the handler falls back to
    the in-memory session attributes."""
    from bbsengine6.bank.api.handler import BankServiceHandler

    ws = _WS()
    sessions.register_session(id(ws), "alice", is_sysop=False)

    handler = BankServiceHandler(SimpleNamespace(), sessions)
    fake_bank = _FakeBankService()
    monkeypatch.setattr(handler, "bank_service", fake_bank)

    msg = {"type": "bank_balance", "moniker": "alice"}  # no "claims"
    result = asyncio.run(handler.handle_message(None, ws, "/bank", msg))

    assert result["type"] == "bank_balance"
    assert fake_bank.calls == [("get_balance", "alice")]
