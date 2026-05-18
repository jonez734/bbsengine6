# notifyd/notification.py
# Notification dispatcher for sending notifications via bbsengine6.notify

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """
    Dispatch notifications through bbsengine6.notify.

    Handles both IMAP email notifications and custom application event notifications.
    Records all notifications to history for audit trail.
    """

    def __init__(self, storage: Any) -> None:
        """
        Initialize dispatcher.

        Args:
            storage: Storage module with record_notification() function
        """
        self.storage = storage

        # Lazy import to avoid circular dependency if bbsengine6.notify not available
        self._notify = None
        self._urgency_map = None

    def _load_notify(self) -> tuple[Any, Dict[str, Any]]:
        """
        Lazy load notify module and urgency enum.

        Returns:
            Tuple of (notify module, urgency_map dict)
        """
        if self._notify is not None:
            return self._notify, self._urgency_map

        try:
            from bbsengine6 import notify
            from bbsengine6.notify import NotificationUrgency

            # Create urgency mapping
            urgency_map = {
                "ROUTINE": NotificationUrgency.ROUTINE,
                "IMPORTANT": NotificationUrgency.IMPORTANT,
                "URGENT": NotificationUrgency.URGENT,
                "CRITICAL": NotificationUrgency.CRITICAL,
            }

            self._notify = notify
            self._urgency_map = urgency_map
            return notify, urgency_map
        except ImportError as e:
            logger.error(f"Failed to import bbsengine6.notify: {e}")
            raise

    def send_imap_notification(
        self,
        recipient: str,
        email_data: Dict[str, Any],
        server: Any,
    ) -> Optional[int]:
        """
        Send IMAP email notification.

        Args:
            recipient: Recipient moniker (bbsengine6 user identifier)
            email_data: Email data dict with keys: subject, from, body, uid
            server: ImapServer config dict with name, urgency, timeout

        Returns:
            Notification ID from notify.send(), or None on error
        """
        try:
            notify, urgency_map = self._load_notify()

            # Build template variables
            template_vars = {
                "subject": email_data.get("subject", ""),
                "from": email_data.get("from", ""),
                "body": email_data.get("body", "")[:500],  # Truncate body
                "server": server.get("name", "Unknown"),
                "uid": email_data.get("uid", 0),
            }

            # Get urgency from server config
            urgency_str = server.get("urgency", "ROUTINE")
            urgency = urgency_map.get(urgency_str, urgency_map["ROUTINE"])

            # Send notification
            notification_id = notify.send(
                recipient=recipient,
                template="imap-message",
                urgency=urgency,
                **template_vars,
            )

            # Record to history
            self.storage.record_notification(
                self.storage._pool,
                "imap.message",
                [recipient],
                template_vars,
                notification_id=notification_id,
                status="sent",
            )

            logger.debug(f"Sent IMAP notification {notification_id} to {recipient}")
            return notification_id

        except Exception as e:
            logger.error(
                f"Failed to send IMAP notification to {recipient}: {e}", exc_info=True
            )

            # Record failure
            try:
                self.storage.record_notification(
                    self.storage._pool,
                    "imap.message",
                    [recipient],
                    {"error": str(e)},
                    status="failed",
                    error_message=str(e),
                )
            except Exception as record_err:
                logger.error(f"Failed to record notification error: {record_err}")

            return None

    def send_custom_notification(
        self,
        event_type: str,
        recipients: List[str],
        template: str,
        urgency: str,
        template_vars: Dict[str, Any],
    ) -> Optional[int]:
        """
        Send custom event notification.

        Args:
            event_type: Event type ("user.login", "game.started", etc.)
            recipients: List of recipient monikers
            template: Template name (e.g., "user-login")
            urgency: Urgency level (ROUTINE|IMPORTANT|URGENT|CRITICAL)
            template_vars: Dictionary of template variables

        Returns:
            Notification ID from notify.send(), or None on error
        """
        try:
            notify, urgency_map = self._load_notify()

            # Map urgency (default to ROUTINE if not found)
            if urgency not in urgency_map:
                urgency = "ROUTINE"
            urgency_obj = urgency_map.get(urgency, urgency_map.get("ROUTINE"))

            # Send to each recipient
            last_notification_id = None
            for recipient in recipients:
                try:
                    notification_id = notify.send(
                        recipient=recipient,
                        template=template,
                        urgency=urgency_obj,
                        **template_vars,
                    )
                    last_notification_id = notification_id
                except Exception as e:
                    logger.error(f"Failed to send {event_type} to {recipient}: {e}")

            # Record to history
            self.storage.record_notification(
                self.storage._pool,
                event_type,
                recipients,
                template_vars,
                notification_id=last_notification_id,
                status="sent",
            )

            logger.debug(
                f"Sent {event_type} notification to {len(recipients)} recipients"
            )
            return last_notification_id

        except Exception as e:
            logger.error(
                f"Failed to send {event_type} notification: {e}", exc_info=True
            )

            # Record failure
            try:
                self.storage.record_notification(
                    self.storage._pool,
                    event_type,
                    recipients,
                    {"error": str(e)},
                    status="failed",
                    error_message=str(e),
                )
            except Exception as record_err:
                logger.error(f"Failed to record notification error: {record_err}")

            return None
