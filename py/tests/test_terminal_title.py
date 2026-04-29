import pytest
import sys
import io

sys.path.insert(0, "src")

from bbsengine6.io import terminal
from bbsengine6.io import common


pytestmark = pytest.mark.unit


class TestTerminalTitle:
    def test_title_uses_st_terminator(self):
        """Test that title() uses ECMA-48 ST terminator instead of BEL"""
        captured = io.StringIO()
        old_stream = common._current_output_stream
        common.set_output_stream(captured)

        try:
            terminal.title("test title")
            output = captured.getvalue()
            assert "\x1b\\" in output, f"Expected ST (ESC\\) in output, got: {repr(output)}"
            assert "\x07" not in output, f"BEL should not be in output, got: {repr(output)}"
        finally:
            common.set_output_stream(old_stream)

    def test_title_format(self):
        """Test that title() produces correct OSC sequence"""
        captured = io.StringIO()
        old_stream = common._current_output_stream
        common.set_output_stream(captured)

        try:
            terminal.title("my window title")
            output = captured.getvalue()
            expected = "\x1b]0;my window title\x1b\\"
            assert output == expected, f"Expected {repr(expected)}, got {repr(output)}"
        finally:
            common.set_output_stream(old_stream)

    def test_title_with_special_chars(self):
        """Test title() handles special characters correctly"""
        captured = io.StringIO()
        old_stream = common._current_output_stream
        common.set_output_stream(captured)

        try:
            terminal.title("title with : special ; chars")
            output = captured.getvalue()
            assert "title with : special ; chars" in output
        finally:
            common.set_output_stream(old_stream)

    def test_title_empty_string(self):
        """Test title() with empty string"""
        captured = io.StringIO()
        old_stream = common._current_output_stream
        common.set_output_stream(captured)

        try:
            terminal.title("")
            output = captured.getvalue()
            assert "\x1b]0;\x1b\\" == output
        finally:
            common.set_output_stream(old_stream)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
