import ttyio5 as ttyio
import bbsengine6 as bbsengine

from . import lib

if __name__ == "__main__":
    bbsengine.screen.init()
    bbsengine.screen.setarea("con")
    parser = lib.buildargs()
    args = parser.parse_args()
    try:
        lib.runsubmodule(args, "main")
    except EOFError:
        print("EOF")
    except KeyboardInterrupt:
        print("INTR")
    finally:
        ttyio.echo("{decsc}{curpos:%d,0}{el}{decrc}{reset}{/all}" % (ttyio.getterminalheight()))
