# bbsengine6/startup/message_subscription.py
# Hook the bbsengine6 TUI into bed's server-push notifications.
#
# Entry point: subscribe_to_bed(args, moniker, **kwargs). Follows
# CONN_POOL_PATTERN: the optional bed handle arrives in kwargs as "bed".
#
# Order of checks (each failure returns False and the caller falls back
# to DB polling):
#   1. bed instance reachable (bed.client.probe.probe_bed, 0.25s TCP probe)
#   2. a BedConnection: kwargs["bed"] if supplied, else the process
#      singleton from bed.client.get_bed_connection(args)
#   3. a token: resolve_token(args) (--token, else the token file)
#   4. authenticate with auth reconnect, then verify the moniker the
#      SERVER bound to the token matches ``moniker``. The local file is
#      never trusted for identity.
#
# A missing bed or token is logged once per process, at debug level,
# and only when args.debug is True.

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Optional

from bbsengine6 import io

logger = logging.getLogger(__name__)

_debug_notice_lock = threading.Lock()
_debug_notice_emitted = False


def _debug_notice_once(args: Any, text: str) -> None:
    """Emit ``text`` at debug level, at most once per process, if args.debug."""
    global _debug_notice_emitted
    if getattr(args, "debug", False) is not True:
        return
    with _debug_notice_lock:
        if _debug_notice_emitted:
            return
        _debug_notice_emitted = True
    io.echo(f"bbsengine6 messages: {text}; using DB polling", level="debug")


def _probe(args: Any) -> bool:
    try:
        from bed.client.probe import probe_bed
    except ImportError:
        return False
    return bool(probe_bed(args))


def _get_connection(args: Any, **kwargs: Any) -> Optional[Any]:
    supplied = kwargs.get("bed")
    if supplied is not None:
        return supplied
    try:
        from bed.client import get_bed_connection
    except ImportError:
        return None
    return get_bed_connection(args)


def _resolve_token(args: Any) -> str:
    try:
        from bed.tools._token import resolve_token
    except ImportError:
        return ""
    return resolve_token(args) or ""


async def subscribe_to_bed(args: Any, moniker: str, **kwargs: Any) -> bool:
    """Subscribe to bed pushes for ``moniker``. True on success.

    Returns False (caller polls the DB) when bed is absent, no token is
    available, authentication fails, or the server-bound moniker does
    not match ``moniker``.
    """
    moniker = (moniker or "").strip()
    if not moniker:
        return False

    if not _probe(args):
        _debug_notice_once(args, "bed not reachable")
        return False

    token = _resolve_token(args)
    if not token:
        _debug_notice_once(args, "no bed token")
        return False

    conn = _get_connection(args, **kwargs)
    if conn is None:
        _debug_notice_once(args, "no bed connection")
        return False

    try:
        from bed.client.authservice import BedAuthServiceClient
        from bed.client.messageservice import get_message_client

        auth = BedAuthServiceClient(conn)
        reply = await auth.reconnect(token)
        if not reply.get("ok"):
            logger.info("bed reconnect refused: %s", reply.get("code"))
            return False
        bound = (reply.get("moniker") or "").strip()
        if bound != moniker:
            logger.warning(
                "bed bound moniker %r does not match %r; not subscribing",
                bound,
                moniker,
            )
            return False

        # Ownership: the process that created the connection (the singleton
        # path) owns it and may write rotated tokens. A handle supplied by
        # a caller is owned by that caller, so this process does not write.
        owner = kwargs.get("bed") is None
        client = get_message_client(
            conn,
            token=token,
            token_file=getattr(args, "token_file", None),
            owner=owner,
        )
        result = await client.subscribe(moniker)
        return bool(result.get("ok"))
    except Exception:
        io.echo_traceback("bbsengine6.startup.message_subscription.subscribe_to_bed:")
        return False


def subscribe_to_bed_sync(args: Any, moniker: str, **kwargs: Any) -> bool:
    """Synchronous wrapper. Runs subscribe_to_bed on a fresh event loop.

    The asyncio.run() wrapper this replaces closed the loop on return,
    which stopped the connection's receive task and dropped pushes. The
    connection owner keeps its own loop; this wrapper only performs the
    initial handshake.
    """
    if not moniker:
        return False
    try:
        return asyncio.run(subscribe_to_bed(args, moniker, **kwargs))
    except Exception:
        io.echo_traceback(
            "bbsengine6.startup.message_subscription.subscribe_to_bed_sync:"
        )
        return False
