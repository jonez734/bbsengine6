import os
import signal
import tty
import select
import fcntl
import termios
import time
import queue
import threading
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, List

# Global state for tty recovery
_global_tty_settings: Optional[Any] = None
_global_tty_fd: Optional[int] = None


# Raw-session state lives in common (shared with the DSR and mouse queries).
from .common import (  # noqa: E402
    begin_raw_session,
    end_raw_session,
    _in_raw_session,
    _restore_cooked,
)


def _restore_tty():
    """Restore tty settings and clear globals."""
    global _global_tty_settings, _global_tty_fd
    if _global_tty_fd is not None and _global_tty_settings is not None:
        try:
            termios.tcsetattr(_global_tty_fd, termios.TCSADRAIN, _global_tty_settings)
        except Exception:
            pass
    _global_tty_fd = None
    _global_tty_settings = None


def _make_signal_handler(signum: int):
    """Factory for signal handlers that restore tty."""

    def handler(signum, frame):
        _restore_tty()
        if signum == signal.SIGWINCH:
            _handle_sigwinch()
        else:
            signal.default_int_handler(signum, frame)

    return handler


def _handle_sigwinch() -> None:
    """Handle SIGWINCH signal - invoke resize callbacks."""
    with _winlock:
        for cb in _resize_callbacks:
            try:
                cb()
            except Exception:
                pass
        if _default_resize_handler:
            try:
                _default_resize_handler()
            except Exception:
                pass


def register_resize_handler(callback: Callable[[], None]) -> None:
    """Register a callback to be invoked when terminal is resized.

    Callbacks are invoked with no arguments during signal handler context,
    so they should be minimal and thread-safe.
    """
    with _winlock:
        _resize_callbacks.append(callback)


def unregister_resize_handler(callback: Callable[[], None]) -> None:
    """Remove a registered resize handler."""
    with _winlock:
        if callback in _resize_callbacks:
            _resize_callbacks.remove(callback)


def set_resize_handler(callback: Callable[[], None] | None) -> None:
    """Set the default resize handler, replacing any previous one."""
    global _default_resize_handler
    with _winlock:
        _default_resize_handler = callback


def install_signal_handlers() -> None:
    """Install signal handlers for fatal signals and SIGWINCH.
    
    Call this explicitly in non-asyncio programs. For asyncio programs,
    use loop.add_signal_handler() instead.
    """
    global _signal_handlers_installed
    if _signal_handlers_installed:
        return
    
    for sig in _fatal_signals:
        try:
            signal.signal(sig, _make_signal_handler(sig))
        except (OSError, ValueError):
            pass
    
    try:
        signal.signal(signal.SIGWINCH, _make_signal_handler(signal.SIGWINCH))
    except (OSError, ValueError):
        pass
    
    _signal_handlers_installed = True


_fatal_signals = [
    signal.SIGINT,
    signal.SIGQUIT,
    signal.SIGTERM,
    signal.SIGHUP,
]

# Install signal handlers for all fatal signals
for sig in _fatal_signals:
    try:
        signal.signal(sig, _make_signal_handler(sig))
    except (OSError, ValueError):
        pass  # Signal not supported on this platform

# Install SIGWINCH handler separately
_winlock = threading.Lock()
_resize_callbacks: list[Callable[[], None]] = []
_default_resize_handler: Callable[[], None] = None
_signal_handlers_installed = True
try:
    signal.signal(signal.SIGWINCH, _make_signal_handler(signal.SIGWINCH))
except (OSError, ValueError):
    pass  # Signal not supported on this platform


from ..message import cache as _msg_cache
from . import common as _common
from .common import (
    _current_stream_lock,
    _input_queue,
    _input_queue_lock,
    _read_current_input_stream,
    drain_stream_to_queue,
)
from .echo import echo, echo_traceback
from .util import logentry
from .keymap import KEY_MAP
from .const import ESC, ETX, EOF
from . import screen

# Notification support
try:
    from bbsengine6.member import _threadlocal

    _has_member_module = True
except ImportError:
    _has_member_module = False

# Track if bell has been emitted this session (emit only once)

# Track if bottom bar has been updated this session (update only once)
# Last notification status drawn on the bottom bar: per interaction, see _bottombar_status().
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


def _check_kwargs(kwargs: dict) -> dict:
    """The kwargs to forward to _check_notifications: everything except ``moniker``.

    The check takes the session moniker as its first argument. A caller's ``moniker`` keyword must
    not be forwarded as well, or the call passes the moniker twice.
    """
    return {k: v for k, v in kwargs.items() if k != "moniker"}


def _check_notifications(moniker: str, **kwargs) -> tuple[bool, int]:
    """Check for pending notifications. Returns (has_notifications, count).

    Reads the in-process local cache first (populated by past DB hits
    in this session); on cache miss, issues a message.get_unread_count()
    query and primes the cache. The bed server-push fast path is not
    wired in this build: bed subscription lives in
    bbsengine6.startup.message_subscription (currently only present in
    installed venv copies, not in this source tree) and is dormant.
    Until bed push is wired into the live source tree, the
    poll-while-idle loop in getch_str is the active notification
    delivery mechanism.
    """
    try:
        from .. import message as message_module
        if message_module.is_enabled():
            cached = message_module.get_local_unread_count(moniker)
            if cached >= 0:
                return cached > 0, cached
            # Resolve args and pool from the session's bottombar registry when the
            # caller did not pass them, so the count reads the session's database,
            # not the default one (see bottombar.py: the same fallback).
            args = kwargs.get("args")
            pool = kwargs.get("pool")
            if args is None or pool is None:
                from .. import bottombar
                reg = bottombar._resolve_registry()
                args = args if args is not None else getattr(reg, "args", None)
                pool = pool if pool is not None else getattr(reg, "pool", None)
            count = message_module.get_unread_count(
                moniker,
                args=args,
                pool=pool,
                conn=kwargs.get("conn"),
            )
            message_module.set_local_unread_count(moniker, count or 0)
            return (count or 0) > 0, count or 0
    except Exception:
        echo_traceback("bbsengine6.io.getch.333:")
    return False, 0


class BellWindow:
    """Ring once per window of ``window_seconds``, not once per session.

    The first notification opens a window and rings. Notifications that arrive
    while the window is open share that bell. The first one after it closes
    opens a new window and rings again. ``now`` is injectable for tests.
    """

    def __init__(self, window_seconds: float = 5.0) -> None:
        self.window_seconds = float(window_seconds)
        self._opened_at: Optional[float] = None
        self._lock = threading.Lock()

    def should_ring(self, now: Optional[float] = None) -> bool:
        t = time.monotonic() if now is None else now
        with self._lock:
            if self._opened_at is not None and (t - self._opened_at) < self.window_seconds:
                return False
            self._opened_at = t
            return True


_bell_window = BellWindow(5.0)

class BellBaseline:
    """Remember the unread count each moniker's last bell was based on.

    The bell rings only when the count rises above that baseline. Repeated checks
    with the same count do not ring, so a message that stays unread does not ring the
    bell every poll. A drop lowers the baseline, so a later rise rings again. The
    baseline is per process; a reconnect starts it at zero.
    """

    def __init__(self) -> None:
        self._last: dict[str, int] = {}
        self._lock = threading.Lock()

    def should_ring(self, moniker: str, count: int) -> bool:
        with self._lock:
            previous = self._last.get(moniker, 0)
            self._last[moniker] = count
            return count > previous

    def clear(self) -> None:
        with self._lock:
            self._last.clear()


_bell_baseline = BellBaseline()


def _emit_bell_for(baseline: "BellBaseline", moniker: str, count: int) -> bool:
    """Ring once when the count rises for this moniker, and only inside a free bell window.

    The baseline is updated on every call, so a drop resets it even when no bell rings.
    """
    rose = baseline.should_ring(moniker, count)
    if not rose:
        return False
    if not _bell_window.should_ring():
        return False
    echo("{bel}", end="", flush=True)
    return True




def set_bell_window_seconds(seconds: float) -> None:
    """Set the bell window (from bed.json ``notify.bell_window_seconds``)."""
    if float(seconds) < 0:
        raise ValueError("bell_window_seconds must be >= 0")
    _bell_window.window_seconds = float(seconds)


def _push_subscribed(moniker: Optional[str]) -> bool:
    """True when a bed push subscription is active for ``moniker``.

    Set by bbsengine6.startup.message_subscription on a successful
    subscribe. Checked once per wait, so a subscription made mid-session is
    picked up on the next keypress wait.
    """
    if not moniker:
        return False
    try:
        from ..startup import message_subscription as _ms

        return bool(_ms.is_subscribed(moniker))
    except Exception:
        return False


def _emit_notification_bell_once() -> bool:
    """Ring the bell at most once per notification window.

    Kept under its old name for callers. The latch is now a window: see
    :class:`BellWindow`.
    """
    if not _bell_window.should_ring():
        return False
    echo("{bel}", end="", flush=True)
    return True


def _update_bottombar_on_notification() -> bool:
    """Redraw the bottom bar's notification status when it has changed.

    The last status drawn is remembered, so an unchanged status is not redrawn, and a changed status
    (a new message, or a message read) is drawn again. Returns True if a redraw was performed.
    """
    notification_status = screen.get_notification_status()
    with _bottombar_update_lock:
        it = _interaction()
        if notification_status == it.bottombar_status:
            return False
        it.bottombar_status = notification_status

    try:
        # The status string, e.g. "F2: messages (3)".
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
    from ..message import MessageUrgency

    mapping = {
        MessageUrgency.CRITICAL: "{var:message.criticalcolor}",
        MessageUrgency.URGENT: "{var:message.urgentcolor}",
        MessageUrgency.IMPORTANT: "{var:message.importantcolor}",
        MessageUrgency.ROUTINE: "{var:message.routinecolor}",
    }
    if hasattr(urgency, "name"):
        urgency = MessageUrgency[urgency.name] if urgency.name in MessageUrgency.__members__ else urgency
    return mapping.get(urgency, "{var:message.routinecolor}")


def _show_pending_notifications(moniker: str) -> None:
    """Display pending notifications for user.

    This function displays notifications and returns immediately.
    It does NOT wait for user input—that is the caller's responsibility.
    This avoids recursive calls and keeps input handling simple.
    """
    try:
        from .. import message as message_module
        if not message_module.is_enabled():
            echo("{var:normalcolor}Messages unavailable.{/all}")
            return

        notifications = message_module.get_queue(moniker)

        if not notifications:
            echo("{var:normalcolor}No pending messages.{/all}")
            return

        # Display each notification with colors from echo vars
        for n in notifications:
            urgency_str = n.get("urgency", "ROUTINE")
            urgency_color = _get_urgency_color(urgency_str)
            timestamp = n.get("datestamp")
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp_str = timestamp
                else:
                    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp_str = ""
            recipient = n.get("sender_moniker", "Unknown")
            content = n.get("content", "")

            echo(
                f"{urgency_color}[{urgency_str}]{{/all}} {{var:message.datestampcolor}}{timestamp_str}{{/all}}"
            )
            echo(f"{{var:message.recipientcolor}}From:{{/all}} {recipient}")
            echo(f"{content}")
            echo("{var:normalcolor}" + "─" * 40 + "{/all}")

        echo("{var:normalcolor}Press any key to continue...{/all}")

    except Exception as e:
        echo(f"{{var:normalcolor}}Error displaying messages: {e}{{/all}}")


# ============================================================================
# GETCH IMPLEMENTATION
# ============================================================================

# def _read():
#    if _input_queue:
#        return _input_queue.popleft()
#    return _current_input_stream.read(1)


def resolve_escape_sequence(sequence: str, debug: bool = False) -> str | None:
    """Map a complete escape sequence to a key name (shared by both readers).

    Args:
        sequence: The bytes read after and including ESC (length >= 2).
        debug: If True, log unknown sequences and return None.

    Returns:
        KEY_MAP name, or the raw sequence when unknown (None when debug=True).
    """
    # Sort keys by length descending to match longest possible sequence first
    for code, name in sorted(KEY_MAP.items(), key=lambda item: len(item[0]), reverse=True):
        if sequence.endswith(code):
            return name
    if debug:
        logentry(f"unknown escape sequence: {sequence!r}")
        return None
    return sequence


ESC_TAIL_WAIT = 0.05  # seconds to wait for the rest of a split escape sequence


def _read_escape_tail() -> str:
    """Return ESC plus the rest of its sequence, waiting briefly for split bytes.

    A terminal may deliver ESC [ C in separate wakeups. Reading only what is
    already available would leave "[C" behind as text, so after a lone ESC we
    wait up to ESC_TAIL_WAIT for each following byte. The sequence ends at the
    first final byte (0x40-0x7e) after a CSI ("[") or SS3 ("O") introducer.
    A bare ESC followed by nothing stays a bare ESC.
    """
    seq = ESC
    deadline = time.time() + ESC_TAIL_WAIT
    while len(seq) < 10:
        # Bytes already drained into the queue belong to this sequence too.
        with _input_queue_lock:
            queued = _input_queue.popleft() if _input_queue else None
        if queued is not None:
            nxt = queued
        else:
            try:
                nxt = _read_current_input_stream()
            except BlockingIOError:
                if time.time() >= deadline:
                    break
                time.sleep(0.005)
                continue
        seq += nxt
        deadline = time.time() + ESC_TAIL_WAIT
        if len(seq) == 2 and nxt not in ("[", "O"):
            # Not a CSI/SS3 sequence: this is a lone ESC followed by a key.
            # Give the key back to the input queue so it is read as its own key.
            with _input_queue_lock:
                _input_queue.appendleft(nxt)
            return ESC
        if len(seq) >= 3 and 0x40 <= ord(nxt) <= 0x7E:
            break  # final byte of the CSI/SS3 sequence
    return seq


PASTE_START = f"{ESC}[200~"
PASTE_END = f"{ESC}[201~"
PASTE_MAX = 65536  # bytes of paste body kept; longer pastes are cut here


def _read_bracketed_paste() -> str:
    """Collect a bracketed-paste body up to ESC[201~ and return it as "PASTE:<text>".

    Called after ESC[200~ has been read. The body is read from the queue first,
    then the stream, so a paste split across reads is collected whole. A paste
    with no end marker is returned with what arrived, after a short wait.
    """
    body = ""
    deadline = time.time() + max(ESC_TAIL_WAIT, 0.2)
    while len(body) < PASTE_MAX:
        if body.endswith(PASTE_END):
            body = body[: -len(PASTE_END)]
            break
        with _input_queue_lock:
            queued = _input_queue.popleft() if _input_queue else None
        if queued is not None:
            body += queued
            deadline = time.time() + max(ESC_TAIL_WAIT, 0.2)
            continue
        try:
            body += _read_current_input_stream()
            deadline = time.time() + max(ESC_TAIL_WAIT, 0.2)
        except BlockingIOError:
            if time.time() >= deadline:
                break
            time.sleep(0.005)
    return "PASTE:" + body


def _getch_from_queue(debug: bool, fire_events: bool, source_func: str) -> str | None:
    """Return the next key from _input_queue (caller holds _current_stream_lock)."""
    char = _input_queue.popleft()
    if char == ESC:
        return _resolve_queued_escape(
            debug=debug, fire_events=fire_events, source_func=source_func
        )
    return _proc_char(char, debug=debug, fire_events=fire_events, source_func=source_func)


# Event names for keys that have a meaning in the application. The key the reader returns
# is unchanged (KEY_F1, KEY_F2), so existing callers keep working; only the processed name
# on the event is changed. KEY_F1 is help; KEY_F2 is the messages key.
EVENT_KEY_ALIASES = {"KEY_F1": "KEY_HELP", "KEY_F2": "KEY_MESSAGES"}


def _push_key_event(char: str, processed, stage: str, source_func: str) -> None:
    """Push one key event to the dispatcher when it is running.

    Shared by the streamed path (_proc_char) and the queued escape path, so the two can
    not drift apart again: a queued escape previously returned without firing either event.
    """
    if not _event_dispatcher.is_running():
        return
    processed = EVENT_KEY_ALIASES.get(processed, processed) if isinstance(processed, str) else processed
    _event_dispatcher.push_event(
        KeyEvent(
            raw_char=char,
            processed_key=processed,
            timestamp=time.time(),
            stage=stage,
            source_func=source_func,
        )
    )


def _resolve_queued_escape(
    debug: bool = False, fire_events: bool = True, source_func: str = "getch_str"
) -> str | None:
    """Resolve an ESC whose following bytes are already in _input_queue.

    Caller holds _current_stream_lock. Consumes exactly one sequence from the
    queue: a CSI/SS3 sequence through its final byte, a lone ESC followed by
    a key (returns KEY_ESC and leaves the key queued), or a bare ESC.
    """
    with _input_queue_lock:
        queued = list(_input_queue)
    end = _escape_end_queue(queued)
    if end == 1:
        processed = "KEY_ESC"
        seq = ESC
    else:
        seq = ESC + "".join(queued[: end - 1])
        with _input_queue_lock:
            for _ in range(end - 1):
                _input_queue.popleft()
        if seq == PASTE_START:
            processed = _read_bracketed_paste()
        else:
            processed = resolve_escape_sequence(seq, debug=debug)
    if fire_events:
        _push_key_event(seq, processed, "raw", source_func)
        _push_key_event(seq, processed, "processed", source_func)
    return processed


def _escape_end_queue(chars: list) -> int:
    """Return the length of the escape sequence after a queued ESC (1 = lone ESC)."""
    if not chars:
        return 1
    if chars[0] not in ("[", "O"):
        return 1
    for j in range(1, min(len(chars), 9)):
        if 0x40 <= ord(chars[j]) <= 0x7E and j >= 1:
            return j + 2
    return min(len(chars), 10) + 1 if len(chars) >= 9 else 1


def _proc_char(
    char: str,
    debug: bool = False,
    fire_events: bool = True,
    source_func: str = "getch_str",
) -> str | None:
    """Process character and optionally fire events.

    Shared by getch_str() and getch_utf8(). The ESC branch here reads the
    remaining bytes from the stream, then resolves them via
    resolve_escape_sequence(). getch_utf8() does not use this branch; it
    resolves its own sequences through the same helper.

    Args:
        char: Raw character to process
        debug: If True, log unknown escape sequences
        fire_events: If True and dispatcher running, fire key events
        source_func: Label recorded on emitted KeyEvents

    Returns:
        Processed key name or character, or None for unknown sequences when debug=True
    """
    # Fire raw event before processing
    if fire_events:
        _push_key_event(char, None, "raw", source_func)

    # Initialize processed (will be set in all non-exception paths)
    processed: str | None = None

    # 3. Handle Control Characters
    if char == "\x01":
        processed = "KEY_CTRL_A"
    elif char == ETX:  # Ctrl+C (ETX)
        _restore_tty()
        raise KeyboardInterrupt
    elif char == EOF:  # Ctrl+D (EOF)
        _restore_tty()
        raise EOFError
    elif char == "\x05":  # ctrl-e (EOL)
        processed = "KEY_CTRL_E"
    elif char in ("\x7f", "\x08"):
        processed = "KEY_BACKSPACE"
    elif char == "\r":
        processed = "KEY_ENTER"
    elif char == "\x15":  # ctrl-u
        processed = "KEY_CUTTOBOL"
    elif char == "\x17":  # ctrl-w: cut previous word
        processed = "KEY_CTRL_W"
    elif char == "\x19":  # ctrl-y: yank (paste) the cut buffer
        processed = "KEY_YANK"
    elif char == "\t":
        processed = "KEY_TAB"
    # 4. Handle Escape Sequences and Plain ESC
    elif char == ESC:  # ESCAPE
        sequence = _read_escape_tail()

        if sequence == PASTE_START:
            processed = _read_bracketed_paste()
        # A. Check for plain ESC
        elif len(sequence) == 1:
            processed = (
                "KEY_ESC"  # Plain ESC key was pressed (as no other bytes followed)
            )
        else:
            # B/C. Known sequence -> key name; unknown -> raw sequence (or None in debug)
            processed = resolve_escape_sequence(sequence, debug=debug)
    # 5. Return a regular character
    else:
        processed = char

    # Fire processed event after processing
    if fire_events:
        _push_key_event(char, processed, "processed", source_func)

    return processed


def _getch_core(
    reader: "Callable[[], str]",
    source_func: str,
    pending: "Callable[[], str | None] | None" = None,
    timeout: float = 1.0,
    debug: bool = False,
    fire_events: bool = True,
    check_notifications: bool = True,
    idle: "Callable[[], None] | None" = None,
    **kwargs,
) -> str | None:
    """Shared wait/tty/notification/dispatch logic for getch_str and getch_utf8.

    reader() returns the next raw character (already decoded) and raises
    BlockingIOError when no input is available. source_func labels events.

    Args:
        timeout: Seconds to wait for input (default: 1.0). Uses wall-clock time for accuracy.
        debug: If True, log unknown escape sequences and return None
        fire_events: If True, fire key events if dispatcher is running
        check_notifications: If True, check for notifications and emit bell (default: True)
        idle: Optional callback called on idle (timeout) (default: None)
            Called each time getch_str() times out waiting for input.
            Useful for updating status displays, checking notifications, etc.

    Returns:
        Processed key name (e.g., 'a', 'KEY_UP', 'KEY_ENTER'), or None on timeout.
        Note: F2 key returns "KEY_F2" (caller can handle notifications if desired).

    Timeout Accuracy:
        Timeout is measured using wall-clock time (time.time()) to ensure precision.
        During an open-ended wait (timeout=None) the function polls
        message.get_unread_count() every 2s so the bottombar's "(N)"
        indicator stays fresh without hammering the DB. For finite
        timeouts, no mid-wait poll is performed: the outer wait itself
        is the bound, and the next keypress triggers a fresh check via
        the pre-wait path. A future change could swap the open-ended-wait
        poll for bed server-push (see bbsengine6.startup.message_subscription);
        that integration is not wired
        in the live source tree today, so the open-ended-wait poll above
        is the active mechanism.
    """
    moniker = None
    if _has_member_module:
        moniker = getattr(_threadlocal, "moniker", None)

    with _current_stream_lock:
        # Keys typed or pasted before raw mode are still in the line discipline.
        # tty.setraw() discards them, so take them now, while the tty is cooked.
        # Queued in arrival order; readers consume _input_queue before waiting.
        drain_stream_to_queue(_common._current_input_stream, _input_queue)

        if _input_queue:
            char = _input_queue.popleft()
            if char == ESC:
                # The whole sequence may already be queued (drained before raw
                # mode). Take it from the queue in one step, not byte by byte.
                return _resolve_queued_escape(
                    debug=debug, fire_events=fire_events, source_func=source_func
                )
            result = _proc_char(
                char, debug=debug, fire_events=fire_events, source_func=source_func
            )
            return result

        # Characters already drained from the stream by a previous call (UTF-8
        # reader) are returned without waiting: select() cannot see them.
        if pending is not None:
            queued = pending()
            if queued is not None:
                return queued

        # Get file descriptor and settings while holding lock
        fd = _common._current_input_stream.fileno()
        old_settings = termios.tcgetattr(fd)

    # Store settings globally for signal handler
    global _global_tty_settings, _global_tty_fd
    _global_tty_fd = fd
    _global_tty_settings = old_settings

    # Set terminal to raw mode while holding lock briefly (skipped inside a raw session)
    if not _in_raw_session():
        with _current_stream_lock:
            try:
                tty.setraw(fd)
            except Exception:
                _restore_cooked(fd, old_settings)
                raise

    # The pre-wait notification check runs with the tty already raw. A key sent while the check is
    # slow (a database read) is then available to the wait below, instead of sitting in a cooked line
    # buffer until a newline arrives.
    if check_notifications and moniker:
        has_notifications, notification_count = _check_notifications(moniker, **_check_kwargs(kwargs))
        _emit_bell_for(_bell_baseline, moniker, notification_count)
        if has_notifications:
            _update_bottombar_on_notification()

    try:
        # 2. Wait for input using wall-clock timeout for accuracy
        # Lock is released during select() to allow other threads (like echo) to proceed
        start_time = time.time()
        # Notification poll cadence. 2.0s is intentionally loose: the goal
        # is to keep the bottombar's "(N)" indicator fresh during a long
        # idle wait (timeout=None) without hammering the DB. When the
        # caller passes a finite timeout, we just block for the whole
        # timeout -- no mid-wait poll -- because the outer wait is short
        # and a notification check at the next keypress is sufficient.
        # The pre-wait check above (before this loop) covers the
        # "first wait" case so a notification that arrived before the
        # user pressed any key still lights up the bottombar.
        ready = []
        wake_fd = _msg_cache.change_wake_fd()
        # DB poll cadence, used only when no bed push is subscribed for this
        # process (Step 0 fallback). With a push subscription the wait is
        # fully event-driven and this does not apply.
        poll_interval = 2.0
        push_active = _push_subscribed(moniker)

        while True:
            # Calculate elapsed time and remaining timeout
            elapsed = time.time() - start_time
            if timeout is not None and elapsed >= timeout:
                _restore_cooked(fd, old_settings)
                if callable(idle):
                    idle()
                return None

            # Calculate timeout for select
            if timeout is None:
                select_timeout = poll_interval
            else:
                remaining = timeout - elapsed
                select_timeout = remaining if remaining > 0 else 0

            # Wait on stdin and the message-cache wake pipe (LOCK RELEASED HERE).
            # With a push subscription, a count change wakes us immediately.
            # Without one, cap the wait at the DB poll cadence.
            wait_for = select_timeout
            if timeout is None and not push_active:
                wait_for = min(select_timeout, poll_interval)
            # Text-wrapper bytes are invisible to select(); take them into the
            # queue first so a key already read from the fd is not left waiting.
            with _current_stream_lock:
                drain_stream_to_queue(_common._current_input_stream, _input_queue)
            if _input_queue:
                return _getch_from_queue(debug=debug, fire_events=fire_events, source_func=source_func)
            ready, _, _ = select.select(
                [_common._current_input_stream, wake_fd], [], [], wait_for
            )

            if _common._current_input_stream in ready:
                break

            if not ready:
                # Nothing readable: either the finite timeout expired (the loop
                # top returns), or the DB poll cadence elapsed with no bed push.
                if timeout is None and not push_active and check_notifications and moniker:
                    has_notifications, poll_count = _check_notifications(moniker, **_check_kwargs(kwargs))
                    _emit_bell_for(_bell_baseline, moniker, poll_count)
                    if has_notifications:
                        _update_bottombar_on_notification()
                continue

            # The cache changed. Drain the wake, then react from the cache
            # only (no DB query on the wake path). Bell at most once per
            # window; refresh the bottombar.
            _msg_cache.drain_change_wake()
            if check_notifications and moniker:
                count = _msg_cache.get_local_unread_count(moniker)
                _emit_bell_for(_bell_baseline, moniker, count)
                if count > 0:
                    _update_bottombar_on_notification()
            continue

        # Input is available - acquire lock for reading and processing
        with _current_stream_lock:
            # 3. Set Non-Blocking I/O for escape sequence reading
            old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)

            # Take everything the stream has (a split escape sequence arrives in
            # pieces) into the ordered queue, then consume one key from it.
            drain_stream_to_queue(_common._current_input_stream, _input_queue)
            if not _input_queue:
                if old_flags is not None:
                    fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)
                _restore_cooked(fd, old_settings)
                return None

            result = _getch_from_queue(
                debug=debug, fire_events=fire_events, source_func=source_func
            )

            # Restore flags and terminal settings before releasing lock
            if old_flags is not None:
                fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)
            _restore_cooked(fd, old_settings)

            return result

    finally:
        _restore_tty()



# ============================================================================
# PUBLIC READERS: getch_str (existing) and getch_utf8 (new), plus selector
# ============================================================================

# Default reader for getch() when impl= is not given. Per interaction: see _getch_impl().
_GETCH_IMPLS = ("str", "utf8")

# Decoded characters the UTF-8 reader has not returned yet. Per interaction (they belong to
# one input stream). Guarded by _current_stream_lock (held by _getch_core around the read).


def _interaction():
    """The interaction in effect for this context (see bbsengine6.interaction)."""
    from ..interaction import current_session

    return current_session()


def _utf8_pending() -> "deque[str]":
    return _interaction().utf8_pending


def _getch_impl() -> str:
    return _interaction().getch_impl


def _bottombar_status() -> str:
    return _interaction().bottombar_status


def set_getch_impl(name: str) -> None:
    """Set the default reader used by getch() when impl= is not given.

    Args:
        name: "str" (byte-at-a-time, existing default) or "utf8" (drain and decode).
    """
    if name not in _GETCH_IMPLS:
        raise ValueError(f"unknown getch impl {name!r}; expected one of {_GETCH_IMPLS}")
    _interaction().getch_impl = name


def get_getch_impl() -> str:
    """Return the current default reader name."""
    return _getch_impl()


def _read_one_str() -> str:
    """getch_str reader: one character from the current input stream."""
    return _read_current_input_stream()


def _pop_utf8_pending() -> str | None:
    """Return the next already-drained key, or None if none is queued.

    Queued entries are fully resolved key names (ESC sequences are mapped by
    _read_drained_utf8), so they are returned as-is.
    """
    pending = _utf8_pending()
    if pending:
        return pending.popleft()
    return None


def _read_drained_utf8() -> str:
    """getch_utf8 reader: return the next decoded character.

    Drains every character the stream can return without blocking into
    _utf8_pending, then returns them one at a time. Reading stream.read(1)
    keeps the text wrapper's own buffer intact, so no bytes are skipped.
    Raises BlockingIOError when nothing is available.
    """
    pending = _utf8_pending()
    if pending:
        return pending.popleft()

    stream = _common._current_input_stream
    # The fd is non-blocking while _getch_core reads, so stream.read(1) returns
    # promptly with BlockingIOError (or an empty read) once input is exhausted.
    raw: list[str] = []
    while True:
        try:
            ch = stream.read(1)
        except BlockingIOError:
            break
        if not ch:
            break
        raw.append(ch)

    if not raw:
        raise BlockingIOError

    # Resolve ESC sequences here so the queue only holds final key names.
    i = 0
    while i < len(raw):
        if raw[i] != ESC:
            _utf8_pending().append(raw[i])
            i += 1
            continue
        end = _escape_end(raw, i)
        if end == i + 1:
            _utf8_pending().append("KEY_ESC")
        else:
            seq = "".join(raw[i:end])
            _utf8_pending().append(resolve_escape_sequence(seq) or seq)
        i = end

    return _utf8_pending().popleft()


def _escape_end(chars: list[str], start: int) -> int:
    """Return the index just past the escape sequence beginning at chars[start].

    CSI (ESC [) and SS3 (ESC O) sequences end at the first final byte in
    0x40-0x7e. Anything else is ESC plus at most one following character.
    Bounded to 10 characters, matching getch_str.
    """
    if start + 1 >= len(chars):
        return start + 1
    if chars[start + 1] not in ("[", "O"):
        return start + 2 if start + 2 <= len(chars) else start + 1
    limit = min(len(chars), start + 10)
    for j in range(start + 2, limit):
        if 0x40 <= ord(chars[j]) <= 0x7E:
            return j + 1
    return limit


def getch_str(
    timeout: float = 1.0,
    debug: bool = False,
    fire_events: bool = True,
    check_notifications: bool = True,
    idle: "Callable[[], None] | None" = None,
    impl: "str | None" = None,
    **kwargs,
) -> str | None:
    """Read one key with the byte-at-a-time reader (existing behavior).

    impl: Optional override "str" or "utf8" for this call. Default is the
    runtime setting from set_getch_impl(). Passing "utf8" here routes the call
    through the UTF-8 reader; source_func is still "getch_str" when impl is
    "str" and "getch_utf8" when routed to the UTF-8 reader.
    """
    if impl is None:
        impl = _getch_impl()
    if impl == "utf8":
        return getch_utf8(
            timeout=timeout, debug=debug, fire_events=fire_events,
            check_notifications=check_notifications, idle=idle, **kwargs,
        )
    if impl != "str":
        raise ValueError(f"unknown getch impl {impl!r}")
    return _getch_core(
        _read_one_str,
        "getch_str",
        timeout=timeout,
        debug=debug,
        fire_events=fire_events,
        check_notifications=check_notifications,
        idle=idle,
        **kwargs,
    )


def getch_utf8(
    timeout: float = 1.0,
    debug: bool = False,
    fire_events: bool = True,
    check_notifications: bool = True,
    idle: "Callable[[], None] | None" = None,
    impl: "str | None" = None,
    **kwargs,
) -> str | None:
    """Read one key with the drain-and-decode reader.

    Same return contract as getch_str(). Emits events with source_func="getch_utf8".
    impl is accepted for signature symmetry and ignored here.
    """
    return _getch_core(
        _read_drained_utf8,
        "getch_utf8",
        pending=_pop_utf8_pending,
        timeout=timeout,
        debug=debug,
        fire_events=fire_events,
        check_notifications=check_notifications,
        idle=idle,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Per-interaction names: read through the current interaction (Phase 3).
#
# `_bottombar_updated_this_session` and `_GETCH_IMPL` were module globals. They now live on
# the interaction; the module-level names read and write that field, so code and tests that
# use them keep working.
# ---------------------------------------------------------------------------
from ..interaction import install_read_through as _install_read_through  # noqa: E402

_install_read_through(
    __name__,
    {
        "_bottombar_updated_this_session": "bottombar_status",
        "_GETCH_IMPL": "getch_impl",
    },
)
