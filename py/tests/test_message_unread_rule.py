"""The unread definition: pending and delivered count; read does not.

Checks the SQL text, since the database is not available in this test
environment. Also pins that on-connect delivery and the batch mark still
act only on pending rows.
"""

import inspect
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.message.dal import messages as dal  # noqa: E402


class TestUnreadRule(unittest.TestCase):
    def test_count_calls_the_unread_function(self):
        # The unread rule (pending and delivered count; read does not) is
        # defined in bed's engine.bed_count_unread and pinned by bed's tests.
        # bbsengine6 only calls the function.
        src = inspect.getsource(dal.count_unread_for_recipient)
        self.assertIn("engine.bed_count_unread", src)
        self.assertNotIn("status = 'pending'", src)

    def test_on_connect_delivery_still_pending_only(self):
        src = inspect.getsource(dal.list_undelivered_for_recipient)
        self.assertIn("r.status = 'pending'", src)

    def test_batch_mark_only_moves_pending(self):
        src = inspect.getsource(dal.mark_delivered_batch)
        self.assertIn("AND status = 'pending'", src)


if __name__ == "__main__":
    unittest.main()
