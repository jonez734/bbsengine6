import argparse
from bbsengine6 import io, member, database, screen, util


def buildargs(args=None):
    parser = argparse.ArgumentParser("testsetarea")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")
    io.echo("testsetarea.buildargs.100: added --debug", level="debug")

    database.buildargs(parser)

    return parser


def main(args):
    password = io.inputstring("password: ")  # util.inputpassword("password: ")
    member.checkpassword(args, password)


if __name__ == "__main__":
    parser = buildargs()
    args = parser.parse_args()

    #    io.echo("{f6:5}{curpos:%d,0}" % (io.getterminalheight()-5))
    screen.init()

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
