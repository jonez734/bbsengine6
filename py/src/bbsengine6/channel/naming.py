# bbsengine6/channel/naming.py
# Channel naming convention helpers.
#
# The convention (from bbsengine6/TODO.md:257-265) is:
#   casino:table:<moniker>          # e.g. casino:table:blackjack-1
#   empyre:island:<id>              # e.g. empyre:island:5
#   empyre:ship:<id>                # e.g. empyre:ship:3
#   murdermotel:room:<id>           # e.g. murdermotel:room:entrance
#   member:<moniker>                # e.g. member:alice
#   system:shout                    # global chat (all connected users)
#   system:announcements            # sysop-only (reserved)
#
# These helpers are the single source of truth for those formats so
# typo'd format strings don't silently route messages to the wrong
# audience. Modules call ``naming.table_channel("casino", "blackjack-1")``
# instead of f-stringing it inline.
#
# Pervasive in-process callers should prefer these over inline f-strings
# so a future rename (e.g. ``casino:table:`` -> ``casino:tbl:``) is a
# one-line edit instead of a grep-and-replace across every module.

from typing import Tuple


def table_channel(app: str, moniker: str) -> str:
    """Per-table channel: ``<app>:table:<moniker>``."""
    return f"{app}:table:{moniker}"


def member_channel(moniker: str) -> str:
    """Per-member channel: ``member:<moniker>``."""
    return f"member:{moniker}"


def global_channel(app: str) -> str:
    """Per-app global channel: ``<app>:global``."""
    return f"{app}:global"


def announcement_channel() -> str:
    """System-wide announcements channel: ``system:announcements``."""
    return "system:announcements"


def shout_channel() -> str:
    """Global shout channel: ``system:shout``."""
    return "system:shout"


def parse_channel(name: str) -> Tuple[str, str, str]:
    """Decompose ``<app>:<kind>:<id>`` into a (app, kind, id) tuple.

    Returns ``("", "", name)`` when the name is not namespaced. The
    third element is the original ``name`` so callers can decide how
    to handle non-conforming channels.
    """
    if not isinstance(name, str) or ":" not in name:
        return ("", "", name or "")
    parts = name.split(":", 2)
    while len(parts) < 3:
        parts.append("")
    return (parts[0], parts[1], parts[2])
