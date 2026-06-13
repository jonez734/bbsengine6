# line/__init__.py
# Line editor mode - Image BBS-style line-based editor

from typing import Callable

from ..common import (
    create_editor_state,
    load_file,
    save_file,
    get_content,
    init_screen,
    register_bottombar,
    unregister_bottombar,
    unregister_common_handlers,
    register_common_handlers,
    BufferLine,
)


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

    from bbsengine6 import io

    width = io.terminal.width() if not test_mode else 80
    height = io.terminal.height() if not test_mode else 15

    state = create_editor_state(
        filepath=filepath, width=width, height=height, test_mode=test_mode
    )

    if filepath:
        state.buffer = load_file(filepath)

    if len(state.buffer.lines) == 0:
        state.buffer.lines.append(BufferLine(text=""))

    if not test_mode:
        register_bottombar(state)

    try:

        def get_input() -> str | None:
            if input_func is not None:
                return input_func()
            return io.getch(timeout=None)

        def prompt_line(prompt_str: str = "") -> str:
            if test_mode:
                result = get_input()
                if result and result != "KEY_ENTER":
                    return result
                return ""
            return io.inputstring(prompt_str)

        def prompt_integer(prompt_str: str) -> int:
            if test_mode:
                result = get_input()
                if result:
                    try:
                        return int(result)
                    except ValueError:
                        return 0
                return 0
            return io.inputinteger(prompt_str)

        def display_lines(start: int = 0, end: int | None = None) -> None:
            if end is None:
                end = len(state.buffer.lines)
            for i in range(start, min(end, len(state.buffer.lines))):
                line = state.buffer.lines[i]
                text = line.text
                if text.endswith("{f6}"):
                    text = text[:-3]
                io.echo(f"{i + 1}: {text}")

        def display_page(start: int, page_size: int) -> bool:
            end = start + page_size
            display_lines(start, end)
            has_more = end < len(state.buffer.lines)
            return has_more

        def show_help() -> None:
            io.echo("{clear}")
            io.echo("{bold}Line Editor Commands:{normal}")
            io.echo(".h - Help")
            io.echo(".e - Edit line")
            io.echo(".x - Exit")
            io.echo(".s - Save")
            io.echo(".l - List lines")
            io.echo(".i - Insert line")
            io.echo(".d - Delete line(s)")
            io.echo(".r - Read file")
            io.echo(".n - New (clear buffer)")
            io.echo("")
            io.echo("Enter line number to edit that line")
            io.echo("Press {bold}KEY_ENTER{normal} to add new line")
            if not test_mode:
                io.getch()

        def do_list() -> None:
            io.echo("{clear}")
            if len(state.buffer.lines) == 0:
                io.echo("(empty)")
            else:
                display_lines()
            io.echo("")
            io.echo(f"[{len(state.buffer.lines)} lines]")

        def do_save() -> bool:
            if state.filepath is None:
                prompt = prompt_line("Save. filename: ")
                if not prompt:
                    io.echo("Save cancelled")
                    return False
                state.filepath = prompt

            if save_file(state):
                io.echo(f"Saved: {state.filepath}")
                return True
            else:
                io.echo("Save failed")
                return False

        def do_read() -> None:
            prompt = prompt_line("Read. filename: ")
            if not prompt:
                io.echo("Read cancelled")
                return
            new_buffer = load_file(prompt)
            if len(new_buffer.lines) == 0 and prompt:
                io.echo("File not found or empty")
                return
            state.buffer = new_buffer
            state.filepath = prompt
            state.modified = False
            io.echo(f"Read {len(new_buffer.lines)} lines")

        def do_new() -> bool:
            if state.modified:
                io.echo("Buffer modified. Save first? (y/n)")
                ch = get_input()
                if ch and ch.lower() == "y":
                    if not do_save():
                        return False
            state.buffer.lines = [BufferLine(text="")]
            state.filepath = None
            state.modified = False
            io.echo("New buffer")
            return True

        def do_insert() -> None:
            prompt = prompt_integer("Insert at line: ")
            if prompt <= 0 or prompt > len(state.buffer.lines) + 1:
                io.echo("Invalid line number")
                return

            insert_idx = prompt - 1
            state.buffer.lines.insert(insert_idx, BufferLine(text=""))
            state.modified = True
            io.echo(f"Inserted at line {prompt}")

        def do_delete() -> None:
            if len(state.buffer.lines) == 0:
                io.echo("Nothing to delete")
                return

            prompt = prompt_line("Delete line(s): ")
            if not prompt:
                io.echo("Delete cancelled")
                return

            if "-" in prompt:
                parts = prompt.split("-")
                if len(parts) == 2:
                    try:
                        start = int(parts[0]) - 1
                        end = int(parts[1])
                        if 0 <= start < end <= len(state.buffer.lines):
                            del state.buffer.lines[start:end]
                            state.modified = True
                            io.echo(f"Deleted lines {start + 1}-{end}")
                        else:
                            io.echo("Invalid range")
                    except ValueError:
                        io.echo("Invalid range")
            else:
                try:
                    line_num = int(prompt) - 1
                    if 0 <= line_num < len(state.buffer.lines):
                        del state.buffer.lines[line_num]
                        state.modified = True
                        io.echo(f"Deleted line {line_num + 1}")
                    else:
                        io.echo("Invalid line number")
                except ValueError:
                    io.echo("Invalid input")

        def do_edit(line_num: int | None = None) -> None:
            if line_num is None:
                prompt = prompt_integer("Edit line: ")
            else:
                prompt = line_num

            if prompt <= 0 or prompt > len(state.buffer.lines):
                io.echo("Invalid line number")
                return

            edit_idx = prompt - 1
            current_text = state.buffer.lines[edit_idx].text
            if current_text.endswith("{f6}"):
                current_text = current_text[:-3]

            io.echo(f"{prompt}: {current_text}")

            new_text = prompt_line("New text: ")
            if new_text is not None:
                state.buffer.lines[edit_idx].text = new_text
                state.modified = True
                io.echo(f"Line {prompt} updated")

        def process_command(cmd: str) -> bool:
            cmd = cmd.lower()
            if cmd == "h":
                show_help()
                return True
            elif cmd == "x":
                if state.modified:
                    io.echo("File modified. Save? (y/n)")
                    ch = get_input()
                    if ch and ch.lower() == "y":
                        do_save()
                return False
            elif cmd == "s":
                do_save()
                return True
            elif cmd == "l":
                do_list()
                return True
            elif cmd == "r":
                do_read()
                return True
            elif cmd == "n":
                return do_new()
            elif cmd == "i":
                do_insert()
                return True
            elif cmd == "d":
                do_delete()
                return True
            elif cmd == "e":
                do_edit()
                return True
            else:
                io.echo(f"Unknown command: .{cmd}")
                io.echo("Use .h for help")
                return True

        running = True
        page_size = max(10, height - 6)

        while running:
            if not test_mode:
                io.echo("{clear}")
                display_page(0, page_size)

            io.echo("")
            if state.filepath:
                io.echo(
                    f"{{bold}}File:{{normal}} {state.filepath} {{bold}}Lines:{{normal}} {len(state.buffer.lines)}",
                    end="",
                )
            else:
                io.echo(
                    f"{{bold}}File:{{normal}} (new) {{bold}}Lines:{{normal}} {len(state.buffer.lines)}",
                    end="",
                )
            if state.modified:
                io.echo(" {bold}*modified*{normal}", end="")
            io.echo("")
            io.echo(
                "{bold}Enter line number, .command, or press KEY_ENTER for new line:{normal}"
            )

            ch = get_input()

            if ch is None:
                running = False
                break

            if ch == "KEY_F1" or ch == "?":
                show_help()
                continue

            if ch == "KEY_ENTER":
                state.buffer.lines.append(BufferLine(text=""))
                state.cursor_y = len(state.buffer.lines) - 1
                state.modified = True
                continue

            if ch == ".":
                io.echo("command: ", end="", flush=True)
                cmd = get_input()
                if cmd == "KEY_BACKSPACE":
                    io.echo("{eraseline}", end="", flush=True)
                    continue
                if cmd == "KEY_ENTER":
                    io.echo("{eraseline}", end="", flush=True)
                    continue
                if cmd:
                    io.echo(cmd, end="", flush=True)
                    io.echo("")
                    running = process_command(cmd)
                continue

            try:
                line_num = int(ch)
                if line_num > 0:
                    do_edit(line_num)
            except ValueError:
                io.echo(f"Invalid input: {repr(ch)}")
                io.echo("{bell}", end="", flush=True)

    finally:
        if not test_mode:
            io.echo("{clear}", end="", flush=True)
            unregister_bottombar()
        unregister_common_handlers()

    return get_content(state)
