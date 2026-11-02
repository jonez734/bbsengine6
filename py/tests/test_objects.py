"""Tests for bbsengine6.backend.objects: manifest validation and status checks.

The catalog is faked with a cursor that answers each lookup from a set of
present names, so no database is needed.
"""

import json

import pytest

from bbsengine6.backend import objects
from bbsengine6.backend.objects import (
    ManifestError,
    ObjectRef,
    check_objects,
    load_manifest,
)


def _manifest(objs, project="bed"):
    return {"schema_version": 1, "project": project, "objects": objs}


GOOD = [
    {"kind": "role", "name": "bed_obj"},
    {"kind": "schema", "name": "engine"},
    {"kind": "table", "name": "engine.__bed_token"},
    {"kind": "view", "name": "engine.member"},
    {"kind": "sequence", "name": "bank.__account_id_seq"},
    {"kind": "function", "name": "engine.bed_bank_op", "args": "bytea, text, jsonb"},
]


# ---- validation (2.2) -------------------------------------------------------


def test_valid_manifest_loads():
    m = load_manifest(_manifest(GOOD))
    assert m.project == "bed"
    assert len(m.objects) == len(GOOD)
    assert m.objects[-1] == ObjectRef("function", "engine.bed_bank_op", "bytea, text, jsonb")


def test_loads_from_file(tmp_path):
    path = tmp_path / "objects.json"
    path.write_text(json.dumps(_manifest(GOOD)), encoding="utf-8")
    assert load_manifest(str(path)).project == "bed"


def test_malformed_json_file_is_refused(tmp_path):
    path = tmp_path / "objects.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ManifestError, match="cannot read manifest"):
        load_manifest(str(path))


def test_missing_file_is_refused(tmp_path):
    with pytest.raises(ManifestError, match="cannot read manifest"):
        load_manifest(str(tmp_path / "nope.json"))


@pytest.mark.parametrize("bad_version", [0, 2, "1", None])
def test_schema_version_must_be_1(bad_version):
    data = _manifest(GOOD)
    data["schema_version"] = bad_version
    with pytest.raises(ManifestError, match="schema_version"):
        load_manifest(data)


def test_top_level_must_be_object():
    with pytest.raises(ManifestError, match="must be a JSON object"):
        load_manifest(["not", "an", "object"])


@pytest.mark.parametrize("project", ["", None, 3])
def test_project_must_be_nonempty_string(project):
    data = _manifest(GOOD)
    data["project"] = project
    with pytest.raises(ManifestError, match="project"):
        load_manifest(data)


@pytest.mark.parametrize("objs", [[], None, "table"])
def test_objects_must_be_nonempty_list(objs):
    with pytest.raises(ManifestError, match="objects"):
        load_manifest(_manifest(objs))


def test_unknown_kind_is_refused():
    with pytest.raises(ManifestError, match="kind 'index'"):
        load_manifest(_manifest([{"kind": "index", "name": "engine.x"}]))


@pytest.mark.parametrize(
    "entry",
    [
        {"kind": "table", "name": "Engine.Bad"},
        {"kind": "table", "name": "engine.x; DROP TABLE y"},
        {"kind": "table", "name": "engine..x"},
        {"kind": "table", "name": "1bad"},
        {"kind": "role", "name": "bed.obj"},
        {"kind": "schema", "name": "engine.x"},
    ],
)
def test_bad_names_are_refused(entry):
    with pytest.raises(ManifestError):
        load_manifest(_manifest([entry]))


def test_table_name_must_be_qualified_or_bare_identifier():
    # A bare table name is allowed (it resolves on search_path); a dotted one must be well formed.
    load_manifest(_manifest([{"kind": "table", "name": "member"}]))


def test_function_needs_args():
    with pytest.raises(ManifestError, match="needs an 'args' string"):
        load_manifest(_manifest([{"kind": "function", "name": "engine.f"}]))


def test_function_must_be_schema_qualified():
    with pytest.raises(ManifestError, match="schema-qualified"):
        load_manifest(_manifest([{"kind": "function", "name": "f", "args": "text"}]))


def test_function_args_reject_injection_characters():
    with pytest.raises(ManifestError, match="not allowed in a signature"):
        load_manifest(
            _manifest([{"kind": "function", "name": "engine.f", "args": "text); DROP x"}])
        )


def test_args_only_valid_for_functions():
    with pytest.raises(ManifestError, match="only valid for functions"):
        load_manifest(_manifest([{"kind": "table", "name": "engine.x", "args": "text"}]))


def test_duplicate_entries_are_refused():
    dup = [{"kind": "table", "name": "engine.x"}, {"kind": "table", "name": "engine.x"}]
    with pytest.raises(ManifestError, match="duplicate"):
        load_manifest(_manifest(dup))


def test_overloads_are_distinct_not_duplicates():
    overloads = [
        {"kind": "function", "name": "engine.f", "args": "text"},
        {"kind": "function", "name": "engine.f", "args": "integer"},
    ]
    assert len(load_manifest(_manifest(overloads)).objects) == 2


# ---- status (2.1 and 2.3) ---------------------------------------------------


class FakeCursor:
    """Answers each catalog probe from a set of present object keys."""

    def __init__(self, present):
        self.present = present
        self.executed = []

    def execute(self, sql, params=()):
        self.executed.append((sql, params))

    def fetchone(self):
        return {"present": self.executed[-1][1][0] in self.present}


@pytest.fixture
def fake_cursor(monkeypatch):
    """Route database.cursor to the fake, so check_objects uses no real connection."""

    class _Ctx:
        def __init__(self, c):
            self.c = c

        def __enter__(self):
            return self.c

        def __exit__(self, *a):
            return False

    def make(present):
        cur = FakeCursor(present)
        monkeypatch.setattr(objects.database, "cursor", lambda conn=None, **kw: _Ctx(cur))
        return cur

    return make


def _mf(objs):
    return load_manifest(_manifest(objs))


def test_all_present_is_installed(fake_cursor):
    names = {"bed_obj", "engine", "engine.__bed_token"}
    fake_cursor(names)
    m = _mf([
        {"kind": "role", "name": "bed_obj"},
        {"kind": "schema", "name": "engine"},
        {"kind": "table", "name": "engine.__bed_token"},
    ])
    r = check_objects(None, m, conn=object())
    assert r.status == objects.STATUS_INSTALLED
    assert r.missing == []
    assert len(r.present) == 3


def test_none_present_is_not_installed(fake_cursor):
    fake_cursor(set())
    m = _mf([{"kind": "table", "name": "engine.x"}, {"kind": "view", "name": "engine.y"}])
    r = check_objects(None, m, conn=object())
    assert r.status == objects.STATUS_NOT_INSTALLED
    assert [o.name for o in r.missing] == ["engine.x", "engine.y"]
    assert r.present == []


def test_some_present_is_partial_and_lists_missing(fake_cursor):
    fake_cursor({"engine.a"})
    m = _mf([{"kind": "table", "name": "engine.a"}, {"kind": "table", "name": "engine.b"}])
    r = check_objects(None, m, conn=object())
    assert r.status == objects.STATUS_PARTIAL
    assert [o.name for o in r.missing] == ["engine.b"]


def test_function_probe_uses_exact_signature(fake_cursor):
    cur = fake_cursor({"engine.f(text)"})
    m = _mf([{"kind": "function", "name": "engine.f", "args": "text"}])
    r = check_objects(None, m, conn=object())
    assert r.status == objects.STATUS_INSTALLED
    assert cur.executed[-1][1] == ("engine.f(text)",)


def test_overload_missing_is_reported(fake_cursor):
    # engine.f(text) exists, engine.f(integer) does not: exact match means partial.
    fake_cursor({"engine.f(text)"})
    m = _mf([
        {"kind": "function", "name": "engine.f", "args": "text"},
        {"kind": "function", "name": "engine.f", "args": "integer"},
    ])
    r = check_objects(None, m, conn=object())
    assert r.status == objects.STATUS_PARTIAL
    assert r.missing == [ObjectRef("function", "engine.f", "integer")]


def test_each_kind_uses_its_catalog_query(fake_cursor):
    cur = fake_cursor(set())
    m = _mf([
        {"kind": "role", "name": "r1"},
        {"kind": "schema", "name": "s1"},
        {"kind": "table", "name": "s1.t"},
        {"kind": "view", "name": "s1.v"},
        {"kind": "sequence", "name": "s1.q"},
        {"kind": "function", "name": "s1.f", "args": "int"},
    ])
    check_objects(None, m, conn=object())
    sqls = [sql for sql, _ in cur.executed]
    assert "pg_roles" in sqls[0]
    assert "pg_namespace" in sqls[1]
    assert "to_regclass" in sqls[2] and "to_regclass" in sqls[3] and "to_regclass" in sqls[4]
    assert "to_regprocedure" in sqls[5]


def test_check_objects_needs_a_connection():
    m = _mf([{"kind": "table", "name": "engine.x"}])
    with pytest.raises(ValueError, match="conn= or pool="):
        check_objects(None, m)


def test_check_objects_never_runs_ddl(fake_cursor):
    cur = fake_cursor({"engine.x"})
    m = _mf([{"kind": "table", "name": "engine.x"}])
    check_objects(None, m, conn=object())
    for sql, _ in cur.executed:
        upper = sql.upper()
        assert not any(w in upper for w in ("CREATE", "ALTER", "DROP", "GRANT", "INSERT", "UPDATE", "DELETE"))


def test_a_gate_never_passes_on_an_unread_value():
    """A row the checker cannot read is absent, not present. A Mock cursor must not
    make every object look installed."""
    from unittest.mock import MagicMock

    cur = MagicMock()  # fetchone() returns a MagicMock, not a dict or tuple
    m = _mf([{"kind": "table", "name": "engine.x"}])
    assert objects._exists(cur, m.objects[0]) is False


def test_exists_requires_a_true_boolean_from_the_catalog():
    class Cur:
        def __init__(self, row):
            self.row = row

        def execute(self, sql, params=()):
            pass

        def fetchone(self):
            return self.row

    m = _mf([{"kind": "table", "name": "engine.x"}])
    assert objects._exists(Cur({"present": True}), m.objects[0]) is True
    assert objects._exists(Cur({"present": "yes"}), m.objects[0]) is False
    assert objects._exists(Cur(None), m.objects[0]) is False
    assert objects._exists(Cur((True,)), m.objects[0]) is True
    assert objects._exists(Cur(()), m.objects[0]) is False
