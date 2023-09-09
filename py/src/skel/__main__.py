import time
import locale

import ttyio6 as ttyio
import bbsengine6 as bbsengine

from . import module

parser = module.buildargs()
args = parser.parse_args() if parser is not None else None

bbsengine.session.start(args)

bbsengine.screen.init()

locale.setlocale(locale.LC_ALL, "")
time.tzset()

module.init(args)

try:
    module.main(args)
except KeyboardInterrupt:
    ttyio.echo("{/all}{bold}INTR{bold}")
except EOFError:
    ttyio.echo("{/all}{bold}EOF{/bold}")
finally:
    ttyio.echo("{decsc}{curpos:%d,0}{el}{decrc}{reset}{/all}" % (ttyio.getterminalheight()))
