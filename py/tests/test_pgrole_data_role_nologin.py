"""Data roles m_<moniker> are NOLOGIN: only SET ROLE reaches them, never a direct login.

A LOGIN data role lets an OS account of that name connect and skip the login role.
The login role is a member of the data role, so SET ROLE still works under NOLOGIN.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import pgrole


def _conn():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    return conn, cur


@pytest.mark.unit
def test_new_data_role_is_created_nologin():
    conn, cur = _conn()
    cur.fetchone.return_value = None
    with patch.object(pgrole.database, "rolexists", return_value=False), \
         patch.object(pgrole.database, "createrol", return_value=True) as cr, \
         patch.object(pgrole.database, "manage_schema_priv"):
        pgrole._ensure_login_role(object(), "lo_test", conn=conn)
    assert cr.call_args.args[1] == "m_lo_test"
    assert cr.call_args.kwargs.get("login") is False


@pytest.mark.unit
def test_existing_login_capable_data_role_is_altered_nologin():
    conn, cur = _conn()
    cur.fetchone.return_value = None
    with patch.object(pgrole.database, "rolexists", return_value=True), \
         patch.object(pgrole.database, "get_role_privs", return_value={"rolcanlogin": True, "rolsuper": False}), \
         patch.object(pgrole.database, "manage_schema_priv"):
        pgrole._ensure_login_role(object(), "lo_test", conn=conn)
    executed = [c.args[0].as_string(None) if hasattr(c.args[0], "as_string") else str(c.args[0])
                for c in cur.execute.call_args_list]
    assert 'ALTER ROLE "m_lo_test" NOLOGIN' in executed, executed


@pytest.mark.unit
def test_existing_nologin_data_role_is_not_altered():
    conn, cur = _conn()
    cur.fetchone.return_value = None
    with patch.object(pgrole.database, "rolexists", return_value=True), \
         patch.object(pgrole.database, "get_role_privs", return_value={"rolcanlogin": False, "rolsuper": False}), \
         patch.object(pgrole.database, "manage_schema_priv"):
        pgrole._ensure_login_role(object(), "lo_test", conn=conn)
    executed = [c.args[0].as_string(None) if hasattr(c.args[0], "as_string") else str(c.args[0])
                for c in cur.execute.call_args_list]
    assert not any("NOLOGIN" in s for s in executed), executed


@pytest.mark.unit
def test_superuser_data_role_is_never_altered():
    conn, cur = _conn()
    cur.fetchone.return_value = None
    with patch.object(pgrole.database, "rolexists", return_value=True), \
         patch.object(pgrole.database, "get_role_privs", return_value={"rolcanlogin": True, "rolsuper": True}), \
         patch.object(pgrole.database, "manage_schema_priv"):
        pgrole._ensure_login_role(object(), "jam", conn=conn)
    executed = [c.args[0].as_string(None) if hasattr(c.args[0], "as_string") else str(c.args[0])
                for c in cur.execute.call_args_list]
    assert not any("NOLOGIN" in s for s in executed), executed


@pytest.mark.unit
def test_migration_sql_skips_superusers_and_jam_and_is_idempotent():
    from pathlib import Path
    sql = (Path(pgrole.__file__).parent / "sql" / "pgrole.sql").read_text()
    assert "rolcanlogin" in sql and "NOLOGIN" in sql
    assert "rolsuper" in sql, "migration must skip superusers"
    assert "'jam'" in sql, "migration must skip jam (legacy mapping)"


@pytest.mark.unit
def test_createpgrole_sql_creates_nologin_data_roles():
    from pathlib import Path
    sql = (Path(pgrole.__file__).parent / "sql" / "createrol.sql").read_text()
    # Scope to engine.createpgrole's body; engine.createrol is a separate, plain-role helper.
    body = sql.split("CREATE OR REPLACE FUNCTION engine.createpgrole", 1)[1].split("$$ LANGUAGE", 1)[0]
    create = [line for line in body.splitlines() if "CREATE ROLE" in line]
    assert create and all("NOLOGIN" in line for line in create), create


@pytest.mark.unit
def test_createpgrole_is_marked_deprecated():
    from pathlib import Path
    sql = (Path(pgrole.__file__).parent / "sql" / "createrol.sql").read_text()
    header = sql.split("CREATE OR REPLACE FUNCTION engine.createpgrole")[0]
    assert "DEPRECATED" in header, "createpgrole must carry a DEPRECATED marker above its definition"
