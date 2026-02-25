#!/usr/bin/env python3
"""
Test script for the {cha} (cursor horizontal absolute) echo command.
"""

import sys
import os
import io
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import bbsengine6.io
from bbsengine6.io import common


class TestCHACommand(unittest.TestCase):
    """Test {cha} cursor horizontal absolute command"""
    
    def setUp(self):
        """Set up capture of stdout"""
        self.captured_output = io.StringIO()
        
    def test_cha_default_column(self):
        """Test {cha} with no argument defaults to column 1"""
        with patch.object(common, '_current_output_stream', self.captured_output):
            bbsengine6.io.echo("{cha}", end="")
        
        output = self.captured_output.getvalue()
        expected = "\x1b[1G"
        print(f"  Expected: {repr(expected)}")
        print(f"  Actual:   {repr(output)}")
        self.assertEqual(output, expected)
        
    def test_cha_specific_column(self):
        """Test {cha:N} moves cursor to column N"""
        with patch.object(common, '_current_output_stream', self.captured_output):
            bbsengine6.io.echo("{cha:5}", end="")
        
        output = self.captured_output.getvalue()
        expected = "\x1b[5G"
        print(f"  Expected: {repr(expected)}")
        print(f"  Actual:   {repr(output)}")
        self.assertEqual(output, expected)
        
    def test_cha_column_10(self):
        """Test {cha:10} moves cursor to column 10"""
        with patch.object(common, '_current_output_stream', self.captured_output):
            bbsengine6.io.echo("{cha:10}", end="")
        
        output = self.captured_output.getvalue()
        expected = "\x1b[10G"
        print(f"  Expected: {repr(expected)}")
        print(f"  Actual:   {repr(output)}")
        self.assertEqual(output, expected)
        
    def test_cha_with_text(self):
        """Test {cha} followed by text"""
        with patch.object(common, '_current_output_stream', self.captured_output):
            bbsengine6.io.echo("{cha:3}hello", end="")
        
        output = self.captured_output.getvalue()
        expected = "\x1b[3G"
        print(f"  Expected starts with: {repr(expected)}")
        print(f"  Actual:               {repr(output)}")
        self.assertTrue(output.startswith(expected))
        
    def test_cha_repeated(self):
        """Test multiple {cha} commands"""
        with patch.object(common, '_current_output_stream', self.captured_output):
            bbsengine6.io.echo("{cha}{cha:5}", end="")
        
        output = self.captured_output.getvalue()
        expected = "\x1b[1G\x1b[5G"
        print(f"  Expected: {repr(expected)}")
        print(f"  Actual:   {repr(output)}")
        self.assertEqual(output, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
