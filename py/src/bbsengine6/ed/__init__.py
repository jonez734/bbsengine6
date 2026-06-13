# ed/__init__.py
# Terminal-based visual editor package

from typing import Callable

from .common import (
    Justify,
    BufferLine,
    EditorBuffer,
    EditorState,
    create_editor_state,
    load_file,
    save_file,
    get_content,
    init_screen,
    show_help,
    show_notifications,
    exit_prompt,
    register_bottombar,
    unregister_bottombar,
    handle_key,
    set_editor_state,
    unregister_common_handlers,
)


def run(
    args,
    moniker,
    mode: str = "visual",
    filepath: str | None = None,
    input_func: Callable[[], str | None] | None = None,
    test_mode: bool = False,
) -> str | None:
    if mode == "visual":
        from .visual import run as visual_run

        return visual_run(args, moniker, filepath, input_func, test_mode)
    elif mode == "line":
        from .line import run as line_run

        return line_run(args, moniker, filepath, input_func, test_mode)
    else:
        raise ValueError(f"Unknown editor mode: {mode}")


def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs) -> None:
    return None


def help(**kw) -> None:
    show_help()


def main(args, **kw) -> bool:
    kind = kw.get("kind", "visual")
    filepath = kw.get("filepath")
    moniker = kw.get("moniker")

    result = run(args, moniker, mode=kind, filepath=filepath)
    return result is not None


__all__ = [
    "Justify",
    "BufferLine",
    "EditorBuffer",
    "EditorState",
    "create_editor_state",
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
    "unregister_common_handlers",
    "run",
    "init",
    "access",
    "buildargs",
    "help",
    "main",
]
