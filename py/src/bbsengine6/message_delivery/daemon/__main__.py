# notify/daemon/__main__.py
# Module entry point for python -m bbsengine6.notify.daemon

from __future__ import annotations

import sys

from . import cli


if __name__ == "__main__":
    sys.exit(cli.main())
