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
