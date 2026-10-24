"""An existing member's stored osuser and data role are loaded into the edit dict.

Without this, an untouched save passes osuser=None to configurerole on the menu path,
which would clear the member's OS login.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.console import member as console_member


@pytest.mark.unit
def test_load_psql_fills_osuser_and_psqlrole_from_engine_pgrole():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = {"osuser": "lo_os", "rolname": "m_lo_test"}
    m = {"moniker": "lo_test"}
    console_member._load_psql(conn, m)
    assert m["osuser"] == "lo_os"
    assert m["psqlrole"] == "m_lo_test"


@pytest.mark.unit
def test_load_psql_leaves_none_for_a_member_with_no_role():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = None
    m = {"moniker": "new_one"}
    console_member._load_psql(conn, m)
    assert m["osuser"] is None
    assert m["psqlrole"] is None


@pytest.mark.unit
def test_untouched_edit_keeps_the_stored_osuser():
    """Saving an existing member without touching [O]/[X] must not clear osuser."""
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = {"osuser": "lo_os", "rolname": "m_lo_test"}
    m = {"moniker": "lo_test", "loginid": "lo_test", "osuser": None, "psqlrole": None}
    console_member._load_psql(conn, m)
    assert m["osuser"] == "lo_os", "load must run before the menu so the stored value survives"
