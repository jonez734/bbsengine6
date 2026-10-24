"""The OS-username prompt offers a default: the stored osuser, else the loginid."""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.console import member as console_member


def _ask(stored_osuser, loginid="lo_test"):
    conn = MagicMock()
    with patch.object(console_member, "_stored_osuser", return_value=stored_osuser), \
         patch.object(console_member.io, "inputstring", return_value="") as ins, \
         patch.object(console_member.database, "rolexists", return_value=True), \
         patch("bbsengine6.console.member.io.echo"):
        console_member._ask_os_login(object(), loginid, "m_lo_test", conn=conn)
    return ins


@pytest.mark.unit
def test_osuser_prompt_defaults_to_the_loginid_when_nothing_is_stored():
    ins = _ask(stored_osuser=None, loginid="lo_test")
    assert ins.call_args.args[1] == "lo_test"


@pytest.mark.unit
def test_osuser_prompt_defaults_to_the_stored_osuser():
    ins = _ask(stored_osuser="lo_os", loginid="lo_test")
    assert ins.call_args.args[1] == "lo_os"


@pytest.mark.unit
def test_stored_osuser_reads_engine_pgrole_for_the_role():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = {"osuser": "lo_os"}
    assert console_member._stored_osuser(conn, "m_lo_test") == "lo_os"
    sql = cur.execute.call_args.args[0]
    assert "engine.pgrole" in sql and "osuser" in sql
