"""
bbsengine6.console.channel - ``console channel`` subcommand.

Operator-facing channel management. Mirrors the WS-side
ChannelAdminHandler so operators don't need a WebSocket client to
create, list, or toggle channel announce-only / announcer lists.

Verb catalog:

  console channel create <name> [--announce-only] [--announcer M]...
      Create a channel owned by the actor (``--moniker``).

  console channel list [--announce-only|--no-announce-only] [--limit N]
      List configured channels (default 100).

  console channel get <name>
      Show one channel's full record (announcers array, flags, etc).

  console channel set-announce-only <name> true|false
      Toggle the announce_only flag. Requires sysop OR creator.

  console channel add-announcer <name> <moniker>
      Add a member to a channel's announcer list.

  console channel remove-announcer <name> <moniker>
      Remove a member from a channel's announcer list.

Output: JSON to stdout (one envelope per call). Errors are JSON too
with ``{"success": false, "message": "..."}``; non-zero exit on
failure so shell scripts can detect via ``$?``.

Authentication: ``--moniker`` is required. The actor must be a sysop
OR the creator of the channel to mutate it (matches the WS-side
``ChannelService._require_authority``).
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from bbsengine6 import database, io
from bbsengine6.services.channel import ChannelService


def _emit(payload: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, default=str) + "\n")
    sys.stdout.flush()


def _exit_with_error(message: str, code: int = 1) -> None:
    _emit({"success": False, "message": message})
    sys.exit(code)


def _service(args: argparse.Namespace) -> ChannelService:
    return ChannelService(args)


def _resolve_moniker(args: argparse.Namespace) -> str:
    moniker = getattr(args, "moniker", None)
    if not moniker:
        _exit_with_error("--moniker is required for channel operations")
    return moniker


# ---------------------------------------------------------------------------
# Verb implementations
# ---------------------------------------------------------------------------


def cmd_create(args: argparse.Namespace) -> int:
    actor = _resolve_moniker(args)
    service = _service(args)
    result = service.create_channel(
        name=args.name,
        createdby=actor,
        description=args.description,
        announce_only=bool(args.announce_only),
        announcers=list(args.announcer or []),
    )
    _emit(result)
    return 0 if result.get("success") else 1


def cmd_list(args: argparse.Namespace) -> int:
    announce_only = getattr(args, "announce_only", None)
    if announce_only == "yes":
        filter_value = True
    elif announce_only == "no":
        filter_value = False
    else:
        filter_value = None
    service = _service(args)
    channels = service.list_channels(
        limit=int(args.limit), offset=int(args.offset), announce_only=filter_value
    )
    _emit({
        "success": True,
        "channels": channels,
        "limit": int(args.limit),
        "offset": int(args.offset),
    })
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    service = _service(args)
    channel = service.get_channel(args.name)
    if not channel:
        _emit({
            "success": False,
            "message": f"Channel {args.name!r} not found",
            "code": "not_found",
        })
        return 1
    _emit({"success": True, "channel": channel})
    return 0


def cmd_set_announce_only(args: argparse.Namespace) -> int:
    actor = _resolve_moniker(args)
    service = _service(args)
    value = args.value.lower() in ("true", "1", "yes", "on")
    result = service.set_announce_only(
        name=args.name, announce_only=value, by_moniker=actor
    )
    _emit(result)
    return 0 if result.get("success") else 1


def cmd_add_announcer(args: argparse.Namespace) -> int:
    actor = _resolve_moniker(args)
    service = _service(args)
    result = service.add_announcer(
        channel_name=args.name, moniker=args.target_moniker, addedby=actor
    )
    _emit(result)
    return 0 if result.get("success") else 1


def cmd_remove_announcer(args: argparse.Namespace) -> int:
    actor = _resolve_moniker(args)
    service = _service(args)
    result = service.remove_announcer(
        channel_name=args.name,
        moniker=args.target_moniker,
        actor_moniker=actor,
    )
    _emit(result)
    return 0 if result.get("success") else 1


# ---------------------------------------------------------------------------
# Argparse wiring (subcommands are registered via build_subparser)
# ---------------------------------------------------------------------------


_VERBS = {
    "create": cmd_create,
    "list": cmd_list,
    "get": cmd_get,
    "set-announce-only": cmd_set_announce_only,
    "add-announcer": cmd_add_announcer,
    "remove-announcer": cmd_remove_announcer,
}


def buildargs(parser: Optional[argparse.ArgumentParser] = None, **kwargs):
    """Build (or extend) an argparse parser with the channel subcommand tree.

    Adds a top-level ``channel`` subcommand and the verb catalog above.
    Returns the (possibly new) parser.
    """
    if parser is None:
        parser = argparse.ArgumentParser(prog="con channel")
    parser.add_argument(
        "--moniker",
        required=True,
        help="Acting member moniker (must be sysop or channel creator for mutators)",
    )

    sub = parser.add_subparsers(dest="channel_verb", required=True)
    p_create = sub.add_parser("create", help="Create a new channel")
    p_create.add_argument("name", help="Channel name (e.g. casino:table:blackjack-1)")
    p_create.add_argument("--description", default=None)
    p_create.add_argument(
        "--announce-only", action="store_true", dest="announce_only"
    )
    p_create.add_argument(
        "--announcer", action="append", default=[], help="Repeatable"
    )
    p_create.set_defaults(func=cmd_create)

    p_list = sub.add_parser("list", help="List channels")
    p_list.add_argument("--limit", type=int, default=100)
    p_list.add_argument("--offset", type=int, default=0)
    p_list.add_argument(
        "--announce-only",
        choices=["yes", "no", "any"],
        default="any",
        help="Filter by announce_only flag (default: any)",
    )
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="Show one channel")
    p_get.add_argument("name")
    p_get.set_defaults(func=cmd_get)

    p_set = sub.add_parser(
        "set-announce-only", help="Toggle the announce_only flag"
    )
    p_set.add_argument("name")
    p_set.add_argument("value", help="true or false")
    p_set.set_defaults(func=cmd_set_announce_only)

    p_add = sub.add_parser("add-announcer", help="Add an announcer")
    p_add.add_argument("name")
    p_add.add_argument("target_moniker")
    p_add.set_defaults(func=cmd_add_announcer)

    p_rm = sub.add_parser("remove-announcer", help="Remove an announcer")
    p_rm.add_argument("name")
    p_rm.add_argument("target_moniker")
    p_rm.set_defaults(func=cmd_remove_announcer)

    return parser


def main(args: argparse.Namespace, **kwargs) -> bool:
    func = getattr(args, "func", None)
    if func is None:
        _emit({"success": False, "message": "No verb selected"})
        return False
    rc = func(args)
    return rc == 0
