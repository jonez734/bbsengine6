"""
Subscribe and publish access on channels: the subscribe gate, the subscribe authority hook, and
publish-requires-subscription.

Test tiers
----------

``@pytest.mark.unit`` tests
    Use the in-memory ``ChannelService`` decision paths with the channel lookup and the sysop
    check stubbed. No database required.

Integration tests (no marker)
    Use the ``zoid6test`` database against ``engine.__channel``. They need
    ``sql/channel_access_migration.sql`` applied to that database.
"""

from __future__ import annotations

import argparse
import uuid
from unittest.mock import patch

import pytest

from bbsengine6.services import channel as channel_module
from bbsengine6.services.channel import (
    ChannelService,
    register_subscribe_authority,
    unregister_subscribe_authority,
)


def _svc() -> ChannelService:
    return ChannelService(argparse.Namespace(databasename="zoid6test", debug=False))


def _channel(**flags) -> dict:
    base = {
        "name": "casino:table:t1:chat",
        "announce_only": False,
        "subscribe_restricted": False,
        "publish_requires_subscription": False,
        "announcers": [],
    }
    base.update(flags)
    return base


@pytest.fixture
def authority():
    """A subscribe authority that the test controls; always unregistered afterwards."""
    verdicts = {}

    def decide(channel_name, moniker):
        return verdicts.get((channel_name, moniker))

    register_subscribe_authority(decide)
    try:
        yield verdicts
    finally:
        unregister_subscribe_authority(decide)


# ---------------------------------------------------------------- subscribe gate (unit)


@pytest.mark.unit
def test_open_channel_allows_any_member():
    with patch.object(ChannelService, "get_channel", return_value=_channel()), \
         patch.object(channel_module.member_module, "issysop", return_value=False):
        verdict = _svc().can_subscribe("casino:table:t1:chat", "alice")
    assert verdict["allowed"] is True


@pytest.mark.unit
def test_restricted_channel_with_no_authority_denies():
    with patch.object(ChannelService, "get_channel", return_value=_channel(subscribe_restricted=True)), \
         patch.object(channel_module.member_module, "issysop", return_value=False):
        verdict = _svc().can_subscribe("casino:table:t1:events", "alice")
    assert verdict["allowed"] is False


@pytest.mark.unit
def test_restricted_channel_follows_the_authority(authority):
    channel = _channel(subscribe_restricted=True, name="casino:table:t1:events")
    authority[("casino:table:t1:events", "alice")] = True
    authority[("casino:table:t1:events", "mallory")] = False
    with patch.object(ChannelService, "get_channel", return_value=channel), \
         patch.object(channel_module.member_module, "issysop", return_value=False):
        assert _svc().can_subscribe("casino:table:t1:events", "alice")["allowed"] is True
        assert _svc().can_subscribe("casino:table:t1:events", "mallory")["allowed"] is False


@pytest.mark.unit
def test_sysop_subscribes_to_a_restricted_channel_without_an_authority():
    with patch.object(ChannelService, "get_channel", return_value=_channel(subscribe_restricted=True)), \
         patch.object(channel_module.member_module, "issysop", return_value=True):
        verdict = _svc().can_subscribe("casino:table:t1:events", "boss")
    assert verdict["allowed"] is True
    assert verdict["reason"] == "Sysop"


@pytest.mark.unit
def test_a_crashing_authority_denies_rather_than_raising(authority):
    def boom(channel_name, moniker):
        raise RuntimeError("authority down")

    register_subscribe_authority(boom)
    try:
        channel = _channel(subscribe_restricted=True, name="casino:table:t1:events")
        with patch.object(ChannelService, "get_channel", return_value=channel), \
             patch.object(channel_module.member_module, "issysop", return_value=False):
            verdict = _svc().can_subscribe("casino:table:t1:events", "alice")
    finally:
        unregister_subscribe_authority(boom)
    assert verdict["allowed"] is False
    assert "authority down" in verdict["reason"]


@pytest.mark.unit
def test_member_dm_channel_is_owner_only():
    svc = _svc()
    assert svc.can_subscribe("member:alice", "alice")["allowed"] is True
    assert svc.can_subscribe("member:alice", "bob")["allowed"] is False


@pytest.mark.unit
def test_authority_registration_is_idempotent(authority):
    def once(channel_name, moniker):
        return None

    register_subscribe_authority(once)
    register_subscribe_authority(once)
    try:
        assert channel_module._subscribe_authorities.count(once) == 1
    finally:
        unregister_subscribe_authority(once)


# ---------------------------------------------------------------- publish requires subscription (unit)


@pytest.mark.unit
def test_publish_requires_subscription_blocks_a_non_subscriber():
    channel = _channel(publish_requires_subscription=True)
    with patch.object(ChannelService, "get_channel", return_value=channel), \
         patch.object(channel_module.member_module, "issysop", return_value=False):
        verdict = _svc().can_publish(channel["name"], "alice", is_sysop=False, subscribed=False)
    assert verdict["allowed"] is False
    assert "subscription" in verdict["reason"]


@pytest.mark.unit
def test_publish_requires_subscription_allows_a_subscriber():
    channel = _channel(publish_requires_subscription=True)
    with patch.object(ChannelService, "get_channel", return_value=channel):
        verdict = _svc().can_publish(channel["name"], "alice", is_sysop=False, subscribed=True)
    assert verdict["allowed"] is True


@pytest.mark.unit
def test_publish_subscription_rule_does_not_apply_to_sysop():
    channel = _channel(publish_requires_subscription=True)
    with patch.object(ChannelService, "get_channel", return_value=channel):
        verdict = _svc().can_publish(channel["name"], "boss", is_sysop=True, subscribed=False)
    assert verdict["allowed"] is True


@pytest.mark.unit
def test_announce_only_still_applies_without_the_subscription_flag():
    channel = _channel(announce_only=True, announcers=[])
    with patch.object(ChannelService, "get_channel", return_value=channel):
        verdict = _svc().can_publish(channel["name"], "alice", is_sysop=False, subscribed=True)
    assert verdict["allowed"] is False


# ---------------------------------------------------------------- integration (zoid6test)


@pytest.mark.integration
def test_create_channel_stores_the_access_flags():
    name = f"test-access-{uuid.uuid4().hex[:8]}"
    svc = _svc()
    res = svc.create_channel(
        name=name, createdby="bjbed_a", announce_only=True,
        subscribe_restricted=True, publish_requires_subscription=False,
    )
    assert res["success"], res
    try:
        row = svc.get_channel(name)
        assert row["announce_only"] is True
        assert row["subscribe_restricted"] is True
        assert row["publish_requires_subscription"] is False
    finally:
        from bbsengine6 import database
        with database.connect(svc.args) as conn, database.cursor(conn) as cur:
            cur.execute(database.query("DELETE FROM $engine.__channel WHERE name = :n", n=name))
