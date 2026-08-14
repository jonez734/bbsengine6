"""
Unit tests for ``bbsengine6.message.access``.

Pins every (op, session, message) branch of the access decision
matrix. These are unit-only: no DB connection required. Run with
``pytest -m unit tests/test_message_access.py``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bbsengine6.message import access as message_access


pytestmark = pytest.mark.unit


def _session(moniker: str | None = None, *, is_sysop: bool = False):
    """Build a session-like object with .moniker and .is_sysop."""
    return SimpleNamespace(moniker=moniker, is_sysop=is_sysop)


# ---------- module-load time ----------


def test_no_session_kwarg_returns_true():
    """bbsengine6.module.check() calls access() with no session kwarg at
    module-load time; access() must return True so the module loads."""
    assert message_access(None, "run") is True


# ---------- subscribe / unsubscribe / list_pending (self-or-sysop) ----------


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_self_ops_allowed_when_session_owns_target(op):
    s = _session("alice", is_sysop=False)
    msg = {"moniker": "alice"}
    assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_self_ops_denied_on_other_target(op):
    s = _session("alice", is_sysop=False)
    msg = {"moniker": "bob"}
    assert message_access(None, op, session=s, message=msg) is False


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_self_ops_allowed_on_other_target_when_sysop(op):
    s = _session("sysop", is_sysop=True)
    msg = {"moniker": "alice"}
    assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_self_ops_case_insensitive_match(op):
    s = _session("Alice", is_sysop=False)
    msg = {"moniker": "alice"}
    assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
@pytest.mark.parametrize("moniker", ["", None])
def test_self_ops_denied_when_target_missing(op, moniker):
    s = _session("alice", is_sysop=False)
    msg = {"moniker": moniker}
    assert message_access(None, op, session=s, message=msg) is False


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_self_ops_denied_when_session_is_none(op):
    """Unbound websocket -> always deny (mirrors bank.list_all rule)."""
    msg = {"moniker": "alice"}
    assert message_access(None, op, session=None, message=msg) is False


# ---------- unknown op ----------


def test_unknown_op_returns_false():
    s = _session("alice", is_sysop=True)
    assert message_access(None, "frobnicate", session=s, message={"moniker": "alice"}) is False
