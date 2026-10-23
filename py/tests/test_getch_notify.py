"""getch notification behavior: bell window, event-driven wake, DB fallback.

The idle-wait tests use a pty so tty.setraw and termios behave as they do in
the app. The input stream is a text stream, matching sys.stdin.
"""

import importlib
import os
import pty
import sys
import threading
import time
import unittest

# A key that never arrives must fail the test in seconds, not hang the run.
GETCH_TEST_TIMEOUT = 5.0
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

g = importlib.import_module("bbsengine6.io.getch")
import bbsengine6.io.common as common  # noqa: E402
from bbsengine6.message import cache  # noqa: E402
from bbsengine6.member import _threadlocal  # noqa: E402


def _as_member(moniker):
    """getch reads the moniker from the member thread-local, not a kwarg."""
    _threadlocal.moniker = moniker


class TestBellWindow(unittest.TestCase):
    def test_first_rings_and_burst_shares_one_bell(self):
        w = g.BellWindow(5.0)
        self.assertTrue(w.should_ring(0.0))
        self.assertFalse(w.should_ring(1.0))
        self.assertFalse(w.should_ring(4.9))

    def test_message_after_window_rings_again(self):
        w = g.BellWindow(5.0)
        w.should_ring(0.0)
        self.assertTrue(w.should_ring(5.0))

    def test_window_seconds_is_configurable(self):
        w = g.BellWindow(1.0)
        w.should_ring(0.0)
        self.assertTrue(w.should_ring(1.0))

    def test_set_bell_window_rejects_negative(self):
        with self.assertRaises(ValueError):
            g.set_bell_window_seconds(-1)


class TestIdleWait(unittest.TestCase):
    def setUp(self):
        # Each idle test starts with a closed bell window, no session moniker, and an empty unread
        # cache, so state left by an earlier test cannot make the idle check ring or wake.
        g._bell_window = g.BellWindow(5.0)
        from bbsengine6.member import _threadlocal
        _threadlocal.moniker = None
        cache.clear_local_unread_cache()
        self.master, self.slave = pty.openpty()
        self.stream = os.fdopen(self.slave, "r", buffering=1, encoding="utf-8")
        self._saved = common._current_input_stream
        common.set_input_stream(self.stream)
        cache.drain_change_wake()
        # Keys left in the process-wide input queue by an earlier DSR read must not reach this test.
        with common._input_queue_lock:
            common._input_queue.clear()

    def tearDown(self):
        common.set_input_stream(self._saved)
        try:
            self.stream.close()
            os.close(self.master)
        except OSError:
            pass

    def test_finite_timeout_returns_none(self):
        t0 = time.time()
        self.assertIsNone(g.getch_str(timeout=0.3))
        self.assertLess(time.time() - t0, 2.0)

    def test_cache_change_wakes_idle_wait_without_key(self):
        def later():
            time.sleep(0.15)
            cache.set_local_unread_count("wake-test", 1)
            time.sleep(0.15)
            os.write(self.master, b"a")

        _writer = threading.Thread(target=later, daemon=True)

        _writer.start()
        t0 = time.time()
        self.assertEqual(g.getch_str(timeout=GETCH_TEST_TIMEOUT), "a")
        _writer.join(timeout=5)
        self.assertLess(time.time() - t0, 3.0)

    def test_idle_wait_with_no_change_does_not_ring(self):
        with patch.object(g, "_emit_notification_bell_once") as bell:
            def key_later():
                time.sleep(0.2)
                os.write(self.master, b"x")
            _writer = threading.Thread(target=key_later, daemon=True)
            _writer.start()
            self.assertEqual(g.getch_str(timeout=GETCH_TEST_TIMEOUT, moniker=None), "x")
            _writer.join(timeout=5)
        bell.assert_not_called()


class TestBellOnWake(unittest.TestCase):
    def setUp(self):
        self.master, self.slave = pty.openpty()
        self.stream = os.fdopen(self.slave, "r", buffering=1, encoding="utf-8")
        self._saved = common._current_input_stream
        common.set_input_stream(self.stream)
        cache.drain_change_wake()
        # Keys left in the process-wide input queue by an earlier DSR read must not reach this test.
        with common._input_queue_lock:
            common._input_queue.clear()
        cache.set_local_unread_count("bellman", 0)
        _as_member("bellman")

    def tearDown(self):
        common.set_input_stream(self._saved)
        try:
            self.stream.close()
            os.close(self.master)
        except OSError:
            pass

    def test_burst_in_window_rings_once(self):
        """Three changes inside one window must ring once, not three times."""
        g._bell_window = g.BellWindow(5.0)
        rings = []
        real_emit = g._emit_notification_bell_once

        def counting_emit():
            # Same windowing as production; count only actual rings.
            rang = real_emit()
            if rang:
                rings.append(1)
            return rang

        with patch.object(g, "_emit_notification_bell_once", side_effect=counting_emit), \
             patch.object(g, "_update_bottombar_on_notification", return_value=True), \
             patch.object(g, "_push_subscribed", return_value=True), \
             patch.object(common, "_current_input_stream", self.stream), \
             patch("bbsengine6.io.echo"):
            def writes():
                for i in range(3):
                    time.sleep(0.05)
                    cache.set_local_unread_count("bellman", i + 1)
                time.sleep(0.2)
                os.write(self.master, b"k")
            _writer = threading.Thread(target=writes, daemon=True)
            _writer.start()
            self.assertEqual(g.getch_str(timeout=GETCH_TEST_TIMEOUT), "k")
            _writer.join(timeout=5)
        self.assertEqual(len(rings), 1)

    def test_db_fallback_polls_without_push(self):
        with patch.object(g, "_push_subscribed", return_value=False), \
             patch.object(g, "_check_notifications", return_value=(False, 0)) as chk:
            def key_later():
                time.sleep(2.3)
                os.write(self.master, b"z")
            _writer = threading.Thread(target=key_later, daemon=True)
            _writer.start()
            self.assertEqual(g.getch_str(timeout=GETCH_TEST_TIMEOUT), "z")
            _writer.join(timeout=5)
        self.assertGreaterEqual(chk.call_count, 1)


if __name__ == "__main__":
    unittest.main()
