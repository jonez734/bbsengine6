from .echo import echo, rendered_length, echo_traceback
from . import terminal

# terminal import lines as terminal_lines, columns as terminal_columns


# ------------------------
# screen related functions
# ------------------------

bottombarstack = []
rightstack = []


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


def register_bottombar(item):
    """Register a right-side item for the bottombar.

    Args:
        item: str or callable. Callables receive **kwargs and should return str.

    Returns:
        The registered item (same as input).
    """
    if item not in rightstack:
        rightstack.append(item)
    return item


def unregister_bottombar(item):
    """Unregister a right-side item from the bottombar.

    Args:
        item: str or callable to remove from the stack.

    Returns:
        True if item was found and removed, False otherwise.
    """
    if item in rightstack:
        rightstack.remove(item)
        return True
    return False


def _render_rightstack(**kwargs) -> str:
    """Render all registered right-side items as a joined string.

    Items are rendered in registration order, joined with ' | '.
    Callables are invoked with **kwargs; strs are used directly.
    Also includes notification status if there are unread messages.

    Returns:
        Combined string like "F2: notify (3) | murdermotel: 5 moves" or empty str.
    """
    parts = []

    for item in rightstack:
        if callable(item):
            try:
                result = item(**kwargs)
                if result:
                    parts.append(result)
            except Exception:
                echo_traceback("bbsengine6.io.screen._render_rightstack:")
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

    if right is None and rightstack:
        right_buf = _render_rightstack(**kwargs)
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
def popbottombar():
    global bottombarstack

    if len(bottombarstack) == 0:
        return

    if len(bottombarstack) > 0:
        buf = bottombarstack.pop()
        if buf != "":
            updatebottombar(f"{{var:areacolor}}{buf}{{/all}}")

    return


# @since 20240708
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
