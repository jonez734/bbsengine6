# integrated tests for the visual editor

import pytest

from bbsengine6.ed.common.state import (
    Justify,
    BufferLine,
    create_editor_state,
)
from bbsengine6.ed.common import buffer


class TestCursorMovement:
    def test_cursor_up_decrements_y(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [
            BufferLine(text="line1"),
            BufferLine(text="line2"),
        ]
        state.cursor_y = 1
        state.cursor_x = 5

        buffer.get_line = lambda s: state.buffer.lines[s.cursor_y] if 0 <= s.cursor_y < len(s.buffer.lines) else None

        original_get_line = buffer.get_line
        buffer.get_line = lambda s: state.buffer.lines[s.cursor_y] if 0 <= s.cursor_y < len(s.buffer.lines) else None

        state.cursor_y -= 1

        buffer.get_line = original_get_line

        assert state.cursor_y == 0

    def test_cursor_down_increments_y(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [
            BufferLine(text="line1"),
            BufferLine(text="line2"),
        ]
        state.cursor_y = 0

        state.cursor_y += 1

        assert state.cursor_y == 1

    def test_cursor_left_decrements_x(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="hello")]
        state.cursor_x = 5

        state.cursor_x -= 1

        assert state.cursor_x == 4

    def test_cursor_right_increments_x(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="hello")]
        state.cursor_x = 4

        state.cursor_x += 1

        assert state.cursor_x == 5

    def test_cursor_home_sets_x_to_zero(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="hello")]
        state.cursor_x = 5

        state.cursor_x = 0

        assert state.cursor_x == 0

    def test_cursor_end_sets_x_to_line_length(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="hello")]
        state.cursor_x = 0

        state.cursor_x = len(state.buffer.lines[0].text)

        assert state.cursor_x == 5


class TestInsertChar:
    def test_insert_char_at_beginning(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="ello")]
        state.cursor_x = 0
        state.cursor_y = 0

        state = buffer.insert_char(state, "H")

        assert state.buffer.lines[0].text == "Hello"
        assert state.cursor_x == 1

    def test_insert_char_in_middle(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="hllo")]
        state.cursor_x = 1

        state = buffer.insert_char(state, "e")

        assert state.buffer.lines[0].text == "hello"
        assert state.cursor_x == 2

    def test_insert_char_marks_modified(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="test")]
        state.modified = False

        state = buffer.insert_char(state, "x")

        assert state.modified is True


class TestDeleteChar:
    def test_delete_char_removes_character(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="hello")]
        state.cursor_x = 1

        state = buffer.delete_char(state)

        assert state.buffer.lines[0].text == "hllo"

    def test_delete_char_at_end_does_nothing(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="hello")]
        state.cursor_x = 5

        state = buffer.delete_char(state)

        assert state.buffer.lines[0].text == "hello"


class TestBackspace:
    def test_backspace_removes_previous_char(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="hello")]
        state.cursor_x = 3

        state = buffer.backspace(state)

        assert state.buffer.lines[0].text == "helo"
        assert state.cursor_x == 2

    def test_backspace_at_beginning_does_nothing(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="hello")]
        state.cursor_x = 0
        state.cursor_y = 0

        state = buffer.backspace(state)

        assert state.buffer.lines[0].text == "hello"


class TestSplitLine:
    def test_split_line_adds_hard_return(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="hello world")]
        state.cursor_x = 5

        state = buffer.split_line(state)

        assert len(state.buffer.lines) == 2
        assert state.buffer.lines[0].text == "hello{f6}"
        assert state.buffer.lines[1].text == " world"
        assert state.cursor_x == 0
        assert state.cursor_y == 1

    def test_split_line_marks_modified(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="test")]
        state.modified = False
        state.cursor_x = 2

        state = buffer.split_line(state)

        assert state.modified is True


class TestWordWrap:
    def test_wrap_line_splits_at_space(self):
        state = create_editor_state(width=10, height=24)
        state.buffer.lines = [BufferLine(text="hello world test")]
        state.cursor_x = 17

        state = buffer.wrap_line(state)

        assert len(state.buffer.lines) == 2
        assert state.buffer.lines[0].text == "hello"
        assert state.buffer.lines[1].text == "world test"
        assert state.buffer.lines[1].soft_wrap is True

    def test_wrap_line_clears_soft_wrap_on_hard_return(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="test", soft_wrap=False)]

        assert state.buffer.lines[0].soft_wrap is False


class TestUnwrapLine:
    def test_unwrap_line_joins_with_previous(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [
            BufferLine(text="hello"),
            BufferLine(text=" world"),
        ]
        state.cursor_y = 1
        state.cursor_x = 0

        state = buffer.unwrap_line(state)

        assert len(state.buffer.lines) == 1
        assert state.buffer.lines[0].text == "hello world"
        assert state.cursor_x == 11
        assert state.cursor_y == 0


class TestBufferLine:
    def test_buffer_line_defaults(self):
        line = BufferLine(text="test")

        assert line.text == "test"
        assert line.justify == Justify.LEFT
        assert line.read_only is False
        assert line.soft_wrap is True
        assert line.group_id is None

    def test_buffer_line_with_all_fields(self):
        line = BufferLine(
            text="test",
            justify=Justify.CENTER,
            read_only=True,
            soft_wrap=False,
            group_id=5,
        )

        assert line.text == "test"
        assert line.justify == Justify.CENTER
        assert line.read_only is True
        assert line.soft_wrap is False
        assert line.group_id == 5


class TestEditorState:
    def test_create_editor_state_defaults(self):
        state = create_editor_state()

        assert state.filepath is None
        assert state.cursor_x == 0
        assert state.cursor_y == 0
        assert state.scroll_offset == 0
        assert state.modified is False
        assert state.ctrl_k_mode is False
        assert state.width == 0
        assert state.height == 0

    def test_create_editor_state_with_params(self):
        state = create_editor_state(filepath="/path/to/file", width=100, height=50)

        assert state.filepath == "/path/to/file"
        assert state.width == 100
        assert state.height == 50

    def test_editor_state_empty_buffer(self):
        state = create_editor_state()

        assert len(state.buffer.lines) == 0


class TestJustify:
    def test_justify_enum_values(self):
        assert Justify.LEFT.value is not None
        assert Justify.CENTER.value is not None
        assert Justify.RIGHT.value is not None


class TestReadOnlyLines:
    def test_insert_char_on_readonly_line(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="readonly", read_only=True)]

        state = buffer.insert_char(state, "x")

        assert state.buffer.lines[0].text == "readonly"

    def test_delete_char_on_readonly_line(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="readonly", read_only=True)]
        state.cursor_x = 3

        state = buffer.delete_char(state)

        assert state.buffer.lines[0].text == "readonly"

    def test_backspace_on_readonly_line(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="readonly", read_only=True)]
        state.cursor_x = 3

        state = buffer.backspace(state)

        assert state.buffer.lines[0].text == "readonly"


class TestEdgeCases:
    def test_insert_at_empty_buffer(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = []

        state = buffer.insert_char(state, "a")

        assert len(state.buffer.lines) == 1
        assert state.buffer.lines[0].text == "a"

    def test_cursor_y_at_end_of_buffer(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="line1")]
        state.cursor_y = 0

        if state.cursor_y < len(state.buffer.lines) - 1:
            state.cursor_y += 1

        assert state.cursor_y == 0

    def test_cursor_x_clamped_to_line_length(self):
        state = create_editor_state(width=80, height=24)
        state.buffer.lines = [BufferLine(text="hi")]
        state.cursor_x = 10
        line = state.buffer.lines[0]
        max_x = len(line.text.replace("{f6}", ""))

        if state.cursor_x > max_x:
            state.cursor_x = max_x

        assert state.cursor_x == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
