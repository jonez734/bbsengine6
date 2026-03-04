from .echo import echo
from .getch import getch_str as getch


def getstr(prompt: str = "") -> str:
    """Read a string from the user with full line editing support and insert/overwrite indicator."""
    buf: list[str] = []
    cursor = 0
    insert_mode = True

    # Print the prompt
    if prompt:
        echo(prompt, end="", flush=True)

    # Save cursor position (start of input)
    echo("{decsc}", end="", flush=True)

    def update_bottombar():
        nonlocal insert_mode
#        setbottombar("io_demo_getstr", "[INS]" if insert_mode else "[OVR]")

    def draw_line():
        """Redraw the buffer and insert/overwrite indicator with proper cursor positioning."""
        mode = "[INS]" if insert_mode else "[OVR]"
        total_len = len(buf) + len(mode)  # full string length including indicator

        # Move to start of input
        echo("{decrc}", end="", flush=True)

        # Print the buffer
        echo("".join(buf), end="", flush=True)

        # Print insert/overwrite indicator
        echo(f" {mode}", end="", flush=True)

        # Move cursor back to logical position within buffer
        if cursor < len(buf):
            n = len(buf) - cursor
            echo(f"{{cursorleft:{n + len(mode) + 1}}}", end="", flush=True)

    draw_line()  # initial draw
    update_bottombar()

    while True:
        key = getch()
        if key is None:
            continue

        if key in ("\r", "\n", "KEY_ENTER"):
            echo("{f6}", end="", flush=True)
            return "".join(buf)

        elif key == "KEY_BACKSPACE":
            if cursor > 0:
                del buf[cursor - 1]
                cursor -= 1
                echo("{cursorleft}", end="", flush=True)
                draw_line()

#        elif key == "KEY_DC":
#            if cursor < len(buf):
#                del buf[cursor]
#                draw_line()

        elif key == "KEY_LEFT":
            if cursor > 0:
                cursor -= 1
                echo("{cursorleft}", end="", flush=True)

        elif key == "KEY_RIGHT":
            if cursor < len(buf):
                cursor += 1
                echo("{cursorright}", end="", flush=True)

        elif key == "KEY_HOME":
            if cursor > 0:
                echo(f"{{cursorleft:{cursor}}}", end="", flush=True)
                cursor = 0

        elif key == "KEY_END":
            if cursor < len(buf):
                n = len(buf) - cursor
                echo(f"{{cursorright:{n}}}", end="", flush=True)
                cursor = len(buf)

        elif key == "KEY_IC":  # Insert toggle
            insert_mode = not insert_mode
            draw_line()  # update indicator

        else:
            if insert_mode or cursor == len(buf):
                buf.insert(cursor, key)
            else:  # overwrite mode
                buf[cursor] = key
            echo(key, end="", flush=True)
            cursor += 1
#            draw_line()
