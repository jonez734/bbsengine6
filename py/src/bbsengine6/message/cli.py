# bbsengine6/message/cli.py
#
# Operator CLI for the bbsengine6 message subsystem.
#
# Argparse + dispatch lives here so the same entry point is callable
# from the bin shim (``bbsengine6-msg``) and from REPL / tests. Mirrors
# the layout of :mod:`bbsengine6.net.ping`, where the bin shim is a
# one-liner that calls :func:`main`.
#
# Subcommands:
#   list-types, pending, unread, mark-read, mark-delivered, expunge,
#   register-type, resolve, send.
#
# Recipient tokens (``send --to``, ``resolve --to``) may be either
# plain monikers (``alice``, ``bob``) or group references prefixed
# with ``@`` (``@table``, ``@everyone``). The ``@`` prefix is
# dynamically resolved by :func:`bbsengine6.message.resolve_recipients`
# against ``engine.__message_group`` at call time, so dynamically
# managed groups (e.g. casino's ``@table``) work without any CLI-side
# caching.
#
# Mutating verbs (``send``, ``mark-read``, ``mark-delivered``,
# ``expunge``, ``register-type``) require ``--yes`` unless ``--dry-run``
# is set on ``send``. ``send --to`` containing ``@everyone`` is a
# privilege gate (not a confirmation): the CLI checks
# :func:`bbsengine6.backend.lib.issysop` against the connected DB
# role and refuses with a clear error if current_user is not in the
# ``sysop`` pg role.

from __future__ import annotations

import argparse
import sys

from bbsengine6 import io
from bbsengine6.message import (
    MessageUrgency,
    expunge,
    get_pending_messages,
    get_types,
    get_unread_count,
    mark_delivered,
    mark_read,
    register_type,
    render_template,
    resolve_recipients,
    send,
)

_EVERYONE = "@everyone"
_PROG_DEFAULT = "bbsengine6-msg"


def _split_to_tokens(values):
    out = []
    for v in values or ():
        if v is None:
            continue
        for piece in str(v).split(","):
            tok = piece.strip()
            if tok:
                out.append(tok)
    return out


def _parse_vars(pairs):
    out = {}
    for kv in pairs or ():
        if kv is None or "=" not in kv:
            raise ValueError("--vars expects k=v, got: %r" % (kv,))
        k, v = kv.split("=", 1)
        k = k.strip()
        if not k:
            raise ValueError("--vars expects non-empty key, got: %r" % (kv,))
        out[k] = v.strip()
    return out


def _is_everyone_present(recipients):
    return any(r.lower() == _EVERYONE for r in recipients)


def _make_cli_args(database):
    ns = argparse.Namespace()
    ns.databasename = database
    ns.database = database
    return ns


def _check_sysop(database):
    try:
        from bbsengine6.backend.lib import issysop
    except Exception:
        return False
    try:
        return bool(issysop(_make_cli_args(database)))
    except Exception:
        return False


def _print_message_row(row):
    io.echo(
        "#%s [%s] from=%s urgency=%s status=%s"
        % (
            row.get("id"),
            row.get("channel"),
            row.get("sender_moniker"),
            row.get("urgency"),
            row.get("status"),
        )
    )
    content_str = row.get("content") or ""
    io.echo("    " + content_str)


def _cmd_list_types(args):
    types = get_types(database=args.database)
    if not types:
        io.echo("no message types registered", level="info")
        return 0
    for t in types:
        io.echo(
            "%-32s rate=%4d/h approval=%s %s"
            % (
                t["type_name"],
                t["rate_limit_per_hour"],
                "Y" if t["requires_approval"] else "N",
                t["description"] or "",
            )
        )
    return 0


def _cmd_pending(args):
    rows = get_pending_messages(args.moniker, limit=args.limit, database=args.database)
    if not rows:
        io.echo("no pending messages for %s" % args.moniker, level="info")
        return 0
    io.echo("%d pending for %s:" % (len(rows), args.moniker), level="info")
    for r in rows:
        _print_message_row(r)
    return 0


def _cmd_unread(args):
    n = get_unread_count(args.moniker, database=args.database)
    io.echo("%s: %d unread" % (args.moniker, n))
    return 0


def _cmd_mark_read(args):
    if not args.yes:
        io.echo(
            "mark-read mutates engine.__message_recipient; pass --yes",
            level="error",
        )
        return 2
    mark_read(args.message_id, args.moniker, database=args.database)
    io.echo(
        "marked message #%d read for %s" % (args.message_id, args.moniker),
        level="ok",
    )
    return 0


def _cmd_mark_delivered(args):
    if not args.yes:
        io.echo(
            "mark-delivered mutates engine.__message_recipient; pass --yes",
            level="error",
        )
        return 2
    mark_delivered(args.message_id, args.moniker, database=args.database)
    io.echo(
        "marked message #%d delivered for %s" % (args.message_id, args.moniker),
        level="ok",
    )
    return 0


def _cmd_expunge(args):
    if not args.yes:
        io.echo(
            "expunge deletes from engine.__message; pass --yes",
            level="error",
        )
        return 2
    ok = expunge(args.message_id, args.sender, database=args.database)
    if ok:
        io.echo("expunged message #%d" % args.message_id, level="ok")
        return 0
    io.echo(
        "could not expunge #%d (not found or sender mismatch)" % args.message_id,
        level="error",
    )
    return 1


def _cmd_register_type(args):
    if not args.yes:
        io.echo(
            "register-type upserts engine.__message_type; pass --yes",
            level="error",
        )
        return 2
    ok = register_type(
        type_name=args.type_name,
        description=args.description or "",
        rate_limit_per_hour=args.rate_limit,
        requires_approval=args.requires_approval,
        database=args.database,
    )
    if not ok:
        io.echo("register-type failed (message system disabled?)", level="error")
        return 1
    io.echo("registered message type %s" % args.type_name, level="ok")
    return 0


def _cmd_resolve(args):
    tokens = _split_to_tokens(args.to)
    if not tokens:
        io.echo("resolve: at least one --to is required", level="error")
        return 2
    expanded = resolve_recipients(tokens, database=args.database)
    io.echo("input:    %s" % tokens)
    io.echo("expanded: %s" % expanded)
    if _is_everyone_present(tokens) and not expanded:
        io.echo(
            "@everyone expanded to zero approved members",
            level="warning",
        )
    expanded_lower = {e.lower() for e in expanded}
    missing = [
        t
        for t in tokens
        if t.startswith("@")
        and t.lower() != _EVERYONE
        and t[1:].strip().lower() not in expanded_lower
    ]
    if missing:
        for m in missing:
            io.echo(
                "group %s not found in engine.__message_group" % m,
                level="warning",
            )
    return 0


def _cmd_send(args):
    tokens = _split_to_tokens(args.to)
    if not tokens:
        io.echo("send: at least one --to is required", level="error")
        return 2
    if not args.type:
        io.echo("send: --type is required", level="error")
        return 2
    if args.body is None:
        io.echo("send: --body is required", level="error")
        return 2

    try:
        template_vars = _parse_vars(args.vars or [])
    except ValueError as e:
        io.echo("send: %s" % e, level="error")
        return 2

    rendered = render_template(args.body, template_vars)

    if args.dry_run:
        expanded = resolve_recipients(tokens, database=args.database)
        io.echo(
            "[dry-run] type=%s sender=%r urgency=%s"
            % (args.type, args.sender, args.urgency)
        )
        io.echo("[dry-run] recipients_in:  %s" % tokens)
        io.echo("[dry-run] recipients_out: %s" % expanded)
        io.echo("[dry-run] rendered:")
        io.echo(rendered)
        if not expanded:
            io.echo(
                "[dry-run] no recipients after expansion; nothing would be sent",
                level="warning",
            )
        return 0

    if not args.yes:
        io.echo(
            "send mutates engine.__message; pass --yes "
            "(or use --dry-run to preview)",
            level="error",
        )
        return 2

    if _is_everyone_present(tokens):
        if not _check_sysop(args.database):
            io.echo(
                "@everyone requires sysop role on this database; "
                "current_user is not in pg_auth_members for 'sysop'",
                level="error",
            )
            return 1

    try:
        urgency = MessageUrgency(args.urgency.upper())
    except ValueError:
        io.echo(
            "send: invalid --urgency %r (expected one of %s)"
            % (args.urgency, [m.value for m in MessageUrgency]),
            level="error",
        )
        return 2

    msg_id = send(
        notification_type=args.type,
        recipients=tokens,
        template=args.body,
        template_vars=template_vars,
        sender_moniker=args.sender,
        urgency=urgency,
        args=_make_cli_args(args.database),
    )
    if msg_id == 0:
        io.echo(
            "send returned 0: rate-limited, disabled, "
            "or no recipient survived expansion/blocking",
            level="warning",
        )
        return 1
    io.echo("sent message #%d on channel %s" % (msg_id, args.type), level="ok")
    return 0


def build_parser(prog=_PROG_DEFAULT):
    p = argparse.ArgumentParser(
        prog=prog,
        description=(
            "%s: operator CLI for the bbsengine6 message subsystem. "
            "Sends to plain monikers (alice, bob) or @group references "
            "(@table, @everyone); groups are resolved dynamically "
            "against engine.__message_group at call time." % prog
        ),
    )
    p.add_argument(
        "--database",
        default=None,
        help=(
            "target database name (default: $BBSENGINE6_DBNAME or 'zoid6')"
        ),
    )
    p.add_argument(
        "--version",
        action="version",
        version="%s 1.0 (bbsengine6.message.cli)" % prog,
    )

    sub = p.add_subparsers(dest="verb", required=True)

    sp = sub.add_parser("list-types", help="list registered message types")
    sp.set_defaults(func=_cmd_list_types)

    sp = sub.add_parser("pending", help="list pending messages for a moniker")
    sp.add_argument("moniker")
    sp.add_argument("--limit", type=int, default=50)
    sp.set_defaults(func=_cmd_pending)

    sp = sub.add_parser("unread", help="count unread messages for a moniker")
    sp.add_argument("moniker")
    sp.set_defaults(func=_cmd_unread)

    sp = sub.add_parser(
        "mark-read", help="mark a message as read for a recipient (mutating)"
    )
    sp.add_argument("moniker")
    sp.add_argument("--message-id", type=int, required=True)
    sp.add_argument("--yes", action="store_true")
    sp.set_defaults(func=_cmd_mark_read)

    sp = sub.add_parser(
        "mark-delivered",
        help="mark a message as delivered for a recipient (mutating)",
    )
    sp.add_argument("moniker")
    sp.add_argument("--message-id", type=int, required=True)
    sp.add_argument("--yes", action="store_true")
    sp.set_defaults(func=_cmd_mark_delivered)

    sp = sub.add_parser(
        "expunge",
        help="sender-side hard delete of a message (mutating)",
    )
    sp.add_argument("--message-id", type=int, required=True)
    sp.add_argument("--sender", required=True, help="sender moniker (auth check)")
    sp.add_argument("--yes", action="store_true")
    sp.set_defaults(func=_cmd_expunge)

    sp = sub.add_parser(
        "register-type",
        help="upsert a row in engine.__message_type (mutating)",
    )
    sp.add_argument("type_name")
    sp.add_argument("--description", default="")
    sp.add_argument(
        "--rate-limit",
        type=int,
        default=0,
        help="per-hour per-sender limit (0 = unlimited)",
    )
    sp.add_argument("--requires-approval", action="store_true")
    sp.add_argument("--yes", action="store_true")
    sp.set_defaults(func=_cmd_register_type)

    sp = sub.add_parser(
        "resolve",
        help="expand --to tokens via @group/@everyone (read-only)",
    )
    sp.add_argument(
        "--to",
        action="append",
        default=[],
        help="recipient token; repeatable; comma-separated allowed",
    )
    sp.set_defaults(func=_cmd_resolve)

    sp = sub.add_parser(
        "send",
        help="send a message to plain monikers and/or @group references",
    )
    sp.add_argument(
        "--to",
        action="append",
        default=[],
        help=(
            "recipient token (alice, @table, @everyone); "
            "repeatable; comma-separated allowed"
        ),
    )
    sp.add_argument("--type", required=True, help="channel/type name (e.g. casino_kick)")
    sp.add_argument(
        "--body", required=True, help="template body; rendered via render_template"
    )
    sp.add_argument(
        "--sender",
        default=None,
        help="sender moniker (default: system / None)",
    )
    sp.add_argument(
        "--urgency",
        default="ROUTINE",
        help="ROUTINE|IMPORTANT|URGENT|CRITICAL (default ROUTINE)",
    )
    sp.add_argument(
        "--vars",
        action="append",
        default=[],
        help="template variable k=v; repeatable",
    )
    sp.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve + render but do not call send",
    )
    sp.add_argument(
        "--yes", action="store_true", help="confirm mutating action"
    )
    sp.set_defaults(func=_cmd_send)

    return p


def main(argv=None, *, prog=_PROG_DEFAULT):
    p = build_parser(prog=prog)
    try:
        args = p.parse_args(argv)
    except SystemExit as e:
        code = int(getattr(e, "code", 2) or 2)
        return 2 if code == 0 else code
    try:
        return args.func(args)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        io.echo("interrupted", level="warning")
        return 130
    except Exception as exc:
        io.echo("%s: %s" % (prog, exc), level="error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
