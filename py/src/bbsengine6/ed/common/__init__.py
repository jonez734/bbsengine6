# common/__init__.py
# Shared code for all editor modes

from .state import (
    Justify,
    BufferLine,
    EditorBuffer,
    EditorState,
    create_editor_state,
)
from .buffer import (
    get_line,
    get_line_text,
    ensure_line_exists,
    insert_char,
    delete_char,
    backspace,
    wrap_line,
    unwrap_line,
    split_line,
    recalculate_wrap,
)
from .fileops import load_file, save_file, get_content
from .ui import (
    init_screen,
    show_help,
    show_notifications,
    exit_prompt,
    register_bottombar,
    unregister_bottombar,
)
from .keys import (
    handle_key,
    set_editor_state,
    get_editor_state,
    unregister_common_handlers,
    register_common_handlers,
)

__all__ = [
    "Justify",
    "BufferLine",
    "EditorBuffer",
    "EditorState",
    "create_editor_state",
    "get_line",
    "get_line_text",
    "ensure_line_exists",
    "insert_char",
    "delete_char",
    "backspace",
    "wrap_line",
    "unwrap_line",
    "split_line",
    "recalculate_wrap",
    "load_file",
    "save_file",
    "get_content",
    "init_screen",
    "show_help",
    "show_notifications",
    "exit_prompt",
    "register_bottombar",
    "unregister_bottombar",
    "handle_key",
    "set_editor_state",
    "get_editor_state",
    "unregister_common_handlers",
    "register_common_handlers",
]
