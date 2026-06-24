# notify/daemon/hooks.py
# Custom event hook system for bbsengine6 application events

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class EventBus:
    """
    Thread-safe event hook system for application events.

    Events fire asynchronously in daemon threads.
    """

    def __init__(self):
        """Initialize event bus"""
        self._handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def on(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register handler for event type.

        Args:
            event_type: Event identifier ("user.login", etc.)
            handler: Callable that receives event data dict

        Raises:
            TypeError: If handler not callable
        """
        if not callable(handler):
            raise TypeError(f"Handler must be callable, got {type(handler)}")

        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def off(self, event_type: str, handler: Callable) -> None:
        """
        Unregister handler.

        Args:
            event_type: Event type
            handler: Previously registered handler

        Raises:
            ValueError: If handler not registered
        """
        with self._lock:
            if (
                event_type not in self._handlers
                or handler not in self._handlers[event_type]
            ):
                raise ValueError(f"Handler not registered for {event_type}")
            self._handlers[event_type].remove(handler)

    def fire(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Fire event to all registered handlers (non-blocking).

        Args:
            event_type: Event type to fire
            data: Event data dictionary

        Note:
            - Spawns daemon thread for each handler
            - Handlers run in parallel
            - Exceptions logged, don't propagate
            - Returns immediately (non-blocking)
        """
        with self._lock:
            handlers = self._handlers.get(event_type, [])[:]

        for handler in handlers:

            def run_handler():
                try:
                    handler(data)
                except Exception as e:
                    logger.error(
                        f"Error in handler for {event_type}: {e}", exc_info=True
                    )

            thread = threading.Thread(target=run_handler, daemon=True)
            thread.start()

    def get_handlers(self, event_type: str) -> List[Callable]:
        """
        Get list of registered handlers for event type.

        Returns:
            List of handler callables (copy, safe to iterate)
        """
        with self._lock:
            return self._handlers.get(event_type, [])[:]


# Global event bus instance
_event_bus = EventBus()


def fire_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Global function to fire custom event.

    Example:
        from bbsengine6.notify.daemon import fire_event
        fire_event("user.login", {"moniker": "player1"})

    Args:
        event_type: Event identifier
        data: Event data dictionary
    """
    _event_bus.fire(event_type, data)


def register_event_handler(
    event_type: str, handler: Callable[[Dict[str, Any]], None]
) -> None:
    """
    Global function to register event handler.

    Example:
        def on_login(data):
            print(f"User logged in: {data['moniker']}")

        register_event_handler("user.login", on_login)

    Args:
        event_type: Event type identifier
        handler: Callable that receives event data dict

    Raises:
        TypeError: If handler not callable
    """
    _event_bus.on(event_type, handler)


def unregister_event_handler(event_type: str, handler: Callable) -> None:
    """
    Global function to unregister event handler.

    Args:
        event_type: Event type identifier
        handler: Previously registered handler

    Raises:
        ValueError: If handler not registered
    """
    _event_bus.off(event_type, handler)


def get_event_handlers(event_type: str) -> List[Callable]:
    """
    Get list of handlers for event type.

    Args:
        event_type: Event type identifier

    Returns:
        List of registered handlers
    """
    return _event_bus.get_handlers(event_type)
