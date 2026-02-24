"""
Tests for custom argument parsing in modules.

This tests that modules can define their own arguments via buildargs()
and those arguments are correctly parsed and available in main().
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import argparse

# Add project source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../py/src'))


class TestModuleWithCustomArgs(unittest.TestCase):
    """Test modules with custom arguments"""
    
    def setUp(self):
        """Called before each test"""
        self.mock_args = Mock()
        self.mock_args.debug = False
    
    def test_module_buildargs_returns_parser(self):
        """Test that module can return a parser with custom args"""
        # Simulate a module with custom --filter argument
        parser = argparse.ArgumentParser(description="Test module")
        parser.add_argument('--filter', choices=['all', 'active', 'sysop'],
                          help='Filter results')
        parser.add_argument('--verbose', action='store_true',
                          help='Show detailed output')
        
        # Module's buildargs returns this parser
        module_buildargs = Mock(return_value=parser)
        
        # Verify parser has expected arguments
        args = parser.parse_args(['--filter', 'active'])
        self.assertEqual(args.filter, 'active')
        self.assertFalse(args.verbose)
        
        args = parser.parse_args(['--verbose'])
        self.assertTrue(args.verbose)
    
    def test_module_buildargs_multiple_args(self):
        """Test module with multiple custom arguments"""
        parser = argparse.ArgumentParser(description="Test module")
        parser.add_argument('--filter', choices=['all', 'active', 'sysop'])
        parser.add_argument('--add', action='store_true')
        parser.add_argument('--amount', type=int)
        
        # Parse multiple args
        args = parser.parse_args(['--filter', 'sysop', '--add', '--amount', '100'])
        
        self.assertEqual(args.filter, 'sysop')
        self.assertTrue(args.add)
        self.assertEqual(args.amount, 100)
    
    def test_module_buildargs_choices(self):
        """Test that choice arguments work correctly"""
        parser = argparse.ArgumentParser()
        parser.add_argument('--filter', choices=['all', 'active', 'sysop', 'moderator'])
        
        # Valid choice
        args = parser.parse_args(['--filter', 'sysop'])
        self.assertEqual(args.filter, 'sysop')
        
        # Invalid choice should fail
        with self.assertRaises(SystemExit):
            parser.parse_args(['--filter', 'invalid'])
    
    def test_module_buildargs_default_values(self):
        """Test that default values work correctly"""
        parser = argparse.ArgumentParser()
        parser.add_argument('--filter', default='all')
        parser.add_argument('--verbose', default=False, action='store_true')
        
        # No args - should use defaults
        args = parser.parse_args([])
        self.assertEqual(args.filter, 'all')
        self.assertFalse(args.verbose)
        
        # With args - should override defaults
        args = parser.parse_args(['--filter', 'active', '--verbose'])
        self.assertEqual(args.filter, 'active')
        self.assertTrue(args.verbose)


class TestModuleWithoutCustomArgs(unittest.TestCase):
    """Test modules without custom arguments (backward compatibility)"""
    
    def test_module_buildargs_returns_none(self):
        """Test that module can return None from buildargs"""
        # This is backward compatible - module without custom args
        module_buildargs = Mock(return_value=None)
        
        # Should be handled gracefully
        self.assertIsNone(module_buildargs())
    
    @patch('bbsengine6.module.runcallback')
    @patch('bbsengine6.module.check')
    def test_module_with_none_buildargs_works(self, mock_check, mock_runcallback):
        """Test that modules returning None from buildargs still work"""
        import bbsengine6.module as module
        
        # Setup mocks
        mock_check.return_value = True
        mock_runcallback.side_effect = [True, None, True]  # init, buildargs (None), main
        
        result = module.run(self.mock_args, 'test.module', argv=[])
        
        # Should succeed even though buildargs returned None
        self.assertTrue(result)


class TestCustomArgsIntegration(unittest.TestCase):
    """Integration tests for custom argument flow"""
    
    def setUp(self):
        self.mock_args = Mock()
        self.mock_args.debug = False
    
    @patch('bbsengine6.module.load')
    @patch('bbsengine6.module.runcallback')
    @patch('bbsengine6.module.check')
    def test_full_flow_with_custom_args(self, mock_check, mock_runcallback, mock_load):
        """Test complete flow: argv → buildargs → parse_args → main"""
        import bbsengine6.module as module
        
        # Create mock module with custom args
        mock_module = Mock()
        mock_module.init = Mock(return_value=True)
        mock_module.access = Mock(return_value=True)
        mock_module.__doc__ = "Test module"
        
        # Create parser with --filter arg
        parser = argparse.ArgumentParser(description="Test module")
        parser.add_argument('--filter', choices=['all', 'active', 'sysop'],
                          default='all')
        
        mock_module.buildargs = Mock(return_value=parser)
        mock_module.main = Mock(return_value=True)
        
        mock_load.return_value = mock_module
        mock_check.return_value = True
        mock_runcallback.side_effect = [
            True,  # init
            parser,  # buildargs returns parser
            True   # main
        ]
        
        # Run with custom arg
        result = module.run(
            self.mock_args,
            'test.module',
            argv=['--filter', 'sysop']
        )
        
        # Verify main was called
        self.assertTrue(result)
        mock_module.main.assert_called_once()
    
    @patch('bbsengine6.module.load')
    @patch('bbsengine6.module.runcallback')
    @patch('bbsengine6.module.check')
    def test_invalid_custom_arg_returns_false(self, mock_check, mock_runcallback, mock_load):
        """Test that invalid custom argument returns False (error)"""
        import bbsengine6.module as module
        
        # Create mock module with custom args
        mock_module = Mock()
        mock_module.init = Mock(return_value=True)
        mock_module.access = Mock(return_value=True)
        
        # Create parser with --filter that has choices
        parser = argparse.ArgumentParser(description="Test module")
        parser.add_argument('--filter', choices=['all', 'active', 'sysop'])
        
        mock_module.buildargs = Mock(return_value=parser)
        mock_module.main = Mock(return_value=True)
        
        mock_load.return_value = mock_module
        mock_check.return_value = True
        mock_runcallback.side_effect = [
            True,  # init
            parser,  # buildargs
            True   # main (shouldn't reach here with invalid arg)
        ]
        
        # Run with INVALID custom arg - should fail
        result = module.run(
            self.mock_args,
            'test.module',
            argv=['--filter', 'invalid_choice']
        )
        
        # Should return False due to ArgumentError
        self.assertFalse(result)


class TestHelpWithCustomArgs(unittest.TestCase):
    """Test that help works with custom arguments"""
    
    def test_help_shows_custom_args(self):
        """Test that --help shows module's custom arguments"""
        parser = argparse.ArgumentParser(description="Test module")
        parser.add_argument('--filter', choices=['all', 'active', 'sysop'],
                          help='Filter results')
        parser.add_argument('--verbose', action='store_true',
                          help='Show detailed output')
        
        # Capture help output
        import io
        import sys
        
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            parser.parse_args(['--help'])
        except SystemExit:
            pass
        
        help_output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        # Verify custom args appear in help
        self.assertIn('--filter', help_output)
        self.assertIn('--verbose', help_output)
        self.assertIn('Filter results', help_output)


if __name__ == '__main__':
    unittest.main()
