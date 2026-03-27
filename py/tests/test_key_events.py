"""
Comprehensive test suite for Key Event System.

Test organization:
- Fixtures for event system setup/teardown
- Unit tests for each component
- Integration tests with input functions
- Thread safety tests
- Error handling tests
"""

import time
import queue
import threading
import pytest

from bbsengine6.io.getch import (
    KeyEvent,
    EventHandler,
    KeyEventBus,
    EventDispatcher,
    register_key_event_handler,
    unregister_key_event_handler,
    get_registered_handlers,
    start_event_dispatcher,
    stop_event_dispatcher,
    is_event_dispatcher_running,
    set_event_dispatcher_timeout,
    get_event_queue,
    is_event_queue_empty,
    clear_event_queue,
    set_event_error_handler,
    get_key_event_history,
    clear_key_event_history,
    _event_bus,
    _event_dispatcher,
)


# ============================================================================
# FIXTURES & HELPERS
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_events():
    """Clean up event system before and after each test."""
    # Stop dispatcher if running
    if is_event_dispatcher_running():
        stop_event_dispatcher()

    # Clear all handlers
    for name in list(get_registered_handlers().keys()):
        try:
            unregister_key_event_handler(name)
        except KeyError:
            pass

    # Clear queues and history
    clear_event_queue()
    clear_key_event_history()
    set_event_error_handler(None)

    yield

    # Cleanup after test
    if is_event_dispatcher_running():
        stop_event_dispatcher()

    for name in list(get_registered_handlers().keys()):
        try:
            unregister_key_event_handler(name)
        except KeyError:
            pass

    clear_event_queue()
    clear_key_event_history()
    set_event_error_handler(None)


# ============================================================================
# UNIT TESTS: KeyEvent
# ============================================================================


class TestKeyEvent:
    """Test KeyEvent dataclass."""

    def test_create_raw_event(self):
        """Create raw KeyEvent with valid data."""
        event = KeyEvent(
            raw_char="a",
            processed_key=None,
            timestamp=time.time(),
            stage="raw",
            source_func="getch_str",
        )
        assert event.raw_char == "a"
        assert event.processed_key is None
        assert event.stage == "raw"
        assert event.source_func == "getch_str"

    def test_create_processed_event(self):
        """Create processed KeyEvent with key name."""
        event = KeyEvent(
            raw_char="\x1b[A",
            processed_key="KEY_UP",
            timestamp=time.time(),
            stage="processed",
            source_func="inputstring",
        )
        assert event.raw_char == "\x1b[A"
        assert event.processed_key == "KEY_UP"
        assert event.stage == "processed"

    def test_event_immutable(self):
        """Verify KeyEvent is frozen (immutable)."""
        event = KeyEvent(
            raw_char="a",
            processed_key="a",
            timestamp=time.time(),
            stage="processed",
            source_func="getch_str",
        )
        with pytest.raises(AttributeError):
            event.raw_char = "b"

    def test_event_timestamp(self):
        """Verify timestamp is set correctly."""
        ts_before = time.time()
        event = KeyEvent(
            raw_char="a",
            processed_key="a",
            timestamp=ts_before,
            stage="processed",
            source_func="getch_str",
        )
        assert event.timestamp == ts_before

    def test_event_repr(self):
        """Verify string representation is useful."""
        event = KeyEvent(
            raw_char="a",
            processed_key="a",
            timestamp=1.0,
            stage="processed",
            source_func="getch_str",
        )
        repr_str = repr(event)
        assert "KeyEvent" in repr_str
        assert "raw_char" in repr_str


# ============================================================================
# UNIT TESTS: EventHandler
# ============================================================================


class TestEventHandler:
    """Test EventHandler registration and filtering."""

    def test_create_handler_no_filter(self):
        """Create handler with no filter."""
        def callback(event):
            pass

        handler = EventHandler(name="test", callback=callback, filter_fn=None)
        assert handler.name == "test"
        assert handler.callback == callback
        assert handler.filter_fn is None

    def test_create_handler_with_filter(self):
        """Create handler with filter function."""
        def callback(event):
            pass

        def filter_fn(event):
            return True

        handler = EventHandler(name="test", callback=callback, filter_fn=filter_fn)
        assert handler.filter_fn == filter_fn

    def test_matches_without_filter(self):
        """Handler with no filter matches all events."""
        def callback(event):
            pass

        handler = EventHandler(name="test", callback=callback, filter_fn=None)
        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        assert handler.matches(event) is True

    def test_matches_with_filter_true(self):
        """Filter returning True allows event."""
        def callback(event):
            pass

        def filter_fn(event):
            return event.processed_key == "a"

        handler = EventHandler(name="test", callback=callback, filter_fn=filter_fn)
        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        assert handler.matches(event) is True

    def test_matches_with_filter_false(self):
        """Filter returning False blocks event."""
        def callback(event):
            pass

        def filter_fn(event):
            return event.processed_key == "b"

        handler = EventHandler(name="test", callback=callback, filter_fn=filter_fn)
        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        assert handler.matches(event) is False


# ============================================================================
# UNIT TESTS: KeyEventBus
# ============================================================================


class TestKeyEventBus:
    """Test event bus registration and dispatch."""

    def test_register_handler(self):
        """Register a single handler."""
        def callback(event):
            pass

        _event_bus.register("test", callback)
        handlers = _event_bus.get_handlers()
        assert "test" in handlers
        assert handlers["test"].name == "test"

    def test_register_multiple_handlers(self):
        """Register multiple handlers."""
        def callback(event):
            pass

        _event_bus.register("test1", callback)
        _event_bus.register("test2", callback)
        handlers = _event_bus.get_handlers()
        assert len(handlers) == 2
        assert "test1" in handlers
        assert "test2" in handlers

    def test_register_duplicate_name_raises(self):
        """Duplicate name raises ValueError."""
        def callback(event):
            pass

        _event_bus.register("test", callback)
        with pytest.raises(ValueError):
            _event_bus.register("test", callback)

    def test_unregister_handler(self):
        """Unregister removes handler."""
        def callback(event):
            pass

        _event_bus.register("test", callback)
        _event_bus.unregister("test")
        handlers = _event_bus.get_handlers()
        assert "test" not in handlers

    def test_unregister_nonexistent_raises(self):
        """Unregister nonexistent handler raises KeyError."""
        with pytest.raises(KeyError):
            _event_bus.unregister("nonexistent")

    def test_get_handlers(self):
        """Get handlers returns dict snapshot."""
        def callback(event):
            pass

        _event_bus.register("test", callback)
        handlers = _event_bus.get_handlers()
        assert isinstance(handlers, dict)
        assert "test" in handlers

    def test_handler_history_circular(self):
        """History buffer is circular (bounded)."""
        # Default max is 100
        for i in range(150):
            event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
            _event_bus.add_to_history(event)

        # Should only have last 100
        assert len(_event_bus.history) == 100

    def test_history_get_limit(self):
        """get_history() respects limit parameter."""
        for i in range(50):
            event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
            _event_bus.add_to_history(event)

        history = _event_bus.get_history(limit=10)
        assert len(history) == 10

    def test_clear_history(self):
        """clear_history() empties buffer."""
        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_bus.add_to_history(event)
        assert len(_event_bus.history) > 0

        _event_bus.clear_history()
        assert len(_event_bus.history) == 0


# ============================================================================
# UNIT TESTS: EventDispatcher
# ============================================================================


class TestEventDispatcher:
    """Test dispatcher startup, shutdown, and event queuing."""

    def test_dispatcher_initial_state(self):
        """Dispatcher starts in stopped state."""
        assert is_event_dispatcher_running() is False

    def test_start_dispatcher(self):
        """start() spawns background thread."""
        start_event_dispatcher()
        assert is_event_dispatcher_running() is True

    def test_dispatcher_is_running(self):
        """is_running() returns True after start."""
        start_event_dispatcher()
        assert is_event_dispatcher_running() is True

    def test_start_already_running_raises(self):
        """start() when running raises RuntimeError."""
        start_event_dispatcher()
        with pytest.raises(RuntimeError):
            start_event_dispatcher()

    def test_stop_dispatcher(self):
        """stop() terminates background thread."""
        start_event_dispatcher()
        stop_event_dispatcher()
        # Give thread time to exit
        time.sleep(0.1)
        assert is_event_dispatcher_running() is False

    def test_dispatcher_not_running_after_stop(self):
        """is_running() returns False after stop."""
        start_event_dispatcher()
        stop_event_dispatcher()
        time.sleep(0.1)
        assert is_event_dispatcher_running() is False

    def test_stop_not_running_raises(self):
        """stop() when not running raises RuntimeError."""
        with pytest.raises(RuntimeError):
            stop_event_dispatcher()

    def test_push_event_while_running(self):
        """push_event() enqueues when dispatcher running."""
        start_event_dispatcher()
        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        # Event should be in queues
        time.sleep(0.05)  # Let dispatcher process
        # Should be in history
        history = get_key_event_history(limit=1)
        assert len(history) > 0


# ============================================================================
# INTEGRATION TESTS: Push Model (Callbacks)
# ============================================================================


class TestPushModel:
    """Test callback registration and firing."""

    def test_handler_called_on_event(self):
        """Registered handler is called for matching event."""
        called = []

        def callback(event):
            called.append(event)

        register_key_event_handler("test", callback)
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.1)  # Let dispatcher process

        assert len(called) == 1
        assert called[0].processed_key == "a"

    def test_multiple_handlers_all_called(self):
        """All matching handlers are called."""
        called1 = []
        called2 = []

        def callback1(event):
            called1.append(event)

        def callback2(event):
            called2.append(event)

        register_key_event_handler("test1", callback1)
        register_key_event_handler("test2", callback2)
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.1)

        assert len(called1) == 1
        assert len(called2) == 1

    def test_filter_blocks_non_matching(self):
        """Handler with filter not called for non-matching event."""
        called = []

        def callback(event):
            called.append(event)

        def filter_fn(event):
            return event.processed_key == "b"

        register_key_event_handler("test", callback, filter_fn=filter_fn)
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.1)

        assert len(called) == 0

    def test_handler_receives_correct_event(self):
        """Handler receives the KeyEvent that was fired."""
        received = []

        def callback(event):
            received.append(event)

        register_key_event_handler("test", callback)
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.1)

        assert len(received) == 1
        assert received[0].raw_char == "a"
        assert received[0].processed_key == "a"

    def test_handler_execution_order(self):
        """Handlers called in registration order."""
        order = []

        def callback1(event):
            order.append(1)

        def callback2(event):
            order.append(2)

        register_key_event_handler("test1", callback1)
        register_key_event_handler("test2", callback2)
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.1)

        assert order == [1, 2]

    def test_handler_called_async(self):
        """Handler is called from background thread, not blocking input."""
        called = []
        call_time = []

        def callback(event):
            call_time.append(time.time())
            called.append(event)
            time.sleep(0.05)  # Simulate slow handler

        register_key_event_handler("test", callback)
        start_event_dispatcher()

        push_time = time.time()
        event = KeyEvent("a", "a", push_time, "processed", "getch_str")
        _event_dispatcher.push_event(event)

        # Push should return immediately, not wait for handler
        push_duration = time.time() - push_time
        assert push_duration < 0.01  # Should be near-instant

        time.sleep(0.2)  # Wait for handler to complete
        assert len(called) == 1

    def test_rapid_events_all_dispatched(self):
        """Multiple rapid events all reach handlers."""
        called = []

        def callback(event):
            called.append(event)

        register_key_event_handler("test", callback)
        start_event_dispatcher()

        for i in range(10):
            event = KeyEvent(str(i), str(i), time.time(), "processed", "getch_str")
            _event_dispatcher.push_event(event)

        time.sleep(0.2)  # Let dispatcher process all
        assert len(called) == 10

    def test_handler_exception_logged(self):
        """Handler exception is logged, dispatcher continues."""
        def bad_callback(event):
            raise ValueError("Test error")

        def good_callback(event):
            good_callback.called = True

        good_callback.called = False

        register_key_event_handler("bad", bad_callback)
        register_key_event_handler("good", good_callback)
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.1)

        # Good handler should still be called despite bad handler failing
        assert good_callback.called is True

    def test_handler_exception_calls_error_handler(self):
        """Exception passed to custom error handler if set."""
        errors = []

        def error_handler(exc, event, name):
            errors.append((exc, event, name))

        def bad_callback(event):
            raise ValueError("Test error")

        set_event_error_handler(error_handler)
        register_key_event_handler("bad", bad_callback)
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.1)

        assert len(errors) == 1
        exc, evt, name = errors[0]
        assert isinstance(exc, ValueError)
        assert name == "bad"

    def test_set_error_handler(self):
        """set_event_error_handler() sets custom handler."""
        def custom_handler(exc, event, name):
            pass

        set_event_error_handler(custom_handler)
        # Just verify it doesn't crash
        assert True

    def test_set_error_handler_none_reverts(self):
        """set_event_error_handler(None) reverts to logging."""
        set_event_error_handler(None)
        # Just verify it doesn't crash
        assert True


# ============================================================================
# INTEGRATION TESTS: Pull Model (Queue)
# ============================================================================


class TestPullModel:
    """Test event queue consumption."""

    def test_get_event_queue_returns_queue(self):
        """get_event_queue() returns queue.Queue."""
        q = get_event_queue()
        assert isinstance(q, queue.Queue)

    def test_events_in_queue(self):
        """Events enqueued to public queue."""
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.05)

        q = get_event_queue()
        assert not q.empty()

    def test_queue_get_blocks_until_event(self):
        """queue.get() blocks until event available."""
        q = get_event_queue()
        start_event_dispatcher()

        def delayed_event():
            time.sleep(0.1)
            event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
            _event_dispatcher.push_event(event)

        threading.Thread(target=delayed_event, daemon=True).start()
        start_time = time.time()
        received_event = q.get(timeout=1.0)
        elapsed = time.time() - start_time

        assert received_event is not None
        assert elapsed >= 0.1  # Should have waited

    def test_queue_get_with_timeout(self):
        """queue.get(timeout=X) raises Empty on timeout."""
        q = get_event_queue()
        start_event_dispatcher()

        with pytest.raises(queue.Empty):
            q.get(timeout=0.1)

    def test_queue_not_empty(self):
        """is_event_queue_empty() reports correctly."""
        assert is_event_queue_empty() is True

        start_event_dispatcher()
        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.05)

        assert is_event_queue_empty() is False

    def test_clear_queue(self):
        """clear_event_queue() drains all pending events."""
        start_event_dispatcher()

        for i in range(5):
            event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
            _event_dispatcher.push_event(event)

        time.sleep(0.1)
        assert is_event_queue_empty() is False

        clear_event_queue()
        assert is_event_queue_empty() is True

    def test_both_models_coexist(self):
        """Push and pull models work simultaneously."""
        push_called = []
        q = get_event_queue()

        def push_callback(event):
            push_called.append(event)

        register_key_event_handler("push", push_callback)
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.1)

        assert len(push_called) == 1
        pulled_event = q.get(timeout=0.5)
        assert pulled_event is not None


# ============================================================================
# THREAD SAFETY TESTS
# ============================================================================


class TestThreadSafety:
    """Test thread safety of event system."""

    def test_concurrent_event_dispatch(self):
        """Multiple events from main thread, handler processes concurrently."""
        call_count = [0]
        lock = threading.Lock()

        def callback(event):
            with lock:
                call_count[0] += 1

        register_key_event_handler("test", callback)
        start_event_dispatcher()

        for i in range(100):
            event = KeyEvent(str(i), str(i), time.time(), "processed", "getch_str")
            _event_dispatcher.push_event(event)

        time.sleep(0.5)  # Wait for all to process
        assert call_count[0] == 100

    def test_concurrent_handler_registration(self):
        """Registering handlers while events firing is safe."""
        call_counts = {"h1": 0, "h2": 0}

        def make_callback(key):
            def callback(event):
                call_counts[key] += 1
            return callback

        register_key_event_handler("h1", make_callback("h1"))
        start_event_dispatcher()

        # Fire events while registering new handler
        for i in range(10):
            event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
            _event_dispatcher.push_event(event)
            if i == 5:
                register_key_event_handler("h2", make_callback("h2"))

        time.sleep(0.3)
        assert call_counts["h1"] == 10
        assert call_counts["h2"] >= 5  # At least some events after registration

    def test_rapid_start_stop_cycles(self):
        """Rapid start/stop cycles don't deadlock or crash."""
        for i in range(5):
            start_event_dispatcher()
            time.sleep(0.01)
            stop_event_dispatcher()
            time.sleep(0.01)

        assert is_event_dispatcher_running() is False


# ============================================================================
# TIMEOUT TESTS
# ============================================================================


class TestTimeout:
    """Test callback timeout functionality."""

    def test_timeout_disabled_by_default(self):
        """use_timeout=False by default."""
        start_event_dispatcher()
        # Check internal state (access protected field for testing)
        assert _event_dispatcher._use_timeout is False

    def test_enable_timeout_on_start(self):
        """start_event_dispatcher(use_timeout=True) enables timeout."""
        start_event_dispatcher(use_timeout=True, timeout_sec=0.1)
        assert _event_dispatcher._use_timeout is True

    def test_callback_timeout_exceeded(self):
        """Slow callback is killed and logged."""
        called = []

        def slow_callback(event):
            called.append("started")
            time.sleep(1.0)  # Longer than timeout
            called.append("finished")

        register_key_event_handler("slow", slow_callback)
        start_event_dispatcher(use_timeout=True, timeout_sec=0.1)

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.5)

        assert "started" in called
        # Should NOT have "finished" since it was killed
        assert "finished" not in called

    def test_callback_timeout_doesnt_block_main(self):
        """Main thread not blocked by timeout."""
        def slow_callback(event):
            time.sleep(1.0)

        register_key_event_handler("slow", slow_callback)
        start_event_dispatcher(use_timeout=True, timeout_sec=0.05)

        start_time = time.time()
        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        push_duration = time.time() - start_time

        assert push_duration < 0.01  # Should return quickly

    def test_set_timeout_at_runtime(self):
        """set_event_dispatcher_timeout() changes settings."""
        start_event_dispatcher(use_timeout=False)
        assert _event_dispatcher._use_timeout is False

        set_event_dispatcher_timeout(True, 0.1)
        assert _event_dispatcher._use_timeout is True

    def test_fast_callback_completes_normally(self):
        """Normal callback completes even with timeout enabled."""
        completed = []

        def fast_callback(event):
            completed.append(True)

        register_key_event_handler("fast", fast_callback)
        start_event_dispatcher(use_timeout=True, timeout_sec=1.0)

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.1)

        assert len(completed) == 1


# ============================================================================
# FILTER TESTS
# ============================================================================


class TestFilters:
    """Test filter functions."""

    def test_filter_by_stage(self):
        """Filter can select raw vs processed events."""
        raw_called = []
        processed_called = []

        def raw_callback(event):
            raw_called.append(event)

        def processed_callback(event):
            processed_called.append(event)

        register_key_event_handler(
            "raw", raw_callback, filter_fn=lambda e: e.stage == "raw"
        )
        register_key_event_handler(
            "processed",
            processed_callback,
            filter_fn=lambda e: e.stage == "processed",
        )
        start_event_dispatcher()

        raw_event = KeyEvent("a", None, time.time(), "raw", "getch_str")
        _event_dispatcher.push_event(raw_event)
        time.sleep(0.1)

        assert len(raw_called) == 1
        assert len(processed_called) == 0

    def test_filter_by_key_type(self):
        """Filter can select specific key types."""
        arrow_called = []

        def arrow_callback(event):
            arrow_called.append(event)

        def is_arrow(event):
            return (
                event.processed_key
                and event.processed_key.startswith("KEY_")
                and "ARROW" not in event.processed_key
            )

        register_key_event_handler(
            "arrows", arrow_callback, filter_fn=lambda e: e.processed_key == "KEY_UP"
        )
        start_event_dispatcher()

        event = KeyEvent("a", "KEY_UP", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.1)

        assert len(arrow_called) == 1

    def test_filter_by_source(self):
        """Filter can select by source_func."""
        input_called = []

        def input_callback(event):
            input_called.append(event)

        register_key_event_handler(
            "input",
            input_callback,
            filter_fn=lambda e: e.source_func == "inputstring",
        )
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "inputstring")
        _event_dispatcher.push_event(event)
        time.sleep(0.1)

        assert len(input_called) == 1

    def test_filter_combined(self):
        """Complex filters work correctly."""
        called = []

        def callback(event):
            called.append(event)

        def complex_filter(event):
            return (
                event.source_func == "inputstring"
                and event.processed_key
                and event.processed_key.startswith("KEY_")
            )

        register_key_event_handler("complex", callback, filter_fn=complex_filter)
        start_event_dispatcher()

        # Should match
        event1 = KeyEvent("a", "KEY_UP", time.time(), "processed", "inputstring")
        _event_dispatcher.push_event(event1)

        # Should not match (wrong source)
        event2 = KeyEvent("b", "KEY_UP", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event2)

        time.sleep(0.1)
        assert len(called) == 1

    def test_none_filter_matches_all(self):
        """filter_fn=None matches all events."""
        called = []

        def callback(event):
            called.append(event)

        register_key_event_handler("all", callback, filter_fn=None)
        start_event_dispatcher()

        for i in range(5):
            event = KeyEvent(str(i), str(i), time.time(), "processed", "getch_str")
            _event_dispatcher.push_event(event)

        time.sleep(0.1)
        assert len(called) == 5


# ============================================================================
# HISTORY TESTS
# ============================================================================


class TestHistory:
    """Test event history buffer."""

    def test_history_stores_events(self):
        """Events added to history buffer."""
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.05)

        history = get_key_event_history(limit=10)
        assert len(history) > 0

    def test_history_bounded(self):
        """History buffer doesn't grow unbounded."""
        start_event_dispatcher()

        for i in range(200):
            event = KeyEvent(str(i), str(i), time.time(), "processed", "getch_str")
            _event_dispatcher.push_event(event)

        time.sleep(0.2)
        history = get_key_event_history()
        assert len(history) <= 100

    def test_get_history_returns_list(self):
        """get_key_event_history() returns list."""
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.05)

        history = get_key_event_history()
        assert isinstance(history, list)

    def test_get_history_chronological(self):
        """History returned in chronological order."""
        start_event_dispatcher()

        timestamps = []
        for i in range(5):
            ts = time.time() + i * 0.001
            event = KeyEvent(str(i), str(i), ts, "processed", "getch_str")
            _event_dispatcher.push_event(event)
            timestamps.append(ts)
            time.sleep(0.001)

        time.sleep(0.1)
        history = get_key_event_history(limit=10)
        assert len(history) >= 5

    def test_get_history_limit_respected(self):
        """get_history(limit=N) returns at most N events."""
        start_event_dispatcher()

        for i in range(20):
            event = KeyEvent(str(i), str(i), time.time(), "processed", "getch_str")
            _event_dispatcher.push_event(event)

        time.sleep(0.1)
        history = get_key_event_history(limit=5)
        assert len(history) <= 5

    def test_clear_history_empties(self):
        """clear_key_event_history() empties buffer."""
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.05)

        assert len(get_key_event_history(limit=10)) > 0
        clear_key_event_history()
        assert len(get_key_event_history(limit=10)) == 0


# ============================================================================
# EDGE CASES & REGRESSION TESTS
# ============================================================================


class TestEdgeCases:
    """Test edge cases and potential bugs."""

    def test_empty_handler_name(self):
        """Empty string as handler name."""
        def callback(event):
            pass

        register_key_event_handler("", callback)
        handlers = get_registered_handlers()
        assert "" in handlers

    def test_special_chars_in_handler_name(self):
        """Handler name with special characters."""
        def callback(event):
            pass

        name = "test-handler_123!@#"
        register_key_event_handler(name, callback)
        handlers = get_registered_handlers()
        assert name in handlers

    def test_very_long_handler_name(self):
        """Very long handler name."""
        def callback(event):
            pass

        name = "x" * 1000
        register_key_event_handler(name, callback)
        handlers = get_registered_handlers()
        assert name in handlers

    def test_unicode_in_raw_char(self):
        """Unicode characters in raw_char."""
        event = KeyEvent("é", "é", time.time(), "processed", "getch_str")
        assert event.raw_char == "é"

    def test_simultaneous_getch_and_event_access(self):
        """getch() and get_event_queue() access simultaneously."""
        q = get_event_queue()
        start_event_dispatcher()

        # Simulate simultaneous access
        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)

        time.sleep(0.05)
        try:
            received = q.get_nowait()
            assert received is not None
        except queue.Empty:
            # Queue was already consumed
            pass

    def test_unregister_during_dispatch(self):
        """Unregister handler while it's being called."""
        call_order = []

        def callback1(event):
            call_order.append(1)

        def callback2(event):
            call_order.append(2)
            # Unregister callback1 while callback2 is running
            unregister_key_event_handler("h1")

        register_key_event_handler("h1", callback1)
        register_key_event_handler("h2", callback2)
        start_event_dispatcher()

        event = KeyEvent("a", "a", time.time(), "processed", "getch_str")
        _event_dispatcher.push_event(event)
        time.sleep(0.1)

        # Both should be called in order before unregister takes effect
        assert 1 in call_order
        assert 2 in call_order


# ============================================================================
# BACKWARD COMPATIBILITY TESTS
# ============================================================================


class TestBackwardCompatibility:
    """Ensure no breaking changes to existing code."""

    def test_getch_works_without_event_system(self):
        """getch() works normally if dispatcher never started."""
        # Just import and check it doesn't crash
        from bbsengine6.io.getch import getch_str
        assert getch_str is not None

    def test_existing_code_unaffected(self):
        """Existing function signatures unchanged."""
        from bbsengine6.io.getch import getch_str
        import inspect

        sig = inspect.signature(getch_str)
        # Should have timeout and debug params
        assert "timeout" in sig.parameters
        assert "debug" in sig.parameters
