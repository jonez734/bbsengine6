from bbsengine6 import io, screen, session

from . import lib

if __name__ == "__main__":
    parser = lib.buildargs()
    args = parser.parse_args()

    screen.init()
    screen.setarea("con")

    session.start(args)

    try:
        lib.runmodule(args, "main")
    except EOFError:
        print("EOF")
    except KeyboardInterrupt:
        print("INTR")
    finally:
        io.echo("{decsc}{curpos:%d,0}{el}{decrc}{reset}{/all}" % (io.getterminalheight()))
