from .inputchoice import inputchoice
from .echo import echo


def inputboolean(
    prompt: str, default: str | None = None, options: str = "YN", **kwargs
) -> bool | None:
    """Read boolean input from the terminal.

    Args:
        prompt: Display prompt
        default: Default choice (Y/N/T/F)
        options: Valid choices (default "YN")
        **kwargs: Passed to inputchoice

    Returns:
        True for Y/T, False for N/F, None for cancelled
    """
    ch = inputchoice(prompt, options, default, **kwargs)
    if ch is None:
        return None

    ch_upper = ch.upper()
    if ch_upper == "Y" or ch_upper == "T":
        echo("Yes" if ch_upper == "Y" else "True")
        return True
    if ch_upper == "N" or ch_upper == "F":
        echo("No" if ch_upper == "N" else "False")
        return False
    return None