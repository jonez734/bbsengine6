"""
Integration tests for bbsengine6 features.
Tests cross-feature functionality.
"""

import sys
import os
import unittest

# Add project source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../py/src'))


class TestFeatureIntegration(unittest.TestCase):
    """Integration tests for all features working together"""
    
    def setUp(self):
        """Clear caches before each test"""
        from bbsengine6.console import lib
        lib.clear_module_cache()
    
    def tearDown(self):
        """Clear caches after each test"""
        from bbsengine6.console import lib
        lib.clear_module_cache()
    
    def test_discovery_with_subcommands(self):
        """Test that discovery and subcommands work together"""
        from bbsengine6.console import lib
        
        # Build parser with discovered modules
        parser, subparsers = lib.build_subcommand_parser()
        
        # Should have discovered modules as subcommands
        self.assertIn('session', subparsers.choices)
        self.assertIn('memberapproval', subparsers.choices)
    
    def test_parse_discovered_subcommand(self):
        """Test parsing a discovered subcommand"""
        from bbsengine6.console import lib
        
        parser, _ = lib.build_subcommand_parser()
        
        # Parse with discovered subcommand
        args = parser.parse_args(['session'])
        
        self.assertEqual(args.subcommand, 'session')
    
    def test_help_shows_all_discovered_modules(self):
        """Test that help shows all discovered modules"""
        from bbsengine6.console import lib
        import io
        import sys
        
        parser, _ = lib.build_subcommand_parser()
        
        # Capture help
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            parser.parse_args(['--help'])
        except SystemExit:
            pass
        
        help_output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        # Should show multiple discovered modules
        self.assertIn('session', help_output)
        self.assertIn('checkroles', help_output)


class TestBackwardCompatibility(unittest.TestCase):
    """Verify backward compatibility across features"""
    
    def test_existing_modules_still_work(self):
        """Test that existing modules still work"""
        from bbsengine6.console import member, session
        
        # All have required functions
        self.assertTrue(hasattr(member, 'main'))
        self.assertTrue(hasattr(session, 'main'))
    
    def test_parse_known_args_works(self):
        """Test that parse_known_args works for custom args"""
        from bbsengine6.console import lib
        
        parser, _ = lib.build_subcommand_parser()
        
        # Should not error on unknown args (use a discovered subcommand)
        args, remaining = parser.parse_known_args(['session', '--custom', 'value'])
        
        self.assertEqual(args.subcommand, 'session')
        self.assertEqual(remaining, ['--custom', 'value'])


if __name__ == '__main__':
    unittest.main()
