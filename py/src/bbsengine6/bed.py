#!/usr/bin/env python3
# bbsengine6/bed.py
# BED - BBS Engine Daemon
# Generic WebSocket server that loads a router module

import argparse
import asyncio
import importlib
import os
import signal
import sys

# Add current working directory and search up the tree for packages
cwd = os.getcwd()
added_paths = set()

# Walk up the directory tree looking for packages
current = cwd
while current and current != "/":
    if current not in added_paths:
        sys.path.insert(0, current)
        added_paths.add(current)
    
    # Check if this directory is a package (has __init__.py)
    if os.path.isdir(current) and os.path.isfile(os.path.join(current, "__init__.py")):
        # Add parent to potentially find sibling packages
        parent = os.path.dirname(current)
        if parent not in added_paths:
            sys.path.insert(0, parent)
            added_paths.add(parent)
    
    # Move up one level
    parent = os.path.dirname(current)
    if parent == current:  # Reached root
        break
    current = parent

# Also add the directory containing the current working directory
# This handles the case where cwd is inside a package (e.g., zoid6/api/)
parent_dir = os.path.dirname(cwd)
if parent_dir not in added_paths:
    sys.path.insert(0, parent_dir)

from bbsengine6 import io
from bbsengine6.database import buildargs as databasebuildargs
from bbsengine6.net import WebSocketServer
from bbsengine6.net.defaultrouter import DefaultRouter


class BED:
    """BBS Engine Daemon - WebSocket server."""

    def __init__(self, args: argparse.Namespace, MessageRouterClass: type):
        self.args = args
        self.MessageRouterClass = MessageRouterClass
        self.server: WebSocketServer | None = None
        self.router = None
        self._running = False

    async def start(self) -> None:
        """Start the daemon."""
        self.server = WebSocketServer(
            host=self.args.host,
            port=self.args.port,
        )

        db_args = argparse.Namespace()
        db_args.databasename = self.args.databasename
        db_args.databasehost = self.args.databasehost
        db_args.databaseport = self.args.databaseport
        db_args.databaseuser = self.args.databaseuser
        db_args.databasepassword = self.args.databasepassword
        db_args.debug = getattr(self.args, "debug", False)

        self.router = self.MessageRouterClass(db_args)
        self.router.register_all(self.server)

        await self.server.start()
        self._running = True

        io.echo(f"BED started on {self.args.host}:{self.args.port}", level="info")
        io.echo(f"Router: {self.MessageRouterClass.__module__}.{self.MessageRouterClass.__name__}", level="info")

        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            io.echo("BED cancelled", level="info")

    async def stop(self) -> None:
        """Stop the daemon."""
        self._running = False
        if self.server:
            await self.server.stop()
        io.echo("BED stopped", level="info")

    async def restart(self) -> None:
        """Restart the daemon."""
        await self.stop()
        await self.start()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="BED - BBS Engine Daemon")
    databasebuildargs(parser)
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to listen on (default: 8765)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--foreground", "-f",
        action="store_true",
        help="Run in foreground (don't daemonize)",
    )
    parser.add_argument(
        "--pidfile",
        help="Path to PID file",
    )
    parser.add_argument(
        "--router",
        default="defaultrouter",
        help="Module path to MessageRouter class (default: defaultrouter)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    if args.router == "defaultrouter":
        router_class = DefaultRouter
    else:
        module = importlib.import_module(args.router)
        router_class = getattr(module, "MessageRouter")

    bed = BED(args, router_class)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def signal_handler() -> None:
        io.echo("Received shutdown signal", level="info")
        asyncio.create_task(bed.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            pass

    try:
        loop.run_until_complete(bed.start())
    except Exception as e:
        io.echo_traceback(f"BED error: {e}")
        raise


if __name__ == "__main__":
    main()
