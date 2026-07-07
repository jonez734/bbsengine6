import time
import locale
import sys

from bbsengine6 import io, screen
from . import lib

parser = lib.buildargs()

# Handle --help/-h as bare tokens (not as values to other flags).
# The previous "in sys.argv" check matched substrings of any argv
# element, which is fragile (e.g. a value containing "--help"
# as a substring would trigger help).
def _argv_has_help_flag(argv):
    for a in argv:
        if a == "--help" or a == "-h":
            return True
    return False

if _argv_has_help_flag(sys.argv[1:]):
    if parser is not None:
        parser.print_help()
    # Don't call sys.exit() - let flow continue to menu
    args = None
else:
    args = parser.parse_args() if parser is not None else None

screen.init()

locale.setlocale(locale.LC_ALL, "")
time.tzset()

try:
    # Pass the already-parsed `args` and DO NOT forward `argv=`.
    # module.run re-parses argv with every submodule's buildargs,
    # which leaks the parent's flag surface into children. The
    # parent has already parsed; submodules should consume the
    # parsed Namespace.
    lib.runmodule(args, "main")
except KeyboardInterrupt:
    io.echo("{/all}{bold}INTR{/bold}")
except EOFError:
    io.echo("{/all}{bold}EOF{/bold}")
except Exception as e:
    io.echo_traceback(f"bbsengine6.startup: {e}")
finally:
    io.echo(f"{{decsc}}{{curpos:{io.terminal.height()},0}}{{el}}{{reset}}{{decrc}}{{/all}}")
