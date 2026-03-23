"""
Tests for rendered_length() function.

These tests verify that rendered_length() correctly calculates
the visible width of text, ignoring non-printing control sequences.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py/src"))


class TestRenderedLength(unittest.TestCase):
    """Tests for rendered_length() function"""

    def setUp(self):
        """Clear module caches before each test"""
        from bbsengine6.console import lib

        lib.clear_module_cache()
        from bbsengine6.io.echo import rendered_length

        self.rendered_length = rendered_length

    def tearDown(self):
        """Clear module caches after each test"""
        from bbsengine6.console import lib

        lib.clear_module_cache()

    def test_plain_text_matches_len(self):
        """rendered_length() should equal len() for plain text without commands"""
        test_cases = [
            "John Adams",
            "Rutherford B Hayes",
            "Herbert Hoover",
            "Hello World",
            "a",
            "",
            "The quick brown fox jumps over the lazy dog",
            "12345",
            "Hello\tWorld",  # tab
        ]
        for text in test_cases:
            with self.subTest(text=text):
                self.assertEqual(
                    self.rendered_length(text),
                    len(text),
                    f"rendered_length({text!r}) should equal len({text!r})",
                )

    def test_color_commands_ignored(self):
        """rendered_length() should ignore color commands"""
        test_cases = [
            ("{white}Hello", 5),
            ("{white}Hello{/all}", 5),
            ("{red}red{/all} {blue}blue{/all}", 8),  # "red blue" = 8 chars
            ("{inverse}test{/inverse}", 4),
        ]
        for text, expected in test_cases:
            with self.subTest(text=text):
                self.assertEqual(
                    self.rendered_length(text),
                    expected,
                    f"rendered_length({text!r}) should be {expected}",
                )

    def test_variable_commands_ignored(self):
        """rendered_length() should ignore variable expansions"""
        from bbsengine6.io import setvar

        setvar("testvar", "VAR")
        try:
            self.assertEqual(self.rendered_length("{testvar}"), 3)
        finally:
            from bbsengine6.io.echo import _runtime_vars

            _runtime_vars.clear()

    def test_emoji_counted(self):
        """rendered_length() should count emoji characters"""
        self.assertEqual(self.rendered_length(":smile:"), 1)
        self.assertEqual(self.rendered_length(":grin: :wink:"), 3)  # 2 emojis + 1 space

    def test_acs_not_counted(self):
        """rendered_length() should NOT count ACS control codes as visible characters

        ACS (Alternate Character Set) sequences like {acs:vline} produce
        non-printing control codes that switch character sets. They should
        not contribute to the visible width of text.
        """
        test_cases = [
            ("{acs:vline}", 1),  # ACS character takes 1 column
            ("{acs:hline}", 1),
            ("{acs:ulcorner}", 1),
        ]
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.rendered_length(text)
                self.assertEqual(
                    result,
                    expected,
                    f"rendered_length({text!r}) should be {expected}, got {result}",
                )

    def test_mixed_content(self):
        """rendered_length() should handle mixed content correctly"""
        test_cases = [
            ("{white}Hello {red}World{/all}", 11),  # "Hello World" = 11
            ("Hello {acs:vline} World", 13),  # ACS "x" = 1 char
        ]
        for text, expected in test_cases:
            with self.subTest(text=text):
                self.assertEqual(
                    self.rendered_length(text),
                    expected,
                    f"rendered_length({text!r}) should be {expected}",
                )

    def test_wordwrap_shortcut_counted(self):
        """rendered_length() should count % as a visible character"""
        self.assertEqual(self.rendered_length("Hello % World"), 13)

    def test_repeated_whitespace(self):
        """rendered_length() should count visible whitespace (not newlines)"""
        self.assertEqual(self.rendered_length("Hello   World"), 13)  # 3 spaces = 13 total
        self.assertEqual(self.rendered_length("Hello\nWorld"), 10)  # newline not counted
        self.assertEqual(self.rendered_length("Hello\tWorld"), 11)  # tab = 1 char


if __name__ == "__main__":
    unittest.main()
