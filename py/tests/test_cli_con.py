"""
Tests for the ``con channel`` CLI subcommand parser.

CLI tests focus on the argparse wiring and routing, not the underlying
ChannelService calls (those have integration tests in
test_channel_announce_only.py). The mocked ``ChannelService`` here
captures calls so we can verify the right verb / right args reach
the service layer.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from unittest.mock import MagicMock

import pytest

from bbsengine6.console import channel as channel_module


@pytest.fixture
def mock_service(monkeypatch):
    """Patch ChannelService so verb handlers see a stub."""
    captured = MagicMock(name="ChannelService")

    def _factory(args):
        return captured

    monkeypatch.setattr(channel_module, "ChannelService", _factory)
    return captured


def _run_argv(argv: list[str]) -> tuple[int, str]:
    """Run ``con channel <verb> ...`` end-to-end and capture stdout JSON."""
    parser = channel_module.buildargs()
    args = parser.parse_args(argv)
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            rc = channel_module.main(args)
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 1
    output = buf.getvalue().strip()
    return rc, output


class TestChannelCLI:
    """Each verb routes to the right ChannelService method.

    The CLI's ``main`` returns ``True`` (success) / ``False`` (failure),
    not an int rc. Tests assert ``result is True`` / ``result is False``
    accordingly.
    """

    def test_list_uses_list_channels(self, mock_service):
        mock_service.list_channels.return_value = []
        result, output = _run_argv(["--moniker", "sysop", "list"])
        assert result is True
        mock_service.list_channels.assert_called_once()
        kwargs = mock_service.list_channels.call_args.kwargs
        assert kwargs["limit"] == 100
        assert kwargs["offset"] == 0
        assert kwargs["announce_only"] is None
        payload = json.loads(output)
        assert payload["success"] is True
        assert payload["channels"] == []

    def test_list_with_announce_only_filter(self, mock_service):
        mock_service.list_channels.return_value = []
        _run_argv(["--moniker", "sysop", "list", "--announce-only", "yes"])
        kwargs = mock_service.list_channels.call_args.kwargs
        assert kwargs["announce_only"] is True

    def test_list_with_limit_and_offset(self, mock_service):
        mock_service.list_channels.return_value = []
        _run_argv(["--moniker", "sysop", "list", "--limit", "10", "--offset", "20"])
        kwargs = mock_service.list_channels.call_args.kwargs
        assert kwargs["limit"] == 10
        assert kwargs["offset"] == 20

    def test_get_existing_channel(self, mock_service):
        mock_service.get_channel.return_value = {
            "name": "casino:global",
            "announce_only": False,
            "announcers": [],
        }
        result, output = _run_argv(["--moniker", "sysop", "get", "casino:global"])
        assert result is True
        payload = json.loads(output)
        assert payload["success"] is True
        assert payload["channel"]["name"] == "casino:global"

    def test_get_missing_channel_returns_false(self, mock_service):
        mock_service.get_channel.return_value = None
        result, output = _run_argv(["--moniker", "sysop", "get", "nonexistent"])
        assert result is False
        payload = json.loads(output)
        assert payload["success"] is False
        assert payload["code"] == "not_found"

    def test_create_calls_create_channel(self, mock_service):
        mock_service.create_channel.return_value = {"success": True}
        result, output = _run_argv([
            "--moniker", "zoid6:casino",
            "create", "myapp:test",
            "--description", "Test channel",
        ])
        assert result is True
        kwargs = mock_service.create_channel.call_args.kwargs
        assert kwargs["name"] == "myapp:test"
        assert kwargs["createdby"] == "zoid6:casino"
        assert kwargs["description"] == "Test channel"
        assert kwargs["announce_only"] is False
        assert kwargs["announcers"] == []

    def test_create_with_announce_only(self, mock_service):
        mock_service.create_channel.return_value = {"success": True}
        _run_argv([
            "--moniker", "sysop",
            "create", "myapp:vip",
            "--announce-only",
            "--announcer", "alice",
            "--announcer", "bob",
        ])
        kwargs = mock_service.create_channel.call_args.kwargs
        assert kwargs["announce_only"] is True
        assert kwargs["announcers"] == ["alice", "bob"]

    def test_create_failure_returns_false(self, mock_service):
        mock_service.create_channel.return_value = {
            "success": False,
            "message": "Channel already exists",
        }
        result, _ = _run_argv(["--moniker", "sysop", "create", "dup"])
        assert result is False

    def test_set_announce_only_true(self, mock_service):
        mock_service.set_announce_only.return_value = {"success": True}
        result, output = _run_argv([
            "--moniker", "zoid6:casino",
            "set-announce-only", "myapp:test", "true",
        ])
        assert result is True
        kwargs = mock_service.set_announce_only.call_args.kwargs
        assert kwargs["name"] == "myapp:test"
        assert kwargs["announce_only"] is True
        assert kwargs["by_moniker"] == "zoid6:casino"

    def test_set_announce_only_false(self, mock_service):
        mock_service.set_announce_only.return_value = {"success": True}
        _run_argv([
            "--moniker", "sysop",
            "set-announce-only", "myapp:test", "false",
        ])
        kwargs = mock_service.set_announce_only.call_args.kwargs
        assert kwargs["announce_only"] is False

    def test_add_announcer(self, mock_service):
        mock_service.add_announcer.return_value = {"success": True}
        _run_argv([
            "--moniker", "zoid6:casino",
            "add-announcer", "myapp:vip", "alice",
        ])
        kwargs = mock_service.add_announcer.call_args.kwargs
        assert kwargs["channel_name"] == "myapp:vip"
        assert kwargs["moniker"] == "alice"
        assert kwargs["addedby"] == "zoid6:casino"

    def test_remove_announcer(self, mock_service):
        mock_service.remove_announcer.return_value = {"success": True}
        _run_argv([
            "--moniker", "zoid6:casino",
            "remove-announcer", "myapp:vip", "alice",
        ])
        kwargs = mock_service.remove_announcer.call_args.kwargs
        assert kwargs["channel_name"] == "myapp:vip"
        assert kwargs["moniker"] == "alice"
        assert kwargs["actor_moniker"] == "zoid6:casino"

    def test_missing_moniker_exits(self, mock_service):
        """No --moniker flag -> SystemExit with non-zero code."""
        parser = channel_module.buildargs()
        with pytest.raises(SystemExit):
            parser.parse_args(["list"])


class TestChannelAdminHandler:
    """Lightweight test for ChannelAdminHandler registration behavior."""

    def test_allowed_verbs_default(self):
        """All six verbs are allowed when allowed_verbs is None."""
        from bbsengine6.channel.api.handler import ChannelAdminHandler
        from bbsengine6.session import SessionManager

        handler = ChannelAdminHandler(
            args=MagicMock(),
            session_manager=SessionManager(),
            channel_state=MagicMock(),
            allowed_verbs=None,
        )
        assert "channel_create" in handler.allowed_verbs
        assert "channel_list" in handler.allowed_verbs
        assert "channel_get" in handler.allowed_verbs
        assert "channel_set_announce_only" in handler.allowed_verbs
        assert "channel_add_announcer" in handler.allowed_verbs
        assert "channel_remove_announcer" in handler.allowed_verbs

    def test_allowed_verbs_filtered(self):
        """Custom allowed_verbs list restricts to that subset."""
        from bbsengine6.channel.api.handler import ChannelAdminHandler
        from bbsengine6.session import SessionManager

        handler = ChannelAdminHandler(
            args=MagicMock(),
            session_manager=SessionManager(),
            channel_state=MagicMock(),
            allowed_verbs=["channel_list"],
        )
        assert handler.allowed_verbs == {"channel_list"}
