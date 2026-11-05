from .const import FALLBACK_TERMINAL_WIDTH, OSC, ST

import os
import shutil

MAX_WIDTH = 120


def size() -> os.terminal_size:
    return shutil.get_terminal_size()


def columns():
    """
    Return terminal width in columns, clamped to MAX_WIDTH (or env var BBSENGINE_MAX_WIDTH).
    On OSError (unable to determine size) return a sane fallback (100).
    """
    try:
        w = size()[0]
    except OSError:
        return FALLBACK_TERMINAL_WIDTH

    max_width = os.environ.get("BBSENGINE_MAX_WIDTH")
    if max_width is not None:
        try:
            max_width = int(max_width)
        except ValueError:
            max_width = MAX_WIDTH
    else:
        max_width = MAX_WIDTH

    return min(w, max_width)


width = columns


def lines():
    return size().lines


height = lines


def title(t: str) -> None:
    """Set the terminal window title."""
    from .common import write_current_output_stream

    write_current_output_stream(f"{OSC}0;{t}{ST}", flush=True)


#: Fallback when neither the client TERM nor the member's stored type has a terminfo entry.
DEFAULT_TERM = "xterm"

#: TERM values that cannot drive a full-screen program (refused, not resolved).
UNUSABLE_TERMS = ("", "dumb")


def resolve(stored=None, client=None):
    """Return ``(value, source)`` for the terminal type to use.

    Order: the client's TERM when it has a terminfo entry (``client``), else the member's
    stored terminal type when valid (``stored``), else ``xterm`` (``default``). A client
    TERM with no entry is rejected by :func:`resolve_notice`, not here.
    """
    from . import terminfo

    if client is None:
        client = os.environ.get("TERM", "")
    if client not in UNUSABLE_TERMS and terminfo.has_entry(client):
        return client, "client"
    if stored and terminfo.has_entry(stored):
        return stored, "stored"
    return DEFAULT_TERM, "default"


def resolve_notice(stored=None, client=None):
    """Return a notice when the client TERM was rejected for having no terminfo entry."""
    if client is None:
        client = os.environ.get("TERM", "")
    if client in UNUSABLE_TERMS:
        return None
    from . import terminfo

    if terminfo.has_entry(client):
        return None
    value, _ = resolve(stored=stored, client=client)
    return f"TERM {client!r} has no terminfo entry; using {value!r} instead."
