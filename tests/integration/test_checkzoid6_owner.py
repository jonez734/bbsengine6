"""
Tests for stage_zero / checkzoid6owner integration.

These tests pin the migration step that reassigns ownership of the
five ``public.*`` SECURITY DEFINER helpers to the dedicated ``zoid6``
role (see ``backend.checkzoid6owner`` and ``backend.checkzoid6role``):

  1. ``init`` returns True, ``buildargs`` returns None, ``access``
     returns True (the four-call contract).
  2. The helpers list exactly matches the loop in ``backend.checkengine``.
  3. ``main`` skips a helper that is not yet installed (no ALTER issued).
  4. ``main`` is a no-op when the helper's owner is already ``zoid6``
     (no ALTER issued).
  5. ``main`` issues ``ALTER FUNCTION public.<fn>(<args>) OWNER TO zoid6``
     when the current owner differs.
  6. ``main`` returns False and increments failcount if the ALTER raises.
  7. ``main`` returns True iff every helper is either already-zoid6 or
     successfully reassigned (or skipped as not installed).
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py/src"))


def _make_args():
    args = Mock()
    args.debug = False
    args.databasename = "zoid6"
    return args


def _fake_cursor_context(fetchone_value):
    """Build a mock that quacks like the ``database.cursor`` context
    manager: ``__enter__`` yields a mock cursor whose ``.fetchone()``
    returns ``fetchone_value``, and ``__exit__`` is a no-op.
    """
    cur = Mock()
    cur.fetchone.return_value = fetchone_value
    cur.execute = Mock()  # captured per-test
    cm = Mock()
    cm.__enter__ = Mock(return_value=cur)
    cm.__exit__ = Mock(return_value=False)
    return cm, cur


class TestCheckZoid6OwnerContract(unittest.TestCase):
    def setUp(self):
        from bbsengine6.backend import checkzoid6owner

        self.mod = checkzoid6owner

    def test_init_returns_true(self):
        self.assertTrue(self.mod.init(_make_args()))

    def test_buildargs_returns_none(self):
        self.assertIsNone(self.mod.buildargs(_make_args()))

    def test_access_returns_true(self):
        self.assertTrue(self.mod.access(_make_args(), op="main"))

    def test_target_role_constant(self):
        self.assertEqual(self.mod.TARGET_ROLE, "zoid6")

    def test_helpers_match_checkengine_list(self):
        """Adding/removing a helper here must also be reflected in
        backend.checkengine's verify loop. Pin the two lists in
        lock-step to surface a drift as a test failure rather than a
        silent privilege-escalation hole."""
        from bbsengine6.backend import checkengine

        src = open(checkengine.__file__).read()
        expected = {
            "public.manage_schema_priv",
            "public.manage_database_priv",
            "public.manage_role_privs",
            "public.manage_secondary_role",
            "public.get_role_privs",
        }
        for name in expected:
            self.assertIn(name, src, f"checkengine.py missing {name!r}")
        self.assertEqual(set(self.mod.HELPERS), {
            "manage_schema_priv",
            "manage_database_priv",
            "manage_role_privs",
            "manage_secondary_role",
            "get_role_privs",
        })


class TestCheckZoid6OwnerMissing(unittest.TestCase):
    """Helpers not yet installed → no ALTER, no error."""

    def setUp(self):
        from bbsengine6.backend import checkzoid6owner

        self.mod = checkzoid6owner
        self.args = _make_args()
        self.fake_conn = Mock()

    def test_missing_helper_is_skipped(self):
        with patch.object(
            self.mod,
            "_qualified_owner",
            return_value=None,
        ) as qo, \
             patch.object(self.mod.database, "cursor") as cursor:
            result = self.mod.main(self.args, conn=self.fake_conn)

        self.assertTrue(result)
        # One lookup per helper, all return None, no ALTER.
        self.assertEqual(qo.call_count, len(self.mod.HELPERS))
        cursor.assert_not_called()


class TestCheckZoid6OwnerAlreadyZoid6(unittest.TestCase):
    """Helpers already owned by zoid6 → no-op, no ALTER."""

    def setUp(self):
        from bbsengine6.backend import checkzoid6owner

        self.mod = checkzoid6owner
        self.args = _make_args()
        self.fake_conn = Mock()

    def test_noop_when_owner_is_already_zoid6(self):
        def fake_lookup(_args, name, _conn):
            return ("public", name, "args text", "zoid6")

        with patch.object(
            self.mod, "_qualified_owner", side_effect=fake_lookup
        ) as qo, \
             patch.object(self.mod.database, "cursor") as cursor:
            result = self.mod.main(self.args, conn=self.fake_conn)

        self.assertTrue(result)
        qo.assert_called()
        cursor.assert_not_called()  # No ALTER issued


class TestCheckZoid6OwnerReassign(unittest.TestCase):
    """Helpers owned by someone else → ALTER FUNCTION ... OWNER TO zoid6."""

    def setUp(self):
        from bbsengine6.backend import checkzoid6owner

        self.mod = checkzoid6owner
        self.args = _make_args()
        self.fake_conn = Mock()

    def test_alters_owner_when_legacy_owner(self):
        # Pretend the helpers exist and are owned by `opencode`
        # (mirrors the actual on-disk state from the dev DB bug).
        def fake_lookup(_args, name, _conn):
            return ("public", name, "args text", "opencode")

        cm, cur = _fake_cursor_context(fetchone_value=None)

        with patch.object(
            self.mod, "_qualified_owner", side_effect=fake_lookup
        ), \
             patch.object(self.mod.database, "cursor", return_value=cm) as cursor, \
             patch.object(self.mod.lib, "hr") as fake_hr:
            result = self.mod.main(self.args, conn=self.fake_conn)

        self.assertTrue(result)
        # One ALTER per helper, all targeting zoid6.
        self.assertEqual(cur.execute.call_count, len(self.mod.HELPERS))
        for c in cur.execute.call_args_list:
            sql_text = c.args[0]
            self.assertIn("ALTER FUNCTION public.", sql_text)
            self.assertIn("OWNER TO zoid6", sql_text)
        cursor.assert_called()
        fake_hr.assert_called_once_with(0)

    def test_alters_owner_for_postgres_owner(self):
        """`postgres` (the previous canonical owner) is also re-routed
        to `zoid6` automatically. The allow-list still accepts
        `postgres` for one release, but the canonical owner is
        `zoid6`, so the bootstrap migrates on first run."""
        def fake_lookup(_args, name, _conn):
            return ("public", name, "args text", "postgres")

        cm, _cur = _fake_cursor_context(fetchone_value=None)

        with patch.object(
            self.mod, "_qualified_owner", side_effect=fake_lookup
        ), \
             patch.object(self.mod.database, "cursor", return_value=cm):
            result = self.mod.main(self.args, conn=self.fake_conn)

        self.assertTrue(result)

    def test_alter_failure_increments_failcount(self):
        """If one ALTER raises, failcount goes up and main returns False."""
        def fake_lookup(_args, name, _conn):
            return ("public", name, "args text", "opencode")

        cur = Mock()
        cur.execute.side_effect = RuntimeError("simulated DDL failure")
        cm = Mock()
        cm.__enter__ = Mock(return_value=cur)
        cm.__exit__ = Mock(return_value=False)

        with patch.object(
            self.mod, "_qualified_owner", side_effect=fake_lookup
        ), \
             patch.object(self.mod.database, "cursor", return_value=cm), \
             patch.object(self.mod.lib, "hr") as fake_hr:
            result = self.mod.main(self.args, conn=self.fake_conn)

        self.assertFalse(result)
        fake_hr.assert_called_once_with(len(self.mod.HELPERS))


class TestQualifiedOwner(unittest.TestCase):
    """The lookup helper that powers the main loop."""

    def setUp(self):
        from bbsengine6.backend import checkzoid6owner

        self.mod = checkzoid6owner

    def test_returns_none_for_missing_function(self):
        cm, _ = _fake_cursor_context(fetchone_value=None)
        with patch.object(self.mod.database, "cursor", return_value=cm):
            self.assertIsNone(
                self.mod._qualified_owner(Mock(), "missing_fn", Mock())
            )

    def test_returns_tuple_for_existing_function(self):
        row = {"args": "action text, priv text", "owner": "zoid6"}
        cm, _ = _fake_cursor_context(fetchone_value=row)
        with patch.object(self.mod.database, "cursor", return_value=cm):
            result = self.mod._qualified_owner(Mock(), "manage_schema_priv", Mock())
        self.assertEqual(result, ("public", "manage_schema_priv", "action text, priv text", "zoid6"))

    def test_handles_tuple_row_form(self):
        """``fetchone`` may return a tuple instead of a dict depending
        on cursor configuration. The helper must handle both."""
        row = ("action text, priv text", "postgres")
        cm, _ = _fake_cursor_context(fetchone_value=row)
        with patch.object(self.mod.database, "cursor", return_value=cm):
            result = self.mod._qualified_owner(Mock(), "manage_schema_priv", Mock())
        self.assertEqual(result, ("public", "manage_schema_priv", "action text, priv text", "postgres"))


if __name__ == "__main__":
    unittest.main()
