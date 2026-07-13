"""
Tests for public.manage_schema_priv — the SECURITY DEFINER helper used by
the engine to grant/revoke schema-level privileges.

The checkengine refuses to call this function unless it is owned by
``postgres`` (see ``database.verify_function_owner``). These tests pin:

  * the function is installed in ``public`` with the right signature;
  * it is owned by ``postgres``;
  * it is marked ``SECURITY DEFINER`` (so it executes as the owner, not
    the caller);
  * ``sysop`` has been granted ``EXECUTE`` on it;
  * ``verify_function_owner`` accepts the install;
  * ``manage_schema_priv('grant', 'USAGE', schema, role)`` actually grants
    the privilege to a role, and the symmetric ``revoke`` removes it;
  * an unknown ``action`` raises an exception;
  * the Python wrapper ``database.manage_schema_priv`` works end-to-end
    against the live database.
"""

from __future__ import annotations

import argparse
import getpass
import os

import psycopg
import pytest

from bbsengine6 import database


FUNCTION_NAME = "manage_schema_priv"
QUALIFIED_NAME = f"public.{FUNCTION_NAME}"
EXPECTED_ARGS = "action text, priv text, target_schema text, target_role text"
EXPECTED_OWNER = "postgres"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def test_args():
    """Lightweight args namespace for tests that don't need the full conftest."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    defaults = {
        "databasename": os.environ.get("BBSENGINE6_DBNAME", "zoid6test"),
        "databasehost": os.environ.get("BBSENGINE6_DBHOST", "localhost"),
        "databaseport": int(os.environ.get("BBSENGINE6_DBPORT", "5432")),
        "databaseuser": os.environ.get("BBSENGINE6_DBUSER", getpass.getuser()),
        "databasepassword": os.environ.get("BBSENGINE6_DBPASSWORD"),
    }
    database.buildargdatabasegroup(parser, defaults)
    return parser.parse_args([])


@pytest.fixture
def isolated_schema_and_role(db_connection):
    """Create a throwaway schema for the duration of one test.

    The autouse ``test_transaction`` fixture in conftest.py wraps every
    test in a transaction that is rolled back at the end, so the
    CREATE SCHEMA here is undone automatically. The fixture targets a
    pre-existing nologin role (``term``) instead of creating a new
    role, so the test does not require ``CREATEROLE`` on the test user.
    The role's privileges on the throwaway schema are likewise rolled
    back, so subsequent tests are unaffected.
    """
    schema = "test_manage_schema_priv"
    role = "term"  # pre-existing nologin role in the test database

    with db_connection.cursor() as cur:
        cur.execute(f'CREATE SCHEMA "{schema}"')
    db_connection.commit()

    yield schema, role

    # The conftest's autouse fixture rolls back, so this is belt-and-
    # braces for safety.
    try:
        with db_connection.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        db_connection.commit()
    except Exception:
        db_connection.rollback()


# ---------------------------------------------------------------------------
# Install / signature / owner / security / execute-grant
# ---------------------------------------------------------------------------


def _row_owner(conn) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT r.rolname AS owner "
            "FROM pg_proc p "
            "JOIN pg_namespace n ON p.pronamespace = n.oid "
            "JOIN pg_roles r ON p.proowner = r.oid "
            "WHERE p.proname = %s AND n.nspname = 'public'",
            (FUNCTION_NAME,),
        )
        row = cur.fetchone()
    assert row is not None, f"{QUALIFIED_NAME} is not installed"
    return row["owner"] if isinstance(row, dict) else row[0]


class TestInstall:
    """Pin the on-disk shape of the function. A regression here is what
    originally caused the verify_function_owner.200 abort in stage_zero."""

    def test_function_exists(self, db_connection):
        with db_connection.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_proc p "
                "JOIN pg_namespace n ON p.pronamespace = n.oid "
                "WHERE p.proname = %s AND n.nspname = 'public'",
                (FUNCTION_NAME,),
            )
            assert cur.fetchone() is not None, (
                f"{QUALIFIED_NAME} is not installed in the public schema"
            )

    def test_signature_matches(self, db_connection):
        with db_connection.cursor() as cur:
            cur.execute(
                "SELECT pg_get_function_identity_arguments(p.oid) AS args "
                "FROM pg_proc p "
                "JOIN pg_namespace n ON p.pronamespace = n.oid "
                "WHERE p.proname = %s AND n.nspname = 'public'",
                (FUNCTION_NAME,),
            )
            row = cur.fetchone()
        assert row is not None
        args = row["args"] if isinstance(row, dict) else row[0]
        assert args == EXPECTED_ARGS, (
            f"signature changed: got {args!r}, expected {EXPECTED_ARGS!r}"
        )

    def test_owner_is_postgres(self, db_connection):
        assert _row_owner(db_connection) == EXPECTED_OWNER, (
            f"{QUALIFIED_NAME} must be owned by {EXPECTED_OWNER!r} for "
            f"checkengine's verify_function_owner gate to pass"
        )

    def test_is_security_definer(self, db_connection):
        with db_connection.cursor() as cur:
            cur.execute(
                "SELECT p.prosecdef AS is_secdef "
                "FROM pg_proc p "
                "JOIN pg_namespace n ON p.pronamespace = n.oid "
                "WHERE p.proname = %s AND n.nspname = 'public'",
                (FUNCTION_NAME,),
            )
            row = cur.fetchone()
        assert row is not None
        is_secdef = row["is_secdef"] if isinstance(row, dict) else row[0]
        assert is_secdef is True, (
            f"{QUALIFIED_NAME} must be SECURITY DEFINER so that the "
            f"engine can grant/revoke as the function owner"
        )

    def test_sysop_has_execute(self, db_connection):
        # has_function_privilege takes a regprocedure, which is finicky
        # to construct from a string in SQL (it requires a fully-typed
        # signature). Look up the function's oid in pg_proc and use
        # that — works regardless of signature, no string escaping.
        with db_connection.cursor() as cur:
            cur.execute(
                "SELECT has_function_privilege("
                "  'sysop',"
                "  ("
                "    SELECT p.oid"
                "    FROM pg_proc p"
                "    JOIN pg_namespace n ON p.pronamespace = n.oid"
                "    WHERE p.proname = %s AND n.nspname = 'public'"
                "  ),"
                "  'EXECUTE'"
                ")",
                (FUNCTION_NAME,),
            )
            row = cur.fetchone()
        assert row is not None
        has_exec = row[0] if isinstance(row, tuple) else list(row.values())[0]
        assert has_exec is True, (
            "the engine's sysop role must have EXECUTE on "
            f"{QUALIFIED_NAME} (the SQL file grants it explicitly)"
        )

    def test_verify_function_owner_accepts(self, test_args, db_connection):
        """The checkengine gate must accept the install as-is."""
        result = database.verify_function_owner(
            test_args, QUALIFIED_NAME, ("postgres",), conn=db_connection
        )
        assert result is True


# ---------------------------------------------------------------------------
# Behaviour: grant / revoke / invalid action
# ---------------------------------------------------------------------------


def _has_schema_priv(conn, role: str, schema: str, priv: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT has_schema_privilege(%s, %s, %s)",
            (role, schema, priv),
        )
        row = cur.fetchone()
    return bool(row[0]) if row else False


class TestBehavior:
    """Exercise the function via direct SQL — the path the engine itself
    takes (``database.manage_schema_priv`` just calls
    ``SELECT manage_schema_priv(...)``)."""

    def test_grant_usage_round_trip(
        self, db_connection, isolated_schema_and_role
    ):
        schema, role = isolated_schema_and_role
        # Sanity: the freshly-created role does not have USAGE yet.
        assert _has_schema_priv(db_connection, role, schema, "USAGE") is False

        with db_connection.cursor() as cur:
            cur.execute(
                "SELECT manage_schema_priv('grant', 'USAGE', %s, %s)",
                (schema, role),
            )
        assert _has_schema_priv(db_connection, role, schema, "USAGE") is True

    def test_revoke_removes_priv(
        self, db_connection, isolated_schema_and_role
    ):
        schema, role = isolated_schema_and_role

        with db_connection.cursor() as cur:
            cur.execute(
                "SELECT manage_schema_priv('grant', 'USAGE', %s, %s)",
                (schema, role),
            )
        assert _has_schema_priv(db_connection, role, schema, "USAGE") is True

        with db_connection.cursor() as cur:
            cur.execute(
                "SELECT manage_schema_priv('revoke', 'USAGE', %s, %s)",
                (schema, role),
            )
        assert _has_schema_priv(db_connection, role, schema, "USAGE") is False

    def test_action_is_case_insensitive(
        self, db_connection, isolated_schema_and_role
    ):
        schema, role = isolated_schema_and_role
        with db_connection.cursor() as cur:
            cur.execute(
                "SELECT manage_schema_priv('GRANT', 'USAGE', %s, %s)",
                (schema, role),
            )
        assert _has_schema_priv(db_connection, role, schema, "USAGE") is True

    def test_invalid_action_raises(
        self, db_connection, isolated_schema_and_role
    ):
        schema, role = isolated_schema_and_role
        with db_connection.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute(
                    "SELECT manage_schema_priv('frobnicate', 'USAGE', %s, %s)",
                    (schema, role),
                )
        db_connection.rollback()


# ---------------------------------------------------------------------------
# Python wrapper
# ---------------------------------------------------------------------------


class TestPythonWrapper:
    """End-to-end through ``database.manage_schema_priv`` (the helper the
    engine modules actually call)."""

    def test_wrapper_grants_and_revokes(
        self, test_args, db_connection, isolated_schema_and_role
    ):
        schema, role = isolated_schema_and_role

        # Grant via the Python wrapper.
        assert (
            database.manage_schema_priv(
                test_args, "grant", "USAGE", schema, role, conn=db_connection
            )
            is True
        )
        assert _has_schema_priv(db_connection, role, schema, "USAGE") is True

        # Revoke via the Python wrapper.
        assert (
            database.manage_schema_priv(
                test_args, "revoke", "USAGE", schema, role, conn=db_connection
            )
            is True
        )
        assert _has_schema_priv(db_connection, role, schema, "USAGE") is False
