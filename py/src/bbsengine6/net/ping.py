"""Shared WebSocket liveness check for any bbsengine6-based daemon.

The :mod:`bbsengine6.net.ping` module provides a single code path for:

* ``websockets.connect()`` with friendly error rendering on
  ``ConnectionRefusedError``, ``OSError``, ``asyncio.TimeoutError``,
  and ``WebSocketException``. The original exception is chained via
  ``raise ... from exc`` for log/debug visibility.
* A "send ping, parse reply" round-trip that every ``*-ping`` CLI
  shim (``bedping``, ``bbsengine6-ping``, ``casino-ping``,
  ``zoid6-ping``) calls through the same function.
* An argparse-based CLI entry point whose ``prog=`` keyword controls
  the error message prefix so the same code renders "bedping: cannot
  connect..." or "casino-ping: cannot connect..." depending on which
  shim invoked it.

:class:`PingUnavailable` is re-exported by :mod:`bed.tools.ping` so
the existing ``bedping`` shim continues to work and the class
identity (``bed.tools.ping.PingUnavailable is bbsengine6.net.ping.PingUnavailable``)
is preserved for tests that import from either location.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

import websockets
from websockets.exceptions import WebSocketException

from bbsengine6 import io


_DEFAULT_TIMEOUT = 5.0
_DEFAULT_HOST = "localhost"
_DEFAULT_PORT = 8765
_DEFAULT_PATH = "/"


class PingUnavailable(Exception):
    """Raised when the target WebSocket is unreachable.

    Carries ``host`` / ``port`` / original ``exc`` so callers can
    render a one-line message naming the configured endpoint. The
    ``prog`` keyword controls the message prefix so each ``*-ping``
    shim identifies itself (``bedping:``, ``bbsengine6-ping:``,
    ``casino-ping:``, ``zoid6-ping:``).
    """

    def __init__(
        self,
        host: str,
        port: int,
        exc: BaseException,
        *,
        prog: str = "ping",
    ) -> None:
        self.host = host
        self.port = port
        self.exc = exc
        self.prog = prog
        super().__init__(
            f"{prog}: cannot connect to ws://{host}:{port}/ "
            f"(is the bed daemon running?): {exc}"
        )


async def connect(
    host: str,
    port: int,
    *,
    path: str = _DEFAULT_PATH,
    timeout: float = _DEFAULT_TIMEOUT,
    prog: str = "ping",
    ping_interval: Optional[float] = None,
    ping_timeout: Optional[float] = None,
) -> Any:
    """Open a WebSocket to ``ws://{host}:{port}{path}``.

    Returns the live websockets protocol object on success. On any
    connection-level failure (``ConnectionRefusedError``, ``OSError``,
    ``asyncio.TimeoutError``, ``WebSocketException``), raises
    :class:`PingUnavailable` with the original exception chained via
    ``raise ... from exc``. The ``prog`` keyword is forwarded to
    :class:`PingUnavailable` so the rendered message identifies the
    caller (e.g. ``bedping:``).

    The ``ping_interval`` and ``ping_timeout`` kwargs forward to
    :func:`websockets.connect` so callers with long blocking
    sections outside the asyncio loop (terminal prompts, human
    menu decisions) can widen the keepalive window. When omitted,
    the websockets library defaults apply (``ping_interval=20``,
    ``ping_timeout=20``). Use these to avoid spurious
    ``ConnectionClosedError: 1011 keepalive ping timeout`` when
    the user's wall-clock between sends exceeds the default 20s.
    """
    url = f"ws://{host}:{port}{path}"
    kwargs: Dict[str, Any] = {}
    if ping_interval is not None:
        kwargs["ping_interval"] = ping_interval
    if ping_timeout is not None:
        kwargs["ping_timeout"] = ping_timeout
    try:
        return await asyncio.wait_for(
            websockets.connect(url, **kwargs), timeout=timeout
        )
    except (
        ConnectionRefusedError,
        OSError,
        asyncio.TimeoutError,
        WebSocketException,
    ) as exc:
        raise PingUnavailable(host, port, exc, prog=prog) from exc


async def send_ping(
    host: str,
    port: int,
    *,
    path: str = _DEFAULT_PATH,
    timeout: float = _DEFAULT_TIMEOUT,
    prog: str = "ping",
) -> Dict[str, Any]:
    """Send ``{"type":"ping"}`` and return the parsed JSON reply.

    Opens a connection via :func:`connect` (so connection-level
    failures share the :class:`PingUnavailable` path), sends the
    ping frame, reads one reply with the same timeout, and parses
    the result as JSON.
    """
    ws = await connect(host, port, path=path, timeout=timeout, prog=prog)
    try:
        await ws.send(json.dumps({"type": "ping"}))
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        return json.loads(raw)
    finally:
        try:
            await ws.close()
        except Exception:
            pass


def build_parser(prog: str = "ping") -> argparse.ArgumentParser:
    """Build the standard ``*-ping`` argparse parser.

    All consumer shims share the same flag set so ``--host``,
    ``--port``, ``--path``, and ``--timeout`` behave identically
    regardless of which project owns the entry point. The ``prog``
    argument is forwarded to :class:`argparse.ArgumentParser` so
    ``--help`` shows the correct program name.
    """
    p = argparse.ArgumentParser(
        prog=prog,
        description=(
            f"{prog}: send a ping to the bbsengine6-based WebSocket "
            f"daemon (default: {_DEFAULT_HOST}:{_DEFAULT_PORT})."
        ),
    )
    p.add_argument(
        "--host",
        default=_DEFAULT_HOST,
        help=f"WebSocket host (default: {_DEFAULT_HOST})",
    )
    p.add_argument(
        "--port",
        type=int,
        default=_DEFAULT_PORT,
        help=f"WebSocket port (default: {_DEFAULT_PORT})",
    )
    p.add_argument(
        "--path",
        default=_DEFAULT_PATH,
        help=f"WebSocket path (default: {_DEFAULT_PATH})",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=_DEFAULT_TIMEOUT,
        help=f"Operation timeout in seconds (default: {_DEFAULT_TIMEOUT})",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"{prog} 1.0 (bbsengine6.net.ping)",
    )
    return p


def main(argv: Optional[List[str]] = None, *, prog: str = "ping") -> int:
    """CLI entry point shared by every ``*-ping`` shim.

    Parses args, runs :func:`send_ping` synchronously, prints the
    reply on success. On :class:`PingUnavailable`, calls
    :func:`bbsengine6.io.echo` with ``level="error"`` so the operator
    sees a one-line friendly message and returns ``1`` so the shim
    exits non-zero. No Python traceback escapes on connection failure.
    """
    p = build_parser(prog=prog)
    args = p.parse_args(argv)
    try:
        result = asyncio.run(
            send_ping(
                args.host,
                args.port,
                path=args.path,
                timeout=args.timeout,
                prog=prog,
            )
        )
    except PingUnavailable as exc:
        io.echo(str(exc), level="error")
        return 1
    print(f"<- {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
