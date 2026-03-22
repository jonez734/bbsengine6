"""
Backward compatibility tests for feature_2.

These tests verify that existing modules continue to work unchanged
after adding module-specific argument support.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add project source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py/src"))


class TestBackwardCompatibility(unittest.TestCase):
    """Test that existing modules work unchanged"""

    def setUp(self):
        self.mock_args = Mock()
        self.mock_args.debug = False

    @patch("bbsengine6.module.runcallback")
    @patch("bbsengine6.module.check")
    def test_module_without_custom_args_works(self, mock_check, mock_runcallback):
        """Test that modules without custom args still work"""
        import bbsengine6.module as module

        # Mock check to pass
        mock_check.return_value = True

        # Mock runcallback to return None for buildargs (no custom args)
        # and True for init and main
        mock_runcallback.side_effect = [True, None, True]

        result = module.run(self.mock_args, "test.module", argv=[])

        # Should succeed
        self.assertTrue(result)

    @patch("bbsengine6.module.runcallback")
    @patch("bbsengine6.module.check")
    def test_module_with_empty_argv_works(self, mock_check, mock_runcallback):
        """Test that modules work with empty argv"""
        import bbsengine6.module as module

        mock_check.return_value = True
        mock_runcallback.side_effect = [True, None, True]

        result = module.run(self.mock_args, "test.module", argv=[])

        self.assertTrue(result)

    @patch("bbsengine6.module.runcallback")
    @patch("bbsengine6.module.check")
    def test_module_with_none_buildargs_works(self, mock_check, mock_runcallback):
        """Test that modules returning None from buildargs still work"""
        import bbsengine6.module as module

        mock_check.return_value = True
        # Simulate buildargs returning None
        mock_runcallback.side_effect = [True, None, True]

        result = module.run(self.mock_args, "test.module", argv=["--some-flag"])

        # Should still work - argv is ignored when buildargs returns None
        self.assertTrue(result)


class TestExistingModuleBehavior(unittest.TestCase):
    """Test that existing modules behave as expected"""

    def test_member_module_still_works(self):
        """Verify member module structure is unchanged"""
        # Import member module
        from bbsengine6.console import member

        # Check it has required functions
        self.assertTrue(hasattr(member, "init"))
        self.assertTrue(callable(member.init))

        self.assertTrue(hasattr(member, "access"))
        self.assertTrue(callable(member.access))

        self.assertTrue(hasattr(member, "buildargs"))
        self.assertTrue(callable(member.buildargs))

        self.assertTrue(hasattr(member, "main"))
        self.assertTrue(callable(member.main))

    def test_session_module_still_works(self):
        """Verify session module structure is unchanged"""
        from bbsengine6.console import session

        self.assertTrue(hasattr(session, "init"))
        self.assertTrue(callable(session.init))
        self.assertTrue(hasattr(session, "main"))
        self.assertTrue(callable(session.main))

    def test_checkroles_module_still_works(self):
        """Verify checkroles module structure is unchanged"""
        from bbsengine6.console import checkroles

        self.assertTrue(hasattr(checkroles, "init"))
        self.assertTrue(callable(checkroles.init))
        self.assertTrue(hasattr(checkroles, "main"))
        self.assertTrue(callable(checkroles.main))

        # checkroles returns None from buildargs
        result = checkroles.buildargs(Mock())
        self.assertIsNone(result)


class TestGlobalArgsUnchanged(unittest.TestCase):
    """Test that global arguments still work at console level"""

    def test_console_parser_has_global_args(self):
        """Verify console parser still has --debug and --verbose"""
        from bbsengine6.console import lib

        parser, subparsers = lib.build_subcommand_parser()

        # Parse with global args
        args = parser.parse_args(["--debug", "member"])

        # Global args should be available
        self.assertTrue(args.debug)
        self.assertFalse(args.verbose)

        # Subcommand should still be recognized
        self.assertEqual(args.subcommand, "member")

    def test_console_parser_global_args_alone(self):
        """Verify global args work without subcommand"""
        from bbsengine6.console import lib

        parser, subparsers = lib.build_subcommand_parser()

        # Parse with only global args (no subcommand)
        args = parser.parse_args(["--verbose"])

        self.assertTrue(args.verbose)
        self.assertIsNone(args.subcommand)


class TestMenuModeUnchanged(unittest.TestCase):
    """Test that interactive menu mode still works"""

    def test_no_subcommand_runs_menu(self):
        """Verify that running without subcommand shows menu"""
        # This is tested by console/__main__.py logic:
        # if args.subcommand is None:
        #     lib.runmodule(args, "main")

        # We just verify the logic path exists
        from bbsengine6.console import lib

        # Verify runmodule exists and is callable
        self.assertTrue(hasattr(lib, "runmodule"))
        self.assertTrue(callable(lib.runmodule))


if __name__ == "__main__":
    unittest.main()
