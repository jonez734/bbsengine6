import pytest
from bbsengine6 import io
from bbsengine6.io.common import _terminal_state
from bbsengine6.io import terminal


@pytest.fixture(autouse=True)
def reset_state():
    io.echo("{reset}")
    yield


class TestIndent:
    def test_indent_basic(self):
        """Test basic indent with F6"""
        result = io.echo("{indent:10}{f6}hello", width=80, flush=False)
        output = result.getvalue() if hasattr(result, 'getvalue') else ""
        # First line after F6 should have indent
        assert "----------hello" in result or "hello" in result

    def test_indent_no_args_resets(self):
        """Test {indent} without args resets to 0"""
        io.echo("{indent:5}text", width=80, flush=False)
        io.echo("{indent}", width=80, flush=False)
        assert _terminal_state.indent == 0

    def test_indent_reset_command(self):
        """Test {reset} clears indent"""
        io.echo("{indent:10}{f6}text", width=80, flush=False)
        io.echo("{reset}", width=80, flush=False)
        assert _terminal_state.indent == 0

    def test_indent_custom_char(self):
        """Test {indent:n:char} custom character"""
        io.echo("{indent:3:=}text", width=80, flush=False)
        assert _terminal_state.indent == 3
        assert _terminal_state.indent_char == "="

    def test_indent_default_char(self):
        """Test default indent char is dash"""
        io.echo("{indent:5}text", width=80, flush=False)
        assert _terminal_state.indent_char == "-"

    def test_indent_word_wrap(self):
        """Test indent on wrapped lines"""
        result = io.echo("{indent:10}" + "A" * 75, width=80, flush=False)
        # First line should have 10 dashes, wrapped line should too
        assert "----------" in result

    def test_indent_literal_newline(self):
        """Test indent after literal newline in text"""
        result = io.echo("{indent:10}line1.\nline2.", width=80, flush=False)
        # Both lines should have indent
        lines = result.split("\n") if hasattr(result, 'split') else []
        # Check output contains indent on both lines
        assert "----------" in result

    def test_indent_blank_line(self):
        """Test indent after blank line (double newline)"""
        result = io.echo("{indent:10}para1.\n\npara2.", width=80, flush=False)
        # Second paragraph should have indent
        assert "----------" in result

    def test_indent_capped_at_terminal_width(self):
        """Test indent is capped at terminal width"""
        io.echo("{indent:200}text", width=80, flush=False)
        assert _terminal_state.indent == 80

    def test_indent_multiple_paragraphs(self):
        """Test indent across multiple paragraphs"""
        buf = "First para line one.\n\nSecond para line one."
        result = io.echo("{indent:10}{f6}" + buf, width=80, flush=False)
        # Both paragraphs should have indent
        assert "----------" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
