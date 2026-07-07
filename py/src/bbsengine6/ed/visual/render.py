# visual/render.py
# Visual editor rendering

from bbsengine6 import io
from bbsengine6 import bottombar

from ..common import EditorState, Justify


def render_line(line_num: int, group_id: int | None, soft_wrap: bool, text: str) -> str:
    if group_id is None:
        prefix = f"{line_num + 1}: "
    elif soft_wrap:
        continuation = chr(ord("a") + (line_num - group_id))
        prefix = f"{group_id}{continuation}: "
    else:
        prefix = f"{group_id}: "

    return prefix + text


def apply_justify(text: str, justify: Justify, width: int) -> str:
    text = text.replace("{f6}", "")

    if justify == Justify.CENTER:
        return text.center(width)
    elif justify == Justify.RIGHT:
        return text.rjust(width)
    else:
        return text.ljust(width)


def render(state: EditorState, **kwargs) -> None:
    io.echo("{clear}", end="", flush=True)

    display_width = state.width

    start_line = state.scroll_offset
    end_line = min(start_line + state.height - 1, len(state.buffer.lines))

    for i in range(start_line, end_line):
        line = state.buffer.lines[i]
        display_line = render_line(
            i,
            line.group_id,
            line.soft_wrap,
            line.text,
        )
        display_line = apply_justify(display_line, line.justify, display_width)
        io.echo(display_line)

    for _ in range(state.height - (end_line - start_line)):
        io.echo(" " * display_width)

    cursor_y = state.cursor_y - state.scroll_offset + 1
    cursor_x = state.cursor_x + 2

    io.echo(
        f"{{curpos:{cursor_y},{cursor_x}}}",
        end="",
        flush=True,
    )

    bottombar.setbottombar(kwargs.get("args"), "editor", state=state)
