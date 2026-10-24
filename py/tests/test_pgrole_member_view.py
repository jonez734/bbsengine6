"""engine.pgrole_member: one definition of the member-to-psql-role join.

Replaces the join repeated in showpgrole, memberapproval and pgrole. It exposes the
member, the data role and the OS login, and is registered with checkclasses like the
other engine views.
"""

from pathlib import Path

import pytest

from bbsengine6 import pgrole
from bbsengine6.backend import checkclasses

SQL = Path(pgrole.__file__).parent / "sql" / "pgrole_member_view.sql"


@pytest.mark.unit
def test_view_file_defines_the_join_once():
    text = SQL.read_text()
    assert "create or replace view engine.pgrole_member" in text.lower()
    assert "engine.__member" in text and "engine.pgrole" in text
    assert "join" in text.lower()


@pytest.mark.unit
def test_view_exposes_moniker_loginid_rolname_and_osuser():
    text = SQL.read_text().lower()
    for col in ("moniker", "loginid", "rolname", "osuser"):
        assert col in text, col


@pytest.mark.unit
def test_view_is_registered_with_checkclasses():
    assert ("engine.pgrole_member", "pgrole_member_view.sql") in checkclasses.classlist


@pytest.mark.unit
def test_view_is_granted_to_the_console_roles():
    text = SQL.read_text().lower()
    assert "grant select" in text and "on engine.pgrole_member" in text
    assert "sysop" in text


@pytest.mark.unit
def test_approval_lookup_uses_the_view():
    """The approval default reads osuser from the view, not an inline join.

    showpgrole keeps its LEFT JOIN (it also needs created_at and last_ack_at, which the
    view does not expose), and pgrole._sync_groups keeps its inner join (it must fail
    when there is no row). Those stay as they are.
    """
    text = (Path(pgrole.__file__).parent / "console" / "memberapproval.py").read_text()
    assert "engine.pgrole_member" in text
    assert "join engine.pgrole" not in text.lower()
