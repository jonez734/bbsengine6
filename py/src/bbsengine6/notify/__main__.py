# notify/__main__.py
# Module entry point for python -m bbsengine6.notify

from __future__ import annotations

import locale
import sys
import time

from . import main as main_module


def main() -> int:
    locale.setlocale(locale.LC_ALL, "")
    time.tzset()
    return main_module.main()


if __name__ == "__main__":
    sys.exit(main())
