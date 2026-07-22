from .echo import echo, echo_traceback, rendered_length
from . import terminal

import threading
import warnings
from typing import List


def _warn_shim_deprecated(name: str) -> None:
    """Emit a one-time-per-call-site DeprecationWarning for back-compat shims.

    The bbsengine6.io.screen bottombar-fragment API (setbottombar,
    register_bottombar_fragment, unregister_bottombar_fragment,
    clear_bottombar_fragments, _render_bottombar_fragments) is a back-compat
    shim. New code should import directly from bbsengine6.bottombar.
    """
    warnings.warn(
        f"bbsengine6.io.screen.{name} is a back-compat shim; "
        f"import from bbsengine6.bottombar instead.",
        DeprecationWarning,
        stacklevel=3,
    )

# terminal import lines as terminal_lines, columns as terminal_columns


# ------------------------
# screen related functions
# ------------------------

# Bottombar fragment handling now lives in bbsengine6.bottombar. The names
# below are kept here as thin shims so that pre-existing call sites
# (bbsengine6.io.screen.register_bottombar_fragment, _render_bottombar_fragments,
# _bottombar_fragments, etc.) continue to work without modification.
#
# The legacy `_bottombar_fragments` global was a plain list. It is now a
# `_LockedList` owned by the default FragmentRegistry, aliased here so
# that test code (and any other caller) that does
# `screen._bottombar_fragments.append(...)` / `.remove(...)` / `.clear()`
# continues to work. Both this alias and the registry's `items` attribute
# reference the same underlying list, so writes through one are visible
# to the other.

from .. import bottombar as _bottombar_mod

# Back-compat aliases onto the default registry's underlying list and lock.
# These are read by callers (and tests) that still touch
# `screen._bottombar_fragments` directly. They intentionally point at the
# *default* registry, not the ContextVar-routed one — door mode is the
# only mode that ever reads this alias. Per-connection routing goes
# through the shim functions below, which call
# `_bottombar_mod._resolve_registry()`.
_default_registry = _bottombar_mod.default_registry()
_bottombar_fragments = _default_registry.items
_bottombar_fragments_lock = _default_registry.lock

bottombarstack = []
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


# ---- Fragment registry back-compat shims --------------------------------
#
# _bottombar_fragments / _bottombar_fragments_lock are now aliases onto
# the default FragmentRegistry's _LockedList (see bbsengine6.bottombar).
# All mutating and reading ops go through that list's lock, so the
# snapshot taken during render() doesn't see a torn state.


def register_bottombar_fragment(item):
    """Back-compat shim — delegates to bbsengine6.bottombar.

    Deprecated: import bbsengine6.bottombar.register_bottombar_fragment
    directly. The shim will be removed in a future release.
    """
    _warn_shim_deprecated("register_bottombar_fragment")
    return _bottombar_mod.register_bottombar_fragment(item)


def unregister_bottombar_fragment(item):
    """Back-compat shim — delegates to bbsengine6.bottombar.

    Deprecated: import bbsengine6.bottombar.unregister_bottombar_fragment
    directly. The shim will be removed in a future release.
    """
    _warn_shim_deprecated("unregister_bottombar_fragment")
    return _bottombar_mod.unregister_bottombar_fragment(item)


def _render_bottombar_fragments(**kwargs) -> str:
    """Back-compat shim — delegates to bbsengine6.bottombar.

    Resolves the active registry through the bottombar ContextVar (BED
    per-connection override) or the named cache, falling back to the
    default registry. Calls `get_notification_status` (this module's
    function) so existing tests that
    `patch("bbsengine6.io.screen.get_notification_status")` keep
    working. Without this, the patch would target the wrong module.

    Deprecated: import bbsengine6.bottombar.render_for(name) or
    bbsengine6.bottombar.default_registry().render() directly. The
    shim will be removed in a future release.
    """
    _warn_shim_deprecated("_render_bottombar_fragments")
    registry = _bottombar_mod._resolve_registry()

    merged = dict(kwargs)
    if registry.args is not None and "args" not in merged:
        merged["args"] = registry.args
    if registry.player is not None and "player" not in merged:
        merged["player"] = registry.player
    if registry.pool is not None and "pool" not in merged:
        merged["pool"] = registry.pool

    items_snapshot = registry.items.snapshot()

    parts: List[str] = []

    for item in items_snapshot:
        if callable(item):
            try:
                result = item(**merged)
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
    """Back-compat shim — delegates to bbsengine6.bottombar.

    Preserves the original signature (left, right=None, **kwargs) used by
    callers like bbsengine6/console/lib.py and bbsengine6/demo_bottombar_stack.py
    that pass an explicit `right=...` callable or string. When `right` is
    None, the registered fragments are used (unchanged).

    Emits the result via the local `updatebottombar()` (not via
    bbsengine6.bottombar) so existing test code that does
    `patch("bbsengine6.io.screen.updatebottombar")` keeps working.

    Deprecated: call bbsengine6.bottombar.setbottombar(args, left) instead.
    The shim will be removed in a future release.
    """
    _warn_shim_deprecated("setbottombar")
    terminalwidth = terminal.width() - 2

    if callable(left) is True:
        left_buf = left(**kwargs)
    else:
        left_buf = left

    registry = _bottombar_mod._resolve_registry()
    if right is None:
        right_buf = registry.render(**kwargs) if len(registry) else ""
    elif callable(right) is True:
        right_buf = right(**kwargs)
    else:
        right_buf = right

    if right_buf is None:
        right_buf = ""

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

    Back-compat shim — delegates to bbsengine6.bottombar._get_notification_status.
    """
    args = kwargs.get("args", None)
    pool = kwargs.get("pool", None)
    return _bottombar_mod._get_notification_status(args=args, pool=pool, **kwargs)


# @since 20230523 copied from bbsengine5
def clear_bottombar_fragments() -> None:
    """Back-compat shim — delegates to bbsengine6.bottombar.

    Deprecated: import bbsengine6.bottombar.clear_bottombar_fragments
    directly. The shim will be removed in a future release.
    """
    _warn_shim_deprecated("clear_bottombar_fragments")
    _bottombar_mod.clear_bottombar_fragments()


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
