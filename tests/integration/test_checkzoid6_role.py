"""
Tests for stage_zero / checkzoid6role integration.

These tests pin the dedicated ``zoid6`` owner role used by the
SECURITY DEFINER helpers (see ``backend.checkengine`` and
``backend.checkzoid6owner``):

  1. ``init`` returns True (no-op).
  2. ``buildargs`` returns None (no-op shim).
  3. ``access`` returns True so the dispatcher can route to it.
  4. ``main`` creates the role with the correct attributes when it
     does not exist (NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN INHERIT).
  5. ``main`` is a no-op when the role already exists and has
     NOSUPERUSER.
  6. ``main`` HARD-FAILS when the role already exists but has
     rolsuper=True (a misconfig that would silently break the trust
     model — the verifier would still pass, but the role's purpose
     is to be unprivileged).
  7. ``main`` returns True on success and emits ``lib.hr(0)``;
     returns False on the rolsuper path with ``lib.hr(1)``.
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


class TestCheckZoid6RoleContract(unittest.TestCase):
    """The four-call contract: init / buildargs / access / main."""

    def setUp(self):
        from bbsengine6.backend import checkzoid6role

        self.mod = checkzoid6role

    def test_init_returns_true(self):
        self.assertTrue(self.mod.init(_make_args()))

    def test_buildargs_returns_none(self):
        self.assertIsNone(self.mod.buildargs(_make_args()))

    def test_access_returns_true(self):
        # Public — only the bootstrap superuser reaches this code path
        # in practice, but the dispatcher gate returns True so the
        # module is routable.
        self.assertTrue(self.mod.access(_make_args(), op="main"))

    def test_module_name_constant(self):
        # The role name must match the value used by checkengine's
        # acceptable_owners and by checkzoid6owner.
        self.assertEqual(self.mod.ROLE_NAME, "zoid6")


class TestCheckZoid6RoleCreate(unittest.TestCase):
    """``main`` creates the role with the correct attributes when missing."""

    def setUp(self):
        from bbsengine6.backend import checkzoid6role

        self.mod = checkzoid6role
        self.args = _make_args()
        self.fake_conn = Mock()

    def test_creates_role_when_missing_with_correct_attributes(self):
        with patch.object(self.mod.database, "rolexists", return_value=False) as rolexists, \
             patch.object(self.mod.database, "createrol", return_value=True) as createrol, \
             patch.object(self.mod.database, "get_role_privs") as getprivs:
            result = self.mod.main(self.args, conn=self.fake_conn)

        self.assertTrue(result)
        rolexists.assert_called_once_with(self.args, "zoid6", conn=self.fake_conn)
        createrol.assert_called_once()
        kwargs = createrol.call_args.kwargs
        self.assertEqual(kwargs["superuser"], False)
        self.assertEqual(kwargs["login"], False)
        self.assertEqual(kwargs["createdb"], False)
        self.assertEqual(kwargs["createrole"], False)
        self.assertEqual(kwargs["inherit"], True)
        # If the role didn't exist, get_role_privs must NOT be called
        # (it would be called only on the exists-and-nosuper branch).
        getprivs.assert_not_called()

    def test_creates_role_returns_false_on_createrol_failure(self):
        with patch.object(self.mod.database, "rolexists", return_value=False), \
             patch.object(self.mod.database, "createrol", return_value=False), \
             patch.object(self.mod.lib, "hr") as fake_hr:
            result = self.mod.main(self.args, conn=self.fake_conn)

        self.assertFalse(result)
        fake_hr.assert_called_once_with(1)  # failcount == 1


class TestCheckZoid6RoleExists(unittest.TestCase):
    """``main`` short-circuits when the role already exists and is
    unprivileged."""

    def setUp(self):
        from bbsengine6.backend import checkzoid6role

        self.mod = checkzoid6role
        self.args = _make_args()
        self.fake_conn = Mock()

    def test_noop_when_role_exists_and_is_unprivileged(self):
        with patch.object(self.mod.database, "rolexists", return_value=True) as rolexists, \
             patch.object(self.mod.database, "createrol") as createrol, \
             patch.object(
                 self.mod.database, "get_role_privs",
                 return_value={"rolsuper": False, "rolcanlogin": False},
             ) as getprivs, \
             patch.object(self.mod.lib, "hr") as fake_hr:
            result = self.mod.main(self.args, conn=self.fake_conn)

        self.assertTrue(result)
        rolexists.assert_called_once()
        createrol.assert_not_called()  # role exists → no create
        getprivs.assert_called_once_with(self.args, "zoid6", conn=self.fake_conn)
        fake_hr.assert_called_once_with(0)

    def test_hard_fails_when_role_is_superuser(self):
        """A zoid6 with rolsuper=True would silently break the trust
        model. The module must refuse to continue."""
        with patch.object(self.mod.database, "rolexists", return_value=True), \
             patch.object(self.mod.database, "createrol") as createrol, \
             patch.object(
                 self.mod.database, "get_role_privs",
                 return_value={"rolsuper": True},
             ), \
             patch.object(self.mod.lib, "hr") as fake_hr:
            result = self.mod.main(self.args, conn=self.fake_conn)

        self.assertFalse(result)
        createrol.assert_not_called()
        fake_hr.assert_called_once_with(1)

    def test_handles_get_role_privs_returning_none(self):
        """If the priv lookup fails for any reason, do not crash; fall
        through to the existing role path. (A misconfig without a
        rolsuper probe defaults to accepting the existing role.)"""
        with patch.object(self.mod.database, "rolexists", return_value=True), \
             patch.object(self.mod.database, "createrol") as createrol, \
             patch.object(self.mod.database, "get_role_privs", return_value=None), \
             patch.object(self.mod.lib, "hr") as fake_hr:
            result = self.mod.main(self.args, conn=self.fake_conn)

        self.assertTrue(result)
        createrol.assert_not_called()
        fake_hr.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
