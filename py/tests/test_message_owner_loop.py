"""The owner loop outlives the subscribe call; asyncio.run is not used."""

import asyncio
import inspect
import os
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.startup import message_subscription as ms  # noqa: E402


class TestOwnerLoop(unittest.TestCase):
    def test_sync_wrapper_does_not_use_asyncio_run(self):
        src = inspect.getsource(ms.subscribe_to_bed_sync)
        self.assertNotIn("asyncio.run(", src)
        self.assertIn("run_coroutine_threadsafe", src)

    def test_owner_loop_keeps_running_after_subscribe_returns(self):
        async def fake_subscribe(args, moniker, **kwargs):
            return True

        with patch.object(ms, "subscribe_to_bed", side_effect=fake_subscribe):
            self.assertTrue(ms.subscribe_to_bed_sync(object(), "alice"))
        loop = ms._owner_loop_get()
        self.assertFalse(loop.is_closed())
        self.assertTrue(loop.is_running())

        # A task scheduled after the first call still runs: the loop is alive.
        done = threading.Event()

        async def ping():
            done.set()

        asyncio.run_coroutine_threadsafe(ping(), loop)
        self.assertTrue(done.wait(2))

    def test_owner_loop_is_a_single_loop(self):
        self.assertIs(ms._owner_loop_get(), ms._owner_loop_get())


if __name__ == "__main__":
    unittest.main()
