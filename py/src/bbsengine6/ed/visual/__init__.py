# visual/__init__.py
# Visual editor mode

from typing import Callable

from ..common import (
    create_editor_state,
    load_file,
    get_content,
    init_screen,
    register_bottombar,
    unregister_bottombar,
    handle_key,
    set_editor_state,
    unregister_common_handlers,
    register_common_handlers,
)
from . import render
from . import keys as visual_keys


def run(
    args,
    moniker,
    filepath: str | None = None,
    input_func: Callable[[], str | None] | None = None,
    test_mode: bool = False,
) -> str | None:
    if not test_mode:
        init_screen()
    register_common_handlers()
    visual_keys.register_visual_handlers()

    from bbsengine6.io import terminal

    width = terminal.width()
    height = terminal.lines()

    state = create_editor_state(filepath=filepath, width=width, height=height, test_mode=test_mode)

    if filepath:
        state.buffer = load_file(filepath)

    if len(state.buffer.lines) == 0:
        from ..common.state import BufferLine

        state.buffer.lines.append(BufferLine(text=""))

    if not test_mode:
        register_bottombar(state)

    try:
        from bbsengine6 import io

        def get_input() -> str | None:
            if input_func is not None:
                return input_func()
            return io.getch(timeout=None)

        while True:
            try:
                if not test_mode:
                    render.render(state)

                set_editor_state(state)

                ch = get_input()

                if ch is None:
                    break

                state = handle_key(ch, state)

                if state.cursor_y < 0:
                    break
            except (KeyboardInterrupt, EOFError):
                state.cursor_y = -1
                break
    finally:
        if not test_mode:
            io.echo("{clear}", end="", flush=True)
            unregister_bottombar()
        visual_keys.unregister_visual_handlers()
        unregister_common_handlers()

    return get_content(state)
