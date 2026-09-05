"""
Tests for the ChannelService and announce-only channel enforcement.

Test tiers
----------

``@pytest.mark.unit`` tests
    In-memory only. Use ``ChannelState`` + a stub ``ChannelService`` to
    verify that ``channel_publish()`` consults the permission check when
    a sender is provided. No database required.

Integration tests (no marker)
    Use the ``zoid6test`` database to exercise the real ``ChannelService``
    against ``engine.__channel`` and ``engine.__channel_announcer``.

Test isolation
--------------

Integration tests generate unique channel names per run (UUID suffix) and
rely on the conftest's per-test transaction rollback. The
``channel_cleanup`` fixture additionally removes any leftover rows whose
name matches the per-user test prefix as a safety net.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import database
from bbsengine6.net import channel_publish
from bbsengine6.net.transport import (
    ChannelState,
    channel_register_callback,
)
from bbsengine6.services.channel import ChannelService


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_test_args(databasename: str = "zoid6test") -> argparse.Namespace:
    """Build args for ChannelService tests against the zoid6test DB."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    defaults = {
        "databasename": databasename,
        "databasehost": "/var/run/postgresql",
        "databaseport": 5432,
        "databaseuser": getpass.getuser(),
        "databasepassword": None,
    }
    database.buildargdatabasegroup(parser, defaults)
    return parser.parse_args([])


@pytest.fixture(scope="function")
def test_args() -> argparse.Namespace:
    return make_test_args()


@pytest.fixture
def channel_service(test_args: argparse.Namespace) -> ChannelService:
    return ChannelService(test_args)


@pytest.fixture
def channel_cleanup(db_connection) -> None:
    """Remove any pre-existing test channels and their announcers.

    Belt-and-suspenders cleanup: per-test transactions in conftest.py
    already roll back inserts, but a unique-name generator (below) and
    this fixture together ensure no leakage even if a test crashes.
    """
    user = getpass.getuser()
    prefix = f"test_{user}_channel_"

    def _purge() -> None:
        with db_connection.cursor() as cur:
            cur.execute(
                "DELETE FROM engine.__channel_announcer "
                "WHERE channel_id IN ("
                "  SELECT id FROM engine.__channel WHERE name LIKE %s"
                ")",
                (prefix + "%",),
            )
            cur.execute(
                "DELETE FROM engine.__channel WHERE name LIKE %s",
                (prefix + "%",),
            )
        db_connection.commit()

    _purge()
    yield
    _purge()


def _unique_channel_name(user: str, suffix: str) -> str:
    """Generate a unique channel name per test invocation."""
    return f"test_{user}_channel_{suffix}_{uuid.uuid4().hex[:8]}"


def _test_user(index: int) -> str:
    """The dynamic test monikers created by conftest.create_test_users."""
    return f"test_{getpass.getuser()}_{index}"


# ---------------------------------------------------------------------------
# Integration tests: engine.__channel CRUD
# ---------------------------------------------------------------------------


class TestChannelCrud:
    """CRUD operations on engine.__channel."""

    def test_create_open_channel(self, channel_service, channel_cleanup):
        name = _unique_channel_name(getpass.getuser(), "open")
        creator = _test_user(1)

        result = channel_service.create_channel(
            name=name, createdby=creator, description="hello"
        )

        assert result["success"] is True
        assert result["channel"]["name"] == name
        assert result["channel"]["announce_only"] is False
        assert result["channel"]["createdby"] == creator

    def test_create_announce_only_channel_with_announcers(
        self, channel_service, channel_cleanup
    ):
        name = _unique_channel_name(getpass.getuser(), "announce")
        creator = _test_user(1)
        announcers = [_test_user(2), _test_user(3)]

        result = channel_service.create_channel(
            name=name,
            createdby=creator,
            announce_only=True,
            announcers=announcers,
        )

        assert result["success"] is True
        assert result["channel"]["announce_only"] is True

        got = channel_service.get_channel(name)
        assert got is not None
        assert got["announce_only"] is True
        for moniker in announcers:
            assert moniker in got["announcers"]

    def test_create_duplicate_returns_error(
        self, channel_service, channel_cleanup
    ):
        name = _unique_channel_name(getpass.getuser(), "dup")
        creator = _test_user(1)

        first = channel_service.create_channel(name=name, createdby=creator)
        assert first["success"] is True

        second = channel_service.create_channel(name=name, createdby=creator)
        assert second["success"] is False
        assert "exists" in second["message"].lower()

    def test_create_requires_name(self, channel_service, channel_cleanup):
        result = channel_service.create_channel(
            name="", createdby=_test_user(1)
        )
        assert result["success"] is False

    def test_get_channel_returns_none_for_missing(
        self, channel_service, channel_cleanup
    ):
        result = channel_service.get_channel(
            f"test_{getpass.getuser()}_channel_nonexistent_xyz"
        )
        assert result is None

    def test_list_channels_includes_created(
        self, channel_service, channel_cleanup
    ):
        name = _unique_channel_name(getpass.getuser(), "list")
        creator = _test_user(1)

        channel_service.create_channel(name=name, createdby=creator)
        channels = channel_service.list_channels()
        names = [c["name"] for c in channels]
        assert name in names


# ---------------------------------------------------------------------------
# Integration tests: announcer management
# ---------------------------------------------------------------------------


class TestAnnouncerManagement:
    """add/remove announcer operations."""

    def test_add_announcer(self, channel_service, channel_cleanup):
        name = _unique_channel_name(getpass.getuser(), "add_announcer")
        creator = _test_user(1)
        new_announcer = _test_user(2)

        channel_service.create_channel(
            name=name, createdby=creator, announce_only=True
        )
        result = channel_service.add_announcer(
            channel_name=name, moniker=new_announcer, addedby=creator
        )
        assert result["success"] is True

        got = channel_service.get_channel(name)
        assert new_announcer in got["announcers"]

    def test_add_announcer_missing_channel(
        self, channel_service, channel_cleanup
    ):
        result = channel_service.add_announcer(
            channel_name=f"test_{getpass.getuser()}_channel_missing",
            moniker=_test_user(2),
            addedby=_test_user(1),
        )
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_add_announcer_unknown_member(
        self, channel_service, channel_cleanup
    ):
        name = _unique_channel_name(getpass.getuser(), "unknown_member")
        creator = _test_user(1)

        channel_service.create_channel(
            name=name, createdby=creator, announce_only=True
        )
        result = channel_service.add_announcer(
            channel_name=name,
            moniker="definitely_not_a_real_user_xyz",
            addedby=creator,
        )
        assert result["success"] is False

    def test_remove_announcer(self, channel_service, channel_cleanup):
        name = _unique_channel_name(getpass.getuser(), "remove_announcer")
        creator = _test_user(1)
        announcer = _test_user(2)

        channel_service.create_channel(
            name=name, createdby=creator, announce_only=True
        )
        channel_service.add_announcer(
            channel_name=name, moniker=announcer, addedby=creator
        )

        result = channel_service.remove_announcer(
            channel_name=name, moniker=announcer, actor_moniker=creator
        )
        assert result["success"] is True

        got = channel_service.get_channel(name)
        assert announcer not in got["announcers"]

    def test_remove_announcer_denies_non_creator(self, channel_service, channel_cleanup):
        """Non-creator non-sysop cannot remove an announcer."""
        name = _unique_channel_name(getpass.getuser(), "remove_denied")
        creator = _test_user(1)
        announcer = _test_user(2)
        intruder = _test_user(3)

        channel_service.create_channel(
            name=name, createdby=creator, announce_only=True
        )
        channel_service.add_announcer(
            channel_name=name, moniker=announcer, addedby=creator
        )

        result = channel_service.remove_announcer(
            channel_name=name, moniker=announcer, actor_moniker=intruder
        )
        assert result["success"] is False
        assert "permission denied" in result["message"].lower()

    def test_set_announce_only_denies_non_creator(self, channel_service, channel_cleanup):
        """Non-creator non-sysop cannot toggle announce_only."""
        name = _unique_channel_name(getpass.getuser(), "flag_denied")
        creator = _test_user(1)
        intruder = _test_user(2)

        channel_service.create_channel(name=name, createdby=creator)
        result = channel_service.set_announce_only(
            name=name, announce_only=True, by_moniker=intruder
        )
        assert result["success"] is False
        assert "permission denied" in result["message"].lower()

    def test_set_announce_only_allows_creator(self, channel_service, channel_cleanup):
        """The channel creator can toggle announce_only on their own channel."""
        name = _unique_channel_name(getpass.getuser(), "flag_creator_ok")
        creator = _test_user(1)

        channel_service.create_channel(name=name, createdby=creator)
        result = channel_service.set_announce_only(
            name=name, announce_only=True, by_moniker=creator
        )
        assert result["success"] is True

    def test_add_announcer_denies_non_creator(self, channel_service, channel_cleanup):
        """Non-creator non-sysop cannot add an announcer."""
        name = _unique_channel_name(getpass.getuser(), "add_denied")
        creator = _test_user(1)
        intruder = _test_user(2)
        target = _test_user(3)

        channel_service.create_channel(
            name=name, createdby=creator, announce_only=True
        )
        result = channel_service.add_announcer(
            channel_name=name, moniker=target, addedby=intruder
        )
        assert result["success"] is False
        assert "permission denied" in result["message"].lower()


# ---------------------------------------------------------------------------
# Integration tests: announce_only flag toggle
# ---------------------------------------------------------------------------


class TestSetAnnounceOnly:
    """Toggle announce_only on a channel."""

    def test_set_announce_only(self, channel_service, channel_cleanup):
        name = _unique_channel_name(getpass.getuser(), "set_announce")
        creator = _test_user(1)

        channel_service.create_channel(name=name, createdby=creator)
        result = channel_service.set_announce_only(
            name=name, announce_only=True, by_moniker=creator
        )
        assert result["success"] is True

        got = channel_service.get_channel(name)
        assert got["announce_only"] is True

    def test_set_announce_only_missing_channel(
        self, channel_service, channel_cleanup
    ):
        result = channel_service.set_announce_only(
            name=f"test_{getpass.getuser()}_channel_missing_for_flag",
            announce_only=True,
            by_moniker=_test_user(1),
        )
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Integration tests: can_publish semantics
# ---------------------------------------------------------------------------


class TestCanPublish:
    """Permission check semantics."""

    def test_open_channel_allows_anyone(
        self, channel_service, channel_cleanup
    ):
        name = _unique_channel_name(getpass.getuser(), "open_allow")
        creator = _test_user(1)
        other = _test_user(2)

        channel_service.create_channel(name=name, createdby=creator)

        verdict = channel_service.can_publish(name, other, is_sysop=False)
        assert verdict["allowed"] is True

    def test_announce_only_denies_non_announcer(
        self, channel_service, channel_cleanup
    ):
        name = _unique_channel_name(getpass.getuser(), "announce_deny")
        creator = _test_user(1)
        announcer = _test_user(2)
        outsider = _test_user(3)

        channel_service.create_channel(
            name=name,
            createdby=creator,
            announce_only=True,
            announcers=[announcer],
        )

        verdict = channel_service.can_publish(name, outsider, is_sysop=False)
        assert verdict["allowed"] is False
        assert "announce-only" in verdict["reason"].lower()

    def test_announce_only_allows_announcer(
        self, channel_service, channel_cleanup
    ):
        name = _unique_channel_name(getpass.getuser(), "announce_allow")
        creator = _test_user(1)
        announcer = _test_user(2)

        channel_service.create_channel(
            name=name,
            createdby=creator,
            announce_only=True,
            announcers=[announcer],
        )

        verdict = channel_service.can_publish(name, announcer, is_sysop=False)
        assert verdict["allowed"] is True
        assert "announcer" in verdict["reason"].lower()

    def test_announce_only_allows_sysop(
        self, channel_service, channel_cleanup
    ):
        name = _unique_channel_name(getpass.getuser(), "announce_sysop")
        creator = _test_user(1)

        channel_service.create_channel(
            name=name, createdby=creator, announce_only=True
        )

        verdict = channel_service.can_publish(name, creator, is_sysop=True)
        assert verdict["allowed"] is True
        assert "sysop" in verdict["reason"].lower()

    def test_can_publish_returns_not_found_for_missing_channel(
        self, channel_service
    ):
        verdict = channel_service.can_publish(
            f"test_{getpass.getuser()}_channel_does_not_exist",
            _test_user(1),
        )
        assert verdict["allowed"] is False
        assert "not found" in verdict["reason"].lower()


# ---------------------------------------------------------------------------
# Unit tests: channel_publish() permission gating
# ---------------------------------------------------------------------------


class _StubChannelService:
    """Stand-in for ChannelService.can_publish() with call recording."""

    def __init__(self, verdict: Dict[str, Any]) -> None:
        self._verdict = verdict
        self.calls: List[tuple] = []

    def can_publish(self, channel: str, moniker: str) -> Dict[str, Any]:
        self.calls.append((channel, moniker))
        return self._verdict


def _make_state_with_callback(
    channel: str, received: List[Dict[str, Any]]
) -> ChannelState:
    state = ChannelState()
    channel_register_callback(state, channel, received.append)
    return state


@pytest.mark.unit
class TestChannelPublishGating:
    """Verify channel_publish() consults ChannelService when sender provided."""

    def test_publish_with_no_sender_skips_check(self) -> None:
        received: List[Dict[str, Any]] = []
        state = _make_state_with_callback("open:chan", received)

        asyncio.run(
            channel_publish(
                state=state,
                channel="open:chan",
                message={"hello": "world"},
            )
        )
        assert received == [{"hello": "world"}]

    def test_publish_allowed_when_service_permits(self) -> None:
        received: List[Dict[str, Any]] = []
        state = _make_state_with_callback("open:chan", received)
        stub = _StubChannelService({"allowed": True, "reason": "Channel is open"})

        with patch(
            "bbsengine6.services.channel.ChannelService",
            return_value=stub,
            create=True,
        ):
            asyncio.run(
                channel_publish(
                    state=state,
                    channel="open:chan",
                    message={"hello": "world"},
                    sender_moniker="alice",
                    args=MagicMock(name="args"),
                )
            )

        assert received == [{"hello": "world"}]
        assert stub.calls == [("open:chan", "alice")]

    def test_publish_denied_when_service_rejects(self) -> None:
        received: List[Dict[str, Any]] = []
        state = _make_state_with_callback("announce:chan", received)
        stub = _StubChannelService(
            {"allowed": False, "reason": "Channel is announce-only"}
        )

        with patch(
            "bbsengine6.services.channel.ChannelService",
            return_value=stub,
            create=True,
        ):
            asyncio.run(
                channel_publish(
                    state=state,
                    channel="announce:chan",
                    message={"hello": "world"},
                    sender_moniker="bob",
                    args=MagicMock(name="args"),
                )
            )

        assert received == []
        assert stub.calls == [("announce:chan", "bob")]

    def test_publish_swallows_service_errors(self) -> None:
        """If the service raises, the publish is dropped (fail closed)."""
        received: List[Dict[str, Any]] = []
        state = _make_state_with_callback("announce:chan", received)

        class _BrokenService:
            def can_publish(self, channel: str, moniker: str) -> Dict[str, Any]:
                raise RuntimeError("db down")

        with patch(
            "bbsengine6.services.channel.ChannelService",
            return_value=_BrokenService(),
            create=True,
        ):
            asyncio.run(
                channel_publish(
                    state=state,
                    channel="announce:chan",
                    message={"hello": "world"},
                    sender_moniker="bob",
                    args=MagicMock(name="args"),
                )
            )

        assert received == []

