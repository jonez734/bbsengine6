from .inputchoice import inputchoice
from .echo import echo

# @since 20210203
def inputboolean(prompt:str, default:str=None, options="YN", **kwargs) -> bool:
#    echo(f"inputboolean.100: {prompt=} {default=} {options=}", level="debug")
    ch = inputchoice(prompt, options, default, **kwargs)
    if ch is not None:
        ch = ch.upper()
        if ch == "Y":
            echo("Yes")
            return True
        elif ch == "T":
            echo("True")
            return True
        elif ch == "N":
            echo("No")
            return False
        elif ch == "F":
            echo("False")
            return False
    return None
