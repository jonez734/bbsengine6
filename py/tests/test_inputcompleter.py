"""inputcompleter returns matches from the database module.

Regression: _refresh used a relative import (`from . import database`) that resolved to
bbsengine6.io.database, which does not exist, so every completion raised ImportError.
The database cursor is replaced with a fake so no PostgreSQL is needed.
"""

import contextlib
import importlib

import pytest

ic = importlib.import_module("bbsengine6.io.inputcompleter")
db = importlib.import_module("bbsengine6.database")


class _FakeCursor:
    def execute(self, query, params):
        self.params = params

    def fetchall(self):
        return [{"code": "ACME"}, {"code": "ACE"}, {"code": "BOB"}]


@pytest.fixture
def fake_db(monkeypatch):
    @contextlib.contextmanager
    def cursor(conn, *args, **kwargs):
        yield _FakeCursor()

    monkeypatch.setattr(db, "cursor", cursor)


def test_completer_returns_matches_for_prefix(fake_db):
    c = ic.inputcompleter(object(), None, "customer", "code")
    assert c.completer("A", 0) == "ACME"
    assert c.completer("A", 1) == "ACE"
    assert c.completer("A", 2) is None


def test_completer_does_not_raise_import_error(fake_db):
    c = ic.inputcompleter(object(), None, "customer", "code")
    c.completer("B", 0)  # would raise ImportError before the fix
