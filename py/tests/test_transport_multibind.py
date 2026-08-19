# test_transport_multibind.py
# WebSocketServer.start() with multi-bind: separate listening sockets per
# (family, host, port) tuple, name-based resolution (e.g. ``localhost``
# fans out to both v4 and v6), partial-bind failure cleanup, and back-
# compat for the legacy ``host``/``port`` constructor.

import asyncio
import json
import socket

import pytest
import websockets

from bbsengine6.net.transport import WebSocketServer


pytestmark = pytest.mark.unit


async def _echo_handler(server, websocket, path, message):
    return {"type": "echo", "msg": message}


def _free_port() -> int:
    """Ask the kernel for an unused TCP port. Reused for v4 and v6 binds."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_binds_required_when_binds_kwarg_given() -> None:
    """``binds=[]`` is rejected at construction time so a misconfigured
    config (JSON ``"bind": []``) fails fast instead of silently starting
    with no listeners."""
    with pytest.raises(ValueError, match="at least one"):
        WebSocketServer(binds=[])


def test_binds_and_host_port_are_mutually_exclusive() -> None:
    """Passing both shapes is a config error, not a silent precedence
    rule. Operators must pick one."""
    with pytest.raises(ValueError, match="not both"):
        WebSocketServer(host="127.0.0.1", port=8765,
                        binds=[("127.0.0.1", 8765)])


def test_legacy_host_port_defaults_preserved() -> None:
    """Back-compat: an old caller that passes nothing still gets the
    historical (``"0.0.0.0"``, 8765) bind."""
    s = WebSocketServer()
    assert s._binds == [("0.0.0.0", 8765)]
    assert s.host == "0.0.0.0"
    assert s.port == 8765


def test_legacy_host_port_kwarg_still_works() -> None:
    """Back-compat: code written before multi-bind support landed still
    constructs a single-bind server via the keyword arguments."""
    s = WebSocketServer(host="127.0.0.1", port=12345)
    assert s._binds == [("127.0.0.1", 12345)]


async def _run_dual_stack_bind() -> None:
    """Two literal binds (``127.0.0.1`` + ``::1``) on the same port
    produces two separate listener sockets, both reachable."""
    port = _free_port()
    server = WebSocketServer(
        binds=[("127.0.0.1", port), ("::1", port)],
        handler=_echo_handler,
    )
    await server.start()
    try:
        assert len(server._bound_addrs) == 2, (
            f"expected 2 listeners, got: {server._bound_addrs}"
        )
        families = {fam for fam, _, _ in server._bound_addrs}
        assert families == {"inet", "inet6"}, (
            f"expected inet + inet6, got: {families}"
        )
        # Legacy attribute is the port of the first listener.
        assert server._bound_port == port

        # Both stacks must accept a WS handshake.
        async with websockets.connect(f"ws://127.0.0.1:{port}/") as ws:
            await ws.send(json.dumps({"type": "ping"}))
            resp = json.loads(await ws.recv())
            assert resp["type"] == "echo"
        async with websockets.connect(f"ws://[::1]:{port}/") as ws:
            await ws.send(json.dumps({"type": "ping"}))
            resp = json.loads(await ws.recv())
            assert resp["type"] == "echo"
    finally:
        await server.stop()


def test_dual_stack_bind_via_two_literals() -> None:
    asyncio.run(_run_dual_stack_bind())


async def _run_localhost_resolves_to_both_families() -> None:
    """A single ``localhost`` entry fans out to one v4 and one v6
    listener socket. Confirms ``getaddrinfo(AF_UNSPEC)`` drives the
    expansion that bed's docs describe."""
    port = _free_port()
    server = WebSocketServer(
        binds=[("localhost", port)],
        handler=_echo_handler,
    )
    await server.start()
    try:
        # On every platform the test runs on, ``localhost`` has at least
        # one address (v4); the test is still meaningful when v6 is
        # absent, so don't require ==2.
        assert len(server._bound_addrs) >= 1
        # When v6 is present, ``::1`` must be one of the listeners.
        has_v6 = any(fam == "inet6" for fam, _, _ in server._bound_addrs)
        if has_v6:
            assert any("[::1]" in (host if False else host) or host == "::1"
                       for fam, host, _ in server._bound_addrs)
            async with websockets.connect(f"ws://[::1]:{port}/") as ws:
                await ws.send(json.dumps({"type": "ping"}))
                resp = json.loads(await ws.recv())
                assert resp["type"] == "echo"
        async with websockets.connect(f"ws://127.0.0.1:{port}/") as ws:
            await ws.send(json.dumps({"type": "ping"}))
            resp = json.loads(await ws.recv())
            assert resp["type"] == "echo"
    finally:
        await server.stop()


def test_localhost_resolves_to_both_families() -> None:
    asyncio.run(_run_localhost_resolves_to_both_families())


async def _run_partial_bind_failure_cleanup() -> None:
    """If the second bind fails (e.g. EADDRINUSE because some other
    process is already on that port), the first listener must be
    closed so a half-started daemon does not hold its port."""
    port = _free_port()
    # Hold the v6 port so the second bind in WebSocketServer fails.
    holder = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    holder.bind(("::1", port))
    holder.listen(8)
    try:
        server = WebSocketServer(
            binds=[("127.0.0.1", port), ("::1", port)],
            handler=_echo_handler,
        )
        with pytest.raises(OSError):
            await server.start()
        # After the failure, the v4 socket must be closed: a fresh
        # bind to the same port succeeds.
        rebound = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            rebound.bind(("127.0.0.1", port))
            rebound.listen(8)
            rebound.close()
        except OSError as e:
            pytest.fail(
                f"first bind socket was not closed on partial-bind "
                f"failure; rebind raised: {e}"
            )
    finally:
        holder.close()


def test_partial_bind_failure_closes_already_bound_sockets() -> None:
    asyncio.run(_run_partial_bind_failure_cleanup())


async def _run_stop_is_idempotent() -> None:
    """A second ``stop()`` is a no-op so SIGHUP teardown paths can call
    it without guarding."""
    server = WebSocketServer(host="127.0.0.1", port=0,
                             handler=_echo_handler)
    await server.start()
    await server.stop()
    await server.stop()  # must not raise
    assert server._servers == []
    assert server._server is None


def test_stop_is_idempotent() -> None:
    asyncio.run(_run_stop_is_idempotent())


async def _run_unresolvable_host_raises_before_open() -> None:
    """A bad host name fails the resolve phase BEFORE any socket is
    opened, so the operator does not end up with a half-bound daemon
    from a typo."""
    server = WebSocketServer(
        binds=[("127.0.0.1", 0), ("definitely-not-a-real-host.invalid", 0)],
        handler=_echo_handler,
    )
    with pytest.raises(socket.gaierror):
        await server.start()
    assert server._servers == []


def test_unresolvable_host_raises_before_opening_sockets() -> None:
    asyncio.run(_run_unresolvable_host_raises_before_open())


async def _run_services_visible_across_all_listeners() -> None:
    """A service registered on the server reaches every listener. This
    is the core promise of multi-bind: the operator does not have to
    register anything per-socket."""
    port = _free_port()
    server = WebSocketServer(
        binds=[("127.0.0.1", port), ("::1", port)],
    )
    class EchoSvc:
        async def handle_message(self, _s, _w, _p, message):
            return {"type": "echo", "msg": message}

    server.register_service(EchoSvc(), ["ping"])
    await server.start()
    try:
        for url in (f"ws://127.0.0.1:{port}/", f"ws://[::1]:{port}/"):
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps({"type": "ping"}))
                resp = json.loads(await ws.recv())
                assert resp["type"] == "echo", (
                    f"service did not reach listener {url}: {resp}"
                )
    finally:
        await server.stop()


def test_services_visible_across_all_listeners() -> None:
    asyncio.run(_run_services_visible_across_all_listeners())
