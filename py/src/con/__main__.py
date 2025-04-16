from bbsengine6 import io, screen, session, database
import sys

from . import lib

if __name__ == "__main__":
    parser = lib.buildargs()
    args = parser.parse_args()

    screen.init()
    lib.setbottombar(args, "con")

    try:
        if lib.runmodule(args, "main") is False:
            io.echo(f"error running module main", level="error")
            sys.exit(-1)
    except EOFError:
        io.echo("**EOF**")
    except KeyboardInterrupt:
        io.echo("**INTR**")
    finally:
        io.echo("{decsc}{curpos:%d,0}{el}{decrc}{reset}{/all}" % (io.getterminalheight()))
