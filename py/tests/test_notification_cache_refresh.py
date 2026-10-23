"""The idle notification check and the bottombar re-read the unread count, so a stale count is corrected.

STATUS: expected to fail. The fix (re-read on every check) was tried and reverted: in the full
bbsengine6 run it caused about 66 new failures across unrelated invite, member-verify, owner-loop,
subscription and unicode tests, and the cause was not identified. Until it is, these tests document
the required behaviour and are marked xfail so they do not break the suite.
"""

from unittest.mock import patch

import pytest

from bbsengine6 import message as message_module
import importlib

getch = importlib.import_module("bbsengine6.io.getch")


@pytest.fixture(autouse=True)
def _reset_cache():
    message_module.clear_local_unread_cache()
    yield
    message_module.clear_local_unread_cache()


@pytest.mark.unit
@pytest.mark.xfail(strict=True, reason="refresh causes suite-wide regressions; see module docstring")
def test_idle_check_refreshes_a_stale_cached_count():
    message_module.set_local_unread_count("bob", 3)
    with patch.object(message_module, "is_enabled", return_value=True), \
         patch.object(message_module, "get_unread_count", return_value=4) as db:
        has, count = getch._check_notifications("bob", args=None, pool=None, conn=None)
    db.assert_called_once()
    assert count == 4
    assert has is True
    assert message_module.get_local_unread_count("bob") == 4


@pytest.mark.unit
@pytest.mark.xfail(strict=True, reason="refresh causes suite-wide regressions; see module docstring")
def test_idle_check_reports_no_messages_after_they_are_read():
    message_module.set_local_unread_count("bob", 2)
    with patch.object(message_module, "is_enabled", return_value=True), \
         patch.object(message_module, "get_unread_count", return_value=0):
        has, count = getch._check_notifications("bob", args=None, pool=None, conn=None)
    assert (has, count) == (False, 0)
    assert message_module.get_local_unread_count("bob") == 0


@pytest.mark.unit
@pytest.mark.xfail(strict=True, reason="refresh causes suite-wide regressions; see module docstring")
def test_bottombar_reads_the_same_count_as_the_idle_check():
    from bbsengine6 import bottombar
    message_module.set_local_unread_count("bob", 3)
    with patch.object(message_module, "is_enabled", return_value=True), \
         patch.object(message_module, "get_unread_count", return_value=4), \
         patch("bbsengine6.member._threadlocal") as tl:
        tl.moniker = "bob"
        text = bottombar._get_notification_status(args=None, pool=None)
    assert text == "F2: messages (4)"
