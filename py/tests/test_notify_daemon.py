# test_notify_daemon.py
# Entry point tests for python -m bbsengine6.notify.daemon

from bbsengine6.notify.daemon import NotifyDaemon, EventBus, fire_event, register_event_handler


class TestDaemonExports:
    """Test daemon module exports."""

    def test_notify_daemon_exists(self):
        assert NotifyDaemon is not None

    def test_event_bus_exists(self):
        assert EventBus is not None

    def test_fire_event_exists(self):
        assert callable(fire_event)

    def test_register_event_handler_exists(self):
        assert callable(register_event_handler)


class TestEventBus:
    """Test EventBus basic functionality."""

    def test_event_bus_on_and_get(self):
        bus = EventBus()

        def handler(data):
            pass

        bus.on("test.event", handler)
        handlers = bus.get_handlers("test.event")
        assert len(handlers) == 1
        assert handlers[0] is handler

    def test_event_bus_fire(self):
        bus = EventBus()
        received = []

        def handler(data):
            received.append(data)

        bus.on("test.fire", handler)
        bus.fire("test.fire", {"value": 42})
        assert len(received) == 1
        assert received[0] == {"value": 42}

    def test_event_bus_off(self):
        bus = EventBus()

        def handler(data):
            pass

        bus.on("test.off", handler)
        bus.off("test.off", handler)
        handlers = bus.get_handlers("test.off")
        assert len(handlers) == 0


class TestGlobalEventFunctions:
    """Test global fire_event and register_event_handler."""

    def test_fire_event_and_register(self):
        received = []

        def handler(data):
            received.append(data)

        register_event_handler("global.test", handler)
        fire_event("global.test", {"msg": "hello"})
        assert len(received) == 1
        assert received[0] == {"msg": "hello"}

    def test_fire_unknown_event_noops(self):
        fire_event("nonexistent.event", {})
