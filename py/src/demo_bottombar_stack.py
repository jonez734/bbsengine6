#!/usr/bin/env python3
"""
Demo of the new stack-based right side bottombar functionality.

Shows:
- Static strings in the right side stack
- Callable items that return dynamic strings
- Automatic notification status from bbsengine6
- Registration and unregistration
"""

import sys
import time

sys.path.insert(0, "/home/opencode/data/work/bbsengine6/py/src")

from bbsengine6.io.echo import echo
from bbsengine6 import io
from bbsengine6.io import screen, terminal


def static_item(**kwargs):
    """A simple static string item."""
    _ = kwargs
    return "static: hello"


def dynamic_item(**kwargs):
    """A callable that returns a dynamic value."""
    _ = kwargs
    return f"dynamic: {time.strftime('%H:%M:%S')}"


def player_status(**kwargs):
    """Example of a module-specific status callback."""
    player_name = kwargs.get("player", "Unknown")
    return f"player: {player_name}"


def run(args=None):
    io.echo("{f6:2}")
    screen.init()
    io.echo("")

    io.echo("{titlecolor}Stack-Based Bottombar Demo{/titlecolor}")
    io.echo("")
    io.echo("This demo shows the new right-side stack functionality:")
    io.echo("  - Items can be str or callable")
    io.echo("  - Callables are invoked with **kwargs on each render")
    io.echo("  - Items are joined with ' | ' separator")
    io.echo("  - Notifications (F2: notify) are prepended automatically")
    io.echo("")
    io.echo("Watch the bottom bar update as time passes...")
    io.echo("Press Ctrl+C to exit.")
    io.echo("")

    screen.register_bottombar(static_item)
    screen.register_bottombar("just a string")
    screen.register_bottombar(dynamic_item)
    screen.register_bottombar(lambda **kw: f"lambda: {1 + 1}")

    try:
        iteration = 0
        while True:
            screen.setbottombar(
                f"demo iteration {iteration}",
                player="TestPlayer",
            )
            io.echo(f"  Iteration {iteration} - checking stack...")
            time.sleep(2)
            iteration += 1

            if iteration == 3:
                io.echo("")
                io.echo("Removing dynamic_item from stack...", level="notice")
                screen.unregister_bottombar(dynamic_item)

            if iteration == 6:
                io.echo("")
                io.echo("Adding another static string...", level="notice")
                screen.register_bottombar("added at runtime")

            if iteration == 8:
                io.echo("")
                io.echo("Clearing entire stack...", level="notice")
                screen.rightstack.clear()
                screen.setbottombar("stack cleared", "no more items")
                break

    except KeyboardInterrupt:
        io.echo("")
        io.echo("Exiting... (Ctrl+C)")
    except EOFError:
        io.echo("")
        io.echo("Exiting... (Ctrl+D)")
    finally:
        echo(
            f"{{savecursor}}{{curpos:{terminal.height()},0}}{{el}}{{reset}}{{restorecursor}}"
        )

    io.echo("")
    io.echo("Stack contents at exit:")
    for i, item in enumerate(screen.rightstack):
        kind = "callable" if callable(item) else "str"
        io.echo(f"  [{i}] {kind}: {item if isinstance(item, str) else item.__name__}")

    screen.rightstack.clear()

    io.echo("")
    io.echo("Done!", level="success")
    return 0


if __name__ == "__main__":
    sys.exit(run())