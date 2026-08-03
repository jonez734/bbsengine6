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

from unittest.mock import MagicMock, patch

import pytest


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
    def test_returns_true_on_row_deleted(self):
        from bbsengine6 import message

        cur = MagicMock()
        cur.rowcount = 1
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=cur)
        conn.commit = MagicMock()

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        with patch.object(message, "getpool", return_value=pool):
            result = message.remove_from_group(7, "alice")

        assert result is True
        cur.execute.assert_called_once()
        sql = cur.execute.call_args[0][0]
        assert "DELETE FROM engine.__message_group_member" in sql
        conn.commit.assert_called_once()

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

        with patch.object(message, "getpool", return_value=pool):
            result = message.remove_from_group(99, "ghost")

        assert result is False

    def test_returns_false_when_disabled(self):
        from bbsengine6 import message

        with patch.object(message, "_message_enabled", False):
            assert message.remove_from_group(1, "alice") is False


# ---------------------------------------------------------------------------
# get_blocked
# ---------------------------------------------------------------------------


class TestGetBlocked:
    def test_returns_list_of_blocker_monikers(self):
        from bbsengine6 import message

        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.fetchall = MagicMock(return_value=[("alice",), ("bob",)])

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=cur)

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        with patch.object(message, "getpool", return_value=pool):
            result = message.get_blocked("carol")

        assert result == ["alice", "bob"]
        sql = cur.execute.call_args[0][0]
        assert "blocked_moniker" in sql
        assert cur.execute.call_args[0][1] == ("carol",)

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

        with patch.object(message, "getpool", return_value=pool):
            assert message.get_blocked("carol") == []


# ---------------------------------------------------------------------------
# get_urgent
# ---------------------------------------------------------------------------


class TestGetUrgent:
    def test_filters_urgent_and_critical_only(self):
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

        with patch.object(message, "getpool", return_value=pool):
            message.get_urgent("alice", limit=10)

        sql = cur.execute.call_args[0][0]
        # Should filter to URGENT + CRITICAL only
        assert "m.urgency IN ('URGENT', 'CRITICAL')" in sql
        # Should order by urgency (CRITICAL first)
        assert "WHEN 'CRITICAL' THEN 0" in sql
        # Args = (moniker, limit)
        assert cur.execute.call_args[0][1] == ("alice", 10)

    def test_returns_dict_shaped_messages(self):
        from bbsengine6 import message

        row = (
            1,  # id
            "system:shout",  # channel
            "alice",  # sender_moniker
            "Help!",  # content
            None,  # data
            "CRITICAL",  # urgency
            None,  # template
            None,  # template_vars
            "2026-07-22T12:00:00",  # datestamp
            "pending",  # status
            None,  # datedelivered
            None,  # dateread
        )
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.fetchall = MagicMock(return_value=[row])

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=cur)

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        with patch.object(message, "getpool", return_value=pool):
            result = message.get_urgent("bob")

        assert len(result) == 1
        assert result[0]["urgency"] == "CRITICAL"
        assert result[0]["channel"] == "system:shout"
        assert result[0]["id"] == 1


# ---------------------------------------------------------------------------
# expunge
# ---------------------------------------------------------------------------


class TestExpunge:
    def test_deletes_only_when_sender_matches(self):
        from bbsengine6 import message

        cur = MagicMock()
        cur.rowcount = 1
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=cur)
        conn.commit = MagicMock()

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        with patch.object(message, "getpool", return_value=pool):
            result = message.expunge(42, "alice")

        assert result is True
        sql = cur.execute.call_args[0][0]
        # The WHERE clause must include the sender check
        assert "sender_moniker = %s" in sql
        assert "id = %s" in sql
        assert cur.execute.call_args[0][1] == (42, "alice")

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

        with patch.object(message, "getpool", return_value=pool):
            result = message.expunge(42, "someone-else")

        assert result is False


# ---------------------------------------------------------------------------
# get_queue
# ---------------------------------------------------------------------------


class TestGetQueue:
    def test_delegates_to_get_pending_messages(self):
        from bbsengine6 import message

        sentinel = [{"id": 1, "urgency": "ROUTINE"}]
        with patch.object(
            message, "get_pending_messages", return_value=sentinel
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

        with patch.object(message, "is_enabled", return_value=True):
            result = message.resolve_recipients(["alice", "bob"])

        assert result == ["alice", "bob"]

    def test_dedupes_plain_monikers(self):
        from bbsengine6 import message

        with patch.object(message, "is_enabled", return_value=True):
            result = message.resolve_recipients(["alice", "bob", "alice"])

        assert result == ["alice", "bob"]

    def test_expands_everyone_to_all_approved_members(self):
        from bbsengine6 import message

        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.fetchall = MagicMock(return_value=[("alice",), ("bob",), ("carol",)])

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=cur)

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        with patch.object(message, "is_enabled", return_value=True), \
             patch.object(message, "getpool", return_value=pool):
            result = message.resolve_recipients(["@everyone"])

        assert result == ["alice", "bob", "carol"]
        sql = cur.execute.call_args[0][0]
        assert "FROM engine.__member" in sql
        assert "approved = TRUE" in sql

    def test_expands_named_group(self):
        from bbsengine6 import message

        # First call: SELECT id FROM engine.__message_group WHERE name = %s
        id_cur = MagicMock()
        id_cur.__enter__ = MagicMock(return_value=id_cur)
        id_cur.__exit__ = MagicMock(return_value=False)
        id_cur.fetchone = MagicMock(return_value=(5,))

        # Subsequent calls (none, since get_message_group_members is patched)
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=id_cur)

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        with patch.object(message, "is_enabled", return_value=True), \
             patch.object(message, "getpool", return_value=pool), \
             patch.object(
                 message, "get_message_group_members",
                 return_value=["dave", "eve"],
             ):
            result = message.resolve_recipients(["@ops"])

        assert result == ["dave", "eve"]
        id_cur.execute.assert_called_once()
        assert id_cur.execute.call_args[0][1] == ("ops",)

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

        with patch.object(message, "is_enabled", return_value=True), \
             patch.object(message, "getpool", return_value=pool):
            result = message.resolve_recipients(["@nope", "alice"])

        assert result == ["alice"]

    def test_mixed_plain_and_special(self):
        from bbsengine6 import message

        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.fetchall = MagicMock(return_value=[("bob",), ("carol",)])

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=cur)

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        with patch.object(message, "is_enabled", return_value=True), \
             patch.object(message, "getpool", return_value=pool):
            result = message.resolve_recipients(["alice", "@everyone", "bob"])

        # alice first, then everyone (bob appears once, deduped)
        assert result == ["alice", "bob", "carol"]

    def test_returns_empty_when_disabled(self):
        from bbsengine6 import message

        with patch.object(message, "_message_enabled", False):
            assert message.resolve_recipients(["alice"]) == []


# ---------------------------------------------------------------------------
# set_rate_limit / register_type / get_types
# ---------------------------------------------------------------------------


class TestRateLimitAndTypes:
    def test_set_rate_limit_upserts(self):
        from bbsengine6 import message

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

        with patch.object(message, "getpool", return_value=pool):
            result = message.set_rate_limit("casino:table", 50)

        assert result is True
        sql = cur.execute.call_args[0][0]
        assert "ON CONFLICT (type_name) DO UPDATE" in sql
        assert cur.execute.call_args[0][1] == ("casino:table", "", 50)

    def test_register_type_inserts_with_all_fields(self):
        from bbsengine6 import message

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

        with patch.object(message, "getpool", return_value=pool):
            result = message.register_type(
                "x:new", "new channel", 25, requires_approval=True
            )

        assert result is True
        sql = cur.execute.call_args[0][0]
        assert "ON CONFLICT (type_name) DO UPDATE" in sql
        assert cur.execute.call_args[0][1] == (
            "x:new", "new channel", 25, True,
        )

    def test_get_types_returns_list_of_dicts(self):
        from bbsengine6 import message

        rows = [
            ("casino:table", "casino", 300, False, "2026-07-22"),
            ("system:shout", "shout", 60, False, "2026-07-22"),
        ]
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.fetchall = MagicMock(return_value=rows)

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=cur)

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        with patch.object(message, "getpool", return_value=pool):
            result = message.get_types()

        assert len(result) == 2
        assert result[0] == {
            "type_name": "casino:table",
            "description": "casino",
            "rate_limit_per_hour": 300,
            "requires_approval": False,
            "datemodified": "2026-07-22",
        }


# ---------------------------------------------------------------------------
# @group / @everyone expansion in store_message
# ---------------------------------------------------------------------------


class TestStoreMessageExpandsRecipients:
    def test_store_message_expands_at_references(self):
        """``store_message`` should call ``resolve_recipients`` on its
        recipient list, so ``@group`` and ``@everyone`` work at the
        call site without the caller pre-expanding."""
        from bbsengine6 import message

        # All cursors / conns / pools set up to no-op (we want to
        # verify the call sequence, not the DB writes).
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.fetchone = MagicMock(return_value=(99,))
        cur.rowcount = 0

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=cur)
        conn.commit = MagicMock()

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        expanded = ["alice", "bob", "carol"]

        with patch.object(message, "getpool", return_value=pool), \
             patch.object(
                 message, "resolve_recipients", return_value=expanded
             ) as expand, \
             patch.object(message, "is_blocked", return_value=False), \
             patch.object(message, "check_rate_limit", return_value=(True, 999)):
            result = message.store_message(
                channel="system:shout",
                sender_moniker="alice",
                content="hi",
                recipient_monikers=["@everyone"],
            )

        # resolve_recipients was called with the original list
        expand.assert_called_once()
        assert expand.call_args[0][0] == ["@everyone"]
        # store_message returns the id
        assert result == 99

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

        with patch.object(message, "getpool", return_value=pool), \
             patch.object(
                 message, "resolve_recipients",
                 return_value=["alice", "bob"],
             ) as expand, \
             patch.object(message, "is_blocked", return_value=False), \
             patch.object(message, "check_rate_limit", return_value=(True, 999)):
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
