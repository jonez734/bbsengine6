"""Notification and unread lookups use the registry's args, never the NEEDINFO sentinel."""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import bottombar
from bbsengine6.database import BBSENGINE6_DBNAME_DEFAULT


@pytest.mark.unit
def test_notification_status_with_no_args_uses_registry_args():
    shell_args = MagicMock(databasename="zoid6", debug=False)
    reg = bottombar._resolve_registry()
    reg.set_context(args=shell_args, player=None, pool=None)
    seen = {}

    def fake_unread(moniker, **kw):
        seen["args"] = kw.get("args")
        return 0

    with patch("bbsengine6.member._threadlocal") as tl, \
         patch("bbsengine6.message.is_enabled", return_value=True), \
         patch("bbsengine6.message.get_local_unread_count", return_value=-1), \
         patch("bbsengine6.message.get_unread_count", side_effect=fake_unread), \
         patch("bbsengine6.message.set_local_unread_count"):
        tl.moniker = "jam"
        bottombar._get_notification_status(args=None, pool=None)
    assert seen["args"] is shell_args
    assert getattr(seen["args"], "databasename", None) != BBSENGINE6_DBNAME_DEFAULT
