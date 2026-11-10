from .echo import echo, rendered_length
from .inputorigin import input_origin
from .getch import getch_str as getch


def _choice_origin(prompt: str, width: int):
    """(row, col) where the answer goes, from the shared input origin rule."""
    from .common import get_terminal_state

    st = get_terminal_state()
    row, col, _window = input_origin(prompt, st.cursor_row, st.cursor_col, width)
    return row, col


def _redraw_prompt(prompt: str, origin) -> None:
    """Draw the prompt again, starting at the origin the answer belongs to."""
    if origin is not None:
        echo(f"{{curpos:{origin[0]},{max(1, origin[1] - rendered_length(prompt))}}}", end="", flush=True)
    echo(prompt, end="", flush=True)


def inputchoice(
    prompt: str, options: str, default: str | None = "", **kwargs
) -> str | None:
    noneok = kwargs.get("noneok", False)
    help = kwargs.get("help", None)
    # NOTE: For multi-key function key support (F2-F12), adopt a dict pattern
    # consistent with inputstring's function_key_handlers:
    #   f2_handler={"KEY_F2": handler, "KEY_F3": handler, ...}
    f2_handler = kwargs.get("f2_handler", None)

    rewriteprompt = kwargs.get("rewriteprompt", False)

    default = default.upper() if default is not None else ""

    options = options.upper()
    # echo(f"bbsengine.io.input.100: {options=} {rewriteprompt=}", level="debug")
    if rewriteprompt is True:
        prompt = f"{{var:promptcolor}}{prompt} [{{var:optioncolor}}{options.replace(default, f'({default})')}{{var:promptcolor}}]: {{var:inputcolor}}"
    #  options = "".join(sorted(options))

    echo(prompt, end="", flush=True)
    # The prompt's end is the origin: where the answer is shown, inside any box the caller drew.
    # Read it once, then return to it after help or F2 so the prompt stays with the box.
    origin = _choice_origin(prompt, kwargs.get("width", 80))

    done = False
    ch: str | None = None
    while not done:
        ch = getch(**kwargs)
        if ch is not None:
            ch = ch.upper()

        if ch == "KEY_ENTER":
            if noneok is True:
                return None
            elif default is not None and default != "":
                return default
            else:
                echo("{bell}", end="", flush=True)
                continue
        elif ch == "KEY_HELP" or ch == "KEY_F1":
            echo("help")
            if callable(help):
                help(**kwargs)
            elif type(help) is str:
                echo(help)
            _redraw_prompt(prompt, origin)
        elif ch == "KEY_F2":
            if callable(f2_handler):
                f2_handler(**kwargs)
            elif type(f2_handler) is str:
                echo(f2_handler)
            _redraw_prompt(prompt, origin)
        elif ch is not None:
            if ch[:4] == "KEY_" or ch in options:
                break
            echo("{bell}", end="", flush=True)
            continue

    return ch  # type: ignore[return-value]
