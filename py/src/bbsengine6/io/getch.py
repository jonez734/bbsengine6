# getch.py
# Low-level keyboard input and event handling for terminal applications.
#
# This module provides:
# 1. getch_str() - Non-blocking character read with timeout
# 2. Escape sequence processing for function keys (F1-F12, arrows, etc.)
# 3. Threading-based event system for keyboard input monitoring
#
# Threading Model:
#   - Main thread: Reads characters, fires events to dispatcher, returns immediately
#   - Dispatcher thread: Processes events and invokes registered handlers asynchronously
#
# Timeout Accuracy:
#   - Wall-clock time (time.time()) ensures precision
#   - Poll interval (100ms) for notification checks during idle waits

import os
import tty
import select
import fcntl
import termios
import time
import queue
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Optional, List


from .common import (
    _current_input_stream,
    _current_stream_lock,
    _input_queue,
    _read_current_input_stream,
)
from .echo import echo, echo_traceback
from .util import logentry
from .keymap import KEY_MAP
from .const import ESC, ETX, EOF
from . import screen

# Notification support (with graceful fallback)
try:
    from bbsengine6.member import _threadlocal

    _has_member_module = True
except ImportError:
    _has_member_module = False

try:
    from bbsengine6 import notify

    _has_notify_module = True
except ImportError:
    _has_notify_module = False

# Track if bell has been emitted this session (emit only once)
_notified_this_session = False
_notified_this_session_lock = threading.Lock()

# Track if bottom bar has been updated this session (update only once)
_bottombar_updated_this_session = False
_bottombar_update_lock = threading.Lock()

# ============================================================================
# KEY EVENT SYSTEM - Threading-based async event notification
# ============================================================================


@dataclass(frozen=True)
class KeyEvent:
    """Immutable event data for keyboard input."""

    raw_char: str  # Original byte(s): 'a', '\x1b[A', etc.
    processed_key: str | None  # After _proc_char: 'a', 'KEY_UP', None
    timestamp: float  # time.time() when event was created
    stage: str  # "raw" or "processed"
    source_func: str  # "getch_str", "inputstring", "inputchoice", etc.


@dataclass
class EventHandler:
    """Registered callback with optional filtering."""

    name: str  # Unique identifier
    callback: Callable[[KeyEvent], None]  # Invoked with event
    filter_fn: Optional[Callable[[KeyEvent], bool]]  # Predicate; None = all events

    def matches(self, event: KeyEvent) -> bool:
        """Check if event passes filter."""
        return self.filter_fn(event) if self.filter_fn else True


class KeyEventBus:
    """Manages handler registration and filtering."""

    def __init__(self, history_size: int = 100):
        self._handlers: Dict[str, EventHandler] = {}
        self._lock = threading.Lock()
        self.history: deque = deque(maxlen=history_size)

    def register(
        self,
        name: str,
        callback: Callable[[KeyEvent], None],
        filter_fn: Optional[Callable[[KeyEvent], bool]] = None,
    ) -> None:
        """Register a callback handler."""
        with self._lock:
            if name in self._handlers:
                raise ValueError(f"Handler '{name}' already registered")
            self._handlers[name] = EventHandler(name, callback, filter_fn)

    def unregister(self, name: str) -> None:
        """Remove a registered handler."""
        with self._lock:
            if name not in self._handlers:
                raise KeyError(f"Handler '{name}' not found")
            del self._handlers[name]

    def get_handlers(self) -> Dict[str, EventHandler]:
        """Get snapshot of all handlers."""
        with self._lock:
            return dict(self._handlers)

    def get_history(self, limit: int = 10) -> List[KeyEvent]:
        """Get recent events from history."""
        return list(self.history)[-limit:] if limit > 0 else list(self.history)

    def clear_history(self) -> None:
        """Clear history buffer."""
        self.history.clear()

    def add_to_history(self, event: KeyEvent) -> None:
        """Add event to history buffer."""
        self.history.append(event)


class EventDispatcher:
    """Manages background thread and event dispatch using condition variable for efficient waits.

    The dispatcher uses threading.Condition for proper synchronization instead of busy-wait:
    - Main thread signals condition when events are queued
    - Dispatcher thread waits on condition (sleeps until notified or timeout)
    - No busy-looping or wasted CPU cycles
    """

    def __init__(self, bus: KeyEventBus):
        self.bus = bus
        self._queue: deque = deque()
        self._condition = threading.Condition(threading.Lock())
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._use_timeout = False
        self._timeout_sec = 0.1

    def start(self, use_timeout: bool = False, timeout_sec: float = 0.1) -> None:
        """Start the dispatcher background thread."""
        if self.is_running():
            raise RuntimeError("Event dispatcher already running")

        with self._condition:
            self._use_timeout = use_timeout
            self._timeout_sec = timeout_sec
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run, daemon=True, name="KeyEventDispatcher"
            )
            self._thread.start()

    def stop(self, wait_timeout: float = 2.0) -> None:
        """Stop the dispatcher gracefully."""
        if not self.is_running():
            raise RuntimeError("Event dispatcher not running")

        self._stop_event.set()
        with self._condition:
            self._condition.notify_all()  # Wake thread if waiting
        if self._thread:
            self._thread.join(timeout=wait_timeout)
            self._thread = None

    def is_running(self) -> bool:
        """Check if dispatcher is active."""
        return self._thread is not None and self._thread.is_alive()

    def push_event(self, event: KeyEvent) -> None:
        """Enqueue event for dispatch and signal dispatcher thread."""
        with self._condition:
            self._queue.append(event)
            self._condition.notify()  # Wake dispatcher thread
        _event_queue.put(event)  # Also push to public queue
        self.bus.add_to_history(event)

    def set_timeout(self, use_timeout: bool, timeout_sec: float = 0.1) -> None:
        """Change timeout settings at runtime."""
        if not self.is_running():
            raise RuntimeError("Event dispatcher not running")
        with self._condition:
            self._use_timeout = use_timeout
            self._timeout_sec = timeout_sec

    def _run(self) -> None:
        """Background thread main loop using condition variable for efficient waits."""
        while not self._stop_event.is_set():
            with self._condition:
                # Wait for event or timeout (predicate: queue is not empty)
                while len(self._queue) == 0 and not self._stop_event.is_set():
                    self._condition.wait(timeout=0.1)

                # Check again after wakeup
                if len(self._queue) == 0:
                    continue

                event = self._queue.popleft()

            # Fire all matching handlers (outside lock)
            for handler in self.bus.get_handlers().values():
                if handler.matches(event):
                    self._fire_callback(handler, event)

    def _fire_callback(self, handler: EventHandler, event: KeyEvent) -> None:
        """Fire callback with optional timeout."""
        with self._condition:
            use_timeout = self._use_timeout
            timeout_sec = self._timeout_sec

        try:
            if use_timeout:
                self._fire_with_timeout(handler.callback, event, timeout_sec)
            else:
                handler.callback(event)
        except Exception as e:
            self._handle_error(e, event, handler.name)

    def _fire_with_timeout(
        self,
        callback: Callable[[KeyEvent], None],
        event: KeyEvent,
        timeout_sec: float,
    ) -> None:
        """Fire callback in separate thread with timeout."""
        result_holder = []
        error_holder = []

        def callback_wrapper() -> None:
            try:
                callback(event)
                result_holder.append(True)
            except Exception as e:
                error_holder.append(e)

        thread = threading.Thread(target=callback_wrapper, daemon=True)
        thread.start()
        thread.join(timeout=timeout_sec)

        if thread.is_alive():
            logentry(f"Event handler exceeded timeout ({timeout_sec}s)")
        elif error_holder:
            raise error_holder[0]

    def _handle_error(self, exc: Exception, event: KeyEvent, handler_name: str) -> None:
        """Handle callback error."""
        if _event_error_handler:
            try:
                _event_error_handler(exc, event, handler_name)
            except Exception as e:
                logentry(f"Error handler failed: {e}")
        else:
            logentry(f"Event handler '{handler_name}' error: {exc}")


# Module-level state
_event_bus = KeyEventBus()
_event_dispatcher = EventDispatcher(_event_bus)
_event_queue: queue.Queue[KeyEvent] = queue.Queue()
_event_error_handler: Optional[Callable[[Exception, KeyEvent, str], None]] = None


# Public API Functions


def register_key_event_handler(
    name: str,
    callback: Callable[[KeyEvent], None],
    filter_fn: Optional[Callable[[KeyEvent], bool]] = None,
) -> None:
    """Register a callback to fire on matching events."""
    _event_bus.register(name, callback, filter_fn)


def unregister_key_event_handler(name: str) -> None:
    """Remove a registered handler by name."""
    _event_bus.unregister(name)


def get_registered_handlers() -> Dict[str, EventHandler]:
    """Get snapshot of all registered handlers."""
    return _event_bus.get_handlers()


def start_event_dispatcher(use_timeout: bool = False, timeout_sec: float = 0.1) -> None:
    """Start the event dispatcher background thread."""
    _event_dispatcher.start(use_timeout=use_timeout, timeout_sec=timeout_sec)


def stop_event_dispatcher(wait_timeout: float = 2.0) -> None:
    """Stop the event dispatcher gracefully."""
    _event_dispatcher.stop(wait_timeout=wait_timeout)


def is_event_dispatcher_running() -> bool:
    """Check if dispatcher thread is active."""
    return _event_dispatcher.is_running()


def set_event_dispatcher_timeout(use_timeout: bool, timeout_sec: float = 0.1) -> None:
    """Adjust timeout settings at runtime."""
    _event_dispatcher.set_timeout(use_timeout, timeout_sec)


def get_event_queue() -> queue.Queue[KeyEvent]:
    """Get the shared event queue for custom consumption."""
    return _event_queue


def is_event_queue_empty() -> bool:
    """Check if public queue has no pending events."""
    return _event_queue.empty()


def clear_event_queue() -> None:
    """Drain all pending events from public queue."""
    while not _event_queue.empty():
        try:
            _event_queue.get_nowait()
        except queue.Empty:
            break


def set_event_error_handler(
    handler: Optional[Callable[[Exception, KeyEvent, str], None]],
) -> None:
    """Set custom error handler for callback exceptions."""
    global _event_error_handler
    _event_error_handler = handler


def get_key_event_history(limit: int = 10) -> List[KeyEvent]:
    """Get recent events from circular history buffer."""
    return _event_bus.get_history(limit)


def clear_key_event_history() -> None:
    """Clear the event history buffer."""
    _event_bus.clear_history()


# ============================================================================
# NOTIFICATION SUPPORT HELPERS
# ============================================================================


def _check_notifications(moniker: str, **kwargs) -> tuple[bool, int]:
    """Check for pending notifications. Returns (has_notifications, count)."""
    if not _has_notify_module:
        return False, 0
    try:
        count = notify.count(moniker, **kwargs)
        return (count or 0) > 0, count or 0
    except Exception:
        echo_traceback("bbsengine6.io.getch.333:")
        return False, 0


def _emit_notification_bell_once() -> bool:
    """Emit bell once per session when notifications exist."""
    global _notified_this_session
    with _notified_this_session_lock:
        if _notified_this_session:
            return False
        _notified_this_session = True
    echo("{bel}", end="", flush=True)
    return True


def _update_bottombar_on_notification() -> bool:
    """Update bottom bar once per session to show notification status.

    Returns True if update was performed, False if already updated this session.
    """
    global _bottombar_updated_this_session
    with _bottombar_update_lock:
        if _bottombar_updated_this_session:
            return False
        _bottombar_updated_this_session = True

    try:
        # Get notification status string (e.g., "F2: notify (3)")
        notification_status = screen.get_notification_status()
        if notification_status:
            # Try to use echo_commands to position cursor and display notification
            try:
                from . import terminal

                last_line = terminal.lines()
                echo(
                    f"{{savecursor}}{{bottombarcolor}}{{curpos:{last_line},0}}[{notification_status}]{{/all}}{{restorecursor}}",
                    end="",
                    flush=True,
                    wordwrap=False,
                )
            except Exception:
                # Fallback: output with newline if curpos fails
                echo(f"\n[{notification_status}]", flush=True)
        return True
    except Exception:
        # Silently handle all other errors to avoid crashing getch
        return False


def _get_urgency_color(urgency) -> str:
    """Get color code for urgency level using echo var."""
    from bbsengine6.notify import NotificationUrgency

    mapping = {
        NotificationUrgency.CRITICAL: "{var:notify.criticalcolor}",
        NotificationUrgency.URGENT: "{var:notify.urgentcolor}",
        NotificationUrgency.IMPORTANT: "{var:notify.importantcolor}",
        NotificationUrgency.ROUTINE: "{var:notify.routinecolor}",
    }
    return mapping.get(urgency, "{var:notify.routinecolor}")


def _show_pending_notifications(moniker: str) -> None:
    """Display pending notifications for user.

    This function displays notifications and returns immediately.
    It does NOT wait for user input—that is the caller's responsibility.
    This avoids recursive calls and keeps input handling simple.
    """
    if not _has_notify_module:
        echo("{var:normalcolor}Notifications unavailable.{/all}")
        return

    try:
        queue = notify.get_queue(moniker)
        notifications = queue.get_all()

        if not notifications:
            echo("{var:normalcolor}No pending notifications.{/all}")
            return

        # Display each notification with colors from echo vars
        for n in notifications:
            urgency_color = _get_urgency_color(n.urgency)
            timestamp = datetime.fromtimestamp(n.timestamp).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            recipient = n.recipients[0] if n.recipients else "Unknown"

            echo(
                f"{urgency_color}[{n.urgency.value}]{{/all}} {{var:notify.datestampcolor}}{timestamp}{{/all}}"
            )
            echo(f"{{var:notify.recipientcolor}}To:{{/all}} {recipient}")
            echo(f"{n.message}")
            echo("{var:normalcolor}" + "─" * 40 + "{/all}")

        echo("{var:normalcolor}Press any key to continue...{/all}")

    except Exception as e:
        echo(f"{{var:normalcolor}}Error displaying notifications: {e}{{/all}}")


# ============================================================================
# GETCH IMPLEMENTATION
# ============================================================================

# def _read():
#    if _input_queue:
#        return _input_queue.popleft()
#    return _current_input_stream.read(1)


def _proc_char(char: str, debug: bool = False, fire_events: bool = True) -> str | None:
    """Process character and optionally fire events to dispatcher.

    This function:
    1. Fires a "raw" event before processing (if events enabled)
    2. Processes the character (escape sequences, control keys, regular chars)
    3. Fires a "processed" event after conversion (if events enabled)

    Args:
        char: Raw character to process
        debug: If True, log unknown escape sequences and return None
        fire_events: If True and dispatcher running, fire key events

    Returns:
        Processed key name (e.g., 'a', 'KEY_UP', 'KEY_ENTER') or None if unknown and debug=True

    Event Flow:
        - Raw event: KeyEvent(raw_char=char, processed_key=None, stage='raw')
        - Processing: Handle escapes, control codes, etc.
        - Processed event: KeyEvent(raw_char=char, processed_key=result, stage='processed')
    """
    # Fire raw event before processing
    if fire_events and _event_dispatcher.is_running():
        raw_event = KeyEvent(
            raw_char=char,
            processed_key=None,
            timestamp=time.time(),
            stage="raw",
            source_func="getch_str",
        )
        _event_dispatcher.push_event(raw_event)

    # Initialize processed (will be set in all non-exception paths)
    processed: str | None = None

    # 3. Handle Control Characters
    if char == "\x01":
        processed = "KEY_CTRL_A"
    elif char == ETX:  # Ctrl+C (ETX)
        raise KeyboardInterrupt
    elif char == EOF:  # Ctrl+D (EOF)
        raise EOFError
    elif char == "\x05":  # Ctrl+E (EOL)
        processed = "KEY_CTRL_E"
    elif char in ("\x7f", "\x08"):
        processed = "KEY_BACKSPACE"
    elif char == "\r":
        processed = "KEY_ENTER"
    elif char == "\x15":  # Ctrl+U
        processed = "KEY_CUTTOBOL"
    elif char == "\t":
        processed = "KEY_TAB"
    # Handle Escape Sequences and Plain ESC
    elif char == ESC:
        sequence = char
        # Try to read up to 10 more bytes to form complete escape sequence.
        # Stop when BlockingIOError (no more data) or 10 bytes collected.
        # This handles: ESC followed by nothing (plain ESC), or multi-byte codes like ESC[A.
        for _ in range(10):
            try:
                next_char = _read_current_input_stream()
                sequence += next_char
            except BlockingIOError:
                break  # No more bytes available, sequence complete

        # Check for plain ESC (no additional bytes)
        if len(sequence) == 1:
            processed = "KEY_ESC"
        else:
            # Try to match against known escape sequences.
            # Sort by length (longest first) to match complete sequences correctly.
            found = False
            for code, name in sorted(
                KEY_MAP.items(), key=lambda item: len(item[0]), reverse=True
            ):
                if sequence.endswith(code):
                    processed = name
                    found = True
                    break

            # Unknown escape sequence
            if not found:
                if debug:
                    logentry(f"unknown escape sequence: {sequence!r}")
                    processed = None
                else:
                    # Return raw sequence if not in debug mode
                    processed = sequence
    # Regular character (letter, digit, symbol, etc.)
    else:
        processed = char

    # Fire processed event after processing
    if fire_events and _event_dispatcher.is_running():
        processed_event = KeyEvent(
            raw_char=char,
            processed_key=processed,
            timestamp=time.time(),
            stage="processed",
            source_func="getch_str",
        )
        _event_dispatcher.push_event(processed_event)

    return processed


def getch_str(
    timeout: float = 1.0,
    debug: bool = False,
    fire_events: bool = True,
    check_notifications: bool = True,
    **kwargs,
) -> str | None:
    """Reads a single keypress without blocking and handles control/extended keys.

    Args:
        timeout: Seconds to wait for input (default: 1.0). Uses wall-clock time for accuracy.
        debug: If True, log unknown escape sequences and return None
        fire_events: If True, fire key events if dispatcher is running
        check_notifications: If True, check for notifications and emit bell (default: True)

    Returns:
        Processed key name (e.g., 'a', 'KEY_UP', 'KEY_ENTER'), or None on timeout.
        Note: F2 key returns "KEY_F2" (caller can handle notifications if desired).

    Timeout Accuracy:
        Timeout is measured using wall-clock time (time.time()) to ensure precision.
        The function checks for notifications every 100ms during idle waits.
    """
    global _notified_this_session

    # Check for notifications and emit bell (once) before waiting for input
    moniker = None
    if _has_member_module:
        moniker = getattr(_threadlocal, "moniker", None)

    if check_notifications and moniker and _has_notify_module:
        has_notifications, notification_count = _check_notifications(moniker, **kwargs)
        if has_notifications:
            _emit_notification_bell_once()
            _update_bottombar_on_notification()

    with _current_stream_lock:
        if _input_queue:
            char = _input_queue.popleft()
            result = _proc_char(char, debug=debug, fire_events=fire_events)
            return result
        else:
            fd = _current_input_stream.fileno()
            old_settings = termios.tcgetattr(fd)
            old_flags = None

            try:
                # 1. Set Terminal to Raw Mode
                tty.setraw(fd)

                # 2. Wait for input using wall-clock timeout for accuracy
                start_time = time.time()
                poll_interval = 0.1  # Check notifications every 100ms
                ready = []

                while True:
                    # Calculate elapsed time and remaining timeout
                    elapsed = time.time() - start_time
                    if timeout is not None and elapsed >= timeout:
                        return None  # Timeout reached

                    # Calculate timeout for select
                    if timeout is None:
                        select_timeout = poll_interval
                    else:
                        remaining = timeout - elapsed
                        select_timeout = (
                            min(poll_interval, remaining) if remaining > 0 else 0
                        )

                    # Wait for input with calculated timeout
                    ready, _, _ = select.select(
                        [_current_input_stream], [], [], select_timeout
                    )

                    if ready:
                        break

                    # No input yet - check for notification updates during idle
                    if check_notifications and moniker and _has_notify_module:
                        has_notifications, _ = _check_notifications(moniker, **kwargs)
                        if has_notifications:
                            _update_bottombar_on_notification()

                # 3. Set Non-Blocking I/O for escape sequence reading
                old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)

                try:
                    # Attempt to read a single byte
                    char = _read_current_input_stream()
                except BlockingIOError:
                    # If nothing is available, return None immediately
                    return None

                result = _proc_char(char, debug=debug, fire_events=fire_events)
                return result

            finally:
                # 4. Restore Terminal Settings (CRUCIAL!)
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                # Restore old flags (blocking I/O)
                if old_flags:
                    fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)
