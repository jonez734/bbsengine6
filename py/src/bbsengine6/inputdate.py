import logging
from datetime import datetime
from . import io

_log = logging.getLogger(__name__)


def _load_getdate():
    """Return getdate_next.getdate if a real install is importable, else None.

    A bare namespace package (for example, a source checkout on sys.path
    with no installed distribution) imports fine but has no `getdate`.
    It is treated as "not installed" so the fallback is used.
    """
    try:
        from getdate_next import getdate as _getdate
    except ImportError:
        return None
    return _getdate if callable(_getdate) else None


getdate = _load_getdate()
BACKEND = "getdate_next" if getdate is not None else "dateutil"
_warned_fallback = False


def _warn_fallback_once() -> None:
    """Log once per process that date parsing fell back to dateutil."""
    global _warned_fallback
    if getdate is None and not _warned_fallback:
        _warned_fallback = True
        _log.warning(
            "getdate_next is not installed; date input falls back to "
            "dateutil.parser, which accepts a narrower set of expressions. "
            "Install getdate-next (pip install getdate-next) to restore full parsing."
        )


def _verify_date_expression(args, buffer, **kwargs) -> bool:
    if buffer.strip() == "":
        return kwargs.get("noneok", False)
    if getdate is None:
        _warn_fallback_once()
        try:
            from dateutil import parser as _dateutil_parser

            return _dateutil_parser.parse(buffer) is not None
        except (ValueError, TypeError, ImportError):
            return False
    return getdate(buffer) is not None


def inputdate(
    prompt: str, oldvalue: str | datetime | None = None, **kwargs
) -> datetime | None:
    noneok = kwargs.get("noneok", False)

    if oldvalue is None:
        oldstr = ""
    elif isinstance(oldvalue, datetime):
        oldstr = str(oldvalue)
    else:
        oldstr = str(oldvalue)

    buf = io.inputstring(prompt, oldstr, verify=_verify_date_expression, **kwargs)

    if buf is None or buf == "":
        return None

    if getdate is None:
        _warn_fallback_once()
        try:
            from dateutil import parser as _dateutil_parser

            return _dateutil_parser.parse(buf)
        except (ValueError, TypeError, ImportError):
            return None

    return getdate(buf)
