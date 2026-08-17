# bbsengine6/message/__init__.py
#
# Unified message system: package facade.
#
# Layout:
#   - ``lib``     -- implementation (DB schema, send / get / mark /
#                    rate-limit / group / template). All public names
#                    below come from there via wildcard re-export.
#   - ``access``  -- per-op authorization policy. Bed's message service
#                    (``bed.api.message``) calls this for every
#                    ``message_subscribe`` / ``message_unsubscribe`` /
#                    ``message_list_pending`` request, mirroring the
#                    bank/auth pattern at ``bbsengine6.bank.access`` /
#                    ``bbsengine6.auth.access``.
#
# No ``psycopg`` imports anywhere in this package. All DB plumbing is
# reached through ``bbsengine6.database``.

from __future__ import annotations

from bbsengine6.message.lib import *  # noqa: F401,F403

import argparse
from typing import Any, Dict, Optional


__version__ = "202608130000"


# Public surface of the package. ``lib`` defines the canonical names;
# ``access`` lives here because it is part of the module API contract.
__all__ = [
    "Message",
    "MessageUrgency",
    "send",
    "store_message",
    "store_message_with_checks",
    "register_type",
    "register_type_compat",
    "get_types",
    "get_pending_messages",
    "get_pending_messages_prioritized",
    "deliver_pending_on_connect",
    "get_unread_count",
    "mark_delivered",
    "mark_read",
    "expunge",
    "get_queue",
    "resolve_recipients",
    "is_enabled",
    "enable",
    "disable",
    "get_local_unread_count",
    "set_local_unread_count",
    "bump_local_unread_count",
    "clear_local_unread_cache",
    "create_message_group",
    "add_to_message_group",
    "remove_from_group",
    "get_message_group_members",
    "get_user_groups",
    "block_sender",
    "unblock_sender",
    "is_blocked",
    "get_blocked",
    "check_rate_limit",
    "record_message_sent",
    "set_rate_limit",
    "get_message_type_rate_limit",
    "render_template",
    "render_message_content",
    "parse_variables_from_content",
    "get_builtin_variables",
    "validate_template",
    "get_urgent",
    "access",
]


def init(args, **kw) -> bool:
    """Register ``bbsengine6.message`` as a first-class module.

    Called by the bbsengine6 module loader at startup. Registers the
    module under the canonical name and exposes ``access`` so callers
    can resolve it via ``bbsengine6.get_module_api``.
    """
    from bbsengine6 import register_module

    register_module(
        name="bbsengine6.message",
        module_path="bbsengine6.message",
        version=__version__,
        apis={"access": access},
    )
    return True


def buildargs(args, **kw):
    """No message-specific CLI flags."""
    return None


def main(args, **kw) -> bool:
    """No-op entry point; ``bed.api.message`` is the runtime consumer."""
    return True


def _moniker_eq(a: Optional[str], b: Optional[str]) -> bool:
    """Case-insensitive moniker comparison after strip."""
    if not a or not b:
        return False
    return a.strip().lower() == b.strip().lower()


def _get_session(kwargs: Dict[str, Any]) -> Optional[Any]:
    return kwargs.get("session")


def _get_message(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    msg = kwargs.get("message")
    return msg if isinstance(msg, dict) else {}


def access(args: argparse.Namespace, op: str, /, **kwargs: Any) -> bool:
    """Authorize ``op`` for the given session/message pair.

    Returns True if the session is allowed to perform ``op`` on the
    target described by ``message``; False otherwise. The caller
    decides how to surface the denial (``forbidden`` envelope,
    ``not_authenticated`` envelope, etc.).

    Convention: ``op`` is a domain verb (the operation the caller
    wants to perform), not the wire-protocol message type. The bed
    WS handler maintains its own ``message_type -> op`` mapping and
    calls this function with the domain verb. See ``_TYPE_TO_OP`` in
    ``bed.api.message``.

    Recognized op values:
      "subscribe"    -- bind a websocket to a moniker for NOTIFY fanout
      "unsubscribe"  -- drop the websocket binding
      "list_pending" -- read the pending message queue for a moniker

    Required kwargs (both optional, both default to "deny"):
      session : bed.api.session.SessionState (or any object with
                ``.moniker: str`` and ``.is_sysop: bool`` attributes),
                or ``None`` for an unbound websocket.
      message : dict, the incoming wire-shaped payload.

    The function does NOT perform input validation (moniker present,
    non-empty). That is the caller's job and lives next to the
    wire-envelope shape checks. Mixing validation into access() would
    couple it to wire-protocol codes.

    At module-load time (``bbsengine6.module.check`` calls us with
    ``op="run"`` and no extra kwargs), there is no session yet. We
    allow the module to load for anyone; the per-op rules below only
    fire when the caller passes a ``session`` kwarg.
    """
    session = _get_session(kwargs)
    message = _get_message(kwargs)

    if "session" not in kwargs:
        return True

    # Runtime call: session kwarg was explicitly passed. ``None`` means
    # the websocket is unbound, which is always a denial.
    if session is None:
        return False

    if op in ("subscribe", "unsubscribe", "list_pending"):
        target = (message.get("moniker") or "").strip()
        if not target:
            return False
        if getattr(session, "is_sysop", False):
            return True
        return _moniker_eq(getattr(session, "moniker", None), target)

    return False
