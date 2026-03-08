from datetime import datetime
from getdate_next import getdate
from . import io


def _verify_date_expression(args, buffer, **kwargs) -> bool:
    if buffer.strip() == "":
        return kwargs.get("noneok", False)
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
        if noneok:
            return None
        return None

    result = getdate(buf)
    return result
