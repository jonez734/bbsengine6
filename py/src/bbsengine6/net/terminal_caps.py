"""Terminal capability reports from clients (the ``terminal_caps`` message).

A client runs :func:`bbsengine6.io.terminal.report` in the process that owns the
member's terminal, then sends the result here. The server only validates and stores it; it
never probes a remote terminal, because its own tty and environment describe the server, not
the member.

Wire shapes:

  request:  {"type": "terminal_caps", "request_id": ..., "caps": {...}}
  reply:    {"type": "terminal_caps_ack", "request_id": ..., "stored": true}
            or {"type": "terminal_caps_ack", "request_id": ..., "stored": false,
                "error": "<reason>"}

Accepted ``caps`` fields (all optional except ``source``):

  term        str, at most 64 chars, the TERM the client used
  color       "truecolor" | "256" | null: the colour level the client can use
  source      "query" | "colorterm" | "screen" | "unknown"
  ansi        str or null, at most 64 chars, the DA reply text

Anything else is rejected, so an unknown field is an error rather than silently kept.
"""

from __future__ import annotations

import weakref
from typing import Any, Dict, Optional

__all__ = [
    "MAX_TERM_LEN",
    "MAX_ANSI_LEN",
    "COLOR_LEVELS",
    "SOURCES",
    "TerminalCapsError",
    "validate_terminal_caps",
    "store_terminal_caps",
    "get_terminal_caps",
    "forget_terminal_caps",
    "handle_terminal_caps",
]

MAX_TERM_LEN = 64
MAX_ANSI_LEN = 64
COLOR_LEVELS = ("truecolor", "256", None)
SOURCES = ("query", "colorterm", "screen", "unknown")
_FIELDS = {"term", "color", "source", "ansi"}


class TerminalCapsError(ValueError):
    """The terminal_caps payload is malformed. The message is safe to send to the client."""


def validate_terminal_caps(caps: Any) -> Dict[str, Any]:
    """Return a cleaned copy of ``caps``, or raise :class:`TerminalCapsError`."""
    if not isinstance(caps, dict):
        raise TerminalCapsError("caps must be an object")
    unknown = set(caps) - _FIELDS
    if unknown:
        raise TerminalCapsError(f"unknown field: {sorted(unknown)[0]}")
    if caps.get("source") not in SOURCES:
        raise TerminalCapsError("source must be query, colorterm, screen, or unknown")

    clean: Dict[str, Any] = {"source": caps["source"]}

    term = caps.get("term", "")
    if not isinstance(term, str) or len(term) > MAX_TERM_LEN:
        raise TerminalCapsError("term must be a string of at most 64 characters")
    clean["term"] = term

    color = caps.get("color")
    if color not in COLOR_LEVELS:
        raise TerminalCapsError('color must be "truecolor", "256", or null')
    clean["color"] = color

    ansi = caps.get("ansi")
    if ansi is not None and (not isinstance(ansi, str) or len(ansi) > MAX_ANSI_LEN):
        raise TerminalCapsError("ansi must be a string of at most 64 characters or null")
    clean["ansi"] = ansi
    return clean


# Stored per connection. A weak key lets the entry go with the socket, so a closed
# connection never leaves caps behind.
_store: "weakref.WeakKeyDictionary[Any, Dict[str, Any]]" = weakref.WeakKeyDictionary()


def store_terminal_caps(websocket: Any, caps: Dict[str, Any]) -> None:
    """Keep ``caps`` for this connection, replacing any earlier report."""
    _store[websocket] = caps


def get_terminal_caps(websocket: Any) -> Optional[Dict[str, Any]]:
    """The caps a client reported on this connection, or None when it reported none."""
    return _store.get(websocket)


def forget_terminal_caps(websocket: Any) -> None:
    """Drop the caps for this connection (called when it closes)."""
    _store.pop(websocket, None)


def handle_terminal_caps(websocket: Any, message: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and store a ``terminal_caps`` message. Returns the ack to send back."""
    request_id = message.get("request_id")
    try:
        clean = validate_terminal_caps(message.get("caps"))
    except TerminalCapsError as exc:
        return {
            "type": "terminal_caps_ack",
            "request_id": request_id,
            "stored": False,
            "error": str(exc),
        }
    store_terminal_caps(websocket, clean)
    return {"type": "terminal_caps_ack", "request_id": request_id, "stored": True}
