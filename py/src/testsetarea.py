import argparse

import bbsengine6 as bbsengine
from bbsengine6 import bottombar, io


def buildargs(args=None):
    parser = argparse.ArgumentParser("testsetarea")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")
    io.echo("testsetarea.buildargs.100: added --debug", level="debug")

    return parser


def main(args=None):
    bottombar.push(left="testsetarea first call")
    io.inputboolean("continue? ", "Y")
    bottombar.push(left="testsetarea second call")
    io.inputboolean("continue? ", "Y")
    bottombar.pop()
    io.echo(
        "testsetarea.140: pop done, left=%r" % (bottombar.default_registry().left),
        level="debug",
    )

    io.inputboolean("continue? ", "Y")
    io.echo("testsetarea.160: done", level="debug")


if __name__ == "__main__":
    parser = buildargs()
    args = parser.parse_args()

    io.echo("{f6:5}{curpos:%d,0}" % (io.getterminalheight() - 5))
    bbsengine.initscreen(bottommargin=1)

    try:
        main(args)
    except KeyboardInterrupt:
        io.echo("{/all}{bold}INTR{bold}")
    except EOFError:
        io.echo("{/all}{bold}EOF{/bold}")
    finally:
        io.echo(
            "{decsc}{curpos:%d,0}{el}{decrc}{reset}{/all}" % (io.getterminalheight())
        )
