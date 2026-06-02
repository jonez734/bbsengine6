from .echo import echo, rendered_length, echo_traceback
from . import terminal

import threading

# terminal import lines as terminal_lines, columns as terminal_columns


# ------------------------
# screen related functions
# ------------------------

bottombarstack = []
_bottombar_fragments = []
_bottombar_fragments_lock = threading.Lock()
_bottombarstack_lock = threading.Lock()


def init(args=None, topmargin=1, bottommargin=1):
    echo("{f6:3}{cursorup:3}", end="", flush=True)
    h = terminal.lines() - bottommargin
    #  logentry(f"asimov.io.util.screen_init.100: {topmargin=} {h=}", level="debug")
    echo(f"{{savecursor}}", end="")
    echo(f"{{decstbm:{topmargin},{h}}}", end="")
    echo(f"{{restorecursor}}", flush=True, end="")

    #  terminalheight = ttyio.getterminalheight()
    #  ttyio.echo(f"{{decsc}}{{decstbm:{topmargin},{terminalheight-bottommargin}}}{{decrc}}") #  % (topmargin, terminalheight-bottommargin)) #  % (topmargin, terminalheight-bottommargin))

    return


def updatebottombar(buf: str) -> None:
    """Render the bottom bar on the last terminal line without line wrapping."""
    echo(
        f"{{savecursor}}{{bottombarcolor}}{{curpos:{terminal.lines()},0}}{buf}{{restorecursor}}",
        wordwrap=False,
        end="",
        flush=True,
    )
    return


def register_bottombar_fragment(item):
    """Register a fragment for the bottombar right side.

    Args:
        item: str or callable. Callables receive **kwargs and should return str.

    Returns:
        The registered item (same as input).
    """
    with _bottombar_fragments_lock:
        if item not in _bottombar_fragments:
            _bottombar_fragments.append(item)
    return item


def unregister_bottombar_fragment(item):
    """Unregister a fragment from the bottombar right side.

    Args:
        item: str or callable to remove from the fragments list.

    Returns:
        True if item was found and removed, False otherwise.
    """
    with _bottombar_fragments_lock:
        if item in _bottombar_fragments:
            _bottombar_fragments.remove(item)
            return True
    return False


def _render_bottombar_fragments(**kwargs) -> str:
    """Render all registered fragments for the bottombar right side.

    Fragments are rendered in registration order, joined with ' | '.
    Callables are invoked with **kwargs; strs are used directly.
    Also includes notification status if there are unread messages.

    Returns:
        Combined string like "F2: notify (3) | murdermotel: 5 moves" or empty str.
    """
    with _bottombar_fragments_lock:
        items_snapshot = list(_bottombar_fragments)

    parts = []

    for item in items_snapshot:
        if callable(item):
            try:
                result = item(**kwargs)
                if result:
                    parts.append(str(result))
            except Exception:
                echo_traceback("bbsengine6.io.screen._render_bottombar_fragments:")
        elif item:
            parts.append(str(item))

    notification_status = get_notification_status(**kwargs)
    if notification_status:
        parts.insert(0, notification_status)

    return " | ".join(parts)


# @since 20230523 copied from bbsengine5
# @since 20250517 rewrite
# from wcwidth import wcswidth, wcwidth
def setbottombar(left, right=None, **kwargs):
    terminalwidth = terminal.width() - 2

    if callable(left) is True:
        left_buf = left(**kwargs)
    else:
        left_buf = left

    if right is None and _bottombar_fragments:
        right_buf = _render_bottombar_fragments(**kwargs)
    elif callable(right) is True:
        right_buf = right(**kwargs)
    else:
        right_buf = right

    left_len = rendered_length(left_buf)
    right_len = rendered_length(right_buf)
    max_left_len = terminalwidth - right_len
    if left_len > max_left_len:
        left_buf = left_buf[: max_left_len - 5] + "..."
    padding = " " * (terminalwidth - left_len - right_len)
    updatebottombar(f"{{bottombarcolor}}{left_buf}{padding}{right_buf}{{/all}}")
    return True


# @since 20240708
# @since 20240517
# @since 20251208
setarea = setbottombar


# @since 20260327 - notification status for bottombar right side
def get_notification_status(**kwargs) -> str:
    """Get notification status string for bottombar right side.

    Returns:
        "F2: notify (N)" if notifications > 0, else empty string.
    """
    try:
        from bbsengine6 import notify
        from bbsengine6.member import _threadlocal

        # Get moniker from thread-local storage (already logged in)
        moniker = getattr(_threadlocal, "moniker", None)
        if not moniker:
            return ""

        count = notify.count(moniker, **kwargs)
        if count and count > 0:
            return f"F2: notify ({count})"
    except Exception:
        echo_traceback("bbsengine6.io.screen.91:")
    return ""


# @since 20230523 copied from bbsengine5
def clear_bottombar_fragments() -> None:
    """Remove all registered fragments from the bottombar right side.

    Useful when exiting a mode (e.g. playground) that may have added
    context-specific fragments, returning to a cleaner lobby state.
    """
    with _bottombar_fragments_lock:
        _bottombar_fragments.clear()


def popbottombar():
    with _bottombarstack_lock:
        if not bottombarstack:
            return
        buf = bottombarstack.pop()
    if buf != "":
        updatebottombar(f"{{var:areacolor}}{buf}{{/all}}")
    return


poparea = popbottombar

# @since 20230523
##def title(buf):
##  return io.terminal.title(buf)


# @since 20210301
# @see https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
# @since 20240102 copied to bbsengine6
def updateprogress(iteration, total, fill="#"):
    terminalwidth = terminal.width()
    decimals = 0
    length = terminalwidth - 20
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = length * iteration // total
    bar = fill * filledLength + "." * (length - filledLength)
    buf = f"{{var:labelcolor}}Progress [{{var:valuecolor}}{percent:3s}%{{var:labelcolor}}]: [{bar}]{{/fgcolor}}"
    updatebottombar(buf)
    return
