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
            "checkflag",
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
        If the schema already exists, checkengine must not call
        createschema (which would raise DuplicateSchema on a re-run).
        """
        args = _make_args()
        fake_conn = Mock()
        fake_pool = Mock()

        with patch.object(self.checkengine.database, "schemaexists", return_value=True) as schemaexists, \
             patch.object(self.checkengine.database, "createschema") as createschema, \
             patch.object(self.checkengine.database, "manage_schema_priv", return_value=True):
            result = self.checkengine.main(args, conn=fake_conn, pool=fake_pool)

        self.assertTrue(result)
        schemaexists.assert_called_once()
        createschema.assert_not_called()

    def test_main_creates_schema_when_missing(self):
        """
        If the schema is missing, checkengine must call createschema
        using the caller-provided conn/pool.
        """
        args = _make_args()
        fake_conn = Mock()
        fake_pool = Mock()

        with patch.object(self.checkengine.database, "schemaexists", return_value=False), \
             patch.object(self.checkengine.database, "createschema", return_value=True) as createschema, \
             patch.object(self.checkengine.database, "manage_schema_priv", return_value=True):
            result = self.checkengine.main(args, conn=fake_conn, pool=fake_pool)

        self.assertTrue(result)
        createschema.assert_called_once()
        # The connection/pool from the stage 1 loop must be propagated,
        # so the schema is created in the target DB (e.g. zoid6), not
        # re-derived from args and pointing back at the admin DB.
        _, kwargs = createschema.call_args
        self.assertIn("conn", kwargs)
        self.assertIs(kwargs["conn"], fake_conn)
        self.assertIn("pool", kwargs)
        self.assertIs(kwargs["pool"], fake_pool)
        # And the schema name must be the one we depend on elsewhere.
        args_list, _ = createschema.call_args
        self.assertEqual(args_list[1], "engine")

    def test_main_returns_false_when_createschema_fails(self):
        """
        If createschema fails, checkengine must return False so the
        stage 1 loop breaks and the transaction rolls back.
        """
        args = _make_args()
        fake_conn = Mock()
        fake_pool = Mock()

        with patch.object(self.checkengine.database, "schemaexists", return_value=False), \
             patch.object(self.checkengine.database, "createschema", return_value=False), \
             patch.object(self.checkengine, "lib") as fake_lib:
            fake_lib.fail = Mock()
            fake_lib.ok = Mock()
            result = self.checkengine.main(args, conn=fake_conn, pool=fake_pool)

        self.assertFalse(result)
        fake_lib.fail.assert_called_once()


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
