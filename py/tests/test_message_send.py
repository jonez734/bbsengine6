"""
Tests for the ``send()`` shim and ``register_type_compat`` adapter in
``bbsengine6.message``.

These were added so call sites that previously imported from
``bbsengine6.message_delivery`` (e.g. ``casino.api.handler`` and
``casino.services.bank``) can migrate to the unified ``bbsengine6.message``
API without breaking the bed/zoid6 startup chain.

The tests use mocks (no real database) so they run in any environment,
matching the pattern in ``test_message_phase1_gaps.py``.

Coverage:
    - ``send()`` module presence and signature
    - ``send()`` routes to ``store_message`` with the legacy kwargs
      (``notification_type`` -> channel, ``recipients`` -> ``recipient_monikers``)
    - ``send()`` template rendering
    - ``send()`` urgency coercion (MessageUrgency, str, None, unknown)
    - ``send()`` ``args.databasename`` -> database passthrough
    - ``send()`` ``args.database`` wins over ``args.databasename``
    - ``send()`` input validation (empty ``notification_type``,
      non-list ``recipients``, non-string ``template``)
    - ``send()`` honors the ``_message_enabled`` flag
    - ``register_type_compat()`` module presence and adapter mapping
    - ``register_type_compat()`` honors the ``_message_enabled`` flag
    - ``_coerce_urgency`` and ``_db_from_args`` helpers
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module-level presence
# ---------------------------------------------------------------------------


class TestSendShimPresent:
    def test_send_and_adapter_present(self):
        from bbsengine6 import message

        assert hasattr(message, "send"), "missing: send"
        assert callable(message.send), "send not callable"
        assert hasattr(message, "register_type_compat"), "missing: register_type_compat"
        assert callable(message.register_type_compat), "register_type_compat not callable"
        assert hasattr(message, "_coerce_urgency"), "missing: _coerce_urgency"
        assert callable(message._coerce_urgency), "_coerce_urgency not callable"
        assert hasattr(message, "_db_from_args"), "missing: _db_from_args"
        assert callable(message._db_from_args), "_db_from_args not callable"


# ---------------------------------------------------------------------------
# _coerce_urgency
# ---------------------------------------------------------------------------


class TestCoerceUrgency:
    def test_none_returns_routine(self):
        from bbsengine6 import message

        assert message._coerce_urgency(None) == "ROUTINE"

    def test_empty_string_returns_routine(self):
        from bbsengine6 import message

        assert message._coerce_urgency("") == "ROUTINE"

    def test_enum_member_returns_value(self):
        from bbsengine6 import message

        assert message._coerce_urgency(message.MessageUrgency.URGENT) == "URGENT"
        assert message._coerce_urgency(message.MessageUrgency.CRITICAL) == "CRITICAL"
        assert message._coerce_urgency(message.MessageUrgency.IMPORTANT) == "IMPORTANT"
        assert message._coerce_urgency(message.MessageUrgency.ROUTINE) == "ROUTINE"

    def test_string_passthrough(self):
        from bbsengine6 import message

        assert message._coerce_urgency("URGENT") == "URGENT"

    def test_unknown_string_falls_back_to_routine(self):
        from bbsengine6 import message

        assert message._coerce_urgency("MAYDAY") == "ROUTINE"


# ---------------------------------------------------------------------------
# _db_from_args
# ---------------------------------------------------------------------------


class TestDbFromArgs:
    def test_none_returns_none(self):
        from bbsengine6 import message

        assert message._db_from_args(None) is None

    def test_args_with_database(self):
        from bbsengine6 import message

        assert message._db_from_args(SimpleNamespace(database="zoid6")) == "zoid6"

    def test_args_with_databasename_legacy(self):
        from bbsengine6 import message

        assert message._db_from_args(SimpleNamespace(databasename="legacy_db")) == "legacy_db"

    def test_database_wins_over_databasename(self):
        from bbsengine6 import message

        args = SimpleNamespace(database="winner", databasename="loser")
        assert message._db_from_args(args) == "winner"

    def test_empty_database_falls_back_to_databasename(self):
        from bbsengine6 import message

        args = SimpleNamespace(database="", databasename="fallback")
        assert message._db_from_args(args) == "fallback"

    def test_no_attributes_returns_none(self):
        from bbsengine6 import message

        assert message._db_from_args(SimpleNamespace()) is None


# ---------------------------------------------------------------------------
# send() — input validation
# ---------------------------------------------------------------------------


class TestSendValidation:
    def test_empty_notification_type_raises(self):
        from bbsengine6 import message

        with pytest.raises(ValueError, match="notification_type"):
            message.send("", ["alice"], "hi")

    def test_missing_recipients_raises(self):
        from bbsengine6 import message

        with pytest.raises(ValueError, match="recipients"):
            message.send("casino_kick", [], "hi")

    def test_non_list_recipients_raises(self):
        from bbsengine6 import message

        with pytest.raises(ValueError, match="recipients"):
            message.send("casino_kick", "alice", "hi")

    def test_non_string_template_raises(self):
        from bbsengine6 import message

        with pytest.raises(ValueError, match="template"):
            message.send("casino_kick", ["alice"], template=123)


# ---------------------------------------------------------------------------
# send() — disabled subsystem
# ---------------------------------------------------------------------------


class TestSendDisabled:
    def test_returns_zero_when_message_disabled(self):
        from bbsengine6 import message

        with patch.object(message, "_message_enabled", False):
            result = message.send(
                notification_type="casino_kick",
                recipients=["alice"],
                template="You were kicked",
            )
        assert result == 0


# ---------------------------------------------------------------------------
# send() — happy path: routes to store_message
# ---------------------------------------------------------------------------


def _make_pool_with_message_id(message_id: int):
    """Build a mock ConnectionPool whose ``store_message`` chain returns
    the given message_id. Returns (pool, store_message_mock)."""
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor = MagicMock(return_value=cur)
    conn.commit = MagicMock()

    pool = MagicMock()
    pool.connection = MagicMock(return_value=conn)
    return pool


class TestSendRoutesToStoreMessage:
    def test_returns_store_message_result(self):
        from bbsengine6 import message

        with patch.object(message, "store_message", return_value=42) as sm:
            result = message.send(
                notification_type="casino_kick",
                recipients=["alice", "bob"],
                template="You were kicked from {table}",
                template_vars={"table": "bj-1"},
                sender_moniker="admin",
                urgency=message.MessageUrgency.IMPORTANT,
                args=SimpleNamespace(databasename="zoid6"),
            )

        assert result == 42
        sm.assert_called_once()
        kwargs = sm.call_args.kwargs
        # notification_type -> channel (verbatim, no prefix)
        assert kwargs["channel"] == "casino_kick"
        assert kwargs["sender_moniker"] == "admin"
        assert kwargs["recipient_monikers"] == ["alice", "bob"]
        # template rendered into content
        assert kwargs["content"] == "You were kicked from bj-1"
        # urgency coerced to string
        assert kwargs["urgency"] == "IMPORTANT"
        # template preserved for re-rendering
        assert kwargs["template"] == "You were kicked from {table}"
        assert kwargs["template_vars"] == {"table": "bj-1"}
        # database pulled from args.databasename
        assert kwargs["database"] == "zoid6"

    def test_database_attribute_wins(self):
        from bbsengine6 import message

        args = SimpleNamespace(database="from_database", databasename="from_databasename")
        with patch.object(message, "store_message", return_value=1) as sm:
            message.send(
                notification_type="casino.bankalert",
                recipients=["sysop"],
                template="house_alert",
                args=args,
            )
        assert sm.call_args.kwargs["database"] == "from_database"

    def test_renders_template_with_missing_vars(self):
        from bbsengine6 import message

        with patch.object(message, "store_message", return_value=1) as sm:
            message.send(
                notification_type="casino_kick",
                recipients=["alice"],
                template="Kicked {who} from {where}",
                # no template_vars at all -> {who} and {where} stay literal
            )
        # render_template replaces each var with the string from the dict;
        # missing keys are absent and the placeholders remain.
        assert sm.call_args.kwargs["content"] == "Kicked {who} from {where}"

    def test_urgency_string_passthrough(self):
        from bbsengine6 import message

        with patch.object(message, "store_message", return_value=1) as sm:
            message.send(
                notification_type="casino_kick",
                recipients=["alice"],
                template="hi",
                urgency="URGENT",
            )
        assert sm.call_args.kwargs["urgency"] == "URGENT"

    def test_urgency_none_defaults_to_routine(self):
        from bbsengine6 import message

        with patch.object(message, "store_message", return_value=1) as sm:
            message.send(
                notification_type="casino_kick",
                recipients=["alice"],
                template="hi",
            )
        assert sm.call_args.kwargs["urgency"] == "ROUTINE"

    def test_no_args_database_is_none(self):
        from bbsengine6 import message

        with patch.object(message, "store_message", return_value=1) as sm:
            message.send(
                notification_type="casino_kick",
                recipients=["alice"],
                template="hi",
            )
        assert sm.call_args.kwargs["database"] is None

    def test_data_kwarg_passes_through(self):
        from bbsengine6 import message

        payload = {"custom": "payload", "n": 7}
        with patch.object(message, "store_message", return_value=1) as sm:
            message.send(
                notification_type="casino_kick",
                recipients=["alice"],
                template="hi",
                data=payload,
            )
        assert sm.call_args.kwargs["data"] is payload

    def test_should_persist_kwarg_accepted_but_ignored(self):
        """The new system always persists; the kwarg is kept for API
        parity with message_delivery.send and must not be forwarded to
        store_message."""
        from bbsengine6 import message

        with patch.object(message, "store_message", return_value=1) as sm:
            result = message.send(
                notification_type="casino_kick",
                recipients=["alice"],
                template="hi",
                should_persist=False,
            )
        assert result == 1
        assert "should_persist" not in sm.call_args.kwargs

    def test_extra_kwargs_swallowed(self):
        """Unknown kwargs (e.g. legacy pool/conn) must not break the
        shim and must not be forwarded to store_message."""
        from bbsengine6 import message

        with patch.object(message, "store_message", return_value=1) as sm:
            message.send(
                notification_type="casino_kick",
                recipients=["alice"],
                template="hi",
                pool="ignored",
                conn="ignored",
                garbage="ignored",
            )
        forwarded = sm.call_args.kwargs
        for k in ("pool", "conn", "garbage"):
            assert k not in forwarded


# ---------------------------------------------------------------------------
# register_type_compat()
# ---------------------------------------------------------------------------


class TestRegisterTypeCompatPresent:
    def test_module_exports_it(self):
        from bbsengine6 import message

        assert callable(message.register_type_compat)


class TestRegisterTypeCompatDisabled:
    def test_returns_false_when_disabled(self):
        from bbsengine6 import message

        with patch.object(message, "_message_enabled", False):
            ok = message.register_type_compat(
                "casino.bankalert",
                message.MessageUrgency.ROUTINE,
                100,
                True,
                SimpleNamespace(databasename="zoid6"),
            )
        assert ok is False


class TestRegisterTypeCompatAdapter:
    """The compat adapter must accept the legacy positional signature
    and forward to the new ``register_type`` function with the
    documented column mapping."""

    def test_legacy_signature_routes_to_register_type(self):
        from bbsengine6 import message

        with patch.object(message, "register_type", return_value=True) as rt:
            ok = message.register_type_compat(
                "casino.bankalert",
                message.MessageUrgency.ROUTINE,
                100,
                True,
                SimpleNamespace(databasename="zoid6"),
            )

        assert ok is True
        rt.assert_called_once()
        kwargs = rt.call_args.kwargs
        assert kwargs["type_name"] == "casino.bankalert"
        # urgency -> description (encodes default urgency)
        assert "ROUTINE" in kwargs["description"]
        # max_per_user_per_hour -> rate_limit_per_hour
        assert kwargs["rate_limit_per_hour"] == 100
        # persist_by_default ignored -> requires_approval always False
        assert kwargs["requires_approval"] is False
        # args.databasename -> database
        assert kwargs["database"] == "zoid6"

    def test_new_signature_also_works(self):
        """The new keyword-only signature must still work for callers
        that already migrated to the new schema."""
        from bbsengine6 import message

        with patch.object(message, "register_type", return_value=True) as rt:
            ok = message.register_type_compat(
                "casino.bankalert",
                description="Casino bank alerts",
                rate_limit_per_hour=50,
                requires_approval=True,
                database="zoid6",
            )

        assert ok is True
        rt.assert_called_once()
        kwargs = rt.call_args.kwargs
        assert kwargs["type_name"] == "casino.bankalert"
        assert kwargs["description"] == "Casino bank alerts"
        assert kwargs["rate_limit_per_hour"] == 50
        assert kwargs["requires_approval"] is True
        assert kwargs["database"] == "zoid6"

    def test_no_urgency_skips_description(self):
        from bbsengine6 import message

        with patch.object(message, "register_type", return_value=True) as rt:
            message.register_type_compat(
                "casino.bankalert",
                urgency=None,
                max_per_user_per_hour=10,
            )
        assert rt.call_args.kwargs["description"] == ""
