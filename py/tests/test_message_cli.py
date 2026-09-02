# test_message_cli.py
# Tests for bbsengine6.message.cli (operator CLI shim).

from unittest.mock import patch

import pytest

from bbsengine6.message import cli as cli_module
from bbsengine6.message.cli import build_parser, main

# ---------------------------------------------------------------------
# Helpers


def _free_port():  # pragma: no cover
    import socket as _s
    with _s.socket(_s.AF_INET, _s.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------
# _split_to_tokens


class TestSplitToTokens:
    def test_single_value(self):
        assert cli_module._split_to_tokens(["alice"]) == ["alice"]

    def test_repeated_values(self):
        assert cli_module._split_to_tokens(["alice", "bob"]) == ["alice", "bob"]

    def test_comma_separated(self):
        assert cli_module._split_to_tokens(["@table,bob"]) == ["@table", "bob"]

    def test_mixed_repeated_and_comma(self):
        assert cli_module._split_to_tokens(["alice", "@table,bob", ""]) == [
            "alice",
            "@table",
            "bob",
        ]

    def test_strips_whitespace(self):
        assert cli_module._split_to_tokens(["  alice  ,  @table  "]) == [
            "alice",
            "@table",
        ]

    def test_empty_or_none(self):
        assert cli_module._split_to_tokens([]) == []
        assert cli_module._split_to_tokens(None) == []
        assert cli_module._split_to_tokens(["", "  "]) == []


# ---------------------------------------------------------------------
# _parse_vars


class TestParseVars:
    def test_basic(self):
        assert cli_module._parse_vars(["n=3", "name=alice"]) == {
            "n": "3",
            "name": "alice",
        }

    def test_value_with_equals(self):
        assert cli_module._parse_vars(["expr=a=b"]) == {"expr": "a=b"}

    def test_empty_value(self):
        assert cli_module._parse_vars(["x="]) == {"x": ""}

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            cli_module._parse_vars(["noequals"])
        with pytest.raises(ValueError):
            cli_module._parse_vars(["=missingkey"])

    def test_empty_input(self):
        assert cli_module._parse_vars([]) == {}


# ---------------------------------------------------------------------
# build_parser


class TestBuildParser:
    def test_prog_default(self):
        p = build_parser()
        assert p.prog == "bbsengine6-msg"

    def test_prog_override(self):
        p = build_parser(prog="custom-name")
        assert p.prog == "custom-name"

    def test_version_action(self):
        p = build_parser(prog="x")
        with pytest.raises(SystemExit):
            p.parse_args(["--version"])

    def test_required_subcommand(self):
        p = build_parser(prog="x")
        with pytest.raises(SystemExit):
            p.parse_args([])

    def test_database_flag(self):
        p = build_parser(prog="x")
        args = p.parse_args(["--database", "zoid6", "list-types"])
        assert args.database == "zoid6"
        assert args.verb == "list-types"

    def test_send_requires_type_and_body(self):
        p = build_parser(prog="x")
        # Missing --type and --body
        with pytest.raises(SystemExit):
            p.parse_args(["send"])
        # Missing --body
        with pytest.raises(SystemExit):
            p.parse_args(["send", "--type", "x"])
        # Missing --type
        with pytest.raises(SystemExit):
            p.parse_args(["send", "--body", "b"])
        # --to is optional; with --type + --body it should parse.
        args = p.parse_args(["send", "--to", "alice", "--type", "x", "--body", "b"])
        assert args.to == ["alice"]

    def test_send_parses_all_flags(self):
        p = build_parser(prog="x")
        args = p.parse_args(
            [
                "send",
                "--to", "alice",
                "--to", "@table,bob",
                "--type", "casino_kick",
                "--body", "Round {n}",
                "--sender", "house",
                "--urgency", "URGENT",
                "--vars", "n=3",
                "--vars", "x=y",
                "--dry-run",
            ]
        )
        assert args.to == ["alice", "@table,bob"]
        assert args.type == "casino_kick"
        assert args.body == "Round {n}"
        assert args.sender == "house"
        assert args.urgency == "URGENT"
        assert args.vars == ["n=3", "x=y"]
        assert args.dry_run is True
        assert args.yes is False

    def test_resolve_help(self):
        p = build_parser(prog="x")
        args = p.parse_args(["resolve", "--to", "@table", "--to", "alice,bob"])
        assert args.to == ["@table", "alice,bob"]


# ---------------------------------------------------------------------
# _cmd_list_types


class TestListTypes:
    @patch("bbsengine6.message.cli.get_types")
    def test_empty(self, mock_get):
        mock_get.return_value = []
        rc = main(["list-types"])
        assert rc == 0
        mock_get.assert_called_once()

    @patch("bbsengine6.message.cli.get_types")
    def test_renders_rows(self, mock_get):
        mock_get.return_value = [
            {
                "type_name": "casino_kick",
                "rate_limit_per_hour": 10,
                "requires_approval": False,
                "description": "kicked from table",
            },
            {
                "type_name": "casino:approval",
                "rate_limit_per_hour": 0,
                "requires_approval": True,
                "description": "needs mod",
            },
        ]
        rc = main(["list-types"])
        assert rc == 0


# ---------------------------------------------------------------------
# _cmd_pending / _cmd_unread


class TestPending:
    @patch("bbsengine6.message.cli.get_pending_messages")
    def test_empty(self, mock_get):
        mock_get.return_value = []
        rc = main(["pending", "alice"])
        assert rc == 0
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "alice"
        assert kwargs.get("limit") == 50

    @patch("bbsengine6.message.cli.get_pending_messages")
    def test_renders(self, mock_get):
        mock_get.return_value = [
            {
                "id": 7,
                "channel": "casino_kick",
                "sender_moniker": "house",
                "content": "bye",
                "urgency": "URGENT",
                "status": "pending",
            }
        ]
        rc = main(["pending", "alice", "--limit", "5"])
        assert rc == 0


class TestUnread:
    @patch("bbsengine6.message.cli.get_unread_count")
    def test_renders(self, mock_get):
        mock_get.return_value = 3
        rc = main(["unread", "alice"])
        assert rc == 0


# ---------------------------------------------------------------------
# mark-* / expunge mutating verbs require --yes


class TestMutatingRequireYes:
    @patch("bbsengine6.message.cli.mark_read")
    def test_mark_read_requires_yes(self, mock_op):
        rc = main(["mark-read", "alice", "--message-id", "1"])
        assert rc == 2
        mock_op.assert_not_called()

    @patch("bbsengine6.message.cli.mark_read")
    def test_mark_read_with_yes(self, mock_op):
        rc = main(["mark-read", "alice", "--message-id", "1", "--yes"])
        assert rc == 0
        mock_op.assert_called_once_with(1, "alice", database=None)

    @patch("bbsengine6.message.cli.mark_delivered")
    def test_mark_delivered_requires_yes(self, mock_op):
        rc = main(["mark-delivered", "alice", "--message-id", "1"])
        assert rc == 2
        mock_op.assert_not_called()

    @patch("bbsengine6.message.cli.mark_delivered")
    def test_mark_delivered_with_yes(self, mock_op):
        rc = main(["mark-delivered", "alice", "--message-id", "1", "--yes"])
        assert rc == 0
        mock_op.assert_called_once_with(1, "alice", database=None)

    @patch("bbsengine6.message.cli.expunge")
    def test_expunge_requires_yes(self, mock_op):
        rc = main(["expunge", "--message-id", "1", "--sender", "alice"])
        assert rc == 2
        mock_op.assert_not_called()

    @patch("bbsengine6.message.cli.expunge")
    def test_expunge_with_yes(self, mock_op):
        mock_op.return_value = True
        rc = main(
            ["expunge", "--message-id", "1", "--sender", "alice", "--yes"]
        )
        assert rc == 0

    @patch("bbsengine6.message.cli.expunge")
    def test_expunge_failure(self, mock_op):
        mock_op.return_value = False
        rc = main(
            ["expunge", "--message-id", "1", "--sender", "alice", "--yes"]
        )
        assert rc == 1

    @patch("bbsengine6.message.cli.register_type")
    def test_register_type_requires_yes(self, mock_op):
        rc = main(["register-type", "casino_kick"])
        assert rc == 2
        mock_op.assert_not_called()

    @patch("bbsengine6.message.cli.register_type")
    def test_register_type_with_yes(self, mock_op):
        mock_op.return_value = True
        rc = main(
            [
                "register-type", "casino_kick",
                "--description", "kicked",
                "--rate-limit", "10",
                "--requires-approval",
                "--yes",
            ]
        )
        assert rc == 0
        mock_op.assert_called_once_with(
            type_name="casino_kick",
            description="kicked",
            rate_limit_per_hour=10,
            requires_approval=True,
            database=None,
        )


# ---------------------------------------------------------------------
# resolve (read-only)


class TestResolve:
    @patch("bbsengine6.message.cli.resolve_recipients")
    def test_expansion(self, mock_resolve):
        mock_resolve.return_value = ["alice", "bob", "charlie"]
        rc = main(["resolve", "--to", "alice", "--to", "@table"])
        assert rc == 0
        mock_resolve.assert_called_once()
        args = mock_resolve.call_args[0][0]
        assert args == ["alice", "@table"]

    @patch("bbsengine6.message.cli.resolve_recipients")
    def test_everyone_empty_warns(self, mock_resolve):
        mock_resolve.return_value = []
        rc = main(["resolve", "--to", "@everyone"])
        assert rc == 0

    @patch("bbsengine6.message.cli.resolve_recipients")
    def test_missing_group_warns(self, mock_resolve):
        mock_resolve.return_value = ["alice"]
        rc = main(["resolve", "--to", "@nonexistent", "--to", "alice"])
        assert rc == 0

    def test_no_to_errors(self):
        rc = main(["resolve"])
        assert rc == 2


# ---------------------------------------------------------------------
# send (mutating)


class TestSend:
    @patch("bbsengine6.message.cli.render_template")
    def test_dry_run_does_not_call_send(self, mock_render, monkeypatch):
        mock_render.return_value = "rendered body"
        captured = []
        def _resolve(tokens, database=None):
            captured.append(tokens)
            return ["alice", "bob"]
        monkeypatch.setattr(cli_module, "resolve_recipients", _resolve)
        rc = main(
            [
                "send",
                "--to", "alice",
                "--to", "@table,bob",
                "--type", "casino_kick",
                "--body", "Round {n}",
                "--vars", "n=3",
                "--dry-run",
            ]
        )
        assert rc == 0
        assert captured == [["alice", "@table", "bob"]]
        # send() must not have been invoked: only render + resolve.

    def test_requires_yes_when_not_dry_run(self):
        rc = main(
            [
                "send",
                "--to", "alice",
                "--type", "casino_kick",
                "--body", "hi",
            ]
        )
        assert rc == 2

    @patch("bbsengine6.message.cli.render_template")
    @patch("bbsengine6.message.cli.send")
    def test_successful_send(self, mock_send, mock_render):
        mock_render.return_value = "hello alice"
        mock_send.return_value = 42
        rc = main(
            [
                "send",
                "--to", "alice",
                "--to", "@table",
                "--type", "casino_kick",
                "--body", "Round {n}",
                "--vars", "n=3",
                "--sender", "house",
                "--yes",
            ]
        )
        assert rc == 0
        mock_send.assert_called_once()
        kwargs = mock_send.call_args.kwargs
        assert kwargs["notification_type"] == "casino_kick"
        assert kwargs["recipients"] == ["alice", "@table"]
        assert kwargs["sender_moniker"] == "house"
        assert kwargs["template_vars"] == {"n": "3"}

    @patch("bbsengine6.message.cli.render_template")
    @patch("bbsengine6.message.cli.send")
    def test_send_zero_returns_1(self, mock_send, mock_render):
        mock_render.return_value = "x"
        mock_send.return_value = 0
        rc = main(
            [
                "send",
                "--to", "alice",
                "--type", "casino_kick",
                "--body", "x",
                "--yes",
            ]
        )
        assert rc == 1

    @patch("bbsengine6.message.cli.render_template")
    def test_invalid_urgency(self, mock_render):
        mock_render.return_value = "x"
        rc = main(
            [
                "send",
                "--to", "alice",
                "--type", "casino_kick",
                "--body", "x",
                "--urgency", "NOPE",
                "--yes",
            ]
        )
        assert rc == 2

    @patch("bbsengine6.message.cli._check_sysop")
    @patch("bbsengine6.message.cli.render_template")
    @patch("bbsengine6.message.cli.send")
    def test_everyone_requires_sysop(self, mock_send, mock_render, mock_sysop):
        mock_sysop.return_value = False
        mock_render.return_value = "x"
        rc = main(
            [
                "send",
                "--to", "@everyone",
                "--type", "casino_kick",
                "--body", "x",
                "--yes",
            ]
        )
        assert rc == 1
        mock_send.assert_not_called()

    @patch("bbsengine6.message.cli._check_sysop")
    @patch("bbsengine6.message.cli.render_template")
    @patch("bbsengine6.message.cli.send")
    def test_everyone_with_sysop_proceeds(self, mock_send, mock_render, mock_sysop):
        mock_sysop.return_value = True
        mock_render.return_value = "x"
        mock_send.return_value = 99
        rc = main(
            [
                "send",
                "--to", "@everyone",
                "--type", "casino_kick",
                "--body", "x",
                "--yes",
            ]
        )
        assert rc == 0
        mock_send.assert_called_once()

    def test_missing_to_errors(self):
        rc = main(["send", "--type", "x", "--body", "y", "--yes"])
        assert rc == 2

    def test_invalid_vars(self):
        rc = main(
            [
                "send",
                "--to", "alice",
                "--type", "x",
                "--body", "y",
                "--vars", "noequals",
                "--yes",
            ]
        )
        assert rc == 2


# ---------------------------------------------------------------------
# main error paths


class TestMainErrorPaths:
    def test_unknown_verb_returns_2(self):
        rc = main(["nonexistent"])
        assert rc == 2

    @patch("bbsengine6.message.cli.get_types")
    def test_handler_exception_returns_1(self, mock_get):
        mock_get.side_effect = RuntimeError("boom")
        rc = main(["list-types"])
        assert rc == 1

    def test_keyboard_interrupt_returns_130(self, monkeypatch):
        def _boom(args):
            raise KeyboardInterrupt()
        monkeypatch.setattr(cli_module, "_cmd_list_types", _boom)
        rc = main(["list-types"])
        assert rc == 130
