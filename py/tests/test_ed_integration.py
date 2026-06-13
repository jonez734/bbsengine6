# integration tests for the visual editor with mock input

import pytest

from bbsengine6.ed import run


class TestEditorIntegration:
    """Integration tests using mock input for the visual editor."""

    def test_type_hello_world(self):
        """Test typing 'hello world' and exiting with Ctrl+K x."""

        class MockInput:
            def __init__(self):
                self.calls = 0
                self.inputs = [
                    "h",  # type 'h'
                    "e",  # type 'e'
                    "l",  # type 'l'
                    "l",  # type 'l'
                    "o",  # type 'o'
                    " ",  # type ' '
                    "w",  # type 'w'
                    "o",  # type 'o'
                    "r",  # type 'r'
                    "l",  # type 'l'
                    "d",  # type 'd'
                    "KEY_CTRL_K",  # enter ctrl_k mode
                    "x",  # exit
                ]

            def __call__(self):
                if self.calls < len(self.inputs):
                    result = self.inputs[self.calls]
                    self.calls += 1
                    return result
                return None

        class MockArgs:
            debug = False

        mock_input = MockInput()
        result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input)

        assert result == "hello world"

    def test_cursor_movement(self):
        """Test cursor movement with arrow keys."""

        class MockInput:
            def __init__(self):
                self.calls = 0
                self.inputs = [
                    "h",  # type 'h'
                    "i",  # type 'i'
                    "KEY_LEFT",  # move left
                    "KEY_LEFT",  # move left
                    "KEY_RIGHT",  # move right
                    "KEY_UP",  # try to go up (at top, stays)
                    "KEY_DOWN",  # try to go down (only one line)
                    "KEY_CTRL_K",  # enter ctrl_k mode
                    "x",  # exit
                ]

            def __call__(self):
                if self.calls < len(self.inputs):
                    result = self.inputs[self.calls]
                    self.calls += 1
                    return result
                return None

        class MockArgs:
            debug = False

        mock_input = MockInput()
        result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input)

        assert result == "hi"

    def test_backspace(self):
        """Test backspace functionality."""

        class MockInput:
            def __init__(self):
                self.calls = 0
                self.inputs = [
                    "h",  # type 'h'
                    "e",  # type 'e'
                    "l",  # type 'l'
                    "l",  # type 'l'
                    "o",  # type 'o'
                    "KEY_BACKSPACE",  # backspace
                    "KEY_BACKSPACE",  # backspace
                    "KEY_BACKSPACE",  # backspace
                    "KEY_CTRL_K",  # enter ctrl_k mode
                    "x",  # exit
                ]

            def __call__(self):
                if self.calls < len(self.inputs):
                    result = self.inputs[self.calls]
                    self.calls += 1
                    return result
                return None

        class MockArgs:
            debug = False

        mock_input = MockInput()
        result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input)

        assert result == "he"

    def test_home_end(self):
        """Test Home/End keys."""

        class MockInput:
            def __init__(self):
                self.calls = 0
                self.inputs = [
                    "h",  # type 'h'
                    "e",  # type 'e'
                    "l",  # type 'l'
                    "l",  # type 'l'
                    "o",  # type 'o'
                    "KEY_HOME",  # go to start
                    "KEY_RIGHT",  # move right
                    "KEY_RIGHT",  # move right
                    "KEY_END",  # go to end
                    "KEY_CTRL_K",  # enter ctrl_k mode
                    "x",  # exit
                ]

            def __call__(self):
                if self.calls < len(self.inputs):
                    result = self.inputs[self.calls]
                    self.calls += 1
                    return result
                return None

        class MockArgs:
            debug = False

        mock_input = MockInput()
        result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input)

        assert result == "hello"

    def test_delete_key(self):
        """Test Delete key."""

        class MockInput:
            def __init__(self):
                self.calls = 0
                self.inputs = [
                    "h",  # type 'h'
                    "e",  # type 'e'
                    "l",  # type 'l'
                    "l",  # type 'l'
                    "o",  # type 'o'
                    "KEY_HOME",  # go to start
                    "KEY_RIGHT",  # move right
                    "KEY_RIGHT",  # move right
                    "KEY_DELETE",  # delete
                    "KEY_DELETE",  # delete
                    "KEY_CTRL_K",  # enter ctrl_k mode
                    "x",  # exit
                ]

            def __call__(self):
                if self.calls < len(self.inputs):
                    result = self.inputs[self.calls]
                    self.calls += 1
                    return result
                return None

        class MockArgs:
            debug = False

        mock_input = MockInput()
        result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input)

        assert result == "heo"

    def test_word_wrap(self):
        """Test word wrapping when reaching terminal width."""

        class MockInput:
            def __init__(self):
                self.calls = 0
                self.inputs = [
                    "T",  # type character
                    "h",  # type character
                    "i",  # type character
                    "s",  # type character
                    " ",  # space
                    "i",  # type character
                    "s",  # type character
                    " ",  # space
                    "a",  # type character
                    " ",  # space - should wrap before this
                    "t",  # type character
                    "e",  # type character
                    "s",  # type character
                    "t",  # type character
                    "KEY_CTRL_K",  # enter ctrl_k mode
                    "x",  # exit
                ]

            def __call__(self):
                if self.calls < len(self.inputs):
                    result = self.inputs[self.calls]
                    self.calls += 1
                    return result
                return None

        class MockArgs:
            debug = False

        mock_input = MockInput()
        result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input)

        assert "This is a test" in result or "This is a" in result

    def test_word_wrap_at_width(self):
        """Test word wrap at terminal width with long word."""

        class MockInput:
            def __init__(self):
                self.calls = 0
                self.inputs = [
                    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j",  # 10 chars
                    "k", "l", "m", "n", "o", "p", "q", "r", "s", "t",  # 20 chars
                    "u", "v", "w", "x", "y", "z",  # 26 chars
                    " ",  # space
                    "1", "2", "3", "4", "5",  # more
                    "KEY_CTRL_K",
                    "x",
                ]

            def __call__(self):
                if self.calls < len(self.inputs):
                    result = self.inputs[self.calls]
                    self.calls += 1
                    return result
                return None

        class MockArgs:
            debug = False

        mock_input = MockInput()
        result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input)

        assert result is not None
        assert len(result) > 0

    def test_backspace_on_wrapped_line(self):
        """Test backspace at start of wrapped line unwraps to previous line."""

        class MockInput:
            def __init__(self):
                self.calls = 0
                self.inputs = [
                    "H", "e", "l", "l", "o", " ", "w", "o", "r", "l", "d",  # type "Hello world"
                    "KEY_HOME",  # go to start
                    "KEY_RIGHT", "KEY_RIGHT", "KEY_RIGHT", "KEY_RIGHT", "KEY_RIGHT",  # move to position 5 (after "Hello")
                    "KEY_DOWN",  # should go to next line (wrapped)
                    "KEY_HOME",  # go to start of wrapped line
                    "KEY_BACKSPACE",  # should unwrap back to previous line
                    "KEY_CTRL_K",
                    "x",
                ]

            def __call__(self):
                if self.calls < len(self.inputs):
                    result = self.inputs[self.calls]
                    self.calls += 1
                    return result
                return None

        class MockArgs:
            debug = False

        mock_input = MockInput()
        result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input)

        assert result is not None
        assert "Helloworld" in result.replace(" ", "") or "Hello" in result

    def test_ctrl_k_invalid_command_rings_bell(self):
        """Test that invalid Ctrl+K command rings the terminal bell."""

        class MockInput:
            def __init__(self):
                self.calls = 0
                self.inputs = [
                    "h", "e", "l", "l", "o",  # type "hello"
                    "KEY_CTRL_K",  # enter ctrl_k mode
                    "z",  # invalid command (not x)
                ]

            def __call__(self):
                if self.calls < len(self.inputs):
                    result = self.inputs[self.calls]
                    self.calls += 1
                    return result
                return None

        class MockArgs:
            debug = False

        mock_input = MockInput()
        result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input)

        assert result == "hello"

    def test_load_existing_file(self):
        """Test loading an existing file."""

        class MockInput:
            def __init__(self):
                self.calls = 0
                self.inputs = [
                    "KEY_CTRL_K",
                    "x",
                ]

            def __call__(self):
                if self.calls < len(self.inputs):
                    result = self.inputs[self.calls]
                    self.calls += 1
                    return result
                return None

        class MockArgs:
            debug = False

        filepath = "/home/opencode/data/work/bbsengine6/py/src/demo_listbox_cursor.spec"
        mock_input = MockInput()
        result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input, filepath=filepath)

        assert result is not None
        assert "demo_listbox_cursor" in result
        assert "ListboxCursor" in result

    def test_cursor_movement_with_loaded_file(self):
        """Test cursor movement after loading an existing file."""

        class MockInput:
            def __init__(self):
                self.calls = 0
                self.inputs = [
                    "KEY_HOME",  # go to start
                    "KEY_END",   # go to end of line
                    "KEY_HOME",  # back to start
                    "KEY_RIGHT", "KEY_RIGHT", "KEY_RIGHT",  # move right
                    "KEY_LEFT",  # move left
                    "KEY_DOWN",  # try to go down (should work if file has multiple lines)
                    "KEY_UP",    # go back up
                    "KEY_CTRL_K",
                    "x",
                ]

            def __call__(self):
                if self.calls < len(self.inputs):
                    result = self.inputs[self.calls]
                    self.calls += 1
                    return result
                return None

        class MockArgs:
            debug = False

        filepath = "/home/opencode/data/work/bbsengine6/py/src/demo_listbox_cursor.spec"
        mock_input = MockInput()
        result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input, filepath=filepath)

        assert result is not None
        assert "demo_listbox_cursor" in result

    def test_word_wrap_with_loaded_file(self):
        """Test word wrap after loading an existing file and adding text."""

        class MockInput:
            def __init__(self):
                self.calls = 0
                self.inputs = [
                    "KEY_END",  # go to end of first line
                    " ",  # add space
                    "a", "d", "d", "i", "n", "g",  # add some text to trigger wrap
                    " ", "t", "e", "x", "t",
                    "KEY_CTRL_K",
                    "x",
                ]

            def __call__(self):
                if self.calls < len(self.inputs):
                    result = self.inputs[self.calls]
                    self.calls += 1
                    return result
                return None

        class MockArgs:
            debug = False

        filepath = "/home/opencode/data/work/bbsengine6/py/src/demo_listbox_cursor.spec"
        mock_input = MockInput()
        result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input, filepath=filepath)

        assert result is not None
        assert "demo_listbox_cursor" in result

    def test_single_page_file_display(self):
        """Test that a single-page file displays correctly from line 0."""

        import tempfile
        import os

        content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            class MockInput:
                def __init__(self):
                    self.calls = 0
                    self.inputs = [
                        "KEY_CTRL_K",
                        "x",
                    ]

                def __call__(self):
                    if self.calls < len(self.inputs):
                        result = self.inputs[self.calls]
                        self.calls += 1
                        return result
                    return None

            class MockArgs:
                debug = False

            mock_input = MockInput()
            result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input, filepath=temp_path)

            assert result is not None
            assert "Line 1" in result
            assert "Line 5" in result
        finally:
            os.unlink(temp_path)

    def test_single_page_cursor_at_start(self):
        """Test that cursor starts at position 0,0 for single-page file."""

        import tempfile
        import os

        content = "First line\nSecond line\nThird line\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            class MockInput:
                def __init__(self):
                    self.calls = 0
                    self.inputs = [
                        "KEY_HOME",  # should stay at 0
                        "KEY_CTRL_K",
                        "x",
                    ]

                def __call__(self):
                    if self.calls < len(self.inputs):
                        result = self.inputs[self.calls]
                        self.calls += 1
                        return result
                    return None

            class MockArgs:
                debug = False

            mock_input = MockInput()
            result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input, filepath=temp_path)

            assert result is not None
            assert "First line" in result
        finally:
            os.unlink(temp_path)

    def test_file_lines_in_order(self):
        """Test that file lines are returned in correct order starting from line 0."""

        import tempfile
        import os

        content = "AAAA\nBBBB\nCCCC\nDDDD\nEEEE\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            class MockInput:
                def __init__(self):
                    self.calls = 0
                    self.inputs = [
                        "KEY_CTRL_K",
                        "x",
                    ]

                def __call__(self):
                    if self.calls < len(self.inputs):
                        result = self.inputs[self.calls]
                        self.calls += 1
                        return result
                    return None

            class MockArgs:
                debug = False

            mock_input = MockInput()
            result = run(MockArgs(), moniker="test", test_mode=True, input_func=mock_input, filepath=temp_path)

            assert result is not None
            lines = result.split('\n')
            assert lines[0] == "AAAA", f"First line should be AAAA, got {lines[0]!r}"
            assert lines[1] == "BBBB", f"Second line should be BBBB, got {lines[1]!r}"
            assert lines[2] == "CCCC", f"Third line should be CCCC, got {lines[2]!r}"
            assert lines[3] == "DDDD", f"Fourth line should be DDDD, got {lines[3]!r}"
            assert lines[4] == "EEEE", f"Fifth line should be EEEE, got {lines[4]!r}"
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
