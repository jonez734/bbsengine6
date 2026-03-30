"""
Verify system login ID and machine account configuration.

Checks that the current system login ID exists and is properly configured
for BBS engine database operations. Validates machine account settings for
the system user running the BBS engine.
"""

import dbus
from dbus.exceptions import DBusException

from bbsengine6 import io, util


def init(args, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, **kwargs) -> bool:
    return True


def _get_user_properties(username: str) -> dict | None:
    """
    Fetch user properties from system via DBus AccountsService.

    Args:
        username: System username to look up

    Returns:
        dict of user properties or None if user not found
    """
    try:
        system_bus = dbus.SystemBus()
        accounts_service = system_bus.get_object(
            "org.freedesktop.Accounts", "/org/freedesktop/Accounts"
        )
        accounts_interface = dbus.Interface(
            accounts_service, "org.freedesktop.Accounts"
        )
        user_path = accounts_interface.FindUserByName(username)

        user_object = system_bus.get_object("org.freedesktop.Accounts", user_path)
        user_interface = dbus.Interface(user_object, dbus.PROPERTIES_IFACE)

        properties = {
            "username": user_interface.Get("org.freedesktop.Accounts.User", "UserName"),
            "real_name": user_interface.Get(
                "org.freedesktop.Accounts.User", "RealName"
            ),
            "home_directory": user_interface.Get(
                "org.freedesktop.Accounts.User", "HomeDirectory"
            ),
            "shell": user_interface.Get("org.freedesktop.Accounts.User", "Shell"),
            "enabled": user_interface.Get("org.freedesktop.Accounts.User", "Enabled"),
        }
        return properties

    except DBusException as e:
        if "org.freedesktop.Accounts.Error.UserDoesNotExist" in str(e):
            return None
        io.echo(f"DBus error checking user: {e}", level="error")
        return None


def main(args, **kwargs) -> bool:
    """
    Verify current login ID and machine account configuration.

    Returns:
        bool: True if login ID is valid and properly configured
    """
    current_loginid = util.getcurrentloginid(args)

    io.echo(
        f"{{var:labelcolor}}login id {{var:valuecolor}}{current_loginid}{{var:labelcolor}}: ",
        end="",
    )

    user_props = _get_user_properties(current_loginid)

    if user_props is None:
        io.echo("not found", level="error")
        return False

    if not user_props.get("enabled", False):
        io.echo("disabled", level="error")
        return False

    io.echo("ok", level="ok")
    return True
