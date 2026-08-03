# bbsengine6/startup/message_subscription.py
# Hook the bbsengine6 TUI into bed's server-push notifications.
#
# Called from bbsengine6.startup.main() at end of bootstrap. If bed
# is reachable, opens a BedConnection and registers a
# BedMessageServiceClient subscription for the current session's
# moniker. The push handler updates bbsengine6.message local cache
# so getch.py/bottombar.py can read counts without a DB hit.
#
# Bed is optional: if unreachable (no daemon running, network
# unavailable, etc.) the function logs a warning and returns False.
# Callers should treat False as "fall back to DB polling".

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from bbsengine6 import io

logger = logging.getLogger(__name__)


async def _connect_bed(args: Any) -> Optional[Any]:
    """Open a BedConnection if bed_host/bed_port are configured."""
    bed_host = getattr(args, "bed_host", None)
    bed_port = getattr(args, "bed_port", None)
    if not bed_host or not bed_port:
        return None
    try:
        from bed.client.connection import BedConnection
    except ImportError:
        io.echo_traceback("bbsengine6.startup.message_subscription._connect_bed:")
        return None
    return BedConnection(args)


async def subscribe_to_bed(
    args: Any, moniker: str
) -> bool:
    """Subscribe to bed's message pushes for the current user.

    Returns True if the subscription succeeded (or the user is not
    authenticated and no subscription is needed). Returns False if
    bed is unreachable — caller should fall back to DB polling.
    """
    if not moniker:
        return False

    conn = await _connect_bed(args)
    if conn is None:
        return False

    try:
        from bed.client.messageservice import get_message_client
        client = get_message_client(conn)
        result = await client.subscribe(moniker)
        return bool(result.get("ok"))
    except Exception:
        io.echo_traceback("bbsengine6.startup.message_subscription.subscribe_to_bed:")
        return False


def subscribe_to_bed_sync(
    args: Any, moniker: str
) -> bool:
    """Synchronous wrapper for subscribe_to_bed.

    Suitable for calling from non-async code paths (e.g. the
    bbsengine6 startup main()). Runs the coroutine to completion
    using asyncio.run. Safe to call multiple times; the underlying
    client is process-wide.
    """
    if not moniker:
        return False
    try:
        return asyncio.run(subscribe_to_bed(args, moniker))
    except Exception:
        io.echo_traceback(
            "bbsengine6.startup.message_subscription.subscribe_to_bed_sync:"
        )
        return False
