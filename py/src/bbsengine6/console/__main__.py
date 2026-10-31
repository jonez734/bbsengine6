"""Console entry point: ``python -m bbsengine6.console``.

Delegates to :mod:`bbsengine6.console.tui`, the console TUI. Kept so the
package still runs with ``-m``; the TUI itself is ``python -m
bbsengine6.console.tui`` and the ``console`` script.
"""

import sys

from . import tui

if __name__ == "__main__":
    sys.exit(tui.cli())
