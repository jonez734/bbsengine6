# visual/keys.py
# Visual editor specific key handlers
# Uses inputstring.KEY_ACTIONS registry with wrapper functions

from bbsengine6.io.inputstring import add_key_mapping, remove_key_mapping

from ..common import get_editor_state
from ..common import buffer as buffer_module


_registered_keys: list[str] = []


def _wrapper_up(buffer: str, curpos: int, scroll_offset: int, max_width: int) -> tuple:
    state = get_editor_state()
    if state and state.cursor_y > 0:
        state.cursor_y -= 1
        if state.cursor_x > 0:
            line = buffer_module.get_line(state)
            if line:
                max_x = len(line.text.replace("{f6}", ""))
                if state.cursor_x > max_x:
                    state.cursor_x = max_x
    return (buffer, curpos, scroll_offset)


def _wrapper_down(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> tuple:
    state = get_editor_state()
    if state and state.cursor_y < len(state.buffer.lines) - 1:
        state.cursor_y += 1
        if state.cursor_x > 0:
            line = buffer_module.get_line(state)
            if line:
                max_x = len(line.text.replace("{f6}", ""))
                if state.cursor_x > max_x:
                    state.cursor_x = max_x
    return (buffer, curpos, scroll_offset)


def _wrapper_left(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> tuple:
    state = get_editor_state()
    if state:
        if state.cursor_x > 0:
            state.cursor_x -= 1
        elif state.cursor_y > 0:
            state = buffer_module.unwrap_line(state)
    return (buffer, state.cursor_x if state else curpos, scroll_offset)


def _wrapper_right(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> tuple:
    state = get_editor_state()
    if state:
        line = buffer_module.get_line(state)
        if line:
            max_x = len(line.text.replace("{f6}", ""))
            if state.cursor_x < max_x:
                state.cursor_x += 1
            elif state.cursor_x >= state.width - 1:
                state = buffer_module.wrap_line(state)
    return (buffer, state.cursor_x if state else curpos, scroll_offset)


def _wrapper_home(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> tuple:
    state = get_editor_state()
    if state:
        state.cursor_x = 0
    return (buffer, 0, scroll_offset)


def _wrapper_end(buffer: str, curpos: int, scroll_offset: int, max_width: int) -> tuple:
    state = get_editor_state()
    if state:
        line = buffer_module.get_line(state)
        if line:
            state.cursor_x = len(line.text.replace("{f6}", ""))
    return (buffer, state.cursor_x if state else curpos, scroll_offset)


def _wrapper_pageup(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> tuple:
    state = get_editor_state()
    if state:
        state.scroll_offset = max(0, state.scroll_offset - state.height)
        state.cursor_y = max(0, state.cursor_y - state.height)
    return (buffer, curpos, scroll_offset)


def _wrapper_pagedown(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> tuple:
    state = get_editor_state()
    if state:
        max_scroll = len(state.buffer.lines) - state.height
        state.scroll_offset = max(
            0, min(max_scroll, state.scroll_offset + state.height)
        )
        state.cursor_y = min(len(state.buffer.lines) - 1, state.cursor_y + state.height)
    return (buffer, curpos, scroll_offset)


def _wrapper_backspace(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> tuple:
    state = get_editor_state()
    if state:
        state = buffer_module.backspace(state)
        if state.cursor_y < len(state.buffer.lines):
            return (state.buffer.lines[state.cursor_y].text, state.cursor_x, state.scroll_offset)
    return (buffer, curpos, scroll_offset)


def _wrapper_delete(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> tuple:
    state = get_editor_state()
    if state:
        state = buffer_module.delete_char(state)
        if state.cursor_y < len(state.buffer.lines):
            return (state.buffer.lines[state.cursor_y].text, state.cursor_x, state.scroll_offset)
    return (buffer, curpos, scroll_offset)


def _wrapper_enter(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> tuple:
    state = get_editor_state()
    if state:
        state = buffer_module.split_line(state)
    return (buffer, curpos, scroll_offset)


def register_visual_handlers() -> None:
    global _registered_keys

    handlers = [
        ("KEY_UP", _wrapper_up),
        ("KEY_DOWN", _wrapper_down),
        ("KEY_LEFT", _wrapper_left),
        ("KEY_RIGHT", _wrapper_right),
        ("KEY_HOME", _wrapper_home),
        ("KEY_END", _wrapper_end),
        ("KEY_PAGEUP", _wrapper_pageup),
        ("KEY_PAGEDOWN", _wrapper_pagedown),
        ("KEY_BACKSPACE", _wrapper_backspace),
        ("KEY_DELETE", _wrapper_delete),
        ("KEY_ENTER", _wrapper_enter),
    ]

    for key, handler in handlers:
        add_key_mapping(key, handler)
        _registered_keys.append(key)


def unregister_visual_handlers() -> None:
    global _registered_keys

    for key in _registered_keys:
        remove_key_mapping(key)

    _registered_keys = []
