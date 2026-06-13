# keys.py
# Key registry and common handlers for the editor
# Uses inputstring.KEY_ACTIONS registry with wrapper functions

from bbsengine6 import io
from bbsengine6.io.inputstring import add_key_mapping, remove_key_mapping

from .state import EditorState
from . import buffer, ui


_editor_state_ref: EditorState | None = None
_registered_keys: list[str] = []


def set_editor_state(state: EditorState) -> None:
    global _editor_state_ref
    _editor_state_ref = state


def get_editor_state() -> EditorState | None:
    return _editor_state_ref


def handle_key(ch: str | None, state: EditorState) -> EditorState:
    global _editor_state_ref
    _editor_state_ref = state

    if ch is None:
        return state

    if state.ctrl_k_mode:
        if ch.lower() == "x":
            if ui.exit_prompt(state):
                state.cursor_y = -1
        else:
            io.echo("{bell}", end="", flush=True)
            state.ctrl_k_mode = False
        return state

    from bbsengine6.io.inputstring import KEY_ACTIONS

    handler = KEY_ACTIONS.get(ch)
    if handler is not None:
        handlers = [handler] if callable(handler) else handler
        for h in handlers:
            try:
                result = h(
                    state.buffer.lines[state.cursor_y].text
                    if state.cursor_y < len(state.buffer.lines)
                    else "",
                    state.cursor_x,
                    state.scroll_offset,
                    state.width,
                )
                if result is not None:
                    if len(result) >= 3:
                        new_buffer, new_curpos, new_scroll = result[:3]
                        if state.cursor_y < len(state.buffer.lines):
                            state.buffer.lines[state.cursor_y].text = new_buffer
                        state.cursor_x = new_curpos
                        state.scroll_offset = new_scroll
            except Exception:
                pass

    if len(ch) == 1:
        return buffer.insert_char(state, ch)

    return state


def _wrapper_f1(buffer: str, curpos: int, scroll_offset: int, max_width: int) -> tuple:
    ui.show_help()
    io.getch()
    return (buffer, curpos, scroll_offset)


def _wrapper_f2(buffer: str, curpos: int, scroll_offset: int, max_width: int) -> tuple:
    try:
        from bbsengine6.member import _threadlocal

        moniker = getattr(_threadlocal, "moniker", None)
    except Exception:
        moniker = None

    ui.show_notifications(moniker)
    io.getch()
    return (buffer, curpos, scroll_offset)


def _wrapper_ctrl_k(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> tuple:
    state = get_editor_state()
    if state:
        state.ctrl_k_mode = not state.ctrl_k_mode
    return (buffer, curpos, scroll_offset)


def register_common_handlers() -> None:
    global _registered_keys

    handlers = [
        ("KEY_F1", _wrapper_f1),
        ("KEY_F2", _wrapper_f2),
        ("KEY_CTRL_K", _wrapper_ctrl_k),
    ]

    for key, handler in handlers:
        add_key_mapping(key, handler)
        _registered_keys.append(key)


def unregister_common_handlers() -> None:
    global _registered_keys

    for key in _registered_keys:
        remove_key_mapping(key)

    _registered_keys = []
