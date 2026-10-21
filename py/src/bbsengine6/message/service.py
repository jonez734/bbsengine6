# bbsengine6/message/service.py
#
# Business orchestration for bbsengine6.message. Calls into the DAL
# (``bbsengine6.message.dal``) for Postgres I/O and into the cache
# (``bbsengine6.message.cache``) for in-process state. Owns the
# enable/disable gate, rate-limit gating, blocking filter, recipient
# expansion, and the legacy ``send()`` shim. Mirrors
# ``casino/src/casino/services/``.
# !42!
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from bbsengine6 import io
from bbsengine6.database import getpool

from bbsengine6.message import cache
from bbsengine6.message.dal import (
    blocking as dal_blocking,
    groups as dal_groups,
    messages as dal_messages,
    ratelimit as dal_ratelimit,
    recipients as dal_recipients,
    types as dal_types,
)
from bbsengine6.message.lib import (
    _db_from_args,
    _make_args,
    _resolve_db,
)
from bbsengine6.message import templates


from enum import Enum


class MessageUrgency(Enum):
    ROUTINE = "ROUTINE"
    IMPORTANT = "IMPORTANT"
    URGENT = "URGENT"
    CRITICAL = "CRITICAL"


_message_enabled: bool = True

# Roles allowed to address ``@everyone``. Set by the host application from its
# own config (bed reads ``message.everyone_allowed_roles`` from bed.json).
# Default: sysops only.
_everyone_allowed_roles: List[str] = ["sysop"]

# Pending-message age limit in days for list_pending. 0 = no limit.
_pending_max_age_days: int = 0
# Hard cap on one page of list_pending, regardless of what a caller asks for.
PENDING_PAGE_MAX: int = 100


def configure(
    *,
    everyone_allowed_roles: Optional[List[str]] = None,
    pending_max_age_days: Optional[int] = None,
) -> None:
    """Set message policy from the host application's config.

    ``everyone_allowed_roles`` lists the roles that may send to ``@everyone``.
    Supported roles: ``"sysop"``. ``pending_max_age_days`` drops pending
    messages older than that many days from list_pending (0 = keep all).
    ``None`` leaves the current value unchanged.
    """
    global _everyone_allowed_roles, _pending_max_age_days
    if everyone_allowed_roles is not None:
        _everyone_allowed_roles = [str(r).strip().lower() for r in everyone_allowed_roles if str(r).strip()]
    if pending_max_age_days is not None:
        if int(pending_max_age_days) < 0:
            raise ValueError("pending_max_age_days must be >= 0")
        _pending_max_age_days = int(pending_max_age_days)


_RESERVED_SOURCES = ("member", "operator")


def _source_may_address_group(
    source: str, group_name: str, database_name: str
) -> bool:
    """Named sources are limited to the group prefixes they are registered for.

    ``member`` and ``operator`` senders are governed by their own rules and
    are not checked here. Any other source must hold a registration in
    ``engine.__message_source`` that covers ``group_name``.
    """
    if source in _RESERVED_SOURCES:
        return True
    args = _make_args(database_name)
    return bool(
        dal_recipients.source_may_address_group(args, source, group_name)
    )


def _sender_may_address_group(
    sender_moniker: Optional[str],
    source: str,
    group_id: int,
    database_name: str,
) -> bool:
    """True if this sender may address the named group.

    - Named system sources are governed by the source registry, not here.
    - Operator/CLI calls (no sender) are unrestricted.
    - A member sender must belong to the group, or be a sysop.
    """
    if source not in ("member",) or sender_moniker is None:
        return True
    from bbsengine6.member import lib as member_lib

    args = _make_args(database_name)
    if member_lib.issysop(args, moniker=sender_moniker) is True:
        return True
    return bool(dal_groups.is_member(args, group_id, sender_moniker))


def _sender_may_broadcast(sender_moniker: Optional[str], database_name: str) -> bool:
    """True if the sender may address ``@everyone`` under the configured roles.

    ``sender_moniker=None`` means an operator/CLI call with no member identity,
    which is allowed. Otherwise the sender must hold one of the configured roles.
    """
    if sender_moniker is None:
        return True
    from bbsengine6.member import lib as member_lib

    args = _make_args(database_name)
    for role in _everyone_allowed_roles:
        if role == "sysop" and member_lib.issysop(args, moniker=sender_moniker) is True:
            return True
    return False


def is_enabled() -> bool:
    return _message_enabled


def enable() -> None:
    global _message_enabled
    _message_enabled = True


def disable() -> None:
    global _message_enabled
    _message_enabled = False


def _coerce_urgency(urgency: Any) -> str:
    """Coerce a ``MessageUrgency`` enum (or string) to the string form
    accepted by ``store_message``.
    """
    if urgency is None or urgency == "":
        return "ROUTINE"
    if isinstance(urgency, MessageUrgency):
        return urgency.value
    s = str(urgency)
    valid = {m.value for m in MessageUrgency}
    return s if s in valid else "ROUTINE"


def _check_blocking_and_ratelimit(
    sender_moniker: Optional[str],
    channel: str,
    recipient_monikers: Optional[List[str]],
    database: Optional[str],
) -> Tuple[Optional[List[str]], bool, Dict[str, Any]]:
    """Apply rate limiting and blocking checks before insertion."""
    diagnostics: Dict[str, Any] = {
        "rate_limit_ok": True,
        "recipients_blocked": [],
        "recipients_skipped": [],
    }

    allowed_recipients: Optional[List[str]] = None
    if recipient_monikers:
        allowed_recipients = []
        for recipient in recipient_monikers:
            if sender_moniker is not None and is_blocked(
                recipient, sender_moniker, database=database
            ):
                diagnostics["recipients_blocked"].append(recipient)
                continue
            allowed_recipients.append(recipient)
        diagnostics["recipients_skipped"] = [
            r for r in recipient_monikers if r not in allowed_recipients
        ]

    return allowed_recipients, True, diagnostics


def store_message(
    channel: str,
    sender_moniker: Optional[str],
    content: str,
    recipient_monikers: Optional[List[str]] = None,
    data: Optional[Dict[str, Any]] = None,
    urgency: str = "ROUTINE",
    template: Optional[str] = None,
    template_vars: Optional[Dict[str, Any]] = None,
    database: Optional[str] = None,
    source: str = "member",
) -> int:
    """Store a message in the database and create recipients.

    Thin wrapper over :func:`store_message_with_checks` returning
    only the message id.
    """
    result = store_message_with_checks(
        channel=channel,
        sender_moniker=sender_moniker,
        content=content,
        recipient_monikers=recipient_monikers,
        data=data,
        urgency=urgency,
        template=template,
        template_vars=template_vars,
        database=database,
        source=source,
    )
    return result.get("message_id", 0)


def store_message_with_checks(
    channel: str,
    sender_moniker: Optional[str],
    content: str,
    recipient_monikers: Optional[List[str]] = None,
    data: Optional[Dict[str, Any]] = None,
    urgency: str = "ROUTINE",
    template: Optional[str] = None,
    template_vars: Optional[Dict[str, Any]] = None,
    database: Optional[str] = None,
    source: str = "member",
) -> Dict[str, Any]:
    """Store a message and return full per-recipient diagnostics.

    Returns a dict with::

        {
            "message_id": int,           # 0 if denied or disabled
            "rate_limit_ok": bool,
            "recipients_stored": List[str],
            "recipients_blocked": List[str],
            "recipients_skipped": List[str],
        }
    """
    empty: Dict[str, Any] = {
        "message_id": 0,
        "rate_limit_ok": True,
        "recipients_stored": [],
        "recipients_blocked": [],
        "recipients_skipped": [],
    }

    if not _message_enabled:
        return empty

    database = _resolve_db(database)

    if recipient_monikers:
        try:
            expanded = resolve_recipients(
                recipient_monikers,
                database=database,
                sender_moniker=sender_moniker,
                source=source,
            )
        except PermissionError as e:
            # Denied broadcast: nothing is stored, and the reason is reported
            # rather than surfacing as a database error.
            return {
                **empty,
                "denied_reason": str(e),
            }
        recipient_monikers = expanded

    allowed_recipients, rate_limit_ok, diagnostics = _check_blocking_and_ratelimit(
        sender_moniker, channel, recipient_monikers, database
    )

    if not rate_limit_ok:
        return {
            "message_id": 0,
            "rate_limit_ok": False,
            "recipients_stored": [],
            "recipients_blocked": diagnostics.get("recipients_blocked", []),
            "recipients_skipped": diagnostics.get("recipients_skipped", []),
        }

    # Recipients were requested but every one was blocked or skipped. Storing
    # the row would leave an orphan message with no recipients and return a
    # live message_id to the caller. Report it as not stored instead.
    if recipient_monikers and not allowed_recipients:
        return {
            "message_id": 0,
            "rate_limit_ok": True,
            "recipients_stored": [],
            "recipients_blocked": diagnostics.get("recipients_blocked", []),
            "recipients_skipped": diagnostics.get("recipients_skipped", []),
        }

    args = _make_args(database)

    # Reserve a rate slot only for a message that will actually be stored.
    # Early returns above never consume one. If the insert fails, release.
    reserved = False
    if sender_moniker is not None:
        ok, _remaining = dal_ratelimit.try_reserve(args, sender_moniker, channel)
        if not ok:
            return {
                "message_id": 0,
                "rate_limit_ok": False,
                "recipients_stored": [],
                "recipients_blocked": diagnostics.get("recipients_blocked", []),
                "recipients_skipped": diagnostics.get("recipients_skipped", []),
            }
        reserved = True

    try:
        message_id = dal_messages.store_message_with_recipients(
            args,
            channel,
            sender_moniker,
            content,
            data,
            urgency,
            template,
            template_vars,
            allowed_recipients,
            source=source,
        )
    except Exception:
        if reserved:
            dal_ratelimit.release(args, sender_moniker, channel)
        raise

    stored: List[str] = list(allowed_recipients) if allowed_recipients else []

    # The rate slot was reserved atomically in _check_blocking_and_ratelimit,
    # so it is not recorded again here.

    return {
        "message_id": message_id,
        "rate_limit_ok": True,
        "recipients_stored": stored,
        "recipients_blocked": diagnostics.get("recipients_blocked", []),
        "recipients_skipped": diagnostics.get("recipients_skipped", []),
    }


def get_pending_page(
    moniker: str,
    limit: int = 50,
    before: Optional[tuple] = None,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """One page of pending messages for list_pending.

    ``limit`` is clamped to ``1..PENDING_PAGE_MAX``. ``before`` is the
    ``(datestamp, id)`` cursor from the last row of the previous page. Rows older
    than the configured pending age limit are excluded.
    """
    if not _message_enabled:
        return []
    limit = max(1, min(int(limit), PENDING_PAGE_MAX))
    database = _resolve_db(database)
    args = _make_args(database)
    return dal_messages.list_pending_page(
        args,
        moniker,
        limit,
        before=before,
        max_age_days=_pending_max_age_days,
    )


def get_pending_messages(
    moniker: str,
    limit: int = 50,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get pending messages for a user (delivered on connect)."""
    if not _message_enabled:
        return []

    database = _resolve_db(database)
    args = _make_args(database)
    return dal_messages.list_pending_for_recipient(args, moniker, limit, prioritized=False)


def get_pending_messages_prioritized(
    moniker: str,
    limit: int = 50,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get pending messages, ordered by urgency first."""
    if not _message_enabled:
        return []

    database = _resolve_db(database)
    args = _make_args(database)
    return dal_messages.list_pending_for_recipient(args, moniker, limit, prioritized=True)


def mark_delivered(
    message_id: int,
    moniker: str,
    database: Optional[str] = None,
) -> None:
    """Mark a message as delivered."""
    if not _message_enabled:
        return

    database = _resolve_db(database)
    args = _make_args(database)
    dal_messages.mark_delivered(args, message_id, moniker)


def mark_read(
    message_id: int,
    moniker: str,
    database: Optional[str] = None,
) -> None:
    """Mark a message as read."""
    if not _message_enabled:
        return

    database = _resolve_db(database)
    args = _make_args(database)
    dal_messages.mark_read(args, message_id, moniker)


def get_unread_count(
    moniker: str,
    database: Optional[str] = None,
    *,
    args: Any = None,
    pool: Any = None,
    conn: Any = None,
) -> int:
    """Get count of unread messages for a user.

    Returns 0 when the message system is disabled or the
    ``engine.__message_recipient`` table does not exist.
    """
    if not _message_enabled:
        return 0

    db_label = _resolve_db(database, args)

    def _missing_table_warning() -> int:
        io.echo(
            f"bbsengine6.message.get_unread_count.100: "
            f"engine.__message_recipient missing in {db_label or 'current db'}; "
            f"returning 0 (run checkmessage + migrate_notify_to_message.sql "
            f"to install the unified message schema)",
            level="warn",
        )
        return 0

    if conn is not None:
        try:
            result = dal_messages.count_unread_for_recipient(
                _make_args(db_label) if db_label else None,
                moniker,
                conn=conn,
            )
            if result == 0:
                # Could be a real zero or a missing table. Distinguish
                # via the probe to preserve the original warning path.
                from bbsengine6.message.dal._pool import table_exists

                with conn.cursor() as cur:
                    if not table_exists(cur, "engine", "__message_recipient"):
                        return _missing_table_warning()
            return result
        except Exception:
            return _missing_table_warning()

    if pool is None:
        if database is None and args is not None:
            database = _resolve_db(database, args)
        if database is None:
            database = _resolve_db(None)
        args_obj = _make_args(database)
    else:
        args_obj = args if args is not None else _make_args(_resolve_db(database))

    try:
        result = dal_messages.count_unread_for_recipient(args_obj, moniker)
        if result == 0:
            from bbsengine6.message.dal._pool import table_exists

            with getpool(args_obj).connection() as c, c.cursor() as cur:
                if not table_exists(cur, "engine", "__message_recipient"):
                    return _missing_table_warning()
        return result
    except Exception:
        return _missing_table_warning()


def get_local_unread_count(moniker: str) -> int:
    return cache.get_local_unread_count(moniker)


def set_local_unread_count(moniker: str, count: int) -> None:
    cache.set_local_unread_count(moniker, count)


def bump_local_unread_count(moniker: str, delta: int = 1) -> None:
    cache.bump_local_unread_count(moniker, delta)


def clear_local_unread_cache() -> None:
    cache.clear_local_unread_cache()


def deliver_pending_on_connect(
    moniker: str,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Deliver all pending messages to user on connect."""
    if not _message_enabled:
        return []

    database = _resolve_db(database)
    args = _make_args(database)
    # Only never-delivered rows. A row already marked delivered is not
    # pushed again, so unread-but-delivered messages do not crowd out
    # ROUTINE traffic on every login.
    messages = dal_messages.list_undelivered_for_recipient(
        args, moniker, 50, prioritized=True
    )

    if messages:
        dal_messages.mark_delivered_batch(
            args, [msg["id"] for msg in messages], moniker
        )

    return messages


def create_message_group(
    name: str,
    createdby: Optional[str] = None,
    description: Optional[str] = None,
    database: Optional[str] = None,
) -> int:
    if not _message_enabled:
        return 0
    database = _resolve_db(database)
    args = _make_args(database)
    return dal_groups.create(args, name, createdby, description)


def add_to_message_group(
    group_id: int,
    member_moniker: str,
    addedby: Optional[str] = None,
    database: Optional[str] = None,
) -> bool:
    if not _message_enabled:
        return False
    database = _resolve_db(database)
    args = _make_args(database)
    dal_groups.add_member(args, group_id, member_moniker, addedby)
    return True


def ensure_message_group(
    name: str,
    createdby: Optional[str] = None,
    description: Optional[str] = None,
    database: Optional[str] = None,
) -> int:
    """Return the id of group ``name``, creating it if it does not exist."""
    if not _message_enabled:
        return 0
    database_name = _resolve_db(database)
    args = _make_args(database_name)
    existing = dal_recipients.get_group_id_by_name(args, name)
    if existing >= 0:
        return existing
    return dal_groups.create(args, name, createdby, description)


def group_member_add(
    name: str,
    member_moniker: str,
    addedby: Optional[str] = None,
    database: Optional[str] = None,
) -> bool:
    """Add ``member_moniker`` to group ``name`` (created if missing). Idempotent."""
    if not _message_enabled:
        return False
    gid = ensure_message_group(name, createdby=addedby, database=database)
    if not gid:
        return False
    return add_to_message_group(gid, member_moniker, addedby=addedby, database=database)


def group_member_remove(
    name: str,
    member_moniker: str,
    database: Optional[str] = None,
) -> bool:
    """Remove ``member_moniker`` from group ``name``. True if a row was removed."""
    if not _message_enabled:
        return False
    database_name = _resolve_db(database)
    args = _make_args(database_name)
    gid = dal_recipients.get_group_id_by_name(args, name)
    if gid < 0:
        return False
    removed = remove_from_group(gid, member_moniker, database=database_name)
    if removed and not dal_groups.list_members(args, gid):
        dal_groups.delete_group(args, gid)
    return removed


def group_delete(name: str, database: Optional[str] = None) -> bool:
    """Delete group ``name`` and its members. True if the group existed."""
    if not _message_enabled:
        return False
    database_name = _resolve_db(database)
    args = _make_args(database_name)
    gid = dal_recipients.get_group_id_by_name(args, name)
    if gid < 0:
        return False
    return dal_groups.delete_group(args, gid)


def group_names_with_prefix(prefix: str, database: Optional[str] = None) -> List[str]:
    """Names of every group under ``prefix:``, for reconciliation."""
    if not _message_enabled:
        return []
    args = _make_args(_resolve_db(database))
    return dal_groups.list_group_names_with_prefix(args, prefix)


def group_member_monikers(name: str, database: Optional[str] = None) -> List[str]:
    """Members of group ``name``, or [] if it does not exist."""
    if not _message_enabled:
        return []
    database_name = _resolve_db(database)
    args = _make_args(database_name)
    gid = dal_recipients.get_group_id_by_name(args, name)
    if gid < 0:
        return []
    return dal_groups.list_members(args, gid)


def register_named_source(
    source: str,
    group_prefix: str,
    description: Optional[str] = None,
    database: Optional[str] = None,
) -> bool:
    """Let named ``source`` address groups under ``group_prefix``. Idempotent."""
    if not _message_enabled:
        return False
    args = _make_args(_resolve_db(database))
    dal_recipients.register_source(args, source, group_prefix, description)
    return True


def unregister_named_source(
    source: str,
    group_prefix: Optional[str] = None,
    database: Optional[str] = None,
) -> bool:
    """Remove a named source's registration (one prefix, or all if None)."""
    if not _message_enabled:
        return False
    args = _make_args(_resolve_db(database))
    dal_recipients.unregister_source(args, source, group_prefix)
    return True


def get_message_group_members(
    group_id: int,
    database: Optional[str] = None,
) -> List[str]:
    if not _message_enabled:
        return []
    database = _resolve_db(database)
    args = _make_args(database)
    return dal_groups.list_members(args, group_id)


def get_user_groups(
    moniker: str,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not _message_enabled:
        return []
    database = _resolve_db(database)
    args = _make_args(database)
    return dal_groups.list_user_groups(args, moniker)


def block_sender(
    blocker_moniker: str,
    blocked_moniker: str,
    database: Optional[str] = None,
) -> bool:
    if not _message_enabled:
        return False
    database = _resolve_db(database)
    args = _make_args(database)
    dal_blocking.block(args, blocker_moniker, blocked_moniker)
    return True


def unblock_sender(
    blocker_moniker: str,
    blocked_moniker: str,
    database: Optional[str] = None,
) -> bool:
    if not _message_enabled:
        return False
    database = _resolve_db(database)
    args = _make_args(database)
    dal_blocking.unblock(args, blocker_moniker, blocked_moniker)
    return True


def is_blocked(
    blocker_moniker: str,
    blocked_moniker: str,
    database: Optional[str] = None,
) -> bool:
    if not _message_enabled:
        return False
    database = _resolve_db(database)
    args = _make_args(database)
    return dal_blocking.is_blocked(args, blocker_moniker, blocked_moniker)


def check_rate_limit(
    sender_moniker: str,
    message_type: str,
    database: Optional[str] = None,
) -> Tuple[bool, int]:
    if not _message_enabled:
        return True, 999
    database = _resolve_db(database)
    args = _make_args(database)
    return dal_ratelimit.check(args, sender_moniker, message_type)


def record_message_sent(
    sender_moniker: str,
    message_type: str,
    database: Optional[str] = None,
) -> bool:
    if not _message_enabled:
        return True
    database = _resolve_db(database)
    args = _make_args(database)
    dal_ratelimit.record(args, sender_moniker, message_type)
    return True


def get_message_type_rate_limit(
    message_type: str,
    database: Optional[str] = None,
) -> int:
    if not _message_enabled:
        return 0
    database = _resolve_db(database)
    args = _make_args(database)
    return dal_ratelimit.get_type_limit(args, message_type)


def remove_from_group(
    group_id: int,
    member_moniker: str,
    database: Optional[str] = None,
) -> bool:
    if not _message_enabled:
        return False
    database = _resolve_db(database)
    args = _make_args(database)
    return dal_groups.remove_member(args, group_id, member_moniker)


def get_blocked(
    moniker: str,
    database: Optional[str] = None,
) -> List[str]:
    if not _message_enabled:
        return []
    database = _resolve_db(database)
    args = _make_args(database)
    return dal_blocking.list_blocked_by(args, moniker)


def get_urgent(
    moniker: str,
    limit: int = 50,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not _message_enabled:
        return []
    database = _resolve_db(database)
    args = _make_args(database)
    return dal_messages.list_urgent_for_recipient(args, moniker, limit)


def expunge(
    message_id: int,
    sender_moniker: str,
    database: Optional[str] = None,
) -> bool:
    if not _message_enabled:
        return False
    database = _resolve_db(database)
    args = _make_args(database)
    return dal_messages.expunge_sender_message(args, message_id, sender_moniker)


def get_queue(
    moniker: str,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Pending messages for a user (legacy notify-era API)."""
    return get_pending_messages(moniker, limit=1000, database=database)


def resolve_recipients(
    recipients: List[str],
    database: Optional[str] = None,
    sender_moniker: Optional[str] = None,
    source: str = "member",
) -> List[str]:
    """Expand ``@group_name`` and ``@everyone`` references.

    Returns a flat list of monikers with duplicates removed (order
    preserved by first occurrence). Expansion is recursive for
    nested groups with a depth cap to prevent infinite loops.
    """
    if not _message_enabled:
        return []

    seen: Set[str] = set()
    expanded: List[str] = []

    def _add(moniker: str) -> None:
        if moniker and moniker not in seen:
            seen.add(moniker)
            expanded.append(moniker)

    pending = list(recipients)
    depth = 0
    MAX_DEPTH = 10
    # Group names already expanded. A group that (directly or through other
    # groups) contains itself is expanded once, so a cycle terminates.
    expanded_groups: Set[str] = set()

    while pending and depth < MAX_DEPTH:
        depth += 1
        next_pending: List[str] = []
        for r in pending:
            if not r:
                continue
            if r.startswith("@"):
                token = r[1:].strip()
                if not token:
                    continue
                database_name = _resolve_db(database)
                args = _make_args(database_name)
                if token.lower() == "everyone":
                    if source not in _RESERVED_SOURCES:
                        raise PermissionError(
                            f"source {source!r} may not address @everyone"
                        )
                    if not _sender_may_broadcast(sender_moniker, database_name):
                        raise PermissionError(
                            "only sysops may address @everyone"
                        )
                    for m in dal_recipients.list_all_approved_member_monikers(args):
                        _add(m)
                    continue
                key = token.lower()
                if key in expanded_groups:
                    continue
                if not _source_may_address_group(source, token, database_name):
                    raise PermissionError(
                        f"source {source!r} is not registered for group {token!r}"
                    )
                expanded_groups.add(key)
                group_id = dal_recipients.get_group_id_by_name(args, token)
                if group_id >= 0 and not _sender_may_address_group(
                    sender_moniker, source, group_id, database_name
                ):
                    raise PermissionError(
                        f"only members of {token!r} (or sysops) may address it"
                    )
                if group_id >= 0:
                    for m in get_message_group_members(
                        group_id, database=database_name
                    ):
                        # A member written as "@group" is a nested reference
                        # and is expanded on the next pass; a plain moniker is
                        # added directly.
                        if m and m.startswith("@"):
                            next_pending.append(m)
                        else:
                            _add(m)
            else:
                _add(r)
        pending = next_pending

    return expanded


def set_rate_limit(
    type_name: str,
    limit: int,
    database: Optional[str] = None,
) -> bool:
    if not _message_enabled:
        return False
    database = _resolve_db(database)
    args = _make_args(database)
    dal_types.set_rate_limit(args, type_name, limit)
    return True


def register_type(
    type_name: str,
    description: str = "",
    rate_limit_per_hour: int = 0,
    requires_approval: bool = False,
    database: Optional[str] = None,
) -> bool:
    if not _message_enabled:
        return False
    database = _resolve_db(database)
    args = _make_args(database)
    dal_types.upsert(
        args, type_name, description, rate_limit_per_hour, requires_approval
    )
    return True


def get_types(
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not _message_enabled:
        return []
    database = _resolve_db(database)
    args = _make_args(database)
    return dal_types.list_all(args)


def send(
    notification_type: str,
    recipients: List[str],
    template: str,
    template_vars: Optional[Dict[str, Any]] = None,
    sender_moniker: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    urgency: Any = None,
    should_persist: bool = True,
    args: Optional[Any] = None,
    source: str = "member",
    **kwargs: Any,
) -> int:
    """Send a notification through the unified message system.

    ``source`` tags where the message came from (``member``, ``operator``,
    or a registered named source). A named source may address only the
    groups it is registered for in ``engine.__message_source``.

    Thin shim over :func:`store_message` that accepts the legacy
    ``message_delivery.send`` kwarg names.

    ``should_persist=False`` means "do not store": the call returns 0 and
    nothing is written. Previously the flag was accepted and ignored, so a
    caller expecting a transient notification would silently create a row.

    Unknown keyword arguments raise TypeError. Previously they were swallowed,
    so a misspelled option (``recipent=``) did nothing and gave no error.
    """
    if kwargs:
        raise TypeError(
            f"send() got unexpected keyword argument(s): {sorted(kwargs)}"
        )

    if not _message_enabled:
        return 0

    if not notification_type:
        raise ValueError("notification_type is required")
    if not recipients or not isinstance(recipients, list):
        raise ValueError("recipients must be a non-empty list")
    if not isinstance(template, str):
        raise ValueError("template must be a string")

    if not should_persist:
        return 0

    rendered = templates.render_template(template, template_vars or {})
    db = _db_from_args(args)

    return store_message(
        channel=notification_type,
        sender_moniker=sender_moniker,
        content=rendered,
        recipient_monikers=list(recipients),
        data=data,
        urgency=_coerce_urgency(urgency),
        template=template,
        template_vars=template_vars,
        database=db,
        source=source,
    )


def register_type_compat(
    type_name: str,
    urgency: Any = None,
    max_per_user_per_hour: int = 0,
    persist_by_default: bool = True,
    args: Optional[Any] = None,
    **kwargs: Any,
) -> bool:
    """Adapter that accepts the legacy ``message_delivery.register_type``
    positional signature and forwards to :func:`register_type`.
    """
    if not _message_enabled:
        return False

    if "description" in kwargs:
        description = kwargs["description"]
    elif urgency is not None:
        description = f"default_urgency={_coerce_urgency(urgency)}"
    else:
        description = ""

    rate_limit_per_hour = int(
        kwargs.get("rate_limit_per_hour", max_per_user_per_hour)
    )
    requires_approval = bool(kwargs.get("requires_approval", False))
    database = kwargs.get("database", _db_from_args(args))

    return register_type(
        type_name=type_name,
        description=description,
        rate_limit_per_hour=rate_limit_per_hour,
        requires_approval=requires_approval,
        database=database,
    )


def render_template(template: str, variables: Dict[str, Any]) -> str:
    return templates.render_template(template, variables)


def render_message_content(
    content: str,
    template: Optional[str],
    template_vars: Optional[Dict[str, Any]],
) -> str:
    return templates.render_message_content(content, template, template_vars)


def parse_variables_from_content(content: str) -> List[str]:
    return templates.parse_variables_from_content(content)


def get_builtin_variables() -> Dict[str, Any]:
    return templates.get_builtin_variables()


def validate_template(template: str) -> Tuple[bool, List[str]]:
    return templates.validate_template(template)
