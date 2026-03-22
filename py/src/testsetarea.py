import argparse

from bbsengine6 import io


def buildargs(args=None):
    parser = argparse.ArgumentParser("testsetarea")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")
    io.echo("testsetarea.buildargs.100: added --debug", level="debug")

    return parser


def main(args=None):
    bbsengine.setarea("testsetarea first call", stack=True)
    io.echo("testsetarea.100: areastack=%r" % (bbsengine.areastack), level="debug")
    io.inputboolean("continue? ", "Y")
    bbsengine.setarea("testsetarea second call", stack=False)
    io.echo("testsetarea.120: areastack=%r" % (bbsengine.areastack), level="debug")
    io.inputboolean("continue? ", "Y")
    bbsengine.poparea()
    io.echo(
        "testsetarea.140: areastack=%r len=%d"
        % (bbsengine.areastack, len(bbsengine.areastack)),
        level="debug",
    )

    io.inputboolean("continue? ", "Y")
    io.echo("testsetarea.160: areastack=%r" % (bbsengine.areastack), level="debug")


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
