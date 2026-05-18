# notifyd/storage.py
# PostgreSQL storage for IMAP state and notification history

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised when storage operation fails"""

    pass


def ensure_schema(pool: Any) -> None:
    """
    Initialize database schema if not exists.
    
    Args:
        pool: PostgreSQL connection pool from bbsengine6.database.getpool()
    
    Raises:
        StorageError: If schema creation fails
    """
    # Placeholder - will read from SQL files
    pass


def get_last_uid(pool: Any, server: str, mailbox: str) -> int:
    """
    Get last processed email UID for a server/mailbox.
    
    Args:
        pool: PostgreSQL connection pool
        server: Server name ("Gmail", etc.)
        mailbox: Mailbox name ("INBOX", etc.)
    
    Returns:
        Last processed UID (0 if none)
    
    Raises:
        StorageError: If query fails
    """
    # Placeholder
    return 0


def set_last_uid(pool: Any, server: str, mailbox: str, uid: int) -> None:
    """
    Update last processed UID for a server/mailbox.
    
    Args:
        pool: PostgreSQL connection pool
        server: Server name
        mailbox: Mailbox name
        uid: New maximum UID processed
    
    Raises:
        StorageError: If update fails
    """
    # Placeholder
    pass


def record_notification(
    pool: Any,
    notification_type: str,
    recipients: List[str],
    template_vars: Dict[str, Any],
    notification_id: Optional[int] = None,
    status: str = "sent",
    error_message: Optional[str] = None,
) -> int:
    """
    Record sent notification in history.
    
    Args:
        pool: PostgreSQL connection pool
        notification_type: Type (e.g., "imap.message", "user.login")
        recipients: List of recipient monikers
        template_vars: Dictionary of template variables sent
        notification_id: Return value from notify.send()
        status: "sent" | "failed" | "pending"
        error_message: Error details if status="failed"
    
    Returns:
        ID of inserted notification record
    
    Raises:
        StorageError: If insert fails
    """
    # Placeholder
    return 0


def get_notification_history(
    pool: Any,
    limit: int = 100,
    notification_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get recent notifications sent by notifyd.
    
    Args:
        pool: PostgreSQL connection pool
        limit: Maximum number of records to return
        notification_type: Optional filter by type
    
    Returns:
        List of notification history records
    
    Raises:
        StorageError: If query fails
    """
    # Placeholder
    return []
