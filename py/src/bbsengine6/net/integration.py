# internet/integration.py
# Integration layer between internet addressing and bbsengine6.message.

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
    Integrate internet addressing with bbsengine6.message.

    Extends message.store_message() to support SMTP-like addresses (user@machine)
    by routing local recipients to message.store_message() and remote recipients
    to WebSocket transport.
    """

    def __init__(
        self,
        local_machine: str = "local",
        message_module: Optional[Any] = None,
        registry: Optional[MachineRegistry] = None,
    ):
        """
        Initialize integration layer.

        Args:
            local_machine: Local machine identifier
            message_module: bbsengine6.message module (auto-imported if None)
            registry: MachineRegistry for remote machine configs
        """
        self.local_machine = local_machine
        self.registry = registry or get_registry()
        self.router = InternetRouter(local_machine, self.registry)
        self.parser = AddressParser(local_machine)
        self.transport = WebSocketTransport()
        self.message_module = message_module

        # Auto-import message module if not provided
        if self.message_module is None:
            self._try_import_message()

    def _try_import_message(self) -> None:
        """Try to import bbsengine6.message module."""
        try:
            from bbsengine6 import message as message_module

            self.message_module = message_module
        except ImportError:
            self.message_module = None

    def send(
        self,
        channel: str,
        recipients: List[str],
        content: str,
        template: Optional[str] = None,
        template_vars: Optional[Dict[str, Any]] = None,
        sender_moniker: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        urgency: Optional[str] = None,
        conn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Send message to recipients (local and/or remote).

        Automatically detects internet addresses and routes appropriately:
        - Local recipients: send via bbsengine6.message.store_message()
        - Remote recipients: send via WebSocket transport

        Args:
            channel: Message channel (e.g. "member:direct", "system:announcements")
            recipients: List of recipients (can be mixed local and internet addresses)
            content: Message content
            template: Optional template string
            template_vars: Template variables
            sender_moniker: Sender's moniker
            data: Additional message data
            urgency: Message urgency level
            conn: Database connection

        Returns:
            Dict with results:
            {
                "local": message_id (from message.store_message()),
                "remote": Dict[machine] -> (success, message),
                "errors": Dict[address] -> error message,
                "summary": (total_success, total_failed)
            }
        """
        if not self.message_module:
            return {
                "local": None,
                "remote": {},
                "errors": {"all": "bbsengine6.message not available"},
                "summary": (0, len(recipients)),
            }

        # Route recipients
        local_recipients, remote_by_machine, frame_addresses, errors = (
            self.router.route(recipients)
        )

        result: Dict[str, Any] = {
            "local": None,
            "remote": {},
            "errors": errors,
        }

        # Send to local recipients via message.store_message_with_checks()
        if local_recipients:
            try:
                store_result = self.message_module.store_message_with_checks(
                    channel=channel,
                    sender_moniker=sender_moniker,
                    content=content,
                    recipient_monikers=local_recipients,
                    data=data,
                    urgency=urgency,
                    template=template,
                    template_vars=template_vars,
                )
                result["local"] = store_result.get("message_id", 0)
                result["local_stored"] = store_result.get("recipients_stored", [])
                result["local_blocked"] = store_result.get("recipients_blocked", [])
                if not store_result.get("rate_limit_ok", True):
                    result["errors"]["rate_limit"] = (
                        f"Local rate limit exceeded for sender={sender_moniker} "
                        f"on channel={channel}"
                    )
                logger.info(
                    f"Internet integration: sent to "
                    f"{len(store_result.get('recipients_stored', []))} "
                    f"local recipients "
                    f"({len(store_result.get('recipients_blocked', []))} blocked)"
                )
            except Exception as e:
                result["errors"]["local"] = f"Failed to send local messages: {e}"
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

                # Prepare message data
                message_data = {
                    "channel": channel,
                    "content": content,
                    "template": template,
                    "template_vars": template_vars or {},
                    "sender_moniker": sender_moniker,
                    "data": data or {},
                    "urgency": urgency,
                }

                # Send via WebSocket (async)
                success, message = self.transport.send_to_remote_sync(
                    host, port, recipients_list, message_data, auth_token
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

        Returns False if message module is unavailable and there are local recipients.
        """
        local_recipients, _, _, _ = self.router.route(recipients)
        if local_recipients and not self.message_module:
            return False
        return True


# Module-level convenience function
_default_integration: Optional[NotifyIntegration] = None


def get_integration(
    local_machine: str = "local",
    message_module: Optional[Any] = None,
    registry: Optional[MachineRegistry] = None,
) -> NotifyIntegration:
    """Get or create default integration instance."""
    global _default_integration
    if _default_integration is None:
        _default_integration = NotifyIntegration(
            local_machine, message_module, registry
        )
    return _default_integration


def send_with_internet(
    channel: str,
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
    """Convenience function for sending with internet addressing.

    ``channel`` is the channel/topic name (e.g. ``"member:direct"`` or
    ``"system:announcements"``). It is forwarded to
    :meth:`NotifyIntegration.send` as its ``channel`` argument.
    """
    integration = get_integration(local_machine)
    return integration.send(
        channel=channel,
        recipients=recipients,
        template=template,
        template_vars=template_vars,
        sender_moniker=sender_moniker,
        data=data,
        urgency=urgency,
        should_persist=should_persist,
        conn=conn,
    )
