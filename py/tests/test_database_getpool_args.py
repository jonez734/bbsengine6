"""
test_database_getpool_args.py

Regression test: ensure ``bbsengine6.database.getpool`` honors
``args.databasename`` even if a caller passes an args namespace whose
databasename differs from the env-var default (``BBSENGINE6_DBNAME``).

Before the fix in ``getpool``, the DSN was built by ``make_dsn(args)``
which read ``getattr(args, "databasename", None)`` directly. That path
was correct, but a future refactor that forgot to read the attribute
would silently fall back to a stale or default dbname. The fix makes
the args.databasename -> dbname mapping explicit in ``getpool`` itself,
so the contract is robust against such refactors.
"""

import argparse

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _isolate_default(monkeypatch):
    """Pin ``make_dsn``'s last-resort fallback to a fixed sentinel so
    this test file does not depend on environment, JSON files, or
    the literal default constants.

    Intercepts only tier 5 (the hardcoded last-resort defaults).
    Tiers 1-4 (kwargs, args attr, env var, ``config["global"]``)
    flow through the original :func:`bbsengine6.database._resolve_db_settings`
    unimpeded.
    """
    from bbsengine6 import database

    monkeypatch.setattr(database, "BBSENGINE6_DBNAME_DEFAULT", "SENTINEL_DB")
    monkeypatch.setattr(database, "BBSENGINE6_DBHOST_DEFAULT", "SENTINEL_HOST")
    monkeypatch.setattr(database, "BBSENGINE6_DBPORT_DEFAULT", 6543)


class _FakePool:
    """Minimal stand-in for psycopg_pool.ConnectionPool that captures
    the DSN string it was constructed with so tests can assert against
    it without opening a real PostgreSQL connection."""

    instances = []

    def __init__(self, conninfo, **kwargs):
        self.conninfo = conninfo
        self.kwargs = kwargs
        self.closed = False
        _FakePool.instances.append(self)

    def close(self):
        self.closed = True


def _make_args(databasename="zoid6", host="localhost", port=5432, user=None, password=None):
    return argparse.Namespace(
        databasename=databasename,
        databasehost=host,
        databaseport=port,
        databaseuser=user,
        databasepassword=password,
        debug=False,
    )


@pytest.fixture(autouse=True)
def _reset_pool_cache(monkeypatch):
    """Wipe the global pool cache and install a fake pool class so no
    real DB connection is attempted."""
    from bbsengine6 import database

    database.reset_pool_cache()
    _FakePool.instances = []
    monkeypatch.setattr(database, "ConnectionPool", _FakePool)
    yield
    database.reset_pool_cache()
    _FakePool.instances = []


def test_getpool_uses_args_databasename():
    """The default path: only args is supplied; getpool must use
    args.databasename verbatim in the DSN."""
    from bbsengine6 import database

    args = _make_args(databasename="zoid6")
    pool = database.getpool(args)

    assert pool is _FakePool.instances[-1]
    assert "dbname=zoid6" in pool.conninfo
    assert "host=localhost" in pool.conninfo
    assert "port=5432" in pool.conninfo
    assert "bbsengine6" not in pool.conninfo


def test_getpool_does_not_pick_up_env_default(monkeypatch):
    """If BBSENGINE6_DBNAME=bbsengine6 is set in the env and the user
    passes --database zoid6, the DSN must contain zoid6, not bbsengine6."""
    from bbsengine6 import database

    monkeypatch.setenv("BBSENGINE6_DBNAME", "bbsengine6")
    args = _make_args(databasename="zoid6")
    pool = database.getpool(args)

    assert "dbname=zoid6" in pool.conninfo
    assert "bbsengine6" not in pool.conninfo


def test_getpool_kwarg_dbname_overrides_args(monkeypatch):
    """Explicit ``database=`` kwarg wins over args.databasename
    (backward-compat behavior preserved)."""
    from bbsengine6 import database

    args = _make_args(databasename="zoid6")
    pool = database.getpool(args, database="override_db")

    assert "dbname=override_db" in pool.conninfo


def test_getpool_kwargs_fall_back_to_args_when_no_dbname(monkeypatch):
    """With no explicit dbname kwarg but other kwargs supplied, the
    args.databasename must still be picked up."""
    from bbsengine6 import database

    args = _make_args(databasename="zoid6")
    pool = database.getpool(args, host="db.example.com", port=5433)

    assert "dbname=zoid6" in pool.conninfo
    assert "host=db.example.com" in pool.conninfo
    assert "port=5433" in pool.conninfo


def test_getpool_cache_keyed_by_dsn(monkeypatch):
    """Two different args.databasename values must produce two distinct
    pools, not collide in the cache."""
    from bbsengine6 import database

    p1 = database.getpool(_make_args(databasename="zoid6"))
    p2 = database.getpool(_make_args(databasename="other_db"))

    assert p1 is not p2
    assert "dbname=zoid6" in p1.conninfo
    assert "dbname=other_db" in p2.conninfo


def test_getpool_repeated_call_returns_cached(monkeypatch):
    """Same args twice returns the same pool object (cache hit)."""
    from bbsengine6 import database

    args = _make_args(databasename="zoid6")
    p1 = database.getpool(args)
    p2 = database.getpool(args)
    assert p1 is p2


class _EmptyArgs:
    """Namespace-like object with no database* attributes at all,
    simulating a caller that never ran database.buildargs."""


def test_make_dsn_uses_env_fallback_when_args_has_no_db_attrs(monkeypatch):
    """If args is a Namespace with no database* attributes, make_dsn
    must still produce a DSN using env-var defaults (BBSENGINE6_DB*).
    Without this, psycopg falls back to libpq defaults: unix socket and
    PGDATABASE — silently connecting to the wrong database."""
    from bbsengine6 import database

    monkeypatch.delenv("BBSENGINE6_DBNAME", raising=False)
    monkeypatch.delenv("BBSENGINE6_DBHOST", raising=False)
    monkeypatch.delenv("BBSENGINE6_DBPORT", raising=False)

    args = _EmptyArgs()
    dsn = database.make_dsn(args)

    assert "dbname=SENTINEL_DB" in dsn
    assert "host=SENTINEL_HOST" in dsn
    assert "port=6543" in dsn
    # Critically: must NOT rely on libpq's silent unix-socket fallback
    assert "host=" in dsn
    assert "dbname=" in dsn


def test_make_dsn_env_var_overrides_missing_attr(monkeypatch):
    """When args has no databasename attr and BBSENGINE6_DBNAME is set,
    the env var must be used."""
    from bbsengine6 import database

    monkeypatch.setenv("BBSENGINE6_DBNAME", "from_env_db")
    monkeypatch.setenv("BBSENGINE6_DBHOST", "envhost.example.com")
    monkeypatch.setenv("BBSENGINE6_DBPORT", "6543")

    args = _EmptyArgs()
    dsn = database.make_dsn(args)

    assert "dbname=from_env_db" in dsn
    assert "host=envhost.example.com" in dsn
    assert "port=6543" in dsn


def test_make_dsn_args_attr_takes_precedence_over_env(monkeypatch):
    """When args has databasename AND env var is set, args wins."""
    from bbsengine6 import database

    monkeypatch.setenv("BBSENGINE6_DBNAME", "from_env_should_lose")
    args = _make_args(databasename="zoid6")
    dsn = database.make_dsn(args)

    assert "dbname=zoid6" in dsn
    assert "from_env_should_lose" not in dsn


def test_getpool_uses_env_fallback_when_args_databasename_missing(monkeypatch):
    """getpool must produce a valid DSN even when args has no
    databasename attribute (caller skipped database.buildargs)."""
    from bbsengine6 import database

    monkeypatch.delenv("BBSENGINE6_DBNAME", raising=False)
    args = _EmptyArgs()
    pool = database.getpool(args)

    assert "dbname=SENTINEL_DB" in pool.conninfo
    assert "host=SENTINEL_HOST" in pool.conninfo
    assert "port=6543" in pool.conninfo


def test_make_dsn_does_not_silently_use_unix_socket(monkeypatch):
    """Regression: before the env-var fallback, make_dsn returned
    'port=5432' only (no host=, no dbname=) when args lacked the
    database* attributes, which made psycopg fall back to the unix
    socket at /var/run/postgresql/.s.PGSQL.5432 with PGDATABASE from
    the user's shell. The DSN must always specify host and dbname
    explicitly so behavior is independent of the surrounding shell."""
    from bbsengine6 import database

    monkeypatch.delenv("BBSENGINE6_DBNAME", raising=False)
    monkeypatch.delenv("BBSENGINE6_DBHOST", raising=False)
    monkeypatch.delenv("BBSENGINE6_DBPORT", raising=False)

    args = _EmptyArgs()
    dsn = database.make_dsn(args)

    # Both keys must be present and non-empty
    assert "dbname=SENTINEL_DB" in dsn
    assert "host=SENTINEL_HOST" in dsn
    # And the unix-socket-specific libpq default must NOT be what
    # makes the DSN "work" — we must always supply our own values.
    assert "/var/run/postgresql" not in dsn
