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
    def test_count_includes_delivered_and_excludes_read(self):
        # The unread rule now lives in the zoid6-owned SQL function bed calls.
        sql_path = os.path.join(
            os.path.dirname(dal.__file__), "..", "..", "sql", "bed_message_read_functions.sql"
        )
        with open(sql_path) as fh:
            fn = fh.read()
        self.assertIn("status IN ('pending', 'delivered')", fn)
        self.assertNotIn("status = 'pending'", fn)

    def test_on_connect_delivery_still_pending_only(self):
        src = inspect.getsource(dal.list_undelivered_for_recipient)
        self.assertIn("r.status = 'pending'", src)

    def test_batch_mark_only_moves_pending(self):
        src = inspect.getsource(dal.mark_delivered_batch)
        self.assertIn("AND status = 'pending'", src)


if __name__ == "__main__":
    unittest.main()
