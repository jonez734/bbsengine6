"""Startup (stage_one -> checkclasses) imports the pgrole_member view when it is missing.

A database that already has engine.pgrole gets the view on the next startup, because
checkclasses imports any classlist entry whose class does not exist yet.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.backend import checkclasses, stage_one


@pytest.mark.unit
def test_stage_one_runs_checkclasses():
    assert "checkclasses" in open(stage_one.__file__).read()


@pytest.mark.unit
def test_missing_view_is_imported_from_its_sql_file():
    conn = MagicMock()
    imported = []

    def fake_exists(args, cls, conn=None, **kw):
        return cls != "engine.pgrole_member"

    def fake_import(args, sql, conn=None, rollback=True, **kw):
        imported.append(sql)
        return True

    with patch.object(checkclasses, "classexists", side_effect=fake_exists), \
         patch.object(checkclasses.database, "importsql", side_effect=fake_import), \
         patch.object(checkclasses.lib, "retry_on_transient", side_effect=lambda f: f()), \
         patch.object(checkclasses.lib, "_ensure_autocommit_off"), \
         patch.object(checkclasses.database, "cursor") as cur_cm, \
         patch("bbsengine6.backend.checkclasses.io.echo"):
        cur_cm.return_value.__enter__.return_value = MagicMock()
        ok = checkclasses.main(object(), conn=conn)
    assert ok is True
    assert "pgrole_member_view.sql" in imported, imported


@pytest.mark.unit
def test_existing_view_is_not_reimported():
    conn = MagicMock()
    imported = []
    with patch.object(checkclasses, "classexists", return_value=True), \
         patch.object(checkclasses.database, "importsql", side_effect=lambda *a, **k: imported.append(a[1]) or True), \
         patch.object(checkclasses.lib, "_ensure_autocommit_off"), \
         patch.object(checkclasses.database, "cursor") as cur_cm, \
         patch("bbsengine6.backend.checkclasses.io.echo"):
        cur_cm.return_value.__enter__.return_value = MagicMock()
        checkclasses.main(object(), conn=conn)
    assert "pgrole_member_view.sql" not in imported
