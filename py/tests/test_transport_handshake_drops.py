# test_transport_handshake_drops.py
# Regression test: clients that TCP-connect and close without sending an HTTP
# upgrade request must produce a single WARNING log with the peer address,
# not a multi-frame traceback.

import asyncio
import json
import logging

import pytest
import websockets

from bbsengine6.net.transport import WebSocketServer


pytestmark = pytest.mark.unit


async def _echo_handler(server, websocket, path, message):
    return {"type": "echo", "msg": message}


async def _run_empty_handshake(caplog) -> None:
    """A TCP peer that closes immediately must log a single WARNING with the
    peer's address; no Traceback text in the captured logs."""
    server = WebSocketServer(host="127.0.0.1", port=0, handler=_echo_handler)
    await server.start()
    try:
        port = server._bound_port
        assert port is not None

        caplog.set_level(logging.WARNING, logger="bbsengine6.net.transport")

        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.close()
        await writer.wait_closed()
        # Give the server a moment to handle the closed connection.
        await asyncio.sleep(0.3)

        warnings = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING
            and r.name == "bbsengine6.net.transport"
        ]
        messages = [r.getMessage() for r in warnings]
        assert any("WS handshake failed" in m for m in messages), (
            f"Expected 'WS handshake failed' WARNING, got: {messages}"
        )
        assert any("127.0.0.1" in m for m in messages), (
            f"Expected peer IP 127.0.0.1 in WARNING, got: {messages}"
        )

        # No Traceback text from our transport logger: exc_info must be None
        # on the WS-handshake WARNING, and no record should contain
        # "Traceback" in its rendered message.
        for r in warnings:
            if "WS handshake failed" in r.getMessage():
                assert r.exc_info is None, (
                    f"WS handshake WARNING must not carry exc_info; got: "
                    f"{r.getMessage()}"
                )
        joined = "\n".join(messages)
        assert "Traceback" not in joined, (
            f"No Traceback text expected in transport WARNING logs; got: {joined}"
        )
    finally:
        await server.stop()


async def _run_normal_connect_no_warning(caplog) -> None:
    """Regression: a normal WebSocket handshake must not be flagged as failed."""
    server = WebSocketServer(host="127.0.0.1", port=0, handler=_echo_handler)
    await server.start()
    try:
        port = server._bound_port
        assert port is not None

        caplog.set_level(logging.WARNING, logger="bbsengine6.net.transport")

        async with websockets.connect(f"ws://127.0.0.1:{port}/") as ws:
            await ws.send(json.dumps({"type": "ping"}))
            resp = await ws.recv()
        parsed = json.loads(resp)
        assert parsed["type"] == "echo"

        await asyncio.sleep(0.2)

        failed = [
            r for r in caplog.records
            if r.name == "bbsengine6.net.transport"
            and "WS handshake failed" in r.getMessage()
        ]
        assert not failed, (
            f"Unexpected WS handshake failed WARNING on normal connect: "
            f"{[r.getMessage() for r in failed]}"
        )
    finally:
        await server.stop()


async def _run_accepted_peer_logged(caplog) -> None:
    """Successful connections still log the accepted peer at DEBUG."""
    server = WebSocketServer(host="127.0.0.1", port=0, handler=_echo_handler)
    await server.start()
    try:
        port = server._bound_port
        assert port is not None

        caplog.set_level(logging.DEBUG, logger="bbsengine6.net.transport")

        async with websockets.connect(f"ws://127.0.0.1:{port}/") as ws:
            await ws.send(json.dumps({"type": "ping"}))
            await ws.recv()

        await asyncio.sleep(0.2)

        accepted = [
            r for r in caplog.records
            if r.name == "bbsengine6.net.transport"
            and "on_connect accepted" in r.getMessage()
        ]
        assert accepted, (
            f"Expected DEBUG 'on_connect accepted' log; got: "
            f"{[r.getMessage() for r in caplog.records if r.name == 'bbsengine6.net.transport']}"
        )
        assert any("127.0.0.1" in r.getMessage() for r in accepted), (
            f"Expected peer IP in accepted log; got: "
            f"{[r.getMessage() for r in accepted]}"
        )
    finally:
        await server.stop()


def test_empty_handshake_logs_peer_without_traceback(caplog) -> None:
    asyncio.run(_run_empty_handshake(caplog))


def test_real_ws_connect_still_works(caplog) -> None:
    asyncio.run(_run_normal_connect_no_warning(caplog))


def test_real_ws_connect_reports_accepted_peer(caplog) -> None:
    asyncio.run(_run_accepted_peer_logged(caplog))
