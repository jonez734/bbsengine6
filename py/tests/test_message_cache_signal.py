"""Cache change signal: generation counter, wake fd, and Event."""

import os
import select
import sys
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.message import cache  # noqa: E402


class TestCacheSignal(unittest.TestCase):
    def setUp(self):
        cache.drain_change_wake()
        cache.clear_local_unread_cache()
        cache.drain_change_wake()

    def test_every_write_bumps_generation(self):
        g0 = cache.change_generation()
        cache.set_local_unread_count("alice", 1)
        cache.bump_local_unread_count("alice", 1)
        cache.clear_local_unread_cache()
        self.assertEqual(cache.change_generation(), g0 + 3)

    def test_write_makes_wake_fd_readable(self):
        cache.set_local_unread_count("alice", 2)
        r, _, _ = select.select([cache.change_wake_fd()], [], [], 0)
        self.assertTrue(r)

    def test_drain_clears_wake_and_event(self):
        cache.set_local_unread_count("alice", 2)
        cache.drain_change_wake()
        r, _, _ = select.select([cache.change_wake_fd()], [], [], 0)
        self.assertFalse(r)
        self.assertFalse(cache.wait_for_change(0))

    def test_wait_for_change_wakes_from_other_thread(self):
        cache.drain_change_wake()
        threading.Timer(0.05, lambda: cache.set_local_unread_count("bob", 1)).start()
        self.assertTrue(cache.wait_for_change(2))

    def test_writer_does_not_block_when_nobody_reads(self):
        cache.drain_change_wake()
        for i in range(20000):
            cache.set_local_unread_count("alice", i)
        cache.drain_change_wake()

    def test_reads_do_not_signal(self):
        g0 = cache.change_generation()
        cache.get_local_unread_count("alice")
        self.assertEqual(cache.change_generation(), g0)


if __name__ == "__main__":
    unittest.main()
