import argparse

from bbsengine6.io.echo import echo
from bbsengine6.io.util import screen_init, setbottombar
from bbsengine6.io.inputstring import inputstring


def main(args, **kwargs):
    screen_init()
    setbottombar("test", "again")
    buf = inputstring("> ", "a previous value")
    echo(f"{buf=}", flush=True, end="\n")


if __name__ == "__main__":
    args = argparse.Namespace()

    try:
        main(args)
    except KeyboardInterrupt:
        echo("**INTR**")
    except EOFError:
        echo("**EOF**")
    finally:
        echo("{reset:all}", flush=True, end="")
