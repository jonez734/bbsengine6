import logging
import logging.handlers
import os

from typing import Optional, Union

from . import conf


# Define the get_safe_path function within the utility module
def safe_path(
    *components: Union[str, os.PathLike],
    base_dir: Optional[Union[str, os.PathLike]] = None,
    must_exist: bool = False,
    resolve_symlinks: bool = True,
) -> str:
    """
    Construct a robust, secure, and flexible filesystem path.

    Expands user (~) and environment variables, normalizes, makes the path absolute,
    and (optionally) ensures it stays within a specified base directory (security check).

    Parameters
    ----------
    *components : str | os.PathLike
        Path components to join, e.g. ("~/data", "images", "foo.png").
    base_dir : str | os.PathLike | None
        Optional. If given, ensures the resulting path is inside this directory
        and validates that the base_dir exists and is a directory.
    must_exist : bool
        If True, raises FileNotFoundError if the final path does not exist.
    resolve_symlinks : bool
        If True, resolves symbolic links before applying traversal checks.

    Returns
    -------
    str
        The fully resolved, absolute, normalized safe path.

    Raises
    ------
    ValueError
        If directory traversal, path escape outside base_dir is detected, or base_dir doesn't exist.
    FileNotFoundError
        If must_exist=True and the path does not exist.
    """

    if not components:
        raise ValueError("At least one path component must be provided.")

    # 1. Expand ~ and environment variables
    expanded = [os.path.expandvars(os.path.expanduser(str(c))) for c in components]

    # 2. Join, normalize, and make absolute
    # Strip leading slashes from all components except the first to prevent
    # absolute paths from overriding previous components (os.path.join behavior)
    normalized = [expanded[0]] + [c.lstrip('/') for c in expanded[1:]]
    joined_path = os.path.normpath(os.path.join(*normalized))
    abs_path = os.path.abspath(joined_path)

    # 3. Optionally resolve symlinks for maximum safety
    # os.path.realpath is preferred for security as it resolves all symlinks
    resolved_path = os.path.realpath(abs_path) if resolve_symlinks else abs_path

    # 4. Traversal/Containment Check (The security feature)
    if base_dir is not None:
        base_dir_expanded = os.path.expandvars(os.path.expanduser(str(base_dir)))
        base_dir_abs = os.path.abspath(base_dir_expanded)
        base_dir_resolved = (
            os.path.realpath(base_dir_abs) if resolve_symlinks else base_dir_abs
        )

        # Security Check 1: Base directory must exist and be a directory
        if not os.path.isdir(base_dir_resolved):
            raise ValueError(
                f"Invalid base_dir: Base directory must exist and be a directory: {base_dir_resolved}"
            )

        # Security Check 2: Check for path escape (directory traversal)
        # Ensure resolved_path starts with base_dir_resolved plus the separator
        # OR is exactly the base_dir_resolved path (if the target IS the base dir).
        is_contained = (
            resolved_path.startswith(base_dir_resolved + os.sep)
            or resolved_path == base_dir_resolved
        )

        if not is_contained:
            raise ValueError(
                f"Invalid path: {resolved_path} is outside allowed base_dir {base_dir_resolved}"
            )

    # 5. Existence Check
    if must_exist and not os.path.exists(resolved_path):
        raise FileNotFoundError(f"Path not found: {resolved_path}")

    return resolved_path


get_safe_path = safe_path

# default syslog handler
default_handler = logging.handlers.SysLogHandler(address="/dev/log")
default_formatter = logging.Formatter(
    "%(name)s[%(process)d]: %(levelname)s %(message)s"
)
default_handler.setFormatter(default_formatter)


def logentry(
    message,
    level=logging.INFO,
    *,
    handler=None,
    formatter=None,
    logger_name=conf.LOGGER_NAME,
):
    """
    Write a log entry to syslog (by default), with optional handler/formatter overrides.

    Args:
        message (str): The log message.
        level (int): Logging level (default=logging.INFO).
        handler (logging.Handler, optional): Custom logging handler.
        formatter (logging.Formatter, optional): Custom formatter.
        logger_name (str): Name for the logger (default="myapp").
    """

    h = handler or default_handler
    f = formatter or default_formatter

    # Ensure formatter is applied
    h.setFormatter(f)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)  # capture all levels
    if not any(isinstance(x, type(h)) for x in logger.handlers):
        logger.addHandler(h)

    levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARNING,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
        #        "exception":logging.EXCEPTION,
    }

    if level in levels:
        level = levels[level]
    else:
        level = logging.NOTSET

    logger.log(level, message)
    return


def safe_distance(p1, p2):
    """
    Compute Euclidean distance between two points.

    Supports:
    - 2D points (x, y)
    - 3D points (x, y, z)
    - Input as tuple, list, or numpy array

    Returns:
        float: Euclidean distance

    Raises:
        ValueError: if points are invalid or have mismatched dimensions
    """
    import math

    # Convert to list/tuple if NumPy array
    try:
        p1 = tuple(p1)
        p2 = tuple(p2)
    except TypeError:
        raise ValueError(
            f"safe_distance: Points must be iterable, got {type(p1)} and {type(p2)}"
        )

    if len(p1) != len(p2):
        raise ValueError(
            f"safe_distance: Points must have same dimensions, got {len(p1)} and {len(p2)}"
        )

    # Compute Euclidean distance
    squared_diff_sum = sum((a - b) ** 2 for a, b in zip(p1, p2))
    return math.sqrt(squared_diff_sum)
