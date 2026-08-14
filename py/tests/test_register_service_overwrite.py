# test_register_service_overwrite.py
# WebSocketServer.register_service must emit a WARNING when it would
# overwrite an already-registered handler (per-type or default). The
# overwrite is intentional in some places (bed's PingService swaps in
# after a router's own `["ping"]`) and accidental in others (a custom
# router registering `"auth"` would silently replace bed's
# AuthService). Either way, operators should see it in the log.

import logging

import pytest

from bbsengine6.net.transport import WebSocketServer


pytestmark = pytest.mark.unit


def _make_service(class_name: str):
    """Build a fresh class with the given name whose instances expose
    a no-op async handle_message. Returning a unique class per call
    makes ``service.__class__.__name__`` distinguishable so the
    warning message is informative."""
    async def handle_message(self, server, websocket, path, message):
        return None

    cls = type(class_name, (), {"handle_message": handle_message})
    return cls()


def _warnings(caplog, logger_name: str = "bbsengine6.net.transport"):
    return [
        r for r in caplog.records
        if r.levelno == logging.WARNING and r.name == logger_name
    ]


def test_register_service_warns_when_overwriting_per_type(caplog):
    """A second registration for an already-registered msg_type
    produces a WARNING naming both the previous and the new handler."""
    caplog.set_level(logging.WARNING, logger="bbsengine6.net.transport")
    server = WebSocketServer(host="127.0.0.1", port=0)
    server.register_service(_make_service("First"), ["ping"])
    server.register_service(_make_service("Second"), ["ping"])

    warnings = _warnings(caplog)
    assert len(warnings) == 1, f"expected exactly one WARNING, got: {warnings}"
    msg = warnings[0].getMessage()
    assert "overwriting" in msg
    assert "ping" in msg
    assert "First" in msg
    assert "Second" in msg


def test_register_service_warns_only_for_overwritten_types(caplog):
    """When a registration mixes new and overwritten msg_types, the
    warning names only the overwritten ones in the 'previous=' segment;
    the trailing 'message_types=' segment lists the full request."""
    caplog.set_level(logging.WARNING, logger="bbsengine6.net.transport")
    server = WebSocketServer(host="127.0.0.1", port=0)
    server.register_service(_make_service("First"), ["ping"])
    server.register_service(_make_service("Second"), ["ping", "echo"])

    warnings = _warnings(caplog)
    assert len(warnings) == 1
    msg = warnings[0].getMessage()
    # The "previous=" list enumerates only the keys that were already
    # set; "echo" had no prior registration, so it must not appear
    # there.
    assert "previous=[ping(First)]" in msg
    assert "echo(First)" not in msg


def test_register_service_silent_on_first_registration(caplog):
    """The very first registration for a msg_type does NOT warn;
    only overwrites do."""
    caplog.set_level(logging.WARNING, logger="bbsengine6.net.transport")
    server = WebSocketServer(host="127.0.0.1", port=0)
    server.register_service(_make_service("Only"), ["ping"])
    assert _warnings(caplog) == []


def test_register_service_warns_when_overwriting_default(caplog):
    """Setting a default service after one is already set warns too."""
    caplog.set_level(logging.WARNING, logger="bbsengine6.net.transport")
    server = WebSocketServer(host="127.0.0.1", port=0)
    server.register_service(_make_service("FirstDefault"))
    server.register_service(_make_service("SecondDefault"))

    warnings = _warnings(caplog)
    assert len(warnings) == 1
    msg = warnings[0].getMessage()
    assert "overwriting" in msg
    assert "default service" in msg
    assert "FirstDefault" in msg
    assert "SecondDefault" in msg


def test_register_service_overwrite_picks_last_writer(caplog):
    """Functional behavior: after the warning, get_service returns the
    newer handler (last writer wins)."""
    caplog.set_level(logging.WARNING, logger="bbsengine6.net.transport")
    server = WebSocketServer(host="127.0.0.1", port=0)
    first = _make_service("First")
    second = _make_service("Second")
    server.register_service(first, ["ping"])
    server.register_service(second, ["ping"])
    assert server.get_service("ping") is second
