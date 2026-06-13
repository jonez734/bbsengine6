# buffer.py
# Buffer manipulation functions for the editor

from .state import EditorState, BufferLine


def get_line(state: EditorState, **kwargs) -> BufferLine | None:
    if 0 <= state.cursor_y < len(state.buffer.lines):
        return state.buffer.lines[state.cursor_y]
    return None


def get_line_text(state: EditorState, **kwargs) -> str:
    line = get_line(state)
    if line is None:
        return ""
    return line.text


def ensure_line_exists(state: EditorState, **kwargs) -> EditorState:
    if state.cursor_y >= len(state.buffer.lines):
        state.buffer.lines.append(BufferLine(text=""))
    return state


def insert_char(state: EditorState, char: str, **kwargs) -> EditorState:
    if state.cursor_y >= len(state.buffer.lines):
        state = ensure_line_exists(state)

    line = state.buffer.lines[state.cursor_y]
    if line.read_only:
        return state

    text = line.text
    before = text[: state.cursor_x]
    after = text[state.cursor_x :]
    line.text = before + char + after
    state.cursor_x += 1
    state.modified = True

    if line.soft_wrap:
        state = recalculate_wrap(state, state.cursor_y)

    if state.cursor_x >= state.width:
        state = wrap_line(state)

    return state


def delete_char(state: EditorState, **kwargs) -> EditorState:
    if state.cursor_y >= len(state.buffer.lines):
        return state

    line = state.buffer.lines[state.cursor_y]
    if line.read_only:
        return state

    text = line.text
    if state.cursor_x < len(text):
        before = text[: state.cursor_x]
        after = text[state.cursor_x + 1 :]
        line.text = before + after
        state.modified = True

        if line.soft_wrap:
            state = recalculate_wrap(state, state.cursor_y)

    return state


def backspace(state: EditorState, **kwargs) -> EditorState:
    if state.cursor_y >= len(state.buffer.lines):
        return state

    line = state.buffer.lines[state.cursor_y]
    if line.read_only:
        return state

    if state.cursor_x == 0:
        if state.cursor_y > 0:
            state = unwrap_line(state)
        return state

    text = line.text
    before = text[: state.cursor_x - 1]
    after = text[state.cursor_x :]
    line.text = before + after
    state.cursor_x -= 1
    state.modified = True

    if line.soft_wrap:
        state = recalculate_wrap(state, state.cursor_y)

    return state


def wrap_line(state: EditorState, **kwargs) -> EditorState:
    if state.cursor_y >= len(state.buffer.lines):
        return state

    line = state.buffer.lines[state.cursor_y]
    if line.read_only:
        return state

    text = line.text
    if len(text) == 0:
        return state

    width = state.width - 4
    if width <= 0:
        width = 80

    last_space = -1
    for i in range(len(text)):
        if text[i] == " ":
            last_space = i
        if i >= width:
            break

    if last_space == -1:
        return state

    before = text[:last_space]
    after = text[last_space + 1 :]

    line.text = before

    group_id = line.group_id
    if group_id is None:
        group_id = state.cursor_y + 1

    new_line = BufferLine(
        text=after,
        justify=line.justify,
        read_only=False,
        soft_wrap=True,
        group_id=group_id,
    )

    state.buffer.lines.insert(state.cursor_y + 1, new_line)
    state.cursor_x = 0
    state.cursor_y += 1
    state.modified = True

    return state


def unwrap_line(state: EditorState, **kwargs) -> EditorState:
    if state.cursor_y == 0:
        return state

    current_line = state.buffer.lines[state.cursor_y]
    prev_line = state.buffer.lines[state.cursor_y - 1]

    if current_line.read_only or prev_line.read_only:
        return state

    prev_line.text += current_line.text
    state.buffer.lines.pop(state.cursor_y)

    state.cursor_y -= 1
    state.cursor_x = len(prev_line.text)
    state.modified = True

    state = recalculate_wrap(state, state.cursor_y)

    return state


def split_line(state: EditorState, **kwargs) -> EditorState:
    if state.cursor_y >= len(state.buffer.lines):
        state = ensure_line_exists(state)

    line = state.buffer.lines[state.cursor_y]
    if line.read_only:
        return state

    text = line.text
    before = text[: state.cursor_x] + "{f6}"
    after = text[state.cursor_x :]

    line.text = before

    group_id = line.group_id
    if group_id is None:
        group_id = state.cursor_y + 1

    new_line = BufferLine(
        text=after,
        justify=line.justify,
        read_only=False,
        soft_wrap=False,
        group_id=group_id,
    )

    state.buffer.lines.insert(state.cursor_y + 1, new_line)
    state.cursor_x = 0
    state.cursor_y += 1
    state.modified = True

    return state


def recalculate_wrap(state: EditorState, line_index: int, **kwargs) -> EditorState:
    if line_index >= len(state.buffer.lines):
        return state

    line = state.buffer.lines[line_index]
    if not line.soft_wrap:
        return state

    group_id = line.group_id
    if group_id is None:
        group_id = line_index + 1

    width = state.width - 4
    if width <= 0:
        width = 80

    end_idx = line_index + 1
    while end_idx < len(state.buffer.lines):
        next_line = state.buffer.lines[end_idx]
        if next_line.group_id != group_id or not next_line.soft_wrap:
            break
        end_idx += 1

    return state
