from datetime import datetime
from . import io

try:
    from getdate_next import getdate
except ImportError:
    getdate = None  # type: ignore[assignment]


def _verify_date_expression(args, buffer, **kwargs) -> bool:
    if buffer.strip() == "":
        return kwargs.get("noneok", False)
    if getdate is None:
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
        try:
            from dateutil import parser as _dateutil_parser

            return _dateutil_parser.parse(buf)
        except (ValueError, TypeError, ImportError):
            return None

    return getdate(buf)
