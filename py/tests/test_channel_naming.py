"""
Tests for bbsengine6.channel.naming helpers.

The naming convention is the contract between modules; if these
helpers drift, channels silently route to the wrong audience.
"""

from __future__ import annotations

from bbsengine6.channel.naming import (
    announcement_channel,
    global_channel,
    member_channel,
    parse_channel,
    shout_channel,
    table_channel,
)


class TestNamingHelpers:
    """Each helper produces the documented format string."""

    def test_table_channel(self):
        assert table_channel("casino", "bj-1") == "casino:table:bj-1"
        # empyre uses 'island' not 'table'; the helper is app-agnostic.
        assert table_channel("empyre", "island-5") == "empyre:table:island-5"

    def test_member_channel(self):
        assert member_channel("alice") == "member:alice"
        assert member_channel("zoid6:casino") == "member:zoid6:casino"

    def test_global_channel(self):
        assert global_channel("casino") == "casino:global"
        assert global_channel("empyre") == "empyre:global"

    def test_announcement_channel(self):
        assert announcement_channel() == "system:announcements"

    def test_shout_channel(self):
        assert shout_channel() == "system:shout"


class TestParseChannel:
    """parse_channel roundtrips with the helpers."""

    def test_table_channel_roundtrip(self):
        app, kind, id_ = parse_channel("casino:table:bj-1")
        assert app == "casino"
        assert kind == "table"
        assert id_ == "bj-1"

    def test_global_channel_roundtrip(self):
        # global_channel produces "casino:global" which only has two
        # segments; parse_channel pads to three.
        app, kind, id_ = parse_channel("casino:global")
        assert app == "casino"
        assert kind == "global"
        assert id_ == ""

    def test_member_channel_roundtrip(self):
        app, kind, id_ = parse_channel("member:alice")
        assert app == "member"
        assert kind == "alice"
        assert id_ == ""

    def test_non_namespaced_returns_empty_app(self):
        app, kind, id_ = parse_channel("notnamespaced")
        assert app == ""
        assert kind == ""
        assert id_ == "notnamespaced"

    def test_empty_string_returns_empty(self):
        app, kind, id_ = parse_channel("")
        assert app == ""
        assert kind == ""
        assert id_ == ""
