"""A fake bed_fetch for the balance tests: returns or raises what a test gives it.

getbalance_info now takes the bed step as a callable, so tests pass one instead of patching a
removed helper. ``bed_fetch(args, moniker)`` returns the reply dict or raises.
"""

from unittest.mock import MagicMock


def fake(return_value=None, side_effect=None):
    """A bed_fetch whose calls return ``return_value`` or raise ``side_effect``."""
    m = MagicMock(return_value=return_value, side_effect=side_effect)
    return m
