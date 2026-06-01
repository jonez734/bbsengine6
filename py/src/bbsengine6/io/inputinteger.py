from .inputstring import inputstring


def inputinteger(
    prompt: str, oldvalue: int | str | None = None, **kwargs
) -> int | list[int] | None:
    """Read integer input from the terminal.

    Args:
        prompt: Display prompt
        oldvalue: Pre-fill value (converted to string)
        **kwargs: Passed to inputstring

    Returns:
        Integer value, list of integers, or None if cancelled
    """
    filter = kwargs.pop("filter", r"^([+-]?[1-9]\d*|0)[ ,]?$")
    default = str(oldvalue) if oldvalue is not None else ""
    buf: str | list[str] = inputstring(prompt, default, filter=filter, **kwargs)

    if buf is None or buf == "":
        return None

    if isinstance(buf, list):
        result: list[int] = []
        for b in buf:
            try:
                result.append(int(b))
            except ValueError:
                return None
        return result

    try:
        return int(buf)
    except ValueError:
        return None
