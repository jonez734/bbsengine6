# notifyd/storage.py
# PostgreSQL storage for IMAP state and notification history

from __future__ import annotations

import json
import logging
from pathlib import Path
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
    try:
        # Read SQL schema file
        schema_file = Path(__file__).parent / "sql" / "001_notifyd_schema.sql"
        sql = schema_file.read_text()
        
        # Execute schema SQL
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
            conn.commit()
        
        logger.debug("Database schema initialized")
    except Exception as e:
        raise StorageError(f"Failed to initialize schema: {e}") from e


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
    try:
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT max_uid FROM notifyd_imap_state
                    WHERE server = %s AND mailbox = %s
                    """,
                    (server, mailbox),
                )
                row = cursor.fetchone()
                return row[0] if row else 0
    except Exception as e:
        raise StorageError(f"Failed to get last UID: {e}") from e


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
    try:
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO notifyd_imap_state (server, mailbox, max_uid)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (server, mailbox)
                    DO UPDATE SET max_uid = %s, updated_at = CURRENT_TIMESTAMP
                    """,
                    (server, mailbox, uid, uid),
                )
            conn.commit()
        
        logger.debug(f"Updated UID for {server}/{mailbox} to {uid}")
    except Exception as e:
        raise StorageError(f"Failed to set last UID: {e}") from e


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
    try:
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO notifyd_history 
                    (notification_type, recipients, notification_id, data, status, error_message)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        notification_type,
                        recipients,
                        notification_id,
                        json.dumps(template_vars),
                        status,
                        error_message,
                    ),
                )
                row = cursor.fetchone()
                record_id = row[0] if row else 0
            conn.commit()
        
        logger.debug(f"Recorded notification {record_id} ({notification_type})")
        return record_id
    except Exception as e:
        raise StorageError(f"Failed to record notification: {e}") from e


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
    try:
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                if notification_type:
                    cursor.execute(
                        """
                        SELECT id, notification_type, recipients, sent_at, 
                               notification_id, data, status, error_message
                        FROM notifyd_history
                        WHERE notification_type = %s
                        ORDER BY sent_at DESC
                        LIMIT %s
                        """,
                        (notification_type, limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, notification_type, recipients, sent_at,
                               notification_id, data, status, error_message
                        FROM notifyd_history
                        ORDER BY sent_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    try:
                        data = json.loads(row[5]) if row[5] else {}
                    except (json.JSONDecodeError, TypeError):
                        data = {}
                    
                    records.append({
                        "id": row[0],
                        "notification_type": row[1],
                        "recipients": row[2],
                        "sent_at": row[3],
                        "notification_id": row[4],
                        "data": data,
                        "status": row[6],
                        "error_message": row[7],
                    })
                
                return records
    except Exception as e:
        raise StorageError(f"Failed to get notification history: {e}") from e
