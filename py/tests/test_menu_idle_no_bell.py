"""An idle read timeout in the menu does not ring the bell.

io.getch returns None when no key arrives within its timeout. That is an idle second, not a wrong key, so the menu must
read again silently. A real unrecognised key still rings the bell.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from bbsengine6 import menu as bmenu


def _menu():
    return bmenu.Menu(SimpleNamespace(debug=False), "test", [bmenu.Item("A", "alpha", None)])


class TestIdleTimeout(unittest.TestCase):
    def _drive(self, keys):
        echoed = []
        feed = iter(keys)
        with patch.object(bmenu.io, "getch", side_effect=lambda *a, **k: next(feed)), \
             patch.object(bmenu.io, "echo", side_effect=lambda t="", *a, **k: echoed.append(str(t))), \
             patch.object(bmenu.io, "setvar"):
            m = _menu()
            m.numitems = len(m.items)
            m.currentitem = m.items[0]
            m.display = lambda: None
            m.handle("prompt: ")
        return echoed

    def test_idle_timeouts_do_not_ring_the_bell(self):
        echoed = self._drive([None, None, None, "A"])
        self.assertFalse(any("{bell}" in t for t in echoed), echoed)

    def test_an_unrecognised_key_still_rings_the_bell(self):
        echoed = self._drive(["KEY_NOTHING_HERE", "A"])
        self.assertTrue(any("{bell}" in t for t in echoed), echoed)


if __name__ == "__main__":
    unittest.main()
