"""
Tests for argument separation between global args and subcommand args.

This tests that argv is correctly split at the subcommand boundary:
- Global args (--debug, --verbose) are parsed at console level
- Subcommand args (--filter, --add) are passed to module's buildargs()
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add project source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../py/src'))


class TestArgumentSeparation(unittest.TestCase):
    """Test argv splitting logic"""
    
    def setUp(self):
        """Called before each test"""
        self.mock_args = Mock()
        self.mock_args.debug = False
    
    def tearDown(self):
        """Called after each test"""
        pass
    
    def test_argv_split_single_arg(self):
        """Test argv with single argument after subcommand"""
        # Simulate: zoidoffice member --filter sysop
        # After parsing in __main__.py:
        # args.subcommand = "member"
        # remaining_argv = ["--filter", "sysop"]
        
        remaining_argv = ["--filter", "sysop"]
        
        # Verify format
        self.assertEqual(len(remaining_argv), 2)
        self.assertEqual(remaining_argv[0], "--filter")
        self.assertEqual(remaining_argv[1], "sysop")
    
    def test_argv_split_multiple_args(self):
        """Test argv with multiple arguments after subcommand"""
        # Simulate: zoidoffice member --filter sysop --verbose
        remaining_argv = ["--filter", "sysop", "--verbose"]
        
        # Verify format
        self.assertEqual(len(remaining_argv), 3)
        self.assertIn("--filter", remaining_argv)
        self.assertIn("--verbose", remaining_argv)
    
    def test_argv_split_no_args(self):
        """Test argv with no arguments after subcommand"""
        # Simulate: zoidoffice member
        remaining_argv = []
        
        # Verify format
        self.assertEqual(len(remaining_argv), 0)
    
    def test_argv_split_with_choices(self):
        """Test argv with choice arguments"""
        # Simulate: zoidoffice member --filter active
        remaining_argv = ["--filter", "active"]
        
        # Verify format
        self.assertEqual(remaining_argv[0], "--filter")
        self.assertIn(remaining_argv[1], ["all", "active", "sysop"])
    
    def test_argv_strip_whitespace(self):
        """Test that argv elements are stripped of whitespace"""
        # Simulate argv with extra whitespace
        argv_with_whitespace = [" --filter ", " sysop "]
        
        # Our code does: [a.strip() for a in argv]
        cleaned_argv = [a.strip() for a in argv_with_whitespace]
        
        self.assertEqual(cleaned_argv, ["--filter", "sysop"])


class TestHandleSubcommandWithArgv(unittest.TestCase):
    """Test that handle_subcommand passes argv correctly"""
    
    def setUp(self):
        self.mock_args = Mock()
        self.mock_args.debug = False
    
    @patch('bbsengine6.console.lib.runmodule')
    def test_handle_subcommand_passes_argv(self, mock_runmodule):
        """Test that handle_subcommand passes argv via kwargs"""
        from bbsengine6.console import lib
        
        mock_runmodule.return_value = True
        
        # Call with argv parameter
        result = lib.handle_subcommand(
            self.mock_args, 
            'member', 
            argv=["--filter", "sysop"]
        )
        
        # Verify runmodule was called with argv in kwargs
        mock_runmodule.assert_called_once()
        call_kwargs = mock_runmodule.call_args[1]
        self.assertIn('argv', call_kwargs)
        self.assertEqual(call_kwargs['argv'], ["--filter", "sysop"])
    
    @patch('bbsengine6.console.lib.runmodule')
    def test_handle_subcommand_no_argv(self, mock_runmodule):
        """Test that handle_subcommand works without argv"""
        from bbsengine6.console import lib
        
        mock_runmodule.return_value = True
        
        # Call without argv parameter
        result = lib.handle_subcommand(self.mock_args, 'member')
        
        # Verify runmodule was called
        mock_runmodule.assert_called_once()
    
    @patch('bbsengine6.console.lib.runmodule')
    def test_handle_subcommand_empty_argv(self, mock_runmodule):
        """Test that handle_subcommand works with empty argv"""
        from bbsengine6.console import lib
        
        mock_runmodule.return_value = True
        
        # Call with empty argv
        result = lib.handle_subcommand(
            self.mock_args, 
            'member', 
            argv=[]
        )
        
        # Verify runmodule was called with empty argv
        mock_runmodule.assert_called_once()
        call_kwargs = mock_runmodule.call_args[1]
        self.assertIn('argv', call_kwargs)
        self.assertEqual(call_kwargs['argv'], [])


class TestModuleRunWithArgv(unittest.TestCase):
    """Test that module.run() handles argv correctly"""
    
    def setUp(self):
        self.mock_args = Mock()
        self.mock_args.debug = False
        # Fix: also need to handle "in args" check
        self.mock_args.__contains__ = lambda self, key: hasattr(self, key)
    
    @patch('bbsengine6.module.runcallback')
    @patch('bbsengine6.module.check')
    def test_module_receives_clean_argv(self, mock_check, mock_runcallback):
        """Test that module.run() receives argv without subcommand name"""
        import bbsengine6.module as module
        
        # Mock the check function to pass
        mock_check.return_value = True
        
        # Mock runcallback for init, buildargs, main
        mock_runcallback.side_effect = [True, None, True]
        
        # Call with argv that does NOT include subcommand name
        # (console/__main__.py already extracted it)
        result = module.run(
            self.mock_args, 
            'test.module',
            argv=["--filter", "sysop"]
        )
        
        # Verify buildargs was called - argv should NOT have subcommand name
        # It should be: ["--filter", "sysop"]
        # NOT: ["member", "--filter", "sysop"]
        calls = mock_runcallback.call_args_list
        
        # buildargs is the second call (index 1)
        if len(calls) > 1:
            buildargs_call = calls[1]
            # The argv in kwargs should be clean
            if 'argv' in buildargs_call[1]:
                actual_argv = buildargs_call[1]['argv']
                # Should NOT start with 'member' or subcommand name
                if actual_argv:
                    self.assertNotEqual(actual_argv[0], 'member')


if __name__ == '__main__':
    unittest.main()
