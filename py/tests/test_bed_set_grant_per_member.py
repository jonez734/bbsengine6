# bbsengine6/py/tests/test_bed_set_grant_per_member.py
# The bed daemon runs SET ROLE <moniker> for every request a member makes (bed/src/bed/main.py,
# role_for_session). Without a grant to the daemon's login role, every data operation is refused
# with "permission denied to set role". Creating a member's login role therefore grants bed SET on it;
# removing the member revokes that grant.

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import pgrole


def _conn():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    return conn, cur


def _statements(cur):
    out = []
    for call in cur.execute.call_args_list:
        stmt = call.args[0]
        out.append(stmt.as_string(None) if hasattr(stmt, "as_string") else str(stmt))
    return out


@pytest.mark.unit
def test_creating_a_login_role_grants_bed_set_on_it():
    conn, cur = _conn()
    with patch.object(pgrole.database, "rolexists", return_value=False), \
         patch.object(pgrole.database, "createrol", return_value=True):
        ok = pgrole.ensure_os_login_role(object(), "jam", "m_jam", conn=conn)
    assert ok is True
    stmts = _statements(cur)
    assert any('GRANT "jam" TO "bed_zoid6"' in s for s in stmts), stmts


@pytest.mark.unit
def test_the_bed_grant_uses_set_true_and_no_inheritance():
    # The daemon only needs to switch into the login role. It should not inherit its privileges.
    conn, cur = _conn()
    with patch.object(pgrole.database, "rolexists", return_value=False), \
         patch.object(pgrole.database, "createrol", return_value=True):
        pgrole.ensure_os_login_role(object(), "jam", "m_jam", conn=conn)
    grant = [s for s in _statements(cur) if 'TO "bed_zoid6"' in s]
    assert grant, "no bed grant issued"
    assert "WITH SET TRUE" in grant[0].upper() and "INHERIT FALSE" in grant[0].upper(), grant[0]


@pytest.mark.unit
def test_remove_login_role_revokes_bed_before_dropping_the_login_role():
    # jam is a protected login role and is never removed by the console; use a regular member.
    conn, cur = _conn()
    with patch.object(pgrole.database, "rolexists", return_value=True), \
         patch.object(pgrole.database, "get_role_privs", return_value={"rolsuper": False}):
        ok = pgrole.remove_os_login_role(object(), "lo_test", "m_lo_test", conn=conn, drop_role=True)
    stmts = _statements(cur)
    revoke_bed = [i for i, s in enumerate(stmts) if 'REVOKE "lo_test" FROM "bed_zoid6"' in s]
    drop = [i for i, s in enumerate(stmts) if s.startswith("DROP ROLE")]
    assert ok is True
    assert revoke_bed, stmts
    assert drop and revoke_bed[0] < drop[0], "bed must be revoked before the login role is dropped"


@pytest.mark.unit
def test_removal_without_dropping_the_role_still_revokes_bed():
    conn, cur = _conn()
    with patch.object(pgrole.database, "rolexists", return_value=True), \
         patch.object(pgrole.database, "get_role_privs", return_value={"rolsuper": False}):
        pgrole.remove_os_login_role(object(), "lo_test", "m_lo_test", conn=conn, drop_role=False)
    assert any('REVOKE "lo_test" FROM "bed_zoid6"' in s for s in _statements(cur))


@pytest.mark.unit
def test_a_protected_login_role_is_never_touched():
    # jam is protected: its bed grant and login role must survive a removal attempt.
    conn, cur = _conn()
    with patch.object(pgrole.database, "rolexists", return_value=True), \
         patch.object(pgrole.database, "get_role_privs", return_value={"rolsuper": False}):
        ok = pgrole.remove_os_login_role(object(), "jam", "m_jam", conn=conn, drop_role=True)
    assert ok is False
    assert not _statements(cur)


@pytest.mark.unit
def test_bed_grant_is_never_made_to_the_shared_member_role():
    # A grant of the login role to member, or of member to bed, would let members act for each other.
    conn, cur = _conn()
    with patch.object(pgrole.database, "rolexists", return_value=False), \
         patch.object(pgrole.database, "createrol", return_value=True):
        pgrole.ensure_os_login_role(object(), "jam", "m_jam", conn=conn)
    stmts = _statements(cur)
    assert not any('TO "member"' in s and '"jam"' in s for s in stmts)
    assert not any('GRANT "member" TO "bed_zoid6"' in s for s in stmts)
