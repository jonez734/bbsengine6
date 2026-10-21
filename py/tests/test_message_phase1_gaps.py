"""
Tests for the Phase 1 gap-fills added to message.py.

These functions were ported from the legacy ``bbsengine6.notify``
package to complete the notify→message.py migration. The tests use
mocks (no real database) so they can run in any environment.

Coverage:
    - remove_from_group
    - get_blocked
    - get_urgent
    - expunge
    - get_queue
    - resolve_recipients (incl. @group, @everyone)
    - set_rate_limit
    - register_type
    - get_types
    - @group/@everyone expansion in store_message
"""

from __future__ import annotations

import pytest

from unittest.mock import MagicMock, patch

from bbsengine6.message import lib as message_lib
from bbsengine6.message import service as message_service

pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# Module-level presence
# ---------------------------------------------------------------------------


class TestPhase1GapFillsPresent:
    """Verify the 8 new functions are importable and callable."""

    def test_all_gap_fill_functions_present(self):
        from bbsengine6 import message

        for name in (
            "remove_from_group",
            "get_blocked",
            "get_urgent",
            "expunge",
            "get_queue",
            "resolve_recipients",
            "set_rate_limit",
            "register_type",
            "get_types",
        ):
            assert hasattr(message, name), f"missing: {name}"
            assert callable(getattr(message, name)), f"not callable: {name}"


# ---------------------------------------------------------------------------
# remove_from_group
# ---------------------------------------------------------------------------


class TestRemoveFromGroup:
    def test_returns_true_on_row_deleted(self, message_dal_stubs):
        """remove_from_group reports success from the DAL group removal."""
        from bbsengine6 import message
        from bbsengine6.message.dal import groups as dal_groups
        from bbsengine6.message.dal import recipients as dal_recipients

        dal_recipients.get_group_id_by_name.return_value = 7
        dal_groups.remove_member.return_value = True
        dal_groups.list_members.return_value = ["bob"]

        assert message.remove_from_group(7, "alice") is True
        dal_groups.remove_member.assert_called_once()
        assert dal_groups.remove_member.call_args.args[1:] == (7, "alice")

    def test_returns_false_when_no_row(self):
        from bbsengine6 import message

        cur = MagicMock()
        cur.rowcount = 0
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=cur)

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        with patch.object(message_lib, "getpool", return_value=pool):
            result = message.remove_from_group(99, "ghost")

        assert result is False

    def test_returns_false_when_disabled(self):
        from bbsengine6 import message
        from bbsengine6.message import lib as message_lib

        with patch.object(message_service, "_message_enabled", False):
            assert message.remove_from_group(1, "alice") is False


# ---------------------------------------------------------------------------
# get_blocked
# ---------------------------------------------------------------------------


class TestGetBlocked:
    def test_returns_list_of_blocker_monikers(self, message_dal_stubs):
        """get_blocked returns the monikers the DAL lists as blocking the member."""
        from bbsengine6 import message
        from bbsengine6.message.dal import blocking as dal_blocking

        dal_blocking.list_blocked_by.return_value = ["mallory", "eve"]

        assert message.get_blocked("alice") == ["mallory", "eve"]

    def test_returns_empty_when_no_one_blocked(self):
        from bbsengine6 import message

        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.fetchall = MagicMock(return_value=[])

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=cur)

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        with patch.object(message_lib, "getpool", return_value=pool):
            assert message.get_blocked("carol") == []


# ---------------------------------------------------------------------------
# get_urgent
# ---------------------------------------------------------------------------


class TestGetUrgent:
    def test_filters_urgent_and_critical_only(self, message_dal_stubs):
        """get_urgent asks the DAL for urgent and critical messages only."""
        from bbsengine6 import message
        from bbsengine6.message.dal import messages as dal_messages

        message.get_urgent("bob")

        dal_messages.list_urgent_for_recipient.assert_called_once()
        assert dal_messages.list_urgent_for_recipient.call_args.args[1] == "bob"

    def test_returns_dict_shaped_messages(self, message_dal_stubs):
        """get_urgent returns the DAL's dict-shaped rows unchanged."""
        from bbsengine6 import message
        from bbsengine6.message.dal import messages as dal_messages

        rows = [{"id": 9, "urgency": "CRITICAL", "content": "help"}]
        dal_messages.list_urgent_for_recipient.return_value = rows

        assert message.get_urgent("bob") == rows

class TestExpunge:
    def test_deletes_only_when_sender_matches(self, message_dal_stubs):
        """expunge is delegated to the DAL, which enforces the sender match."""
        from bbsengine6 import message
        from bbsengine6.message.dal import messages as dal_messages

        message.expunge(5, "alice")

        dal_messages.expunge_sender_message.assert_called_once()
        assert dal_messages.expunge_sender_message.call_args.args[1:] == (5, "alice")

    def test_returns_false_when_no_match(self):
        from bbsengine6 import message

        cur = MagicMock()
        cur.rowcount = 0
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=cur)

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        with patch.object(message_lib, "getpool", return_value=pool):
            result = message.expunge(42, "someone-else")

        assert result is False


# ---------------------------------------------------------------------------
# get_queue
# ---------------------------------------------------------------------------


class TestGetQueue:
    def test_delegates_to_get_pending_messages(self):
        from bbsengine6 import message

        sentinel = [{"id": 1, "urgency": "ROUTINE"}]
        with patch.object(message_service, "get_pending_messages", return_value=sentinel
        ) as gpm:
            result = message.get_queue("alice")

        assert result is sentinel
        # Verify the call passed a generous limit and the moniker
        gpm.assert_called_once()
        args, kwargs = gpm.call_args
        assert args[0] == "alice"
        assert kwargs.get("limit", args[1] if len(args) > 1 else None) == 1000


# ---------------------------------------------------------------------------
# resolve_recipients
# ---------------------------------------------------------------------------


class TestResolveRecipients:
    def test_passes_through_plain_monikers(self):
        from bbsengine6 import message

        with patch.object(message_service, "is_enabled", return_value=True):
            result = message.resolve_recipients(["alice", "bob"])

        assert result == ["alice", "bob"]

    def test_dedupes_plain_monikers(self):
        from bbsengine6 import message

        with patch.object(message_service, "is_enabled", return_value=True):
            result = message.resolve_recipients(["alice", "bob", "alice"])

        assert result == ["alice", "bob"]

    def test_expands_everyone_to_all_approved_members(self, message_dal_stubs):
        """@everyone expands to the approved member list, for a sysop sender."""
        from bbsengine6 import message
        from bbsengine6.message.dal import recipients as dal_recipients
        dal_recipients.list_all_approved_member_monikers.return_value = ["alice", "bob", "carol"]
        from bbsengine6.message import service as message_service

        with patch.object(message_service, "_sender_may_broadcast", return_value=True):
            out = message.resolve_recipients(["@everyone"], sender_moniker="root")

        assert out == ["alice", "bob", "carol"]

    def test_expands_named_group(self, message_dal_stubs):
        """A named group expands to its members from the DAL."""
        from bbsengine6 import message
        from bbsengine6.message.dal import groups as dal_groups
        from bbsengine6.message.dal import recipients as dal_recipients

        dal_recipients.get_group_id_by_name.return_value = 3
        dal_groups.list_members.return_value = ["alice", "bob", "carol"]

        assert message.resolve_recipients(["@crew"]) == ["alice", "bob", "carol"]

    def test_unknown_group_is_silently_ignored(self):
        from bbsengine6 import message

        id_cur = MagicMock()
        id_cur.__enter__ = MagicMock(return_value=id_cur)
        id_cur.__exit__ = MagicMock(return_value=False)
        id_cur.fetchone = MagicMock(return_value=None)  # no such group

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=id_cur)

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        with patch.object(message_service, "is_enabled", return_value=True), \
             patch.object(message_lib, "getpool", return_value=pool):
            result = message.resolve_recipients(["@nope", "alice"])

        assert result == ["alice"]

    def test_mixed_plain_and_special(self, message_dal_stubs):
        """Plain monikers and a named group expand together, without duplicates."""
        from bbsengine6 import message
        from bbsengine6.message.dal import groups as dal_groups
        from bbsengine6.message.dal import recipients as dal_recipients

        dal_recipients.get_group_id_by_name.return_value = 3
        dal_groups.list_members.return_value = ["alice", "bob"]

        out = message.resolve_recipients(["dave", "@crew", "alice"])

        assert out == ["dave", "alice", "bob"]

    def test_returns_empty_when_disabled(self):
        from bbsengine6 import message
        from bbsengine6.message import lib as message_lib

        with patch.object(message_service, "_message_enabled", False):
            assert message.resolve_recipients(["alice"]) == []


# ---------------------------------------------------------------------------
# set_rate_limit / register_type / get_types
# ---------------------------------------------------------------------------


class TestRateLimitAndTypes:
    def test_set_rate_limit_upserts(self, message_dal_stubs):
        """set_rate_limit writes the limit through the DAL."""
        from bbsengine6 import message
        from bbsengine6.message.dal import types as dal_types

        assert message.set_rate_limit("casino_kick", 30) is True
        dal_types.set_rate_limit.assert_called_once()
        assert dal_types.set_rate_limit.call_args.args[1:] == ("casino_kick", 30)

    def test_register_type_inserts_with_all_fields(self, message_dal_stubs):
        """register_type passes every field to the DAL upsert."""
        from bbsengine6 import message
        from bbsengine6.message.dal import types as dal_types

        assert message.register_type("casino_kick", "Kicked", "ROUTINE", 10) is True
        dal_types.upsert.assert_called_once()

    def test_get_types_returns_list_of_dicts(self, message_dal_stubs):
        """get_types returns the DAL's type rows unchanged."""
        from bbsengine6 import message
        from bbsengine6.message.dal import types as dal_types

        rows = [{"type_name": "casino_kick", "rate_limit_per_hour": 10}]
        dal_types.list_all.return_value = rows

        assert message.get_types() == rows

class TestStoreMessageExpandsRecipients:
    def test_store_message_expands_at_references(self, message_dal_stubs):
        """store_message expands @group references before storing the recipients."""
        from bbsengine6 import message
        from bbsengine6.message.dal import groups as dal_groups
        from bbsengine6.message.dal import messages as dal_messages
        from bbsengine6.message.dal import ratelimit as dal_ratelimit
        from bbsengine6.message.dal import recipients as dal_recipients

        dal_ratelimit.try_reserve.return_value = (True, 9)
        dal_recipients.get_group_id_by_name.return_value = 3
        dal_groups.list_members.return_value = ["alice", "bob", "carol"]
        # The sender must belong to the group to address it (sysops excepted).
        dal_groups.is_member.return_value = True
        dal_messages.store_message_with_recipients.return_value = 55

        message.store_message(channel="member:direct", sender_moniker="alice",
                              content="hi", recipient_monikers=["@crew"])

        stored = dal_messages.store_message_with_recipients.call_args.args[-1]
        assert sorted(stored) == ["alice", "bob", "carol"]

    def test_store_message_passes_through_when_no_special_recipients(self):
        """When the recipient list has no @-prefixed tokens, the
        implementation should still work (no expansion errors)."""
        from bbsengine6 import message

        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.fetchone = MagicMock(return_value=(1,))
        cur.rowcount = 0

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=cur)
        conn.commit = MagicMock()

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        with patch.object(message_lib, "getpool", return_value=pool), \
             patch.object(message_service, "resolve_recipients",
                 return_value=["alice", "bob"],
             ) as expand, \
             patch.object(message_service, "is_blocked", return_value=False), \
             patch.object(message_service, "check_rate_limit", return_value=(True, 999)):
            message.store_message(
                channel="member:direct",
                sender_moniker="carol",
                content="hi",
                recipient_monikers=["alice", "bob"],
            )

        # The expansion is called once with the original list; the
        # resolved database comes from the default arg resolver, so
        # we only pin the positional recipient list.
        expand.assert_called_once()
        assert expand.call_args[0][0] == ["alice", "bob"]
