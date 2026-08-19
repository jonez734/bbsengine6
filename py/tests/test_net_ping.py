"""Tests for :mod:`bbsengine6.net.ping` (shared ping CLI helper).

Covers:

* :class:`PingUnavailable` carries host/port/cause and renders a
  one-line message that names the endpoint, hints at the likely
  cause, and prefixes with the caller-supplied ``prog`` name.
* :func:`connect` converts ``ConnectionRefusedError``, ``OSError``,
  ``asyncio.TimeoutError``, and ``WebSocketException`` into
  :class:`PingUnavailable` (no raw exception escapes).
* :func:`ping` sends ``{"type":"ping"}`` and returns the parsed
  reply.
* :func:`main` catches :class:`PingUnavailable`, calls
  :func:`bbsengine6.io.echo` with ``level="error"``, and returns
  ``1`` on connection failure so the ``*-ping`` shims exit non-zero.
* :func:`main` returns ``0`` on the happy path.
"""

from __future__ import annotations

import json
import socket
import sys
from contextlib import contextmanager
from typing import Any, Iterator, List
from unittest.mock import MagicMock, patch

import pytest


# Force-import the helper before patching so we patch the symbol in
# the helper module, not in some downstream re-export.
from bbsengine6.net import ping as ping_helper  # noqa: E402
from bbsengine6.net.ping import (  # noqa: E402
    PingUnavailable,
    build_parser,
    connect,
    main,
    send_ping,
)


# ---------------------------------------------------------------------
# Helpers


def _free_port() -> int:
    """Bind an ephemeral IPv4 port and immediately release it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextmanager
def _argv(*args: str) -> Iterator[None]:
    """Run a block with ``sys.argv`` replaced by ``['ping', *args]``."""
    saved = sys.argv
    sys.argv = ["ping", *args]
    try:
        yield
    finally:
        sys.argv = saved


class _FakeWebSocket:
    """Minimal async-context-manager stand-in for ``websockets`` protocol.

    Implements both the awaitable shape (so ``await websockets.connect(...)``
    in the helper returns this object) and the async context manager shape
    (so consumers can ``async with`` it).
    """

    def __init__(self, frames: List[str]) -> None:
        self._frames = list(frames)
        self.sent: List[str] = []

    async def __aenter__(self) -> "_FakeWebSocket":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    async def send(self, payload: str) -> None:
        self.sent.append(payload)

    async def recv(self) -> str:
        return self._frames.pop(0)

    async def close(self) -> None:
        return None


def _connect_mock(fake: _FakeWebSocket) -> MagicMock:
    """Build a mock for ``websockets.connect(url)`` whose ``side_effect``
    is an async function returning ``fake``. The helper awaits
    ``websockets.connect(url)`` (not the legacy ``async with`` shape)
    so the mock must be an awaitable factory."""

    async def _fake_connect(url: str, **kwargs: Any) -> _FakeWebSocket:
        return fake

    return MagicMock(side_effect=_fake_connect)


# ---------------------------------------------------------------------
# PingUnavailable


class TestPingUnavailableMessage:
    """The exception message names the endpoint, hints at the cause,
    and prefixes with the prog name.
    """

    def test_message_includes_ws_url(self):
        exc = PingUnavailable(
            "localhost", 8765, ConnectionRefusedError("refused")
        )
        assert "ws://localhost:8765/" in str(exc)

    def test_message_includes_running_hint(self):
        exc = PingUnavailable(
            "localhost", 8765, ConnectionRefusedError("refused")
        )
        assert "is the bed daemon running?" in str(exc)

    def test_message_includes_original_exception(self):
        exc = PingUnavailable(
            "localhost", 8765, ConnectionRefusedError("nope")
        )
        assert "nope" in str(exc)

    def test_default_prog_prefix_is_ping(self):
        exc = PingUnavailable("h", 9, OSError("boom"))
        assert str(exc).startswith("ping:")

    def test_custom_prog_prefix(self):
        exc = PingUnavailable(
            "h", 9, OSError("boom"), prog="bedping"
        )
        assert str(exc).startswith("bedping:")

    def test_prog_kwarg_is_keyword_only(self):
        """``prog`` must be keyword-only so the four-arg call site
        doesn't accidentally pass the prog in the exc slot."""
        with pytest.raises(TypeError):
            PingUnavailable("h", 9, OSError("boom"), "bedping")  # type: ignore[misc]

    def test_attributes_carry_host_and_port(self):
        exc = PingUnavailable("h", 9, OSError("boom"))
        assert exc.host == "h"
        assert exc.port == 9

    def test_attributes_carry_prog(self):
        exc = PingUnavailable("h", 9, OSError("boom"), prog="casino-ping")
        assert exc.prog == "casino-ping"

    def test_attributes_carry_original_exception(self):
        cause = ConnectionRefusedError("nope")
        exc = PingUnavailable("h", 9, cause)
        assert exc.exc is cause


# ---------------------------------------------------------------------
# connect() error conversion


class TestConnectConnectionRefused:
    """When ``websockets.connect`` raises ``ConnectionRefusedError``,
    :func:`connect` raises :class:`PingUnavailable`.
    """

    def test_connection_refused_raises_ping_unavailable(self):
        with patch.object(
            ping_helper, "websockets"
        ) as ws_mod:
            ws_mod.connect = MagicMock(
                side_effect=ConnectionRefusedError(
                    "[Errno 111] Connection refused"
                )
            )
            with pytest.raises(PingUnavailable) as cm:
                # ``asyncio.run`` because ``connect`` is async.
                import asyncio

                asyncio.run(connect("localhost", 8765))
        assert "ws://localhost:8765/" in str(cm.value)
        assert "is the bed daemon running?" in str(cm.value)
        assert isinstance(cm.value.__cause__, ConnectionRefusedError)

    def test_custom_prog_propagates(self):
        with patch.object(
            ping_helper, "websockets"
        ) as ws_mod:
            ws_mod.connect = MagicMock(
                side_effect=ConnectionRefusedError("refused")
            )
            import asyncio

            with pytest.raises(PingUnavailable) as cm:
                asyncio.run(connect("localhost", 8765, prog="casino-ping"))
        assert str(cm.value).startswith("casino-ping:")


class TestConnectOtherTransportErrors:
    """``OSError``, ``asyncio.TimeoutError``, and ``WebSocketException``
    must also be converted to :class:`PingUnavailable`.
    """

    def test_oserror_is_friendly(self):
        with patch.object(
            ping_helper, "websockets"
        ) as ws_mod:
            ws_mod.connect = MagicMock(
                side_effect=OSError("host unreachable")
            )
            import asyncio

            with pytest.raises(PingUnavailable) as cm:
                asyncio.run(connect("nope.example", 8765))
        assert "host unreachable" in str(cm.value)
        assert "ws://nope.example:8765/" in str(cm.value)

    def test_timeouterror_is_friendly(self):
        with patch.object(
            ping_helper, "websockets"
        ) as ws_mod:
            ws_mod.connect = MagicMock(
                side_effect=TimeoutError("slow")
            )
            import asyncio

            with pytest.raises(PingUnavailable) as cm:
                asyncio.run(connect("localhost", 8765))
        assert "slow" in str(cm.value)

    def test_websocket_exception_is_friendly(self):
        from websockets.exceptions import WebSocketException

        with patch.object(
            ping_helper, "websockets"
        ) as ws_mod:
            ws_mod.connect = MagicMock(
                side_effect=WebSocketException("bad handshake")
            )
            import asyncio

            with pytest.raises(PingUnavailable) as cm:
                asyncio.run(connect("localhost", 8765))
        assert "bad handshake" in str(cm.value)


class TestConnectHappyPath:
    """On a successful ``websockets.connect``, :func:`connect` returns
    the live WS protocol object.
    """

    def test_returns_ws_object(self):
        import asyncio

        fake = _FakeWebSocket([])
        with patch.object(
            ping_helper, "websockets"
        ) as ws_mod:
            ws_mod.connect = _connect_mock(fake)
            ws = asyncio.run(connect("localhost", 8765))
        assert ws is fake


# ---------------------------------------------------------------------
# ping() round-trip


class TestPingRoundTrip:
    """When the server replies with a valid pong, :func:`send_ping` returns
    the parsed JSON dict.
    """

    def test_ping_round_trip_returns_dict(self):
        import asyncio

        fake = _FakeWebSocket([
            json.dumps({"type": "pong", "name": "bed", "version": "0.0.0"}),
        ])
        with patch.object(
            ping_helper, "websockets"
        ) as ws_mod:
            ws_mod.connect = _connect_mock(fake)
            result = asyncio.run(send_ping("localhost", 8765))
        assert result == {"type": "pong", "name": "bed", "version": "0.0.0"}
        # send_ping() sent exactly one frame, the ping envelope.
        assert len(fake.sent) == 1
        assert json.loads(fake.sent[0]) == {"type": "ping"}


# ---------------------------------------------------------------------
# main() exit codes


class TestMainConnectionRefused:
    """When :func:`send_ping` raises :class:`PingUnavailable`, :func:`main`
    emits a friendly one-liner via ``io.echo(level="error")`` and
    returns ``1``.
    """

    def test_returns_one(self):
        with patch.object(
            ping_helper, "websockets"
        ) as ws_mod, patch.object(
            ping_helper.io, "echo"
        ) as echo:
            ws_mod.connect = MagicMock(
                side_effect=ConnectionRefusedError(
                    "[Errno 111] Connection refused"
                )
            )
            with _argv():
                rc = main()
        assert rc == 1
        echo.assert_called_once()
        msg, kwargs = echo.call_args
        assert "ws://localhost:8765/" in msg[0]
        assert "is the bed daemon running?" in msg[0]
        assert kwargs.get("level") == "error"

    def test_custom_prog_in_message(self):
        with patch.object(
            ping_helper, "websockets"
        ) as ws_mod, patch.object(
            ping_helper.io, "echo"
        ) as echo:
            ws_mod.connect = MagicMock(
                side_effect=ConnectionRefusedError("refused")
            )
            with _argv():
                rc = main(prog="bedping")
        assert rc == 1
        assert "bedping:" in echo.call_args[0][0]

    def test_no_traceback_escapes(self):
        """The connection error must be converted to PingUnavailable so
        no traceback reaches stderr."""
        with patch.object(
            ping_helper, "websockets"
        ) as ws_mod, patch.object(
            ping_helper.io, "echo"
        ):
            ws_mod.connect = MagicMock(
                side_effect=ConnectionRefusedError("refused")
            )
            with _argv():
                # No exception should propagate past main().
                rc = main()
        assert rc == 1


class TestMainHappyPath:
    """When the server returns a valid pong, :func:`main` returns 0."""

    def test_ping_round_trip_returns_zero(self):
        fake = _FakeWebSocket([
            json.dumps({"type": "pong", "name": "bed", "version": "0.0.0"}),
        ])
        with patch.object(
            ping_helper, "websockets"
        ) as ws_mod, patch.object(
            ping_helper.io, "echo"
        ), patch("builtins.print") as _:
            ws_mod.connect = _connect_mock(fake)
            with _argv():
                rc = main()
        assert rc == 0


# ---------------------------------------------------------------------
# build_parser


class TestBuildParser:
    """:func:`build_parser` honors the ``prog`` argument and exposes
    the standard flag set.
    """

    def test_default_prog(self):
        p = build_parser()
        assert p.prog == "ping"

    def test_custom_prog(self):
        p = build_parser(prog="bedping")
        assert p.prog == "bedping"

    def test_default_host(self):
        p = build_parser()
        ns = p.parse_args([])
        assert ns.host == "localhost"

    def test_default_port(self):
        p = build_parser()
        ns = p.parse_args([])
        assert ns.port == 8765

    def test_default_path(self):
        p = build_parser()
        ns = p.parse_args([])
        assert ns.path == "/"

    def test_default_timeout(self):
        p = build_parser()
        ns = p.parse_args([])
        assert ns.timeout == 5.0

    def test_parses_overrides(self):
        p = build_parser(prog="casino-ping")
        ns = p.parse_args([
            "--host", "bed.internal",
            "--port", "9999",
            "--path", "/casino",
            "--timeout", "1.0",
        ])
        assert ns.host == "bed.internal"
        assert ns.port == 9999
        assert ns.path == "/casino"
        assert ns.timeout == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
