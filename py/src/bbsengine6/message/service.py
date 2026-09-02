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

    if sender_moniker is not None:
        allowed, _remaining = check_rate_limit(
            sender_moniker, channel, database=database
        )
        if not allowed:
            diagnostics["rate_limit_ok"] = False
            return None, False, diagnostics

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
        expanded = resolve_recipients(recipient_monikers, database=database)
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

    args = _make_args(database)

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
    )

    stored: List[str] = list(allowed_recipients) if allowed_recipients else []

    if sender_moniker is not None:
        record_message_sent(sender_moniker, channel, database=database)

    return {
        "message_id": message_id,
        "rate_limit_ok": True,
        "recipients_stored": stored,
        "recipients_blocked": diagnostics.get("recipients_blocked", []),
        "recipients_skipped": diagnostics.get("recipients_skipped", []),
    }


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

    messages = get_pending_messages_prioritized(moniker, database=database)

    for msg in messages:
        mark_delivered(msg["id"], moniker, database=database)

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
                    for m in dal_recipients.list_all_approved_member_monikers(args):
                        _add(m)
                else:
                    group_id = dal_recipients.get_group_id_by_name(args, token)
                    if group_id >= 0:
                        members = get_message_group_members(
                            group_id, database=database_name
                        )
                        for m in members:
                            _add(m)
            else:
                _add(r)
        if not next_pending:
            break
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
    **kwargs: Any,
) -> int:
    """Send a notification through the unified message system.

    Thin shim over :func:`store_message` that accepts the legacy
    ``message_delivery.send`` kwarg names.
    """
    if not _message_enabled:
        return 0

    if not notification_type:
        raise ValueError("notification_type is required")
    if not recipients or not isinstance(recipients, list):
        raise ValueError("recipients must be a non-empty list")
    if not isinstance(template, str):
        raise ValueError("template must be a string")

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
