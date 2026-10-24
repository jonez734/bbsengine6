"""Console-driven NOLOGIN migration.

The preview lists the m_ data roles that can still log in (not superusers, not jam).
[K] shows the preview, asks before changing anything, and runs the migration SQL in one
transaction. The startup warning reports pending roles and never blocks startup.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import pgrole
from bbsengine6.console import main as console_main

SQL_DIR = Path(pgrole.__file__).parent / "sql"


def _conn(rows=None, exc=None):
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    if exc is not None:
        cur.execute.side_effect = exc
    cur.fetchall.return_value = rows or []
    cur.fetchone.return_value = rows[0] if rows else None
    return conn, cur


@pytest.mark.unit
def test_preview_lists_only_login_capable_non_superuser_m_roles():
    conn, cur = _conn(rows=[("m_alice",), ("m_bob",)])
    out = pgrole.preview_nologin_migration(object(), conn=conn)
    assert out == ["m_alice", "m_bob"]
    sql = cur.execute.call_args.args[0]
    assert "rolcanlogin" in sql and "rolsuper" in sql
    assert "jam" in sql, "preview must exclude jam"


@pytest.mark.unit
def test_preview_is_read_only():
    conn, cur = _conn(rows=[("m_alice",)])
    pgrole.preview_nologin_migration(object(), conn=conn)
    for c in cur.execute.call_args_list:
        assert not str(c.args[0]).lstrip().lower().startswith(("alter", "update", "insert", "delete", "drop"))


@pytest.mark.unit
def test_migration_sql_is_a_named_file_with_the_nologin_block():
    f = SQL_DIR / "migrate_nologin.sql"
    assert f.is_file(), f
    text = f.read_text()
    assert "nologin" in text.lower()
    assert "'jam'" in text
    assert "rolsuper" in text


@pytest.mark.unit
def test_pgrole_sql_no_longer_carries_the_do_block():
    text = (SQL_DIR / "pgrole.sql").read_text()
    assert "alter role %I nologin" not in text
    assert "rolcanlogin" not in text


@pytest.mark.unit
def test_menu_option_k_is_offered_only_to_sysops():
    src = console_main.__file__
    body = Path(src).read_text()
    assert '"K"' in body or "'K'" in body
    assert "issysop" in body


@pytest.mark.unit
def test_declining_the_prompt_runs_no_alter():
    conn, cur = _conn(rows=[("m_alice",)])
    with patch.object(console_main.io, "inputboolean", return_value=False) as ask, \
         patch.object(console_main.io, "echo"), \
         patch.object(console_main.pgrole, "run_nologin_migration") as run:
        console_main._migrate_nologin(object(), conn=conn, roles=["m_alice"])
    ask.assert_called_once()
    run.assert_not_called()


@pytest.mark.unit
def test_nothing_to_migrate_says_so_and_does_not_prompt():
    conn, cur = _conn(rows=[])
    with patch.object(console_main.io, "inputboolean") as ask, \
         patch.object(console_main.io, "echo") as echo:
        console_main._migrate_nologin(object(), conn=conn, roles=[])
    ask.assert_not_called()
    assert any("nothing to migrate" in str(c.args[0]).lower() for c in echo.call_args_list)


@pytest.mark.unit
def test_run_uses_the_shared_sql_file_in_one_transaction_and_commits():
    conn, cur = _conn()
    with patch.object(pgrole.database, "importsql", return_value=True) as imp:
        ok = pgrole.run_nologin_migration(object(), conn=conn)
    assert ok is True
    assert imp.call_args.args[1] == "migrate_nologin.sql"
    # importsql must not roll back on its own: the runner commits or rolls back once.
    assert imp.call_args.kwargs.get("rollback") is False
    conn.commit.assert_called_once()


@pytest.mark.unit
def test_failed_migration_rolls_back_and_reports():
    conn, cur = _conn()
    with patch.object(pgrole.database, "importsql", side_effect=RuntimeError("boom")):
        ok = pgrole.run_nologin_migration(object(), conn=conn)
    assert ok is False
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()


@pytest.mark.unit
def test_startup_warning_only_when_roles_pending():
    with patch.object(console_main, "pgrole") as pg, patch.object(console_main.io, "echo") as echo:
        pg.preview_nologin_migration.return_value = ["m_alice", "m_bob"]
        console_main._startup_nologin_warning(object(), conn=MagicMock())
    assert any("2 data roles" in str(c.args[0]) for c in echo.call_args_list)


@pytest.mark.unit
def test_startup_warning_silent_when_nothing_pending():
    with patch.object(console_main, "pgrole") as pg, patch.object(console_main.io, "echo") as echo:
        pg.preview_nologin_migration.return_value = []
        console_main._startup_nologin_warning(object(), conn=MagicMock())
    assert echo.call_args_list == []


@pytest.mark.unit
def test_startup_warning_never_raises_on_query_failure():
    with patch.object(console_main, "pgrole") as pg, patch.object(console_main.io, "echo"):
        pg.preview_nologin_migration.side_effect = RuntimeError("permission denied for schema engine")
        console_main._startup_nologin_warning(object(), conn=MagicMock())  # must not raise
