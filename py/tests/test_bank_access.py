"""
Unit tests for ``bbsengine6.bank.access``.

Pins every (op, session, message) branch of the access decision
matrix. These are unit-only: no DB connection required. Run with
``pytest -m unit tests/test_bank_access.py``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bbsengine6.bank import access as bank_access


pytestmark = pytest.mark.unit


def _session(moniker: str | None = None, *, is_sysop: bool = False):
    """Build a session-like object with .moniker and .is_sysop."""
    return SimpleNamespace(moniker=moniker, is_sysop=is_sysop)


# ---------- balance / add / remove / history / pending ----------


@pytest.mark.parametrize("op", ["balance", "add", "remove", "history", "pending"])
def test_self_ops_allowed_when_session_owns_target(op):
    s = _session("alice", is_sysop=False)
    msg = {"moniker": "alice"}
    assert bank_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize("op", ["balance", "add", "remove", "history", "pending"])
def test_self_ops_denied_on_other_target(op):
    s = _session("alice", is_sysop=False)
    msg = {"moniker": "bob"}
    assert bank_access(None, op, session=s, message=msg) is False


@pytest.mark.parametrize("op", ["balance", "add", "remove", "history", "pending"])
def test_self_ops_allowed_on_other_target_when_sysop(op):
    s = _session("sysop", is_sysop=True)
    msg = {"moniker": "alice"}
    assert bank_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize("op", ["balance", "add", "remove", "history", "pending"])
def test_self_ops_case_insensitive_match(op):
    s = _session("Alice", is_sysop=False)
    msg = {"moniker": "alice"}
    assert bank_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize("op", ["balance", "add", "remove", "history", "pending"])
@pytest.mark.parametrize("moniker", ["", None])
def test_self_ops_denied_when_target_missing(op, moniker):
    s = _session("alice", is_sysop=False)
    msg = {"moniker": moniker}
    assert bank_access(None, op, session=s, message=msg) is False


# ---------- list_all ----------


def test_list_all_denied_for_non_sysop():
    s = _session("alice", is_sysop=False)
    assert bank_access(None, "list_all", session=s, message={}) is False


def test_list_all_allowed_for_sysop():
    s = _session("sysop", is_sysop=True)
    assert bank_access(None, "list_all", session=s, message={}) is True


# ---------- transfer ----------


def test_transfer_allowed_when_session_owns_from():
    s = _session("alice", is_sysop=False)
    msg = {"from": "alice", "to": "bob", "requested_by": "alice"}
    assert bank_access(None, "transfer", session=s, message=msg) is True


def test_transfer_denied_when_session_does_not_own_from():
    s = _session("alice", is_sysop=False)
    msg = {"from": "bob", "to": "carol", "requested_by": "alice"}
    assert bank_access(None, "transfer", session=s, message=msg) is False


def test_transfer_allowed_by_sysop_on_any_from():
    s = _session("sysop", is_sysop=True)
    msg = {"from": "alice", "to": "bob", "requested_by": "alice"}
    assert bank_access(None, "transfer", session=s, message=msg) is True


def test_transfer_denied_with_foreign_requested_by():
    s = _session("alice", is_sysop=False)
    msg = {"from": "alice", "to": "bob", "requested_by": "carol"}
    assert bank_access(None, "transfer", session=s, message=msg) is False


def test_transfer_allowed_when_requested_by_matches_session():
    s = _session("alice", is_sysop=False)
    msg = {"from": "alice", "to": "bob", "requested_by": "Alice"}
    assert bank_access(None, "transfer", session=s, message=msg) is True


def test_transfer_allowed_by_sysop_even_with_foreign_requested_by():
    s = _session("sysop", is_sysop=True)
    msg = {"from": "alice", "to": "bob", "requested_by": "carol"}
    assert bank_access(None, "transfer", session=s, message=msg) is True


def test_transfer_allowed_when_requested_by_empty():
    """Caller did not pass requested_by; the wire field is optional."""
    s = _session("alice", is_sysop=False)
    msg = {"from": "alice", "to": "bob", "requested_by": ""}
    assert bank_access(None, "transfer", session=s, message=msg) is True


@pytest.mark.parametrize("missing", ["from", "to"])
def test_transfer_denied_when_endpoint_missing(missing):
    s = _session("alice", is_sysop=False)
    msg = {"from": "alice", "to": "bob"}
    msg.pop(missing)
    assert bank_access(None, "transfer", session=s, message=msg) is False


# ---------- approve / reject ----------


@pytest.mark.parametrize("op", ["approve", "reject"])
def test_approve_reject_allowed_with_valid_id_no_responded_by(op):
    s = _session("bob", is_sysop=False)
    msg = {"transfer_id": 42}
    assert bank_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize("op", ["approve", "reject"])
def test_approve_reject_denied_with_zero_id(op):
    s = _session("bob", is_sysop=False)
    msg = {"transfer_id": 0}
    assert bank_access(None, op, session=s, message=msg) is False


@pytest.mark.parametrize("op", ["approve", "reject"])
def test_approve_reject_denied_with_negative_id(op):
    s = _session("bob", is_sysop=False)
    msg = {"transfer_id": -1}
    assert bank_access(None, op, session=s, message=msg) is False


@pytest.mark.parametrize("op", ["approve", "reject"])
def test_approve_reject_denied_with_non_integer_id(op):
    s = _session("bob", is_sysop=False)
    msg = {"transfer_id": "abc"}
    assert bank_access(None, op, session=s, message=msg) is False


@pytest.mark.parametrize("op", ["approve", "reject"])
def test_approve_reject_denied_with_foreign_responded_by(op):
    s = _session("alice", is_sysop=False)
    msg = {"transfer_id": 42, "responded_by": "carol"}
    assert bank_access(None, op, session=s, message=msg) is False


@pytest.mark.parametrize("op", ["approve", "reject"])
def test_approve_reject_allowed_when_responded_by_matches(op):
    s = _session("alice", is_sysop=False)
    msg = {"transfer_id": 42, "responded_by": "Alice"}
    assert bank_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize("op", ["approve", "reject"])
def test_approve_reject_allowed_by_sysop_with_foreign_responded_by(op):
    s = _session("sysop", is_sysop=True)
    msg = {"transfer_id": 42, "responded_by": "carol"}
    assert bank_access(None, op, session=s, message=msg) is True


# ---------- session-less / unknown op ----------


@pytest.mark.parametrize(
    "op",
    ["balance", "add", "remove", "history", "transfer",
     "approve", "reject", "pending", "list_all"],
)
def test_all_ops_denied_when_session_kwarg_is_none(op):
    """Runtime caller passed ``session=None`` (unbound websocket) -> deny."""
    assert bank_access(None, op, session=None, message={}) is False


@pytest.mark.parametrize(
    "op",
    ["balance", "add", "remove", "history", "transfer",
     "approve", "reject", "pending", "list_all", "run"],
)
def test_module_load_allows_without_session_kwarg(op):
    """bbsengine6.module.check calls access(args, op='run') with no
    session kwarg. The bank module must be loadable by anyone."""
    assert bank_access(None, op, message={}) is True


def test_unknown_op_denied():
    s = _session("sysop", is_sysop=True)
    assert bank_access(None, "totally_made_up_op", session=s, message={}) is False


# ---------- defensive: malformed message ----------


def test_non_dict_message_treated_as_empty():
    s = _session("alice", is_sysop=False)
    assert bank_access(None, "balance", session=s, message=None) is False
    assert bank_access(None, "balance", session=s, message="not a dict") is False


# ---------- module surface ----------


def test_module_surface_present():
    """Pins init / buildargs / main exist with the expected signatures.

    Other code (module.check, module.run) relies on these being
    present at the top level of the bbsengine6.bank package.
    """
    import bbsengine6.bank as pkg

    assert callable(pkg.init)
    assert callable(pkg.buildargs)
    assert callable(pkg.main)
    assert callable(pkg.access)
