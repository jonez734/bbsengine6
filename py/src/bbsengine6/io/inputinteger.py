from .inputstring import inputstring


def inputinteger(
    prompt: str, oldvalue: int | str | None = None, **kwargs
) -> int | None:
    """Read integer input from the terminal.

    Args:
        prompt: Display prompt
        oldvalue: Pre-fill value (converted to string)
        **kwargs: Passed to inputstring

    Returns:
        The integer entered, or None if the entry is empty or not an integer
    """
    filter = kwargs.pop("filter", r"^([+-]?[1-9]\d*|0)[ ,]?$")
    # Only characters that can appear in an integer (and a separator) are accepted
    # while typing; the regex then checks the whole value on Enter.
    kwargs.setdefault("allowed", "0123456789+- ,")
    default = str(oldvalue) if oldvalue is not None else ""
    buf: str = inputstring(prompt, default, filter=filter, **kwargs)

    if buf is None or buf == "":
        return None

    try:
        return int(buf)
    except ValueError:
        return None
