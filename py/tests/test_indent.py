import pytest
import sys

sys.path.insert(0, "src")

from bbsengine6 import io
from bbsengine6.io.common import _terminal_state


@pytest.fixture(autouse=True)
def reset_state():
    io.echo("{reset}")
    yield


class TestIndent:
    def test_indent_sets_state(self):
        """Test {indent:n} sets indent state"""
        io.echo("{indent:10}", width=80, flush=False)
        assert _terminal_state.indent == 10

    def test_indent_no_args_resets(self):
        """Test {indent} without args resets to 0"""
        io.echo("{indent:5}", width=80, flush=False)
        io.echo("{indent}", width=80, flush=False)
        assert _terminal_state.indent == 0

    def test_indent_reset_command(self):
        """Test {reset} clears indent"""
        io.echo("{indent:10}", width=80, flush=False)
        io.echo("{reset}", width=80, flush=False)
        assert _terminal_state.indent == 0

    def test_indent_custom_char(self):
        """Test {indent:n:char} custom character"""
        # Syntax: {indent:3:char} where char is a single character
        io.echo("{indent:3:x}", width=80, flush=False)
        assert _terminal_state.indent == 3
        assert _terminal_state.indent_char == "x"

    def test_indent_default_char(self):
        """Test default indent char is space"""
        io.echo("{indent:5}", width=80, flush=False)
        assert _terminal_state.indent_char == " "

    def test_indent_with_f6(self):
        """Test indent with F6 - should render without error"""
        io.echo("{indent:10}{f6}hello", width=80, flush=False)
        # Just verify it runs without error

    def test_indent_word_wrap(self):
        """Test indent with word wrap - should render without error"""
        io.echo("{indent:10}" + "A" * 75, width=80, flush=False)
        # Just verify it runs without error

    def test_indent_literal_newline(self):
        """Test indent after literal newline in text"""
        io.echo("{indent:10}line1.\nline2.", width=80, flush=False)
        # Just verify it runs without error

    def test_indent_blank_line(self):
        """Test indent after blank line (double newline)"""
        io.echo("{indent:10}para1.\n\npara2.", width=80, flush=False)
        # Just verify it runs without error

    def test_indent_capped_at_terminal_width(self):
        """Test indent is capped at terminal width"""
        io.echo("{indent:200}", width=80, flush=False)
        assert _terminal_state.indent == 80


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
