import argparse

import ttyio5 as ttyio
import bbsengine5 as bbsengine

def buildargs(args=None):
    parser = argparse.ArgumentParser("testsetarea")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")
    ttyio.echo("testsetarea.buildargs.100: added --debug", level="debug")

    return parser

def main(args=None):
    bbsengine.setarea("testsetarea first call", stack=True)
    ttyio.echo("testsetarea.100: areastack=%r" % (bbsengine.areastack), level="debug")
    ttyio.inputboolean("continue? ", "Y")
    bbsengine.setarea("testsetarea second call", stack=False)
    ttyio.echo("testsetarea.120: areastack=%r" % (bbsengine.areastack), level="debug")
    ttyio.inputboolean("continue? ", "Y")
    bbsengine.poparea()
    ttyio.echo("testsetarea.140: areastack=%r len=%d" % (bbsengine.areastack, len(bbsengine.areastack)), level="debug")

    ttyio.inputboolean("continue? ", "Y")
    ttyio.echo("testsetarea.160: areastack=%r" % (bbsengine.areastack), level="debug")

if __name__ == "__main__":
    parser = buildargs()
    args = parser.parse_args()

    ttyio.echo("{f6:5}{curpos:%d,0}" % (ttyio.getterminalheight()-5))
    bbsengine.initscreen(bottommargin=1)

    try:
        main(args)
    except KeyboardInterrupt:
        ttyio.echo("{/all}{bold}INTR{bold}")
    except EOFError:
        ttyio.echo("{/all}{bold}EOF{/bold}")
    finally:
        ttyio.echo("{decsc}{curpos:%d,0}{el}{decrc}{reset}{/all}" % (ttyio.getterminalheight()))
    