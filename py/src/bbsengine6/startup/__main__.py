import time
import locale
import sys

from bbsengine6 import io, screen
from . import lib

parser = lib.buildargs()

# Handle --help/--h without exiting (return to menu)
if "--help" in sys.argv or "-h" in sys.argv:
    if parser is not None:
        parser.print_help()
    # Don't call sys.exit() - let flow continue to menu
    args = None
else:
    args = parser.parse_args() if parser is not None else None

#session.start(args)

screen.init(args)

locale.setlocale(locale.LC_ALL, "")
time.tzset()

# module.init(args)

try:
    if lib.runmodule(args, "main", package="bbsengine6.startup", argv=sys.argv[1:]) is False:
        io.echo(f"{{level.error}} startup failed {{/all}}")
    else:
        io.echo(f"{{level.ok}} startup ok {{/all}}")
except KeyboardInterrupt:
    io.echo("{/all}{bold}INTR{/bold}")
except EOFError:
    io.echo("{/all}{bold}EOF{/bold}")
except Exception as e:
    io.echo_traceback(f"bbsengine6.startup: {e}")
finally:
    io.echo(f"{{decsc}}{{curpos:{io.terminal.height()},0}}{{el}}{{reset}}{{decrc}}{{/all}}")
