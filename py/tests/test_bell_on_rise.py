"""The notification bell rings only when the unread count rises.

A message that stays unread must not ring the bell every poll. The baseline is the count
the last bell was based on, per moniker, per process. A drop resets it, so a later rise
rings again. The 5 s bell window still collapses a burst into one bell.
"""

import importlib
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

g = importlib.import_module("bbsengine6.io.getch")


class TestBellBaseline(unittest.TestCase):
    def test_same_count_on_repeated_checks_rings_once_only(self):
        b = g.BellBaseline()
        self.assertTrue(b.should_ring("alice", 2))
        self.assertFalse(b.should_ring("alice", 2))
        self.assertFalse(b.should_ring("alice", 2))

    def test_rise_rings(self):
        b = g.BellBaseline()
        b.should_ring("alice", 1)
        self.assertTrue(b.should_ring("alice", 2))

    def test_zero_count_never_rings(self):
        b = g.BellBaseline()
        self.assertFalse(b.should_ring("alice", 0))

    def test_drop_resets_and_a_later_rise_rings_again(self):
        b = g.BellBaseline()
        b.should_ring("alice", 3)
        self.assertFalse(b.should_ring("alice", 1))  # drop: baseline becomes 1
        self.assertTrue(b.should_ring("alice", 2))   # 1 -> 2 is a rise

    def test_first_check_with_unread_rings_once(self):
        b = g.BellBaseline()
        self.assertTrue(b.should_ring("alice", 1))
        self.assertFalse(b.should_ring("alice", 1))

    def test_baselines_are_per_moniker(self):
        b = g.BellBaseline()
        b.should_ring("alice", 5)
        self.assertTrue(b.should_ring("bob", 1))

    def test_clear_resets_every_baseline(self):
        b = g.BellBaseline()
        b.should_ring("alice", 5)
        b.clear()
        self.assertTrue(b.should_ring("alice", 5))


class TestEmitRequiresARise(unittest.TestCase):
    def setUp(self):
        g._bell_baseline = g.BellBaseline()
        g._bell_window = g.BellWindow(0.0)  # window off: only the rise rule can suppress

    def test_emit_for_a_moniker_rings_on_rise_only(self):
        from unittest.mock import patch
        with patch.object(g, "echo") as echo:
            self.assertTrue(g._emit_bell_for(g._bell_baseline, "alice", 1))
            self.assertFalse(g._emit_bell_for(g._bell_baseline, "alice", 1))
            self.assertTrue(g._emit_bell_for(g._bell_baseline, "alice", 2))
        self.assertEqual(echo.call_count, 2)


if __name__ == "__main__":
    unittest.main()


import threading  # noqa: E402
import time  # noqa: E402
from unittest.mock import patch  # noqa: E402

import pty  # noqa: E402

from bbsengine6.member import _threadlocal  # noqa: E402
from bbsengine6.message import cache  # noqa: E402
import bbsengine6.io.common as common  # noqa: E402


class TestSteadyUnreadDoesNotRingEveryPoll(unittest.TestCase):
    """A message left unread must ring once, not on every 2 s poll."""

    def setUp(self):
        g._bell_window = g.BellWindow(0.5)  # short window so the poll cadence would ring
        g._bell_baseline = g.BellBaseline()
        _threadlocal.moniker = "bellman"
        cache.set_local_unread_count("bellman", 1)
        cache.drain_change_wake()
        self.master, self.slave = pty.openpty()
        self.stream = os.fdopen(self.slave, "r", buffering=1, encoding="utf-8")
        self._saved = common._current_input_stream
        common.set_input_stream(self.stream)
        with common._input_queue_lock:
            common._input_queue.clear()

    def tearDown(self):
        common.set_input_stream(self._saved)
        _threadlocal.moniker = None
        try:
            self.stream.close()
            os.close(self.master)
        except OSError:
            pass

    def test_steady_unread_count_rings_once_across_several_polls(self):
        rings = []
        real = g._emit_bell_for

        def counting(baseline, moniker, count):
            rang = real(baseline, moniker, count)
            if rang:
                rings.append(count)
            return rang

        with patch.object(g, "_emit_bell_for", side_effect=counting), \
             patch.object(g, "_update_bottombar_on_notification", return_value=True), \
             patch.object(g, "_push_subscribed", return_value=False), \
             patch.object(g, "_check_notifications", return_value=(True, 1)), \
             patch.object(common, "_current_input_stream", self.stream), \
             patch("bbsengine6.io.echo"):
            def key_later():
                time.sleep(4.5)  # more than two 2 s polls with the count still at 1
                os.write(self.master, b"k")
            w = threading.Thread(target=key_later, daemon=True)
            w.start()
            self.assertEqual(g.getch_str(timeout=5.0), "k")
            w.join(timeout=5)
        self.assertEqual(rings, [1], f"steady unread count must ring once, got {rings}")
