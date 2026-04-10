# util - general-purpose utilities for the BBS engine

import logging
import logging.handlers
import os
import random
import re
import threading
from datetime import datetime
from typing import Optional

from . import database, input, io

LOGGER_NAME = "bbsengine6"

_log_lock = threading.Lock()
_default_handler: Optional[logging.handlers.SysLogHandler] = None


def _get_default_handler() -> logging.handlers.SysLogHandler:
    global _default_handler
    if _default_handler is None:
        _default_handler = logging.handlers.SysLogHandler(address="/dev/log")
        _default_handler.setFormatter(
            logging.Formatter("%(name)s[%(process)d]: %(levelname)s %(message)s")
        )
    return _default_handler


def hr(acs: bool = True, width: Optional[int] = None, end: str = "\n") -> bool:
    if width is None:
        width = io.terminal.width() - 2
    io.echo(f" {{boxcolor}}{{hline:{width}}}{{/all}}", end=end)
    return True


def heading(title: str, **kwargs) -> None:
    width = io.terminal.width() - 4
    w = width - len(title)
    if w % 2 == 0:
        repeat = w // 2
        leftpadding = " " * repeat
        rightpadding = " " * repeat
    else:
        repeat = (w - 2) // 2
        leftpadding = " " * (repeat + 2)
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
    singular: str = "singular",
    plural: str = "plural",
    quantity: bool = True,
    emoji: str = "",
    determiner: str = "a",
    **kw,
) -> str:
    if amount is None or amount == 0:
        if quantity is True:
            return f"no {emoji}{plural}"
        return plural

    if quantity is True:
        if amount == 1:
            if determiner != "":
                return f"{emoji} {determiner} {singular}"
            return f"{emoji}{amount} {singular}"
        return f"{emoji}{amount:n} {plural}"

    if amount == 1:
        return f"{emoji}{singular}"
    return f"{emoji}{plural}"


def datestamp(
    t: Optional[object] = None, format: str = "%Y-%m-%d %I:%M%P %Z (%a)"
) -> str:
    from dateutil.tz import tzlocal
    from time import tzset

    tzset()

    if isinstance(t, (int, float)):
        t = datetime.fromtimestamp(t, tzinfo=tzlocal())
    elif t is None:
        t = datetime.now(tzlocal())
    elif isinstance(t, str):
        t = input.getdate(t)
        if isinstance(t, str):
            return t

    assert isinstance(t, datetime), f"datestamp: unexpected type {type(t)} for t"
    return t.strftime(format)


def inputpassword(prompt: str = "password: ", mask: str = "X", **kwargs) -> str:
    return io.inputstring(prompt, "", mask=mask, **kwargs)


def oxfordcomma(seq, conjunction: str = "and") -> Optional[str]:
    """Return a grammatically correct human readable string (with an Oxford comma)."""
    if seq is None:
        return None

    seq = [str(s) for s in seq]

    if len(seq) == 0:
        return ""

    if len(seq) < 3:
        buf = f"{{var:sepcolor}} {conjunction} {{var:valuecolor}}"
        return f"{{var:valuecolor}}{buf.join(seq)}"

    buf = f"{{var:sepcolor}}, {{var:valuecolor}}"
    return f"{{var:valuecolor}}{buf.join(seq[:-1])}{{var:sepcolor}}, {conjunction} {{var:valuecolor}}{seq[-1]}"


def logentry(
    message: str,
    *,
    level: object = logging.INFO,
    handler: Optional[logging.Handler] = None,
    formatter: Optional[logging.Formatter] = None,
    logger_name: str = LOGGER_NAME,
) -> None:
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

    if isinstance(level, int):
        logger.log(level, message)
        return

    level_str = str(level).lower()
    logger.log(levels.get(level_str, logging.INFO), message)


def collapserange(lst: list) -> list:
    """Yield 2-tuple ranges or 1-tuple single elements from list of ints.

    Accepts str or list input. Strings are parsed via expandrange.
    Input is automatically sorted. Negative numbers are not allowed.
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
        if hi - low >= 2:
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

    Accepts str or list input. Handles ranges like "1-5" and "1,3-5,7".
    Reversed ranges (e.g., "5-1") are automatically corrected to "1-5".
    Negative numbers are not allowed.
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


def rangestr(ranges):
    return ",".join(("%i-%i" % r if len(r) == 2 else "%i" % r) for r in ranges)


def printr(ranges):
    print(rangestr(ranges))


def filedisplay(res, **kw) -> None:
    import tempfile
    import os

    width = kw["width"] if "width" in kw else None
    indent = kw["indent"] if "indent" in kw else 0
    more = kw["more"] if "more" in kw else True

    if width is None:
        width = io.terminal.width()

    with res as r:
        content = r.read()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        page_size = 0 if not more else 20
        io.echo_file(tmp_path, page_size=page_size, wordwrap=False)
    finally:
        os.unlink(tmp_path)

    if not more:
        io.echo("{/all}{f6}")


_dice_rng = random.SystemRandom()


def diceroll(sides: int = 6, count: int = 1, mode: str = "single"):
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


def verifyDirExistsWritable(dirname: str, **kw) -> bool:
    dirname = os.path.expanduser(dirname)
    dirname = os.path.expandvars(dirname)
    io.echo(f"verifyDirExistsWritable.100: {dirname=}", level="debug")

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


def verifyFileExistsReadable(filename: str, **kw) -> bool:
    args = kw.get("args")

    filename = os.path.expanduser(filename)
    filename = os.path.expandvars(filename)
    if args is not None and args.debug is True:
        io.echo(f"{filename=}", level="debug")
    return os.path.exists(filename) and os.access(filename, os.R_OK)


def verifyFileExistsReadableWritable(filename, **kw):
    args = kw.get("args")

    filename = os.path.expanduser(filename)
    filename = os.path.expandvars(filename)
    if args is not None and args.debug is True:
        io.echo(
            f"bbsengine6.util.verifyFileExistsReadableWritable.100: {args=} {filename=}"
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


def timedeltastr(delta):
    """Convert a timedelta object to a human-readable duration string.

    Args:
        delta: A datetime.timedelta object

    Returns:
        A formatted string like "02d03h15m30s" (only non-zero units included)

    Example:
        >>> td = datetime.timedelta(days=2, hours=3, minutes=15, seconds=30)
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


def getencryptedpassword(args, plaintextpassword: str) -> Optional[str]:
    io.echo(f"getencryptedpassword.100: {plaintextpassword=}", level="debug")
    sql = "select crypt(%s, gen_salt('md5'))"
    dat = (plaintextpassword,)
    with database.connect(args) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return None

            res = cur.fetchone()
            return res["crypt"]


def init(args=None, **kw) -> None:
    import locale
    import time

    locale.setlocale(locale.LC_ALL, "")
    time.tzset()


def checksum(data: bytes) -> str:
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xEDB88320 if (crc & 1) else 0)
    crc ^= 0xFFFFFFFF
    return f"{crc:08X}"


def ltree_to_path(ltree: str) -> str:
    labels = ltree.split(".")

    if labels[0] == "top":
        labels.pop(0)

    return "/".join(labels)


def chop_last_element(ltree: str) -> str:
    labels = ltree.split(".")
    labels.pop()
    return ".".join(labels)


def tobool(value) -> bool:
    if value is True:
        return True
    if isinstance(value, str) and value.lower() in ("true", "t"):
        return True
    return False


def getremoteaddr() -> Optional[str]:
    val = os.environ.get("SSH_CONNECTION")
    if val is not None:
        return val.split()[0]
    return None


def getcurrentloginid(args, **kwargs) -> str:
    return os.getlogin()


def get_safe_path(args, *components, **kwargs) -> str:
    """
    Constructs a safe path by joining multiple path components.
    Expands environment variables and user home directory and normalizes.
    """
    if not components:
        raise ValueError("At least one path component must be provided.")

    components = [
        os.path.expandvars(os.path.expanduser(component)) for component in components
    ]

    joined_path = os.path.join(*components)

    safe_path = os.path.normpath(joined_path)

    base_dir = os.path.abspath(components[0])
    if not safe_path.startswith(base_dir):
        raise ValueError("Invalid path: directory traversal detected.")

    return safe_path


def load_sql(args, resource_name: str, *, package: Optional[str] = None) -> str:
    """
    Loads an SQL resource file and returns its contents as a string.
    """
    try:
        from importlib.resources import files
    except ImportError:
        try:
            from importlib_resources import files
        except ImportError:
            raise ImportError(
                "load_sql requires 'importlib.resources' (Python 3.9+) or 'importlib_resources'"
            )

    import pathlib

    def _resolve_package(package: Optional[str]) -> str:
        if package is not None:
            return package
        if __package__:
            return __package__ + ".sql"

        base_path = pathlib.Path(__file__).resolve()
        while base_path.parent != base_path:
            if (base_path / "__init__.py").exists():
                return base_path.name + ".sql"
            base_path = base_path.parent

        raise ValueError("Unable to determine the package for resource loading")

    resolved_package = _resolve_package(package)
    return files(resolved_package).joinpath(resource_name).read_text(encoding="utf-8")


def serialize_datetimes(data):
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
