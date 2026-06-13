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
