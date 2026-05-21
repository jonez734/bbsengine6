# internet/integration.py
# Integration layer between internet addressing and bbsengine6.notify.

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .address import AddressParser
from .registry import MachineRegistry, get_registry
from .router import InternetRouter
from .transport import WebSocketTransport

logger = logging.getLogger(__name__)


class NotifyIntegration:
    """
    Integrate internet addressing with bbsengine6.notify.

    Extends notify.send() to support SMTP-like addresses (user@machine)
    by routing local recipients to notify.send() and remote recipients
    to WebSocket transport.
    """

    def __init__(
        self,
        local_machine: str = "local",
        notify_module: Optional[Any] = None,
        registry: Optional[MachineRegistry] = None,
    ):
        """
        Initialize integration layer.

        Args:
            local_machine: Local machine identifier
            notify_module: bbsengine6.notify module (auto-imported if None)
            registry: MachineRegistry for remote machine configs
        """
        self.local_machine = local_machine
        self.registry = registry or get_registry()
        self.router = InternetRouter(local_machine, self.registry)
        self.parser = AddressParser(local_machine)
        self.transport = WebSocketTransport()
        self.notify_module = notify_module

        # Auto-import notify module if not provided
        if self.notify_module is None:
            self._try_import_notify()

    def _try_import_notify(self) -> None:
        """Try to import bbsengine6.notify module."""
        try:
            from bbsengine6 import notify

            self.notify_module = notify
        except ImportError:
            self.notify_module = None

    def send(
        self,
        notification_type: str,
        recipients: List[str],
        template: str,
        template_vars: Optional[Dict[str, Any]] = None,
        sender_moniker: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        urgency: Optional[Any] = None,
        should_persist: bool = True,
        conn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Send notification to recipients (local and/or remote).

        Automatically detects internet addresses and routes appropriately:
        - Local recipients: send via bbsengine6.notify.send()
        - Remote recipients: send via WebSocket transport

        Args:
            notification_type: Type of notification
            recipients: List of recipients (can be mixed local and internet addresses)
            template: Notification template
            template_vars: Template variables
            sender_moniker: Sender's moniker
            data: Additional notification data
            urgency: Notification urgency level
            should_persist: Whether to persist notification
            conn: Database connection

        Returns:
            Dict with results:
            {
                "local": Notification (from notify.send()),
                "remote": Dict[machine] -> (success, message),
                "errors": Dict[address] -> error message,
                "summary": (total_success, total_failed)
            }
        """
        if not self.notify_module:
            return {
                "local": None,
                "remote": {},
                "errors": {"all": "bbsengine6.notify not available"},
                "summary": (0, len(recipients)),
            }

        # Route recipients
        local_recipients, remote_by_machine, frame_addresses, errors = self.router.route(recipients)

        result: Dict[str, Any] = {
            "local": None,
            "remote": {},
            "errors": errors,
        }

        # Send to local recipients via notify.send()
        if local_recipients:
            try:
                result["local"] = self.notify_module.send(
                    notification_type=notification_type,
                    recipients=local_recipients,
                    template=template,
                    template_vars=template_vars,
                    sender_moniker=sender_moniker,
                    data=data,
                    urgency=urgency,
                    should_persist=should_persist,
                    conn=conn,
                )
                logger.info(
                    f"Internet integration: sent to {len(local_recipients)} local recipients"
                )
            except Exception as e:
                result["errors"]["local"] = f"Failed to send local notifications: {e}"
                logger.error(f"Internet integration: local send failed: {e}")

        # Send to remote recipients via WebSocket
        for machine, recipients_list in remote_by_machine.items():
            try:
                # Resolve machine configuration
                host, port, auth_token = self.router.resolve_machine(machine)

                if not host or not port:
                    result["remote"][machine] = (
                        False,
                        f"Machine not configured in registry: {machine}",
                    )
                    logger.warning(f"Internet integration: no config for {machine}")
                    continue

                # Prepare notification data
                notification_data = {
                    "type": notification_type,
                    "template": template,
                    "template_vars": template_vars or {},
                    "sender_moniker": sender_moniker,
                    "data": data or {},
                    "urgency": urgency.value if urgency else None,
                }

                # Send via WebSocket (async)
                success, message = self.transport.send_to_remote_sync(
                    host, port, recipients_list, notification_data, auth_token
                )

                result["remote"][machine] = (success, message)
                if success:
                    logger.info(
                        f"Internet integration: sent to {machine} ({len(recipients_list)} recipients)"
                    )
                else:
                    logger.error(
                        f"Internet integration: failed to send to {machine}: {message}"
                    )

            except Exception as e:
                result["remote"][machine] = (False, str(e))
                logger.error(
                    f"Internet integration: remote delivery error for {machine}: {e}"
                )

        # Calculate summary
        local_success = 1 if result["local"] else 0
        remote_success = sum(1 for success, _ in result["remote"].values() if success)
        total_failed = len(result["errors"]) + (len(remote_by_machine) - remote_success)

        result["summary"] = (local_success + remote_success, total_failed)

        return result

    def can_send_to(self, recipients: List[str]) -> bool:
        """
        Check if integration can send to all recipients.

        Returns False if notify module is unavailable and there are local recipients.
        """
        local_recipients, _, _, _ = self.router.route(recipients)
        if local_recipients and not self.notify_module:
            return False
        return True


# Module-level convenience function
_default_integration: Optional[NotifyIntegration] = None


def get_integration(
    local_machine: str = "local",
    notify_module: Optional[Any] = None,
    registry: Optional[MachineRegistry] = None,
) -> NotifyIntegration:
    """Get or create default integration instance."""
    global _default_integration
    if _default_integration is None:
        _default_integration = NotifyIntegration(local_machine, notify_module, registry)
    return _default_integration


def send_with_internet(
    notification_type: str,
    recipients: List[str],
    template: str,
    template_vars: Optional[Dict[str, Any]] = None,
    sender_moniker: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    urgency: Optional[Any] = None,
    should_persist: bool = True,
    conn: Optional[Any] = None,
    local_machine: str = "local",
) -> Dict[str, Any]:
    """Convenience function for sending with internet addressing."""
    integration = get_integration(local_machine)
    return integration.send(
        notification_type=notification_type,
        recipients=recipients,
        template=template,
        template_vars=template_vars,
        sender_moniker=sender_moniker,
        data=data,
        urgency=urgency,
        should_persist=should_persist,
        conn=conn,
    )
