# tui.py
# Functional Text User Interface for notifications via bbsengine6.notify

from typing import Any, List, Dict, Optional

from .. import database
from ..io.echo import echo
from ..io.inputchoice import inputchoice
from ..listbox import Listbox, ListboxItem


def _fetch_notifications(args: Any, pool: Any, moniker: str) -> List[Dict[str, Any]]:
    """Fetch notifications for a user from the database."""
    try:
        from .lib import get_notifications

        notifications = get_notifications(moniker, limit=50, args=args, pool=pool)
        return [
            {
                "id": n.id,
                "type": n.notification_type,
                "message": n.message,
                "sender": n.sender_moniker or "(system)",
                "urgency": n.urgency.value,
                "data": n.data,
                "timestamp": n.datecreated,
            }
            for n in notifications
        ]
    except Exception as e:
        echo(f"Error fetching notifications: {e}", level="error")
        return []


def _mark_notification_read(
    args: Any, pool: Any, notification_id: int, moniker: str
) -> None:
    """Mark a single notification as read."""
    try:
        from .lib import mark_read

        mark_read(notification_id, moniker, args=args, pool=pool)
    except Exception as e:
        echo(f"Could not mark as read: {e}", level="warn")


def _delete_notification(args: Any, pool: Any, notification_id: int, moniker: str) -> bool:
    """Delete a notification by ID."""
    try:
        from .lib import expunge

        return expunge(notification_id, moniker, args=args, pool=pool)
    except Exception as e:
        echo(f"Error deleting notification: {e}", level="error")
        return False


def _mark_all_read(args: Any, pool: Any, moniker: str) -> None:
    """Mark all notifications as read for a user."""
    try:
        from .lib import get_notifications, mark_read

        notifications = get_notifications(moniker, limit=100, args=args, pool=pool)
        marked = 0
        for n in notifications:
            try:
                mark_read(n.id, moniker, args=args, pool=pool)
                marked += 1
            except Exception:
                pass
        echo(f"Marked {marked} notifications as read", level="info")
    except Exception as e:
        echo(f"Error marking notifications as read: {e}", level="error")


def _show_notification_detail(
    notif: Dict[str, Any], args: Any, pool: Any, moniker: str
) -> None:
    """Display a single notification in detail and mark it read."""
    echo("")
    echo("=== Notification ===", level="info")
    echo(f"Type: {notif['type']}")
    echo(f"From: {notif['sender']}")
    echo(f"Urgency: {notif['urgency']}")
    echo("")
    echo(notif["message"])
    echo("")

    if notif["data"]:
        echo("Data:", level="debug")
        for key, value in notif["data"].items():
            echo(f"  {key}: {value}", level="debug")
        echo("")

    _mark_notification_read(args, pool, notif["id"], moniker)


def run(args: Any, moniker: str, pool: Optional[Any] = None, **kwargs) -> int:
    """
    Main notification TUI loop.

    Args:
        args: bbsengine6 args object
        moniker: Current user moniker
        pool: Database connection pool (optional, will get one if None)
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        Exit code (0 on success, 1 on error)
    """
    return run_until_quit(args, moniker, pool=pool, **kwargs)


def run_until_quit(args: Any, moniker: str, pool: Optional[Any] = None, **kwargs) -> int:
    """
    Main notification TUI loop.

    Args:
        args: bbsengine6 args object
        moniker: Current user moniker
        pool: Database connection pool (optional, will get one if None)
        **kwargs: Additional keyword arguments (ignored, for flexibility)

    Returns:
        Exit code (0 on success, 1 on error)
    """
    _pool = pool
    should_close_pool = False

    if _pool is None:
        try:
            _pool = database.getpool(args)
            should_close_pool = True
        except Exception as e:
            echo(f"Error: Could not connect to database: {e}", level="error")
            return 1

    while True:
        echo("")
        echo("=== Notifications ===", level="info")
        echo(f"User: {moniker}")
        echo("")

        choice = inputchoice(
            "Choose action: ",
            "lrx",
            default="l",
            help="(l)ist messages, (r)ead all unread, e(x)it",
        )

        if choice == "L":
            _run_list(args, _pool, moniker)
        elif choice == "R":
            _mark_all_read(args, _pool, moniker)
        elif choice == "X":
            echo("Goodbye!")
            if should_close_pool:
                _pool.close()
            return 0


def _run_list(args: Any, pool: Any, moniker: str) -> None:
    """List notifications and handle viewing/deletion."""
    notifications = _fetch_notifications(args, pool, moniker)
    if not notifications:
        echo("No notifications", level="info")
        return

    while True:
        items = []
        for n in notifications:
            urgency_marker = ""
            if n["urgency"] == "CRITICAL":
                urgency_marker = "!!! "
            elif n["urgency"] == "URGENT":
                urgency_marker = "!! "
            elif n["urgency"] == "IMPORTANT":
                urgency_marker = "! "

            sender = n["sender"][:20].ljust(20)
            msg = n["message"][:60]
            display = f"{urgency_marker}{sender} {msg}"
            items.append(ListboxItem(content=display, data=n))

        echo("")
        echo("Notifications:", level="info")
        echo("UP/DOWN=navigate, ENTER=view, DEL=delete, ESC=exit")
        echo("")

        try:
            lb = Listbox(
                args,
                title="Notifications",
                items=items,
                itemheight=1,
                itemsperpage=20,
            )
            result = lb.run("Notifications: ")

            if result is None or result.status == "cancelled":
                return

            if result.status == "selected" and result.item and result.item.data:
                _show_notification_detail(result.item.data, args, pool, moniker)

        except Exception as e:
            echo(f"Error in notification list: {e}", level="error")
            return
