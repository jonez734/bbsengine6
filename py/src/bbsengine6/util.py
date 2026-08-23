# util.py
# General-purpose utilities for the BBS engine
#
# This module provides utility functions for logging, terminal output, data parsing,
# file operations, and other common BBS operations. Functions are organized by category:
# - Terminal/Output: hr(), heading(), strip_ansi()
# - Text Utilities: pluralize(), oxfordcomma(), datestamp(), timedeltastr()
# - Range Parsing: expandrange(), collapserange(), rangestr()
# - Input: inputpassword()
# - File/Directory Verification: verify_dir_exists_writable(),
#   verify_file_exists_readable(), verify_file_exists_readable_writable()
#   (deprecated camelCase aliases available for BC)
# - System: getremoteaddr(), getcurrentloginid(), init()
# - Logging: logentry()
# - Other: diceroll(), checksum(), tobool(), ltree_to_path(), chop_last_element(),
#   get_safe_path(), load_sql(), serialize_datetimes(), getencryptedpassword(),
#   filedisplay()
#
# ERROR HANDLING PATTERNS:
# - User-facing errors: Functions like verify_*() use io.echo(..., level="error")
#   to output errors directly to the user and return False on failure
# - Validation errors: Functions like expandrange(), collapserange() raise
#   ValueError or TypeError for invalid input
# - Data transformation: Functions like datestamp(), timedeltastr() may raise
#   AssertionError or other exceptions if given unexpected types
# - Database operations: Functions like getencryptedpassword() return None on
#   database failures
#
# pyright: ignore[import-not-found, reportMissingTypeHints]

import io
import logging
import logging.handlers
import os
import random
import re
import threading
import warnings
from datetime import datetime
from typing import Any, Optional

from . import input, io  # type: ignore

LOGGER_NAME = "bbsengine6"

# Terminal display constants
HR_WIDTH_OFFSET = 2  # Reduction from terminal width for hr() function
HEADING_WIDTH_OFFSET = 4  # Reduction from terminal width for heading()
HEADING_PADDING_ODD_ADJUSTMENT = 2  # Padding adjustment for odd-length titles
PAGINATION_PAGE_SIZE = 20  # Lines per page in filedisplay() with more=True

# Range constants
RANGE_COLLAPSE_MIN_LENGTH = (
    2  # Minimum consecutive numbers to form a range (not collapse to singles)
)

# CRC32 checksum constants
CRC32_INIT = 0xFFFFFFFF  # Initial CRC value
CRC32_POLY = 0xEDB88320  # CRC32 polynomial
CRC32_XOROUT = 0xFFFFFFFF  # Final CRC XOR value

_log_lock = threading.Lock()
_default_handler: Optional[logging.handlers.SysLogHandler] = None


def _get_default_handler() -> logging.handlers.SysLogHandler:
    """Get or create the default syslog handler for BBS engine logging.

    Returns:
        A SysLogHandler configured with standard BBS engine format.
    """
    global _default_handler
    if _default_handler is None:
        _default_handler = logging.handlers.SysLogHandler(address="/dev/log")
        _default_handler.setFormatter(
            logging.Formatter("%(name)s[%(process)d]: %(levelname)s %(message)s")
        )
    return _default_handler


def hr(
    acs: bool = True,
    width: Optional[int] = None,
    end: str = "\n",
    color: str = "{boxcolor}",
) -> bool:
    """Display a horizontal rule using box-drawing characters.

    Args:
        acs: Use ASCII-compatible characters (currently unused, for future compatibility).
        width: Width of the horizontal rule in characters. If None, uses terminal width minus HR_WIDTH_OFFSET.
        end: String to output after the rule (default: newline).
        color: io.echo color spec applied to the rule (default: {boxcolor}).

    Returns:
        Always returns True.

    Example:
        >>> hr()  # Outputs horizontal line at terminal width
        >>> hr(width=40)  # Outputs 40-character horizontal line
        >>> hr(color="{/all}{red}")  # Red rule (e.g. for failure summary)
    """
    if width is None:
        width = io.terminal.width() - HR_WIDTH_OFFSET  # type: ignore
    io.echo(f" {color}{{hline:{width}}}{{/all}}", end=end)
    return True


def heading(title: str, **kwargs) -> None:
    """Display a centered heading with box-drawing borders.

    Creates a box with the title centered inside using terminal width.
    The heading uses box-drawing characters and BBS color tags.

    Args:
        title: The heading text to display (will be centered).
        **kwargs: Additional keyword arguments (unused, for future compatibility).

    Example:
        >>> heading("Main Menu")
        # Displays:
        # ┌────────────────────────┐
        # │      Main Menu         │
        # └────────────────────────┘
    """
    width = io.terminal.width() - HEADING_WIDTH_OFFSET  # type: ignore
    w = width - len(title)
    if w % 2 == 0:
        repeat = w // 2
        leftpadding = " " * repeat
        rightpadding = " " * repeat
    else:
        repeat = (w - HEADING_PADDING_ODD_ADJUSTMENT) // 2
        leftpadding = " " * (repeat + HEADING_PADDING_ODD_ADJUSTMENT)
        rightpadding = " " * (repeat + 1)

    io.echo(
        f"{{/all}}{{normalcolor}} {{boxcolor}}{{ulcorner}}{{hline:{width}}}{{urcorner}}",
        wordwrap=False,
        end="\n",
    )
    io.echo(
        f" {{boxcolor}}{{vline}}{{titlecolor}}{leftpadding}{title}{rightpadding}{{/all}}{{boxcolor}}{{vline}}",
        wordwrap=False,
        end="\n",
    )
    io.echo(
        f" {{llcorner}}{{hline:{width}}}{{lrcorner}}{{/all}}{{f6}}",
        wordwrap=False,
        end="",
    )


def pluralize(
    amount: int,
    singular: str,
    plural: str,
    quantity: bool = True,
    emoji: str = "",
    determiner: str = "a",
    **kw,
) -> str:
    """Format a count with a singular or plural noun phrase.

    Args:
        amount: Coerced to int. 0 yields the plural with a "no" prefix,
            1 yields the singular (with determiner or count), any other
            value (including negatives) yields the plural with the count.
        singular: Singular form of the noun. Required.
        plural: Plural form of the noun. Required. Empty strings are tolerated.
        quantity: If True (default), include the count or determiner in the
            output. If False, return only the noun (with emoji prefix).
        emoji: Optional string prepended to the output. When non-empty, a
            single space separates the emoji from the rest of the phrase.
            When empty, no leading space is produced.
        determiner: Article used for the singular form, e.g. "a", "an"
            (default: "a"). Set to "" to use the count instead of an article.
        **kw: Silently absorbed. Supports the common pattern of spreading
            a caller-side resource dict (e.g. ``**coinres``) without forcing
            every key to be a named parameter.

    Returns:
        A formatted phrase such as "5 apples", "a apple", "no apples",
        or ":moneybag: 5 apples".

    Raises:
        TypeError: If ``amount`` is not coercible to int, or if
            ``singular``/``plural``/``amount`` are bound by both a
            positional argument and ``**kw`` in the same call.
        ValueError: If ``amount`` is a string that is not a valid int literal.

    Examples:
        >>> pluralize(0, "apple", "apples")
        'no apples'
        >>> pluralize(1, "apple", "apples")
        'a apple'
        >>> pluralize(5, "apple", "apples")
        '5 apples'
        >>> pluralize(1, "apple", "apples", determiner="an")
        'an apple'
        >>> pluralize(5, "apple", "apples", emoji=":moneybag:")
        ':moneybag: 5 apples'
        >>> pluralize(1, "apple", "apples", emoji=":moneybag:")
        ':moneybag: a apple'
        >>> pluralize(0, "apple", "apples", emoji=":moneybag:")
        ':moneybag: no apples'
    """
    amount = int(amount)
    prefix = f"{emoji} " if emoji else ""

    if amount == 0:
        if quantity is True:
            return f"{prefix}no {plural}"
        return f"{prefix}{plural}"

    if amount == 1:
        if quantity is True:
            if determiner:
                return f"{prefix}{determiner} {singular}"
            return f"{prefix}{amount} {singular}"
        return f"{prefix}{singular}"

    if quantity is True:
        return f"{prefix}{amount:d} {plural}"
    return f"{prefix}{plural}"


def datestamp(
    t: Optional[object] = None, format: str = "%Y-%m-%d %I:%M%P %Z (%a)"
) -> str:
    """Convert a datetime value to a formatted string representation.

    Args:
        t: The time value to format. Can be:
           - None: uses current time
           - int/float: treated as Unix timestamp
           - str: parsed via input.getdate()
           - datetime: used as-is
        format: strftime format string (default: "%Y-%m-%d %I:%M%P %Z (%a)").

    Returns:
        Formatted datetime string.

    Raises:
        AssertionError: If t is not a recognized type.

    Examples:
        >>> datestamp()  # Current time
        '2026-05-19 02:30PM EDT (Mon)'
        >>> datestamp(0)  # Unix epoch
        '1970-01-01 08:00PM EST (Thu)'
    """
    from dateutil.tz import tzlocal
    from time import tzset

    tzset()

    if isinstance(t, (int, float)):
        t = datetime.fromtimestamp(t, tzinfo=tzlocal())  # type: ignore
    elif t is None:
        t = datetime.now(tzlocal())
    elif isinstance(t, str):
        t = input.getdate(t)
        if isinstance(t, str):
            return t

    assert isinstance(t, datetime), f"datestamp: unexpected type {type(t)} for t"
    return t.strftime(format)


def inputpassword(prompt: str = "password: ", mask: str = "X", **kwargs) -> str:
    """Prompt user for password input with character masking.

    Args:
        prompt: The prompt text to display (default: "password: ").
        mask: Character to display instead of actual input (default: "X").
        **kwargs: Additional arguments passed to io.inputstring().

    Returns:
        The entered password as a string.

    Example:
        >>> pwd = inputpassword("Enter your password: ")
    """
    return io.inputstring(prompt, "", mask=mask, **kwargs)


def oxfordcomma(seq, conjunction: str = "and") -> Optional[str]:
    """Return a grammatically correct human readable string (with an Oxford comma).

    Joins a sequence of items with proper grammar and color markup for BBS display.
    Handles two items (no Oxford comma needed) and three+ items (with Oxford comma).

    The returned string includes BBS color template variables:
    - {var:sepcolor}: Color for separators and commas
    - {var:valuecolor}: Color for item values

    These variables must be defined in the template/display context where the
    result is rendered.

    Args:
        seq: Sequence of items to join. Items are converted to strings.
             If None, returns None. Non-None items are included.
        conjunction: Word to use before the last item (default: "and").

    Returns:
        Color-tagged string joining items grammatically, or None if seq is None.

    Example:
        >>> oxfordcomma(["apples", "oranges"])
        '{var:valuecolor}apples{var:sepcolor} and {var:valuecolor}oranges'
        >>> oxfordcomma(["apples", "oranges", "bananas"])
        '{var:valuecolor}apples{var:sepcolor}, {var:valuecolor}oranges{var:sepcolor}, and {var:valuecolor}bananas'
    """
    if seq is None:
        return None

    seq = [str(s) if s is not None else repr(s) for s in seq]
    seq = [s for s in seq if s != "None"]

    if len(seq) == 0:
        return ""

    if len(seq) < 3:
        buf = f"{{var:sepcolor}} {conjunction} {{var:valuecolor}}"
        return f"{{var:valuecolor}}{buf.join(seq)}"

    buf = f"{{var:sepcolor}}, {{var:valuecolor}}"
    return f"{{var:valuecolor}}{buf.join(seq[:-1])}{{var:sepcolor}}, {conjunction} {{var:valuecolor}}{seq[-1]}"


def logentry(
    message: str = "",
    *,
    level: object = logging.INFO,
    handler: Optional[logging.Handler] = None,
    formatter: Optional[logging.Formatter] = None,
    logger_name: str = LOGGER_NAME,
    module: str = "",
    action: str = "",
    moniker: str = "",
    loginid: str = "",
    ip_address: str = "",
    fingerprint: str = "",
    table: str = "",
    **kwargs: Any,
) -> None:
    """Log a message to the BBS engine logger.

    Thread-safe logging function that manages handler registration and log level mapping.

    When any of the structured key-value parameters (module, action, moniker, loginid,
    ip_address, fingerprint, table) or **kwargs are provided, the message is formatted
    in the standard log format::

        [module] action key=value key=value free_text_at_end

    If no structured parameters are provided, the message is logged as-is (backward
    compatible behavior).

    Args:
        message: Free-text message (appended at end of formatted output). Defaults to "".
        level: Log level as int (logging.DEBUG, etc.) or string ("debug", "info", "warn",
               "warning", "error", "critical"). Default: logging.INFO.
        handler: Custom logging handler. If None, uses default syslog handler.
        formatter: Custom log formatter. If None, uses handler's formatter.
        logger_name: Name of the logger to use (default: "bbsengine6").
        module: Source module name (e.g., "bank", "casino"). Bracketed in output.
        action: Event action name (e.g., "add_funds", "transfer_request").
        moniker: Member moniker.
        loginid: Login session ID.
        ip_address: Client IP address.
        fingerprint: Client TLS fingerprint.
        table: Table/resource name.
        **kwargs: Additional key-value pairs to include in formatted output.

    Example:
        >>> logentry("insufficient funds", module="bank", action="withdraw",
        ...          moniker="alice", amount=100)
        [bank] withdraw moniker=alice amount=100 insufficient funds

        >>> logentry("User logged in", level="info")
        User logged in
    """
    h = handler or _get_default_handler()
    f = formatter or h.formatter
    h.setFormatter(f)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    with _log_lock:
        if not any(isinstance(x, type(h)) for x in logger.handlers):
            logger.addHandler(h)

    levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARNING,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    structured_fields = [
        (module, "module"),
        (action, "action"),
        (moniker, "moniker"),
        (loginid, "loginid"),
        (ip_address, "ip_address"),
        (fingerprint, "fingerprint"),
        (table, "table"),
    ]
    has_structured = any(v for v, _ in structured_fields) or kwargs

    if has_structured:
        parts = []
        if module:
            parts.append(f"[{module}]")
        if action:
            parts.append(action)
        for value, name in structured_fields[2:]:
            if value:
                parts.append(f"{name}={value}")
        for key, value in kwargs.items():
            if value is not None and value != "":
                parts.append(f"{key}={value}")
        if message:
            parts.append(message)
        message = " ".join(parts)

    if isinstance(level, int):
        logger.log(level, message)
        return

    level_str = str(level).lower()
    logger.log(levels.get(level_str, logging.INFO), message)


def collapserange(lst: list) -> list:
    """Collapse consecutive integers into range tuples for compact representation.

    Converts a list of integers into compact range format. Consecutive numbers
    are grouped into 2-tuples (low, high), isolated numbers are 1-tuples (num,).
    Accepts str or list input. Strings are parsed via expandrange().
    Input is automatically sorted.

    Args:
        lst: List of integers or string range expression (e.g., "1-5,7,10").

    Returns:
        List of tuples:
        - (low, high): Range of consecutive numbers (2+ consecutive)
        - (num,): Single number or isolated pair
        Example: [1, 2, 3, 5, 6, 8] becomes [(1, 3), (5,), (6,), (8,)]

    Raises:
        TypeError: If input is not str or list.
        ValueError: If any element is not an integer, is negative, or is bool.

    Example:
        >>> collapserange([1, 2, 3, 5, 6, 8])
        [(1, 3), (5,), (6,), (8,)]
        >>> collapserange("1-5,7,10")
        [(1, 5), (7,), (10,)]
    """
    if isinstance(lst, str):
        lst = expandrange(lst)
    elif not isinstance(lst, list):
        raise TypeError(f"Expected str or list, got {type(lst).__name__}")

    if not lst:
        return []

    for item in lst:
        if not isinstance(item, int) or isinstance(item, bool):
            raise ValueError(
                f"All elements must be integers, got {type(item).__name__}"
            )
        if item < 0:
            raise ValueError("Negative numbers not allowed")

    sorted_lst = sorted(lst)

    lenlst = len(sorted_lst)
    result = []
    i = 0
    while i < lenlst:
        low = sorted_lst[i]
        while i < lenlst - 1 and sorted_lst[i] + 1 == sorted_lst[i + 1]:
            i += 1
        hi = sorted_lst[i]
        if hi - low >= RANGE_COLLAPSE_MIN_LENGTH:
            result.append((low, hi))
        elif hi - low == 1:
            result.append((low,))
            result.append((hi,))
        else:
            result.append((low,))
        i += 1

    return result


def expandrange(txt: str) -> list:
    """Parse a range expression string into a sorted list of unique integers.

    Converts compact range notation into explicit integer lists. Handles:
    - Single numbers: "3" -> [3]
    - Ranges: "1-5" -> [1, 2, 3, 4, 5]
    - Multiple ranges: "1,3-5,7" -> [1, 3, 4, 5, 7]
    - Reversed ranges: "5-1" -> [1, 2, 3, 4, 5]

    Args:
        txt: Range expression string or list of integers.

    Returns:
        Sorted list of unique integers with all ranges expanded.

    Raises:
        TypeError: If input is not str or list.
        ValueError: If format is invalid (non-numeric, negative, etc.).

    Example:
        >>> expandrange("1-5")
        [1, 2, 3, 4, 5]
        >>> expandrange("1,3-5,7")
        [1, 3, 4, 5, 7]
        >>> expandrange([1, 1, 2, 3])
        [1, 2, 3]
    """
    if isinstance(txt, list):
        txt = ",".join(str(x) for x in txt)
    elif not isinstance(txt, str):
        raise TypeError(f"Expected str or list, got {type(txt).__name__}")

    txt = txt.strip()
    if not txt:
        return []

    elle = []
    for r in txt.split(","):
        r = r.strip()
        if not r:
            continue

        if "-" in r:
            parts = r.split("-", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid range format: '{r}'")

            start_str, end_str = parts[0], parts[1]

            try:
                start = int(start_str)
                end = int(end_str)
            except ValueError:
                raise ValueError(f"Invalid number in range: '{r}'")

            if start < 0 or end < 0:
                raise ValueError("Negative numbers not allowed")

            if start > end:
                start, end = end, start

            elle.extend(range(start, end + 1))
        else:
            try:
                num = int(r)
            except ValueError:
                raise ValueError(f"Invalid number: '{r}'")

            if num < 0:
                raise ValueError("Negative numbers not allowed")

            elle.append(num)

    return sorted(set(elle))


def rangestr(ranges: list) -> str:
    """Convert range tuples to a formatted range string.

    Converts output from collapserange() into a comma-separated string format
    like "1-5,7,10".

    Args:
        ranges: List of range tuples (1-tuples and 2-tuples) as from collapserange().

    Returns:
        Formatted range string (e.g., "1-5,7,10").

    Example:
        >>> rangestr([(1, 5), (7,), (10,)])
        '1-5,7,10'
    """
    return ",".join(("%i-%i" % r if len(r) == 2 else "%i" % r) for r in ranges)


def printr(ranges: list) -> None:
    """Print a formatted range string to stdout.

    Converts ranges to a comma-separated string format and prints it.

    Args:
        ranges: List of range tuples as returned by collapserange().

    Example:
        >>> printr([(1, 5), (7,), (10,)])
        1-5,7,10
    """
    print(rangestr(ranges))


def filedisplay(res: Any, **kw: Any) -> None:
    """Display file content with optional pagination.

    Writes content from a file-like object to a temporary file, then displays it
    using io.echo_file() with optional "more" style pagination.

    Args:
        res: A file-like object (context manager) with read() method.
        **kw: Keyword arguments:
              - 'width': Display width in characters (default: terminal width)
              - 'more': If True, enable pagination with 20-line pages (default: True)

    Example:
        >>> with open("readme.txt") as f:
        ...     filedisplay(f)
        >>> with open("readme.txt") as f:
        ...     filedisplay(f, more=False)  # Display without pagination
    """
    import tempfile
    import os

    width = kw["width"] if "width" in kw else None
    more = kw["more"] if "more" in kw else True

    if width is None:
        width = io.terminal.width()  # type: ignore

    with res as r:
        content = r.read()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        page_size = 0 if not more else PAGINATION_PAGE_SIZE
        io.echo_file(tmp_path, page_size=page_size, wordwrap=False)
    finally:
        os.unlink(tmp_path)

    if not more:
        io.echo("{/all}{f6}")


_dice_rng = random.SystemRandom()


def diceroll(
    sides: int = 6, count: int = 1, mode: str = "single"
) -> int | float | list[int] | None:  # type: ignore
    """Roll one or more dice and return results based on specified mode.

    Uses cryptographically secure random number generator.

    Args:
        sides: Number of sides per die (default: 6).
        count: Number of dice to roll (default: 1).
        mode: How to return results (default: "single"):
              - "single": Return a single roll (ignores count)
              - "list": Return list of all rolls
              - "average": Return average of rolls as float
              - "median": Return median of rolls as int
              - Other: Returns None

    Returns:
        Based on mode:
        - "single": int from 1 to sides
        - "list": list of ints
        - "average": float
        - "median": int
        - Unknown mode: None

    Example:
        >>> diceroll()  # Roll 1d6
        4
        >>> diceroll(6, 3, "list")  # Roll 3d6
        [2, 5, 1]
        >>> diceroll(20, 4, "median")  # Roll 4d20, return median
        12
    """
    if mode == "single":
        return _dice_rng.randint(1, sides)

    result = []
    for x in range(1, count + 1):
        result.append(_dice_rng.randint(1, sides))

    if mode == "list":
        return result
    if mode == "average":
        total = sum(result)
        return total / len(result)
    if mode == "median":
        result.sort()
        middle = len(result) // 2
        if len(result) % 2 == 1:
            return result[middle]
        return int((result[middle - 1] + result[middle]) / 2.0)
    return None


def verify_dir_exists_writable(dirname: str, **kw) -> bool:
    """Verify that a directory exists and is writable.

    Expands user (~) and environment variables in the path.
    Outputs error messages via io.echo() for user feedback.

    Args:
        dirname: Directory path to verify (supports ~ and $VAR expansion).
        **kw: Additional keyword arguments (unused, for future compatibility).

    Returns:
        True if directory exists and is writable, False otherwise.

    Example:
        >>> verify_dir_exists_writable("~/documents")
        True
    """
    dirname = os.path.expanduser(dirname)
    dirname = os.path.expandvars(dirname)
    io.echo(f"verify_dir_exists_writable.100: {dirname=}", level="debug")

    if not os.path.exists(dirname):
        io.echo(f"{dirname!r} does not exist", level="error")
        return False

    if not os.path.isdir(dirname):
        io.echo(f"{dirname!r} is not a directory", level="error")
        return False

    if not os.access(dirname, os.W_OK):
        io.echo(f"{dirname!r} is not writable", level="error")
        return False

    return True


def verifyDirExistsWritable(dirname: str, **kw) -> bool:
    """Deprecated: Use verify_dir_exists_writable() instead.

    .. deprecated:: 9.1.0
        Use verify_dir_exists_writable() instead.
    """
    warnings.warn(
        "verifyDirExistsWritable() is deprecated, use verify_dir_exists_writable() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return verify_dir_exists_writable(dirname, **kw)


def verify_file_exists_readable(filename: str, **kw) -> bool:
    """Verify that a file exists and is readable.

    Expands user (~) and environment variables in the path.
    Optional debug output when args.debug is True.

    Args:
        filename: File path to verify (supports ~ and $VAR expansion).
        **kw: Keyword arguments including optional 'args' object with 'debug' attribute.

    Returns:
        True if file exists and is readable, False otherwise.

    Example:
        >>> verify_file_exists_readable("~/.bashrc")
        True
    """
    args = kw.get("args")

    filename = os.path.expanduser(filename)
    filename = os.path.expandvars(filename)
    if args is not None and args.debug is True:
        io.echo(f"{filename=}", level="debug")
    return os.path.exists(filename) and os.access(filename, os.R_OK)


def verifyFileExistsReadable(filename: str, **kw) -> bool:
    """Deprecated: Use verify_file_exists_readable() instead.

    .. deprecated:: 9.1.0
        Use verify_file_exists_readable() instead.
    """
    warnings.warn(
        "verifyFileExistsReadable() is deprecated, use verify_file_exists_readable() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return verify_file_exists_readable(filename, **kw)


def verify_file_exists_readable_writable(filename: str, **kw) -> bool:
    """Verify that a file exists and is readable and writable.

    Expands user (~) and environment variables in the path.
    Outputs error messages via io.echo() for user feedback.
    Optional debug output when args.debug is True.

    Args:
        filename: File path to verify (supports ~ and $VAR expansion).
        **kw: Keyword arguments including optional 'args' object with 'debug' attribute.

    Returns:
        True if file exists and is both readable and writable, False otherwise.

    Example:
        >>> verify_file_exists_readable_writable("~/config.txt")
        True
    """
    args = kw.get("args")

    filename = os.path.expanduser(filename)
    filename = os.path.expandvars(filename)
    if args is not None and args.debug is True:
        io.echo(
            f"bbsengine6.util.verify_file_exists_readable_writable.100: {args=} {filename=}"
        )

    if not os.path.exists(filename):
        io.echo(f"{filename!r} does not exist")
        return False

    if not os.access(filename, os.W_OK):
        io.echo(f"{filename!r} is not writable")
        return False

    if not os.access(filename, os.R_OK):
        io.echo(f"{filename!r} is not readable")
        return False

    return True


def verifyFileExistsReadableWritable(filename: str, **kw) -> bool:
    """Deprecated: Use verify_file_exists_readable_writable() instead.

    .. deprecated:: 9.1.0
        Use verify_file_exists_readable_writable() instead.
    """
    warnings.warn(
        "verifyFileExistsReadableWritable() is deprecated, use verify_file_exists_readable_writable() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return verify_file_exists_readable_writable(filename, **kw)


def timedeltastr(delta: Any) -> str:
    """Convert a timedelta object to a human-readable duration string.

    Args:
        delta: A datetime.timedelta object

    Returns:
        A formatted string like "02d03h15m30s" (only non-zero units included)

    Example:
        >>> from datetime import timedelta
        >>> td = timedelta(days=2, hours=3, minutes=15, seconds=30)
        >>> timedeltastr(td)
        '02d03h15m30s'
    """
    buf = ""

    seconds = delta.total_seconds()
    minutes = seconds // 60
    seconds -= minutes * 60
    hours = minutes // 60
    minutes -= hours * 60
    days = hours // 24
    hours -= days * 24

    if days != 0:
        buf += f"{days:02.0f}d"
    if hours != 0:
        buf += f"{hours:02.0f}h"
    if minutes != 0:
        buf += f"{minutes:02.0f}m"
    if seconds != 0:
        buf += f"{seconds:02.0f}s"
    return buf


def encryptpassword(plaintextpassword: str) -> str:
    """Return a bcrypt hash of ``plaintextpassword`` computed locally.

    Thin wrapper around :func:`bbsengine6.password_hash.hash_password`.
    No database round-trip: this is the single source of truth for new
    password hashes. ``setpassword`` and ``getencryptedpassword`` both
    delegate here so the cost factor, salt format, and hash prefix stay
    in lock-step with the PHP side (``bbsengine6\\password``) and with
    PostgreSQL's ``crypt(..., gen_salt('bf'))`` default.

    Returns a ``$2b$06$...`` string of length 60. Verifiable by
    :func:`bbsengine6.password_hash.verify_password` locally; PG
    ``crypt(plaintext, stored)`` only recognises the ``$2a$`` prefix
    so cross-platform PG verification is not load-bearing any more.

    See also:
        bbsengine6.password_hash.BCRYPT_PREFIX_RE
        bbsengine6.password_hash._get_bcrypt_rounds
    """
    from . import password_hash

    io.echo(f"bbsengine6.util.encryptpassword.100: {plaintextpassword=}", level="debug")
    return password_hash.hash_password(plaintextpassword)


def getencryptedpassword(args, plaintextpassword: str) -> Optional[str]:
    """Encrypt a plaintext password using the database crypt() function.

    Thin compatibility wrapper around ``encryptpassword``. ``args`` is
    accepted (and ignored) so existing call sites in bbsengine5,
    mistermcfeely, etc. keep working without modification. The hash is
    now produced locally by ``encryptpassword`` rather than via a
    PostgreSQL ``crypt(..., gen_salt('bf'))`` round-trip.

    Args:
        args: Accepted for backward compatibility; not used.
        plaintextpassword: The plaintext password to encrypt.

    Returns:
        The encrypted password string (``$2b$06$...``), or None if
        hashing fails.

    Example:
        >>> encrypted = getencryptedpassword(args, "mypassword")
    """
    io.echo(f"getencryptedpassword.100: {plaintextpassword=}", level="debug")
    return encryptpassword(plaintextpassword)


def init(args=None, **kw) -> None:
    """Initialize locale and timezone settings for the BBS engine.

    Sets the locale to the system default and initializes timezone information.
    Should be called once at application startup.

    Args:
        args: Arguments object (currently unused, for future compatibility).
        **kw: Additional keyword arguments (unused, for future compatibility).

    Example:
        >>> init()  # Call at application startup
    """
    import locale
    import time

    locale.setlocale(locale.LC_ALL, "")
    time.tzset()


def checksum(data: bytes) -> str:
    """Calculate a CRC32 checksum for binary data.

    Computes a CRC32 checksum using standard CRC32 polynomial.

    Args:
        data: Binary data to checksum.

    Returns:
        Checksum as an 8-character hexadecimal string.

    Example:
        >>> checksum(b"hello")
        'D4A4DCA6'
    """
    crc = CRC32_INIT
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (CRC32_POLY if (crc & 1) else 0)
    crc ^= CRC32_XOROUT
    return f"{crc:08X}"


def ltree_to_path(ltree: str) -> str:
    """Convert a PostgreSQL ltree string to a forward-slash delimited path.

    An ltree is a dot-separated hierarchical label format used in PostgreSQL.
    If the first label is "top", it is removed (as it's the implicit root).

    Args:
        ltree: A dot-separated ltree string (e.g., "top.users.admin").

    Returns:
        A forward-slash delimited path (e.g., "users/admin").

    Example:
        >>> ltree_to_path("top.users.admin")
        'users/admin'
        >>> ltree_to_path("users.admin")
        'users/admin'
    """
    labels = ltree.split(".")

    if labels[0] == "top":
        labels.pop(0)

    return "/".join(labels)


def pathToLtree(path: str) -> str:
    """Convert a forward-slash delimited path to a PostgreSQL ltree string.

    Replaces "/" with "." and "-" with "_" to create a valid ltree path.
    This is the inverse of ltree_to_path.

    Args:
        path: A forward-slash delimited path (e.g., "software/python").

    Returns:
        A dot-separated ltree string (e.g., "software.python").

    Example:
        >>> pathToLtree("software/python")
        'software.python'
        >>> pathToLtree("ec_john-edward")
        'ec_john_edward'
    """
    return path.replace("-", "_").replace("/", ".")


def chop_last_element(ltree: str) -> str:
    """Remove the last element from a dot-separated ltree string.

    Useful for navigating to parent nodes in an ltree hierarchy.

    Args:
        ltree: A dot-separated ltree string (e.g., "top.users.admin").

    Returns:
        The ltree with the last element removed (e.g., "top.users").

    Example:
        >>> chop_last_element("top.users.admin")
        'top.users'
    """
    labels = ltree.split(".")
    labels.pop()
    return ".".join(labels)


def tobool(value) -> bool:
    """Convert a value to a boolean.

    Supports Python boolean values and string representations of True/False.

    Args:
        value: Value to convert. Recognized True values:
               - Boolean True
               - Strings "true" or "t" (case-insensitive)
               Everything else is False.

    Returns:
        Boolean value.

    Example:
        >>> tobool(True)
        True
        >>> tobool("true")
        True
        >>> tobool("t")
        True
        >>> tobool(0)
        False
        >>> tobool("false")
        False
    """
    if value is True:
        return True
    if isinstance(value, str) and value.lower() in ("true", "t"):
        return True
    return False


def getremoteaddr() -> Optional[str]:
    """Get the remote client IP address from SSH connection environment.

    Extracts the client IP from the SSH_CONNECTION environment variable.
    This function is designed for SSH-based BBS connections.

    Returns:
        The remote client IP address, or None if not in an SSH session.

    Example:
        >>> getremoteaddr()  # When accessed via SSH
        '192.168.1.100'
    """
    val = os.environ.get("SSH_CONNECTION")
    if val is not None:
        return val.split()[0]
    return None


def getcurrentloginid(args, **kwargs) -> str | None:
    """Get the current logged-in user's login ID.

    Retrieves the login name of the user running the current process.
    Uses os.getlogin() first, falls back to environment variables.

    Args:
        args: Arguments object (currently unused, for future compatibility).
        **kwargs: Additional keyword arguments (unused, for future compatibility).

    Returns:
        The current login ID, or None if unavailable.

    Example:
        >>> getcurrentloginid(args)
        'bbsadmin'
    """
    try:
        return os.getlogin()
    except OSError:
        pass

    # Fallback to environment variables
    for var in ("LOGNAME", "USER", "USERNAME", "SUDO_USER"):
        loginid = os.environ.get(var)
        if loginid:
            return loginid

    return None


def get_safe_path(args, *components, **kwargs) -> str:
    """
    Construct a safe path by joining multiple components and verifying the
    result stays inside the first component (treated as the base directory).

    Expands ~ and environment variables, resolves to absolute paths on both
    sides so the containment check cannot be bypassed by a relative base or
    sibling-prefix collisions.
    """
    if not components:
        raise ValueError("At least one path component must be provided.")

    components = [
        os.path.expandvars(os.path.expanduser(component)) for component in components
    ]

    joined_path = os.path.join(*components)
    safe_path = os.path.abspath(os.path.normpath(joined_path))
    base_dir = os.path.abspath(os.path.normpath(components[0]))

    try:
        safe_path_rel = os.path.relpath(safe_path, base_dir)
    except ValueError:
        # Different drives on Windows etc.
        raise ValueError("Invalid path: directory traversal detected.")
    if safe_path_rel.startswith("..") or os.path.isabs(safe_path_rel):
        raise ValueError("Invalid path: directory traversal detected.")

    return safe_path


def load_sql(args, resource_name: str, *, package: Optional[str] = None) -> str:
    """
    Loads an SQL resource file and returns its contents as a string.

    Primary path uses module.file() (i.e. on-disk package data). Falls back
    to importlib.resources for install layouts where __file__ is not a real
    path (e.g. zip-installed wheels, namespace packages).
    """
    from . import module

    subdir = "sql"
    module_ref = package if package is not None else "bbsengine6"

    if "." in module_ref:
        module_ref = module_ref.rsplit(".", 1)[0]

    primary = module.file(module_ref, subdir, resource_name)
    if primary is not None:
        return primary.read_text(encoding="utf-8")

    try:
        from importlib.resources import files
    except ImportError:
        try:
            from importlib_resources import files  # type: ignore
        except ImportError:
            raise ImportError(
                "load_sql requires 'importlib.resources' (Python 3.9+) or 'importlib_resources'"
            )

    resolved_package = (
        package if package is not None else f"{module_ref}.{subdir}"
    )
    return files(resolved_package).joinpath(resource_name).read_text(encoding="utf-8")


def serialize_datetimes(data: dict) -> dict:
    """Convert datetime values to ISO format strings in a nested dictionary.

    Recursively searches a dictionary for "value" keys and converts any
    datetime objects found to ISO 8601 string format.

    Args:
        data: Dictionary with structure {key: {"value": obj, ...}, ...}.

    Returns:
        Dictionary with same structure but datetime values converted to ISO strings.

    Example:
        >>> from datetime import datetime
        >>> dt = datetime(2026, 5, 19, 14, 30, 0)
        >>> serialize_datetimes({"timestamp": {"value": dt}})
        {'timestamp': {'value': '2026-05-19T14:30:00'}}
    """
    result = {}
    for key, subdict in data.items():
        val = subdict.get("value")
        if isinstance(val, datetime):
            result[key] = {"value": val.isoformat()}
        else:
            result[key] = subdict
    return result


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences from a string for display width measurement."""
    return ANSI_ESCAPE_RE.sub("", s)


# AES-256-GCM Password Encryption Functions
# (Use bbsengine6.password_cipher module for pluggable system)


def get_encryption_key() -> bytes:
    """Get AES-256 encryption key from POSTOFFICE_PASSWORD_KEY environment variable.

    Returns:
        Decrypted 32-byte key from base64-encoded environment variable.

    Raises:
        ValueError: If key is invalid, not set, or wrong length.

    Note:
        Deprecated: Use bbsengine6.password_cipher.config.get_cipher() instead for
        pluggable cipher implementations. This function is provided for
        direct AES-256-GCM use cases.

    Example:
        >>> import os
        >>> key_b64 = "K7nZ9pQmR2xLvW8yFhJdB3sC6eG1kL4mN9tU5vX2yZ3wA="
        >>> os.environ["POSTOFFICE_PASSWORD_KEY"] = key_b64
        >>> key = get_encryption_key()
        >>> len(key)
        32
    """
    import os
    import base64

    key_b64 = os.environ.get("POSTOFFICE_PASSWORD_KEY")
    if not key_b64:
        raise ValueError(
            "POSTOFFICE_PASSWORD_KEY environment variable not set. "
            "Generate with: openssl rand -base64 32"
        )

    try:
        key = base64.b64decode(key_b64)
    except Exception as e:
        raise ValueError(f"POSTOFFICE_PASSWORD_KEY is not valid base64: {e}")

    if len(key) != 32:
        raise ValueError(
            f"POSTOFFICE_PASSWORD_KEY must be 32 bytes (256 bits), got {len(key)} bytes"
        )

    return key


def encrypt_password(plaintext: str) -> str:
    """Encrypt plaintext password with AES-256-GCM.

    Generates a random 96-bit nonce, encrypts the plaintext, and returns
    the result as base64(nonce + ciphertext + auth_tag).

    Args:
        plaintext: Password string to encrypt (plaintext).

    Returns:
        Base64-encoded encrypted password: base64(nonce + ciphertext + auth_tag)

    Raises:
        ValueError: If encryption fails or key is invalid.

    Note:
        Deprecated: Use bbsengine6.password_cipher for pluggable cipher implementations.
        This function provides direct AES-256-GCM encryption.

    Cross-ref:
        bbsengine6.password_cipher.ciphers.aes256gcm.AES256GCMCipher

    Algorithm:
        - Cipher: AES-256-GCM (NIST SP800-38D)
        - Key size: 256 bits (32 bytes)
        - Nonce: 96 bits (12 bytes), random per message
        - Auth tag: 128 bits (16 bytes)

    Cross-language compatible:
        Format works with Python, JavaScript, Rust, Perl, C, PHP, etc.

    Example:
        >>> import os, base64
        >>> os.environ["POSTOFFICE_PASSWORD_KEY"] = base64.b64encode(os.urandom(32)).decode()
        >>> encrypted = encrypt_password("mysecret")
        >>> len(base64.b64decode(encrypted)) >= 28  # 12 bytes nonce + 16 bytes tag
        True
    """
    import os
    import base64
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = get_encryption_key()

    # Generate random 96-bit nonce (12 bytes)
    nonce = os.urandom(12)

    # Create cipher and encrypt
    cipher = AESGCM(key)
    ciphertext = cipher.encrypt(nonce, plaintext.encode("utf-8"), None)

    # Concatenate nonce + ciphertext (ciphertext includes 128-bit auth tag)
    encrypted = nonce + ciphertext

    # Encode as base64 for database storage
    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_password(ciphertext_b64: str) -> str:
    """Decrypt base64-encoded AES-256-GCM encrypted password.

    Args:
        ciphertext_b64: Base64-encoded encrypted password.

    Returns:
        Decrypted plaintext password.

    Raises:
        ValueError: If decryption fails (wrong key, tampering, invalid format, etc.)

    Note:
        Deprecated: Use bbsengine6.password_cipher for pluggable cipher implementations.
        This function provides direct AES-256-GCM decryption.

    Cross-ref:
        bbsengine6.password_cipher.ciphers.aes256gcm.AES256GCMCipher.decrypt

    Example:
        >>> import os, base64
        >>> os.environ["POSTOFFICE_PASSWORD_KEY"] = base64.b64encode(os.urandom(32)).decode()
        >>> encrypted = encrypt_password("mysecret")
        >>> decrypted = decrypt_password(encrypted)
        >>> decrypted == "mysecret"
        True
    """
    import base64
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = get_encryption_key()

    try:
        encrypted = base64.b64decode(ciphertext_b64)
    except Exception as e:
        raise ValueError(f"Failed to decode base64 encrypted password: {e}")

    if len(encrypted) < 28:  # 12 bytes nonce + 16 bytes auth tag minimum
        raise ValueError(
            f"Encrypted password too short: {len(encrypted)} bytes "
            "(expected at least 28 bytes)"
        )

    # Extract nonce and ciphertext
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]

    # Decrypt and verify auth tag
    cipher = AESGCM(key)
    try:
        plaintext = cipher.decrypt(nonce, ciphertext, None)
    except Exception as e:
        raise ValueError(
            f"Failed to decrypt password (authentication tag verification failed): {e}"
        )

    return plaintext.decode("utf-8")


# IMPORTANT DISTINCTION
# =====================
# This module (and bbsengine6.password_hash) contains TWO password systems:
#
# 1. bcrypt Hashing (bbsengine6.password_hash + encryptpassword above)
#    - For member login passwords
#    - One-way: can verify but NOT decrypt
#    - Use in: bbsengine6 authentication
#    - PHP analog: bbsengine6\password\libpassword.php
#
# 2. AES-256-GCM Encryption (encrypt_password/decrypt_password below)
#    - For IMAP/SMTP server credentials
#    - Reversible: can encrypt AND decrypt
#    - Use in: Email system authentication
#    - Lives in bbsengine6.password_cipher package (cipher + storage strategy)
#
# Choose the right one for your use case!
