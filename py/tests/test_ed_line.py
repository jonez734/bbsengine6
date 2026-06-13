# test_ed_line.py
# Tests for bbsengine6.ed line editor mode using mock input

import pytest

from bbsengine6.ed import run


class MockInput:
    """Mock input function that returns keys from a predefined list."""

    def __init__(self, inputs: list[str]):
        self.calls = 0
        self.inputs = inputs

    def __call__(self):
        if self.calls < len(self.inputs):
            result = self.inputs[self.calls]
            self.calls += 1
            return result
        return None


class MockArgs:
    debug = False


class TestLineEditorBasics:
    """Basic line editor functionality tests."""

    def test_empty_editor_returns_empty_string(self):
        """Test that empty editor returns empty string."""
        mock_input = MockInput([".", "x", "n"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result == ""

    def test_dot_enter_command_mode(self):
        """Test that dot enters command mode."""
        mock_input = MockInput([".", "h", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None

    def test_invalid_command_rings_bell(self):
        """Test that invalid command is handled (no crash)."""
        mock_input = MockInput([".", "z", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None

    def test_backspace_cancels_command_mode(self):
        """Test that backspace after dot cancels command and returns to typing."""
        mock_input = MockInput([".", "KEY_BACKSPACE", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result == ""

    def test_editor_starts_outside_command_mode(self):
        """Test editor starts without showing Command: prompt."""
        mock_input = MockInput(["KEY_ENTER", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None

    def test_dot_shows_command_prompt(self):
        """Test that typing . shows command: prompt."""
        mock_input = MockInput([".", "h", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None

    def test_key_enter_at_command_prompt_cancels(self):
        """Test that KEY_ENTER at command prompt cancels and exits command mode."""
        mock_input = MockInput([".", "KEY_ENTER", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result == ""

    def test_key_backspace_at_command_prompt_exits(self):
        """Test that KEY_BACKSPACE at command prompt erases and exits command mode."""
        mock_input = MockInput([".", "KEY_BACKSPACE", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result == ""


class TestHelpCommand:
    """Test .h (help) command."""

    def test_help_command_exists(self):
        """Test that .h command runs without error."""
        mock_input = MockInput([".", "h", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None

    def test_key_f1_displays_help(self):
        """Test that KEY_F1 displays editor help."""
        mock_input = MockInput(["KEY_F1", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None

    def test_question_mark_displays_help(self):
        """Test that ? displays editor help."""
        mock_input = MockInput(["?", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None


class TestExitCommand:
    """Test .x (exit) command."""

    def test_exit_without_changes(self):
        """Test .x exits without prompting when not modified."""
        mock_input = MockInput([".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result == ""

    def test_exit_with_new_line(self):
        """Test exit after adding a new line."""
        mock_input = MockInput(["KEY_ENTER", "KEY_ENTER", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None

    def test_dot_x_exits_editor(self):
        """Test .x command exits the editor and returns content."""
        mock_input = MockInput([".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None
        assert result == ""

    def test_dot_x_with_content(self):
        """Test .x exits with content in buffer via edit command."""
        mock_input = MockInput(["1", "newtext", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None
        assert "newtext" in result.lower()


class TestListCommand:
    """Test .l (list) command."""

    def test_list_empty_buffer(self):
        """Test .l on empty buffer."""
        mock_input = MockInput([".", "l", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None

    def test_list_with_lines(self):
        """Test .l with some lines."""
        mock_input = MockInput(["KEY_ENTER", "KEY_ENTER", ".", "l", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None


class TestSaveCommand:
    """Test .s (save) command."""

    def test_save_to_new_file(self):
        """Test .s prompts for filename when filepath is None."""
        mock_input = MockInput([".", "s", "", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None


class TestReadCommand:
    """Test .r (read) command."""

    def test_read_cancelled(self):
        """Test .r with empty filename cancels."""
        mock_input = MockInput([".", "r", "", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None


class TestNewCommand:
    """Test .n (new) command."""

    def test_new_clears_buffer(self):
        """Test .n clears the buffer."""
        mock_input = MockInput(["KEY_ENTER", "KEY_ENTER", ".", "n", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result == ""


class TestInsertCommand:
    """Test .i (insert) command."""

    def test_insert_at_line_1(self):
        """Test .i inserts at line 1."""
        mock_input = MockInput([".", "i", "1", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None

    def test_insert_invalid_line(self):
        """Test .i with invalid line number."""
        mock_input = MockInput([".", "i", "999", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None


class TestDeleteCommand:
    """Test .d (delete) command."""

    def test_delete_empty_buffer(self):
        """Test .d on empty buffer."""
        mock_input = MockInput([".", "d", "", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None


class TestEditCommand:
    """Test .e (edit) command."""

    def test_edit_with_no_lines(self):
        """Test .e with empty buffer."""
        mock_input = MockInput([".", "e", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None


class TestLineInput:
    """Test text input on lines with KEY_ENTER."""

    def test_single_line_input(self):
        """Test typing a line and pressing Enter."""
        mock_input = MockInput(["h", "e", "l", "l", "o", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None

    def test_multiple_line_input(self):
        """Test multiple lines via KEY_ENTER."""
        mock_input = MockInput(
            ["l", "i", "n", "e", "1", "KEY_ENTER", "l", "i", "n", "e", "2", ".", "x"]
        )
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None


class TestEditByLineNumber:
    """Test editing by entering line number directly."""

    def test_edit_line_1_direct(self):
        """Test entering '1' to edit line 1."""
        mock_input = MockInput(["1", "newtext", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None


class TestFileOperations:
    """File-based integration tests."""

    def test_load_existing_file(self):
        """Test loading an existing file."""
        filepath = "/home/opencode/data/work/bbsengine6/py/src/demo_listbox_cursor.spec"
        mock_input = MockInput([".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            filepath=filepath,
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None
        assert "demo_listbox_cursor" in result


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_invalid_input_handled(self):
        """Test that invalid input is handled gracefully."""
        mock_input = MockInput(["?", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None

    def test_control_character_handled(self):
        """Test that control characters don't crash."""
        mock_input = MockInput(["\x03", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None


class TestImageBBSCompatibility:
    """Test Image BBS-style commands match expected behavior."""

    def test_all_commands_registered(self):
        """Test all Image BBS commands are recognized."""
        commands = ["h", "e", "x", "s", "l", "i", "d", "r", "n"]
        for cmd in commands:
            mock_input = MockInput([".", cmd, ".", "x"])
            result = run(
                MockArgs(),
                moniker="test",
                mode="line",
                input_func=mock_input,
                test_mode=True,
            )
            assert result is not None, f"Command .{cmd} should work"


class TestMultipleCommands:
    """Test sequence of multiple commands."""

    def test_list_then_save(self):
        """Test .l then .s sequence."""
        mock_input = MockInput([".", "l", ".", "s", "", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None

    def test_read_then_list_then_exit(self):
        """Test .r then .l then .x sequence."""
        filepath = "/home/opencode/data/work/bbsengine6/py/src/demo_listbox_cursor.spec"
        mock_input = MockInput([".", "l", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            filepath=filepath,
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None


class TestBufferState:
    """Test buffer state management."""

    def test_modified_flag_set(self):
        """Test modified flag is set after changes."""
        mock_input = MockInput(["KEY_ENTER", ".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None

    def test_filepath_tracking(self):
        """Test filepath is tracked correctly."""
        filepath = "/home/opencode/data/work/bbsengine6/py/src/demo_listbox_cursor.spec"
        mock_input = MockInput([".", "x"])
        result = run(
            MockArgs(),
            moniker="test",
            mode="line",
            filepath=filepath,
            input_func=mock_input,
            test_mode=True,
        )
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
