"""bbsengine6's shipped sql/objects.json: it validates, and it matches the live schema.

The shape test runs with no database. The live check runs only when the
zoid6 database is reachable, and is skipped otherwise.
"""

import json
import shutil
import subprocess
from importlib import resources

import pytest

from bbsengine6.backend import objects


def _shipped_text():
    return resources.files("bbsengine6").joinpath("sql/objects.json").read_text(encoding="utf-8")


def test_shipped_manifest_validates():
    m = objects.load_manifest(json.loads(_shipped_text()))
    assert m.project == "bbsengine6"
    assert len(m.objects) > 0


def test_shipped_manifest_has_no_other_project_objects():
    """bed, casino and postoffice objects live in their own manifests, never here."""
    m = objects.load_manifest(json.loads(_shipped_text()))
    forbidden = ("bed_", "casino_", "postoffice.", "zoid6")
    for obj in m.objects:
        assert not any(obj.name.startswith(p) or p in obj.name for p in forbidden), obj.label()


def test_shipped_manifest_functions_are_schema_qualified_and_exact():
    m = objects.load_manifest(json.loads(_shipped_text()))
    for obj in m.objects:
        if obj.kind == "function":
            assert "." in obj.name
            assert obj.args is not None


def _psql_ok(sql):
    if shutil.which("psql") is None:
        return None
    proc = subprocess.run(
        ["psql", "-d", "zoid6", "-Atc", sql], capture_output=True, text=True, timeout=20, check=False
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() == "t"


@pytest.mark.requires_db
def test_shipped_manifest_matches_live_zoid6_database():
    if _psql_ok("select 1") is None:
        pytest.skip("zoid6 database not reachable")
    m = objects.load_manifest(json.loads(_shipped_text()))
    missing = []
    for obj in m.objects:
        if obj.kind == "role":
            q = f"select exists(select 1 from pg_roles where rolname='{obj.name}')"
        elif obj.kind == "schema":
            q = f"select exists(select 1 from pg_namespace where nspname='{obj.name}')"
        elif obj.kind in ("table", "view", "sequence"):
            q = f"select to_regclass('{obj.name}') is not null"
        else:
            q = f"select to_regprocedure('{obj.name}({obj.args})') is not null"
        if _psql_ok(q) is not True:
            missing.append(obj.label())
    assert missing == [], f"manifest entries missing from the live database: {missing}"
