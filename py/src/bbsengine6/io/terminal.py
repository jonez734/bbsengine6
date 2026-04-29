from .const import MAX_TERMINAL_WIDTH, FALLBACK_TERMINAL_WIDTH, OSC, ST

import shutil
import os


def size() -> os.terminal_size:
    return shutil.get_terminal_size()


def columns():
    """
    Return terminal width in columns. If MAX_TERMINAL_SIZE is None, return the
    terminal's actual width. If MAX_TERMINAL_SIZE is an int, clamp to it.
    On OSError (unable to determine size) return a sane fallback (100).
    """
    try:
        w = size()[0]
    except OSError:
        # Couldn't query terminal size — return fallback.
        return FALLBACK_TERMINAL_WIDTH

    # If MAX_TERMINAL_SIZE is None -> use actual width.
    if MAX_TERMINAL_WIDTH is None:
        return w

    # Otherwise clamp to the configured maximum (ensure it's an int)
    try:
        max_sz = int(MAX_TERMINAL_WIDTH)
    except (TypeError, ValueError):
        # If it's somehow invalid, fall back to the terminal width.
        return w

    return min(w, max_sz)


width = columns


def lines():
    return size().lines


height = lines


def title(t: str) -> None:
    """Set the terminal window title."""
    from .common import write_current_output_stream

    write_current_output_stream(f"{OSC}0;{t}{ST}", flush=True)
