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
)

__all__ = [
    "init",
    "updatebottombar",
    "setbottombar",
    "popbottombar",
    "poparea",
    "get_notification_status",
    "updateprogress",
    "bottombarstack",
]
