import argparse

from bbsengine6 import io


def main(args, **kwargs):
    try:
        io.screen.init()
        io.screen.setbottombar("test", "again")
    except Exception:
        pass
    buf = io.inputstring("> ", "")
    io.echo(f"{buf=}", flush=True, end="\n")


if __name__ == "__main__":
    args = argparse.Namespace()
    main(args)
