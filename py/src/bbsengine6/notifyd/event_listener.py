# notifyd/event_listener.py
# Event handler registration and management

from __future__ import annotations

import logging
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


class EventListener:
    """
    Register and manage event handlers from configuration.

    Converts event configurations into notification handler functions
    and registers them with the event bus.
    """

    def __init__(self, config: Dict[str, Any], dispatcher: Any) -> None:
        """
        Initialize event listener.

        Args:
            config: NotifydConfig dict with "events" section
            dispatcher: NotificationDispatcher instance
        """
        self.config = config
        self.dispatcher = dispatcher

    def register_handlers(self) -> None:
        """
        Register all configured event handlers.

        Iterates through events section of config and registers handlers
        for each event type.
        """
        events_config = self.config.get("events", {})

        if not events_config:
            logger.debug("No events configured")
            return

        for event_type, handlers_config in events_config.items():
            if not isinstance(handlers_config, list):
                logger.warning(
                    f"Event {event_type}: handlers must be list, got {type(handlers_config)}"
                )
                continue

            for handler_config in handlers_config:
                try:
                    handler = self._make_handler(event_type, handler_config)

                    # Import and register with event bus
                    from . import hooks

                    hooks.register_event_handler(event_type, handler)
                    logger.debug(f"Registered handler for {event_type}")

                except Exception as e:
                    logger.error(
                        f"Failed to register handler for {event_type}: {e}",
                        exc_info=True,
                    )

    def _make_handler(
        self, event_type: str, handler_config: Dict[str, Any]
    ) -> Callable:
        """
        Create notification handler function from config.

        Args:
            event_type: Event type identifier
            handler_config: Handler configuration dict with keys:
                - recipients: List of recipient monikers
                - template: Template name
                - urgency: Urgency level (ROUTINE|IMPORTANT|URGENT|CRITICAL)

        Returns:
            Callable that handles the event

        Raises:
            ValueError: If required config keys missing
        """
        # Extract handler config
        recipients = handler_config.get("recipients")
        template = handler_config.get("template")
        urgency = handler_config.get("urgency", "ROUTINE")

        if not recipients:
            raise ValueError(f"{event_type}: recipients required")
        if not template:
            raise ValueError(f"{event_type}: template required")

        if not isinstance(recipients, list):
            raise ValueError(f"{event_type}: recipients must be list")

        # Create handler function
        def handler(data: Dict[str, Any]) -> None:
            """Handle event and send notification"""
            try:
                self.dispatcher.send_custom_notification(
                    event_type=event_type,
                    recipients=recipients,
                    template=template,
                    urgency=urgency,
                    template_vars=data,
                )
            except Exception as e:
                logger.error(
                    f"Error sending {event_type} notification: {e}", exc_info=True
                )

        return handler
