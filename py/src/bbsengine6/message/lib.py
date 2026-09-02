# bbsengine6/message/lib.py
#
# Public re-export facade for the ``bbsengine6.message`` package.
#
# The implementation lives in three layers (mirrors casino's
# ``dal/`` + ``services/`` + ``domain/`` layout):
#
#   - ``bbsengine6.message.dal``     -- pure Postgres I/O. No policy.
#   - ``bbsengine6.message.service`` -- business orchestration.
#   - ``bbsengine6.message.templates`` -- pure rendering helpers.
#   - ``bbsengine6.message.cache``   -- in-memory local unread counter.
#
# This file keeps the ``Message`` dataclass plus the DB helpers
# (``_default_db``, ``_resolve_db``, ``_make_args``, ``_db_from_args``,
# ``_coerce_urgency``) and re-exports every public name from
# ``service`` and ``templates`` via ``__getattr__`` so the package
# surface (``from bbsengine6.message import *``) continues to work
# unchanged for all external callers (bed.api.message,
# bed.tools.message, bed.client.messageservice,
# bbsengine6.net.integration, bbsengine6.member.lib,
# bbsengine6.bottombar, bbsengine6.startup.message_subscription,
# the CLI, and every test).
#
# The ``access()`` authorization policy lives in ``__init__.py``.

from __future__ import annotations

import os
from dataclasses import dataclass
from bbsengine6.database import getpool  # re-exported for @patch() in tests
from datetime import datetime
from typing import Any, Dict, List, Optional


def _default_db() -> str:
    return os.environ.get("BBSENGINE6_DBNAME", "zoid6")


def _resolve_db(database: Optional[str] = None, args: Any = None) -> str:
    if database is not None:
        return database
    if args is not None:
        arg_db = getattr(args, "databasename", None) or getattr(args, "database", None)
        if arg_db:
            return arg_db
    return _default_db()


def _make_args(database: str) -> Any:
    """Create args object for database functions.

    Populates the standard connection fields (host/port/user/password/
    schema) with the same env-var fallbacks used by
    ``bbsengine6.database.buildargs`` so that a downstream ``getpool``
    call sees a complete namespace instead of bare ``database``/
    ``databasename`` attrs.
    """

    class _Args:
        pass

    args = _Args()
    args.database = database
    args.databasename = database
    args.databasehost = os.environ.get("BBSENGINE6_DBHOST", "localhost")
    args.databaseport = int(os.environ.get("BBSENGINE6_DBPORT", "5432"))
    args.databaseuser = os.environ.get("BBSENGINE6_DBUSER")
    args.databasepassword = os.environ.get("BBSENGINE6_DBPASSWORD")
    args.databaseschema = os.environ.get("BBSENGINE6_DBSCHEMA", "engine")
    return args


def _db_from_args(args: Any) -> Optional[str]:
    """Extract the database name from a bed-style ``args`` namespace."""
    if args is None:
        return None
    db = getattr(args, "database", None)
    if db:
        return db
    return getattr(args, "databasename", None)


def _coerce_urgency(urgency: Any) -> str:
    """Coerce a ``MessageUrgency`` enum (or string) to the string form
    accepted by ``store_message``. Delegates to the canonical
    implementation in ``bbsengine6.message.service``.
    """
    from bbsengine6.message.service import _coerce_urgency as _impl

    return _impl(urgency)


@dataclass
class Message:
    id: int
    channel: str
    sender_moniker: Optional[str]
    content: str
    data: Optional[Dict[str, Any]] = None
    urgency: str = "ROUTINE"
    template: Optional[str] = None
    template_vars: Optional[Dict[str, Any]] = None
    datestamp: Optional[datetime] = None

    @property
    def timestamp(self) -> float:
        return self.datestamp.timestamp() if self.datestamp else 0.0

    @property
    def recipients(self) -> List[str]:
        """Return the list of recipient monikers for a stored message.

        Falls back to [] when the message has no recipient rows or no DB
        pool is available. Never raises.
        """
        from bbsengine6.message.dal import messages as dal_messages

        try:
            args = _make_args(_default_db())
            return dal_messages.list_recipients(args, self.id)
        except Exception:
            return []


# Re-export the public service-layer API. ``bbsengine6.message.__init__``
# wildcard-imports from here, so every name below resolves at the
# package surface for external callers.
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
]


def __getattr__(name: str) -> Any:
    """Module-level __getattr__ for re-exports.

    Keeps the public surface reachable via attribute access on
    ``bbsengine6.message.lib`` so existing patches like
    ``@patch("bbsengine6.message.lib.getpool")`` and
    ``@patch("bbsengine6.message.lib.record_message_sent")`` keep
    resolving without re-binding each name eagerly.
    """
    if name in __all__:
        from bbsengine6.message import service

        return getattr(service, name)
    raise AttributeError(f"module 'bbsengine6.message.lib' has no attribute {name!r}")
