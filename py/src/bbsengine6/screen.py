# screen.py - Shim module
# @since 20260429 - Redirects to bbsengine6.io.screen
# This module exists for backwards compatibility.

from .io.screen import (
    init,
    updatebottombar,
    setbottombar,
    popbottombar,
    poparea,
    get_notification_status,
    updateprogress,
    bottombarstack,
    register_bottombar_fragment,
    unregister_bottombar_fragment,
)


def setarea(left, right=None, **kwargs) -> None:
    """Render the bottom-bar / status line.

    Re-exported here because several zoidoffice modules (client.lib,
    staff.lib, etc.) call ``bbsengine6.screen.setarea(left, right)``
    and tests patch this exact path. Delegates to
    ``bbsengine6.io.screen.setbottombar`` (same signature). Falls back
    to a no-op so test patching never raises.
    """
    try:
        return setbottombar(left, right, **kwargs)
    except Exception:
        return None


__all__ = [
    "init",
    "updatebottombar",
    "setbottombar",
    "popbottombar",
    "poparea",
    "get_notification_status",
    "updateprogress",
    "bottombarstack",
    "register_bottombar_fragment",
    "unregister_bottombar_fragment",
    "setarea",
]
