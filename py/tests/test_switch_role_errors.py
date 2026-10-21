"""switch_role reports a denied switch as a permission error, not a missing role.

set_role returns False both when the role does not exist and when the connecting
role may not set it. switch_role must tell them apart, so a denied switch is not
reported as a missing role.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import database


def test_denied_switch_is_a_permission_error():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = ("bed",)
    with patch.object(database, "rolexists", return_value=True), \
         patch.object(database, "set_role", return_value=False):
        with pytest.raises(PermissionError, match="may not set role"):
            with database.switch_role(object(), "m_jam", conn=conn):
                pass


def test_missing_role_is_still_a_value_error():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = ("bed",)
    with patch.object(database, "rolexists", return_value=False):
        with pytest.raises(ValueError, match="does not exist"):
            with database.switch_role(object(), "m_ghost", conn=conn):
                pass
