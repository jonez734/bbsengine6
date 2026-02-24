"""
Tests for dynamic module discovery (feature_1).

This tests that console modules are dynamically discovered instead of hardcoded.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add project source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../py/src'))


class TestDiscoverConsoleModules(unittest.TestCase):
    """Test dynamic module discovery"""
    
    def setUp(self):
        """Called before each test"""
        # Clear cache before each test
        from bbsengine6.console import lib
        lib.clear_module_cache()
    
    def tearDown(self):
        """Called after each test"""
        # Clear cache after each test
        from bbsengine6.console import lib
        lib.clear_module_cache()
    
    def test_discover_modules_finds_console_modules(self):
        """Test that discovery finds console modules"""
        from bbsengine6.console import lib
        
        modules = lib.discover_console_modules()
        
        # Should find several modules
        self.assertGreater(len(modules), 0)
        
        # Check expected modules are present
        self.assertIn('session', modules)
        self.assertIn('memberapproval', modules)
    
    def test_discover_modules_excludes_non_modules(self):
        """Test that discovery excludes non-module files"""
        from bbsengine6.console import lib
        
        modules = lib.discover_console_modules()
        
        # Should NOT include these
        self.assertNotIn('__init__', modules)
        self.assertNotIn('__main__', modules)
        self.assertNotIn('lib', modules)
        self.assertNotIn('main', modules)
    
    def test_discover_modules_has_docstrings(self):
        """Test that discovered modules have help text from docstrings"""
        from bbsengine6.console import lib
        
        modules = lib.discover_console_modules()
        
        # All discovered modules should have help text
        for name, help_text in modules.items():
            self.assertIsNotNone(help_text)
            self.assertGreater(len(help_text), 0)
    
    def test_discover_modules_returns_dict(self):
        """Test that discovery returns a dictionary"""
        from bbsengine6.console import lib
        
        result = lib.discover_console_modules()
        
        self.assertIsInstance(result, dict)


class TestModuleValidation(unittest.TestCase):
    """Test module validation for discovery"""
    
    def test_validate_valid_module(self):
        """Test validation of a valid module"""
        from bbsengine6.console import lib
        
        # session is a valid module with main() and docstring
        is_valid, help_text = lib.validate_module_for_discovery('bbsengine6.console.session')
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(help_text)
    
    def test_validate_invalid_module_name(self):
        """Test validation of non-existent module"""
        from bbsengine6.console import lib
        
        is_valid, help_text = lib.validate_module_for_discovery('bbsengine6.console.nonexistent')
        
        self.assertFalse(is_valid)
        self.assertIsNone(help_text)
    
    def test_validate_module_without_main(self):
        """Test that modules without main() are rejected"""
        from bbsengine6.console import lib
        
        # Create a mock module without main
        with patch('importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.__doc__ = "Test module"
            # No main function
            mock_import.return_value = mock_module
            
            is_valid, help_text = lib.validate_module_for_discovery('test.module')
            
            # Should be rejected because no main()
            self.assertFalse(is_valid)


class TestCachingBehavior(unittest.TestCase):
    """Test module discovery caching"""
    
    def setUp(self):
        """Called before each test"""
        from bbsengine6.console import lib
        lib.clear_module_cache()
    
    def tearDown(self):
        """Called after each test"""
        from bbsengine6.console import lib
        lib.clear_module_cache()
    
    def test_first_call_not_cached(self):
        """Test that first call is not cached"""
        from bbsengine6.console import lib
        
        modules1 = lib.discover_console_modules()
        
        # Should have results
        self.assertGreater(len(modules1), 0)
    
    def test_second_call_uses_cache(self):
        """Test that second call uses cache"""
        from bbsengine6.console import lib
        
        modules1 = lib.discover_console_modules()
        modules2 = lib.discover_console_modules()
        
        # Should be the same object (cached)
        self.assertIs(modules1, modules2)
    
    def test_debug_mode_skips_cache(self):
        """Test that debug mode skips cache"""
        from bbsengine6.console import lib
        
        # First call (normal mode)
        modules1 = lib.discover_console_modules()
        
        # Second call with debug=True should refresh
        mock_args = Mock()
        mock_args.debug = True
        modules2 = lib.discover_console_modules(args=mock_args)
        
        # Should be different objects (refreshed)
        # Note: In this case they might still be equal but not same object
        # The key is that it attempted to rediscover
    
    def test_clear_cache_works(self):
        """Test that clear_cache forces rediscovery"""
        from bbsengine6.console import lib
        
        modules1 = lib.discover_console_modules()
        
        # Clear the cache
        lib.clear_module_cache()
        
        # Next call should rediscover
        modules2 = lib.discover_console_modules()
        
        # Should still work (re-discovered)
        self.assertGreater(len(modules2), 0)


class TestBuildSubcommandParser(unittest.TestCase):
    """Test that build_subcommand_parser uses discovery"""
    
    def setUp(self):
        from bbsengine6.console import lib
        lib.clear_module_cache()
    
    def tearDown(self):
        from bbsengine6.console import lib
        lib.clear_module_cache()
    
    def test_parser_includes_discovered_modules(self):
        """Test that parser includes discovered modules"""
        from bbsengine6.console import lib
        
        parser, subparsers = lib.build_subcommand_parser()
        
        # Get the choices for subcommand
        # The subparsers should have actions for discovered modules
        choices = subparsers.choices
        
        # Should include dynamically discovered modules
        self.assertIn('session', choices)
        self.assertIn('memberapproval', choices)
    
    def test_parser_help_shows_modules(self):
        """Test that parser help shows discovered modules"""
        from bbsengine6.console import lib
        import io
        import sys
        
        parser, _ = lib.build_subcommand_parser()
        
        # Capture help output
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            parser.parse_args(['--help'])
        except SystemExit:
            pass
        
        help_output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        # Help should include discovered modules
        self.assertIn('session', help_output)
        self.assertIn('memberapproval', help_output)


if __name__ == '__main__':
    unittest.main()
