"""
group.py - Group management for notification system.

Provides functional group operations: validation, existence checks, and member retrieval.
Supports nested groups with automatic cycle detection and duplicate removal.
"""

from bbsengine6 import database, io


def validate_name(group_name: str) -> None:
    """Validate group name format.

    Raises:
        ValueError: If group name is invalid
    """
    if not group_name or not isinstance(group_name, str):
        raise ValueError("Invalid group name: must be non-empty string")

    if group_name.startswith("@"):
        raise ValueError("Invalid group name: cannot start with '@'")

    if " " in group_name:
        raise ValueError("Invalid group name: cannot contain spaces")

    if len(group_name) > 100:
        raise ValueError(
            f"Invalid group name: exceeds 100 characters ({len(group_name)})"
        )

    # Validate printable ASCII only (0x20 to 0x7E)
    for i, char in enumerate(group_name):
        code = ord(char)
        if code < 0x20 or code > 0x7E:
            raise ValueError(
                f"Invalid group name: contains non-printable character at position {i}: "
                f"{repr(char)} (0x{code:02x}). Only ASCII (0x20-0x7E) allowed."
            )


def exists(args, group_name: str, **kwargs) -> bool | None:
    """Check if a group exists in the database.

    Validates group name format and checks existence in engine.__notify_group.

    Args:
        args: Application args
        group_name: Group name to validate (case-sensitive)
        **kwargs: Optional - pool, conn

    Returns:
        bool: True if group exists, False if not, None on error

    Raises:
        ValueError: If group_name format is invalid

    Examples:
        >>> exists(args, "ops", pool=pool)
        True
        >>> exists(args, "nonexistent", pool=pool)
        False
    """
    validate_name(group_name)

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo("bbsengine6.group.exists.100: pool=None", level="error")
            return None
        conn = database.connect(args, pool=pool)

    try:
        with database.cursor(conn) as cur:
            sql = "SELECT 1 FROM engine.__notify_group WHERE group_name=%s LIMIT 1"
            dat = (group_name,)
            cur.execute(sql, dat)
            return cur.rowcount > 0
    except Exception:
        io.echo_traceback("bbsengine6.group.exists.100:")
        return None


def get_members(args, group_name: str, **kwargs) -> list[str] | None:
    """Get all member monikers in a group, recursively expanding nested groups.

    Retrieves all members of a notification group from engine.__notify_group,
    recursively expanding any nested groups. Includes cycle detection to prevent
    infinite loops from circular group references.

    Args:
        args: Application args
        group_name: Name of the group
        **kwargs: Optional - pool, conn, _visited (internal: set of visited groups for cycle detection)

    Returns:
        list[str]: List of member monikers in the group (empty list if no members)
        None: On error

    Raises:
        ValueError: If group_name format is invalid or circular reference detected

    Examples:
        >>> get_members(args, "ops", pool=pool)
        ["alice", "bob", "charlie"]
        >>> get_members(args, "empty", pool=pool)
        []
    """
    validate_name(group_name)

    # Initialize visited set for cycle detection
    visited = kwargs.get("_visited", None)
    if visited is None:
        visited = set()
    else:
        visited = set(visited)

    # Detect circular references
    if group_name in visited:
        raise ValueError(
            f"Circular group reference detected: {group_name} is already being expanded"
        )

    visited.add(group_name)

    # Get group members
    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo("bbsengine6.group.get_members.100: pool=None", level="error")
            return None
        conn = database.connect(args, pool=pool)

    try:
        with database.cursor(conn) as cur:
            sql = (
                "SELECT member_moniker FROM engine.__notify_group "
                "WHERE group_name=%s ORDER BY member_moniker"
            )
            dat = (group_name,)
            cur.execute(sql, dat)

            if cur.rowcount == 0:
                return []

            members = []
            for row in cur.fetchall():
                if isinstance(row, dict):
                    member_moniker = row.get("member_moniker")
                else:
                    member_moniker = row[0]

                if not member_moniker:
                    continue

                # Check if this member is itself a group
                is_nested_group = exists(args, member_moniker, conn=conn)

                if is_nested_group:
                    # Recursively expand nested group with cycle detection
                    nested_members = get_members(
                        args,
                        member_moniker,
                        conn=conn,
                        _visited=visited,
                    )
                    if nested_members is not None:
                        members.extend(nested_members)
                else:
                    # Regular member (moniker)
                    members.append(member_moniker)

            # Remove duplicates while preserving order
            seen = set()
            unique_members = []
            for member in members:
                if member not in seen:
                    seen.add(member)
                    unique_members.append(member)

            return unique_members
    except ValueError:
        # Re-raise validation errors (like circular reference detection)
        raise
    except Exception:
        io.echo_traceback("bbsengine6.group.get_members.100:")
        return None
