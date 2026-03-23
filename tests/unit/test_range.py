"""
Tests for expandrange() and collapserange() functions.

These tests verify that the range expansion and collapsing functions
correctly handle various input types and formats.
"""

import unittest

from bbsengine6 import util


class TestExpandRange(unittest.TestCase):
    """Tests for expandrange() function"""

    def test_basic_range(self):
        """expandrange() should expand a basic range like '1-5'"""
        result = util.expandrange("1-5")
        self.assertEqual(result, [1, 2, 3, 4, 5])

    def test_multiple_ranges(self):
        """expandrange() should handle multiple comma-separated ranges"""
        result = util.expandrange("1,3-5,7")
        self.assertEqual(result, [1, 3, 4, 5, 7])

    def test_reversed_range(self):
        """expandrange() should autocorrect reversed ranges like '5-1'"""
        result = util.expandrange("5-1")
        self.assertEqual(result, [1, 2, 3, 4, 5])

    def test_single_number(self):
        """expandrange() should handle a single number"""
        result = util.expandrange("3")
        self.assertEqual(result, [3])

    def test_whitespace(self):
        """expandrange() should handle whitespace around numbers"""
        result = util.expandrange(" 1 , 2 , 3 ")
        self.assertEqual(result, [1, 2, 3])

    def test_empty_string(self):
        """expandrange() should return empty list for empty string"""
        result = util.expandrange("")
        self.assertEqual(result, [])

    def test_list_input(self):
        """expandrange() should accept a list as input"""
        result = util.expandrange([1, 2, 3])
        self.assertEqual(result, [1, 2, 3])

    def test_list_with_duplicates(self):
        """expandrange() should deduplicate list input"""
        result = util.expandrange([1, 1, 2, 2])
        self.assertEqual(result, [1, 2])

    def test_unsorted_list(self):
        """expandrange() should sort list input"""
        result = util.expandrange([3, 1, 2])
        self.assertEqual(result, [1, 2, 3])

    def test_single_element_list(self):
        """expandrange() should handle a single-element list"""
        result = util.expandrange([5])
        self.assertEqual(result, [5])

    def test_invalid_string_raises_value_error(self):
        """expandrange() should raise ValueError for invalid numbers"""
        with self.assertRaises(ValueError) as cm:
            util.expandrange("abc")
        self.assertIn("Invalid number", str(cm.exception))

    def test_negative_number_raises_value_error(self):
        """expandrange() should raise ValueError for negative numbers"""
        with self.assertRaises(ValueError):
            util.expandrange("-5")

    def test_negative_range_raises_value_error(self):
        """expandrange() should raise ValueError for negative ranges"""
        with self.assertRaises(ValueError):
            util.expandrange("-5--1")

    def test_int_input_raises_type_error(self):
        """expandrange() should raise TypeError for non-str/list input"""
        with self.assertRaises(TypeError) as cm:
            util.expandrange(123)
        self.assertIn("Expected str or list", str(cm.exception))

    def test_none_input_raises_type_error(self):
        """expandrange() should raise TypeError for None input"""
        with self.assertRaises(TypeError) as cm:
            util.expandrange(None)
        self.assertIn("Expected str or list", str(cm.exception))


class TestCollapseRange(unittest.TestCase):
    """Tests for collapserange() function"""

    def test_full_range(self):
        """collapserange() should collapse a full range to a tuple"""
        result = util.collapserange([1, 2, 3, 4, 5])
        self.assertEqual(result, [(1, 5)])

    def test_partial_range(self):
        """collapserange() should handle partial ranges correctly"""
        result = util.collapserange([1, 2, 3, 5, 6, 8])
        self.assertEqual(result, [(1, 3), (5,), (6,), (8,)])

    def test_adjacent_pairs(self):
        """collapserange() should handle adjacent pairs - outputs separate tuples"""
        result = util.collapserange([1, 2, 4, 5])
        self.assertEqual(result, [(1,), (2,), (4,), (5,)])

    def test_single_element(self):
        """collapserange() should handle a single element"""
        result = util.collapserange([5])
        self.assertEqual(result, [(5,)])

    def test_string_input(self):
        """collapserange() should accept string input"""
        result = util.collapserange("1-5")
        self.assertEqual(result, [(1, 5)])

    def test_unsorted_input(self):
        """collapserange() should automatically sort unsorted input"""
        result = util.collapserange([5, 4, 3, 2, 1])
        self.assertEqual(result, [(1, 5)])

    def test_empty_list(self):
        """collapserange() should return empty list for empty input"""
        result = util.collapserange([])
        self.assertEqual(result, [])

    def test_empty_string(self):
        """collapserange() should return empty list for empty string"""
        result = util.collapserange("")
        self.assertEqual(result, [])

    def test_negative_number_raises_value_error(self):
        """collapserange() should raise ValueError for negative numbers"""
        with self.assertRaises(ValueError):
            util.collapserange("-1")

    def test_negative_list_raises_value_error(self):
        """collapserange() should raise ValueError for negative numbers in list"""
        with self.assertRaises(ValueError) as cm:
            util.collapserange([1, -1, 3])
        self.assertIn("Negative numbers not allowed", str(cm.exception))

    def test_non_integer_raises_value_error(self):
        """collapserange() should raise ValueError for non-integer elements"""
        with self.assertRaises(ValueError) as cm:
            util.collapserange([1, 2, "a"])
        self.assertIn("must be integers", str(cm.exception))

    def test_int_input_raises_type_error(self):
        """collapserange() should raise TypeError for non-str/list input"""
        with self.assertRaises(TypeError) as cm:
            util.collapserange(123)
        self.assertIn("Expected str or list", str(cm.exception))

    def test_bool_in_list_raises_value_error(self):
        """collapserange() should raise ValueError for bool in list"""
        with self.assertRaises(ValueError) as cm:
            util.collapserange([True, 1, 2])
        self.assertIn("must be integers", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
