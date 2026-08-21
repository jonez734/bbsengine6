"""
Tests for stage_one / checkengine integration.

These tests guard the fix for the `schema "engine" does not exist` error
in stage 1 of the bbsengine6 backend bootstrap:

  - stage 0 creates schema `engine` in the admin DB (postgres)
  - stage 1 must also ensure schema `engine` exists in the target DB (e.g. zoid6)
    before checkfunctions/importsql run.

The fix added `checkengine` to the stage 1 module loop. The tests below
assert:

  1. `checkengine` is in the stage 1 module loop.
  2. `checkengine` runs before `checkfunctions` (ordering matters).
  3. `checkengine.main` is idempotent: it checks `schemaexists` first
     and only calls `createschema` when the schema is missing.
  4. `checkengine.main` uses the caller-provided `conn` (it does not
     open its own connection to a different database).
  5. `checkengine.main` fails fast (returns False) if `createschema`
     fails, so the stage 1 loop breaks and rolls back.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add project source to path (matches existing test layout)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py/src"))


def _make_args():
    """Minimal argparse.Namespace stand-in for backend stage tests."""
    args = Mock()
    args.debug = False
    args.databasename = "zoid6"
    return args


def _fake_cursor_context(fetchone_value=None, current_owner="zoid6"):
    """Build a mock that quacks like the ``database.cursor`` context
    manager used by checkengine's schema bootstrap path.

    ``checkengine`` now issues ``CREATE SCHEMA ... AUTHORIZATION zoid6``
    (or ``ALTER SCHEMA ... OWNER TO zoid6``) directly via a cursor
    rather than going through ``database.createschema``, so the tests
    mock the cursor instead. ``fetchone_value`` is the dict/tuple the
    SELECT-pg_get_userbyid call returns; ``current_owner`` is shorthand
    for the common case where ``fetchone_value`` is not provided.
    """
    if fetchone_value is None:
        fetchone_value = {"owner": current_owner}
    cur = Mock()
    cur.fetchone.return_value = fetchone_value
    cur.execute = Mock()
    cm = Mock()
    cm.__enter__ = Mock(return_value=cur)
    cm.__exit__ = Mock(return_value=False)
    return cm, cur


class TestStageOneModuleLoop(unittest.TestCase):
    """The stage 1 module loop must include checkengine, ordered correctly."""

    def setUp(self):
        from bbsengine6.backend import stage_one

        self.stage_one = stage_one

    def _extract_module_names(self, source: str):
        """
        Pull the tuple of module names out of stage_one.main's source.
        Robust to whitespace/line-wrapping.
        """
        import ast

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                for sub in ast.walk(node):
                    if isinstance(sub, ast.For):
                        try:
                            inner = sub.iter.elts  # Tuple of string constants
                        except AttributeError:
                            continue
                        names = []
                        for elt in inner:
                            if isinstance(elt, ast.Constant) and isinstance(
                                elt.value, str
                            ):
                                names.append(elt.value)
                        return names
        return []

    def test_checkengine_in_module_loop(self):
        """checkengine must appear in the stage 1 module loop."""
        import inspect

        source = inspect.getsource(self.stage_one.main)
        names = self._extract_module_names(source)
        self.assertIn(
            "checkengine",
            names,
            "stage_one.main must call 'checkengine' so the engine "
            "schema is created in the target DB (not just the admin DB).",
        )

    def test_checkengine_runs_before_checkfunctions(self):
        """
        checkengine must run BEFORE checkfunctions. Otherwise the
        importsql / function lookups in checkfunctions hit
        `schema "engine" does not exist` again.
        """
        import inspect

        source = inspect.getsource(self.stage_one.main)
        names = self._extract_module_names(source)
        self.assertIn("checkengine", names)
        self.assertIn("checkfunctions", names)
        self.assertLess(
            names.index("checkengine"),
            names.index("checkfunctions"),
            "checkengine must run before checkfunctions in stage_one.main",
        )

    def test_module_loop_still_runs_known_modules(self):
        """The existing stage 1 modules must still be present."""
        import inspect

        source = inspect.getsource(self.stage_one.main)
        names = self._extract_module_names(source)
        for required in (
            "checkextensions",
            "checkengine",
            "checkfunctions",
            "checkclasses",
            "checkmemberflag",
            "bank",
        ):
            self.assertIn(required, names)


class TestCheckEngineIdempotency(unittest.TestCase):
    """
    checkengine.main must not blindly re-create the schema on every run,
    and must use the connection the stage 1 loop hands it.
    """

    def setUp(self):
        from bbsengine6.backend import checkengine

        self.checkengine = checkengine

    def test_main_skips_createschema_when_schema_exists(self):
        """
        If the schema already exists AND is owned by ``zoid6``, checkengine
        must not issue any DDL. (The previous mock pattern asserted that
        ``createschema`` was not called; the new schema bootstrap issues
        the DDL directly via a cursor with ``AUTHORIZATION zoid6``, so we
        instead assert no CREATE/ALTER was issued.)
        """
        args = _make_args()
        fake_conn = Mock()
        fake_pool = Mock()
        cm, cur = _fake_cursor_context(current_owner="zoid6")

        with patch.object(self.checkengine.database, "functionexists", return_value=True) as functionexists, \
             patch.object(self.checkengine.database, "importsql") as importsql, \
             patch.object(self.checkengine.database, "schemaexists", return_value=True) as schemaexists, \
             patch.object(self.checkengine.database, "cursor", return_value=cm), \
             patch.object(self.checkengine.database, "manage_schema_priv", return_value=True), \
             patch.object(self.checkengine.database, "classexists", return_value=True), \
             patch.object(self.checkengine.database, "verify_function_owner", return_value=True):
            result = self.checkengine.main(args, conn=fake_conn, pool=fake_pool)

        self.assertTrue(result)
        schemaexists.assert_called_once()
        # No CREATE SCHEMA, no ALTER SCHEMA — owner already zoid6.
        execute_calls = [c.args[0] for c in cur.execute.call_args_list]
        self.assertNotIn(
            "CREATE SCHEMA engine AUTHORIZATION zoid6", execute_calls,
        )
        self.assertNotIn(
            "ALTER SCHEMA engine OWNER TO zoid6", execute_calls,
        )
        # manage_schema_priv helper already present — no importsql call.
        self.assertGreaterEqual(functionexists.call_count, 1)
        first_args, _ = functionexists.call_args_list[0]
        self.assertEqual(first_args[1], "public.manage_schema_priv")
        importsql.assert_not_called()

    def test_main_creates_schema_when_missing(self):
        """
        If the schema is missing, checkengine must issue
        ``CREATE SCHEMA engine AUTHORIZATION zoid6`` against the
        caller-provided conn.
        """
        args = _make_args()
        fake_conn = Mock()
        fake_pool = Mock()
        cm, cur = _fake_cursor_context()

        with patch.object(self.checkengine.database, "functionexists", return_value=True), \
             patch.object(self.checkengine.database, "importsql") as importsql, \
             patch.object(self.checkengine.database, "schemaexists", return_value=False), \
             patch.object(self.checkengine.database, "cursor", return_value=cm) as cursor, \
             patch.object(self.checkengine.database, "manage_schema_priv", return_value=True), \
             patch.object(self.checkengine.database, "classexists", return_value=True), \
             patch.object(self.checkengine.database, "verify_function_owner", return_value=True):
            result = self.checkengine.main(args, conn=fake_conn, pool=fake_pool)

        self.assertTrue(result)
        # The CREATE SCHEMA statement must be issued against the
        # caller-provided conn.
        execute_calls = [c.args[0] for c in cur.execute.call_args_list]
        self.assertIn(
            "CREATE SCHEMA engine AUTHORIZATION zoid6", execute_calls,
        )
        # The conn must be propagated, so the schema is created in the
        # target DB (e.g. zoid6), not a different one.
        cursor.assert_called()
        _, kwargs = cursor.call_args
        self.assertIn("conn", kwargs)
        self.assertIs(kwargs["conn"], fake_conn)
        # helper already present — no install attempt.
        importsql.assert_not_called()

    def test_main_returns_false_when_createschema_fails(self):
        """
        If the CREATE SCHEMA statement raises, checkengine must return
        False so the stage 1 loop breaks and the transaction rolls back.
        """
        args = _make_args()
        fake_conn = Mock()
        fake_pool = Mock()

        cur = Mock()
        cur.execute.side_effect = RuntimeError("simulated DDL failure")
        cm = Mock()
        cm.__enter__ = Mock(return_value=cur)
        cm.__exit__ = Mock(return_value=False)

        with patch.object(self.checkengine.database, "functionexists", return_value=True), \
             patch.object(self.checkengine.database, "importsql"), \
             patch.object(self.checkengine.database, "schemaexists", return_value=False), \
             patch.object(self.checkengine.database, "cursor", return_value=cm), \
             patch.object(self.checkengine.database, "classexists", return_value=True), \
             patch.object(self.checkengine.database, "verify_function_owner", return_value=True):
            result = self.checkengine.main(args, conn=fake_conn, pool=fake_pool)

        self.assertFalse(result)

    def test_main_installs_manage_schema_priv_when_missing(self):
        """
        If the public.manage_schema_priv function isn't present in the
        target DB (e.g. running in stage 1 against zoid6, where
        checkfunctions only installs engine.* functions), checkengine
        must install it via importsql('manage_schema_priv.sql', ...)
        before using it. Without this, the grant loop below raises
        `function manage_schema_priv(unknown, unknown, unknown, unknown)
        does not exist`.
        """
        args = _make_args()
        fake_conn = Mock()
        fake_pool = Mock()
        cm, _cur = _fake_cursor_context()

        with patch.object(self.checkengine.database, "functionexists", return_value=False) as functionexists, \
             patch.object(self.checkengine.database, "importsql", return_value=True) as importsql, \
             patch.object(self.checkengine.database, "schemaexists", return_value=True), \
             patch.object(self.checkengine.database, "cursor", return_value=cm), \
             patch.object(self.checkengine.database, "manage_schema_priv", return_value=True) as manage, \
             patch.object(self.checkengine.database, "classexists", return_value=True), \
             patch.object(self.checkengine.database, "verify_function_owner", return_value=True):
            result = self.checkengine.main(args, conn=fake_conn, pool=fake_pool)

        self.assertTrue(result)
        # First call is the helper-install check; subsequent calls are
        # the SECDEF owner-verification loop in checkengine.main.
        self.assertGreaterEqual(functionexists.call_count, 1)
        first_args, _ = functionexists.call_args_list[0]
        self.assertEqual(first_args[1], "public.manage_schema_priv")
        # importsql must be called at least once with the SQL file
        # that defines the helper, and the caller-supplied conn must
        # be propagated so the helper is installed in the target DB,
        # not a different one.
        install_calls = [
            c for c in importsql.call_args_list
            if c[0][1] == "manage_schema_priv.sql"
        ]
        self.assertEqual(
            len(install_calls), 1,
            f"expected exactly one manage_schema_priv.sql install, "
            f"got {len(install_calls)} in {importsql.call_args_list}",
        )
        install_call = install_calls[0]
        is_args, is_kwargs = install_call
        self.assertIn("conn", is_kwargs)
        self.assertIs(is_kwargs["conn"], fake_conn)
        self.assertIn("pool", is_kwargs)
        self.assertIs(is_kwargs["pool"], fake_pool)
        # And the grant loop must have run after the install.
        manage.assert_called()

    def test_main_returns_false_when_manage_schema_priv_install_fails(self):
        """
        If importsql('manage_schema_priv.sql') fails, checkengine must
        return False without proceeding to the grant loop. This keeps
        the stage loop fail-fast and prevents the misleading
        `function ... does not exist` error from surfacing inside the
        grant loop.
        """
        args = _make_args()
        fake_conn = Mock()
        fake_pool = Mock()

        with patch.object(self.checkengine.database, "functionexists", return_value=False), \
             patch.object(self.checkengine.database, "importsql", return_value=False) as importsql, \
             patch.object(self.checkengine.database, "schemaexists") as schemaexists, \
             patch.object(self.checkengine.database, "cursor"), \
             patch.object(self.checkengine.database, "manage_schema_priv") as manage, \
             patch.object(self.checkengine.database, "classexists", return_value=True), \
             patch.object(self.checkengine.database, "verify_function_owner", return_value=True):
            result = self.checkengine.main(args, conn=fake_conn, pool=fake_pool)

        self.assertFalse(result)
        # importsql was called at least once (for the helper install);
        # what matters is that checkengine did NOT proceed past it.
        install_calls = [
            c for c in importsql.call_args_list
            if c[0][1] == "manage_schema_priv.sql"
        ]
        self.assertEqual(len(install_calls), 1)
        # Must NOT have proceeded to schema creation or grant loop.
        schemaexists.assert_not_called()
        manage.assert_not_called()

    def test_main_reassigns_engine_schema_to_zoid6_when_owner_differs(self):
        """
        BC: if the engine schema already exists and is owned by a
        different role (e.g. jam, opencode), checkengine must issue
        ``ALTER SCHEMA engine OWNER TO zoid6`` so the SECDEF helper
        grants below can succeed. Without this, every grant fails
        with ``permission denied for schema engine`` once ``zoid6``
        owns ``manage_schema_priv``.
        """
        args = _make_args()
        fake_conn = Mock()
        fake_pool = Mock()
        # Pretend the existing engine schema is owned by opencode
        # (mirrors the dev DB state prior to migration).
        cm, cur = _fake_cursor_context(current_owner="opencode")

        with patch.object(self.checkengine.database, "functionexists", return_value=True), \
             patch.object(self.checkengine.database, "importsql"), \
             patch.object(self.checkengine.database, "schemaexists", return_value=True), \
             patch.object(self.checkengine.database, "cursor", return_value=cm), \
             patch.object(self.checkengine.database, "manage_schema_priv", return_value=True), \
             patch.object(self.checkengine.database, "classexists", return_value=True), \
             patch.object(self.checkengine.database, "verify_function_owner", return_value=True):
            result = self.checkengine.main(args, conn=fake_conn, pool=fake_pool)

        self.assertTrue(result)
        execute_calls = [c.args[0] for c in cur.execute.call_args_list]
        self.assertIn(
            "ALTER SCHEMA engine OWNER TO zoid6", execute_calls,
        )


class TestStageOneFailsFastWithoutCheckEngine(unittest.TestCase):
    """
    Regression test: without checkengine in the loop, stage_one's
    importsql path would fail with `schema "engine" does not exist`
    in the target DB. We assert the loop now includes the prerequisite
    module and stops at the first failure.
    """

    def test_loop_includes_checkengine_before_anything_referencing_engine_schema(self):
        import inspect

        from bbsengine6.backend import stage_one

        source = inspect.getsource(stage_one.main)
        self.assertIn('"checkengine"', source)
        # The next module after checkengine must be checkfunctions, the
        # first consumer of the engine.* schema.
        import re

        match = re.search(
            r'"checkengine",\s*\n\s*"([^"]+)"', source
        )
        self.assertIsNotNone(
            match,
            "checkengine must be followed by a next module in the loop",
        )
        self.assertEqual(match.group(1), "checkfunctions")


if __name__ == "__main__":
    unittest.main()
