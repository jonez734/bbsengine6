from .echo import echo
from .getch import getch_str as getch


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
            echo(prompt, end="", flush=True)
        elif ch == "KEY_F2":
            if callable(f2_handler):
                f2_handler(**kwargs)
            elif type(f2_handler) is str:
                echo(f2_handler)
            echo(prompt, end="", flush=True)
        elif ch is not None:
            if ch[:4] == "KEY_" or ch in options:
                break
            echo("{bell}", end="", flush=True)
            continue

    return ch  # type: ignore[return-value]
