# ui.py
# Shared UI functions for the editor


from bbsengine6 import io
from bbsengine6 import bottombar

from .state import EditorState


_screen_initialized = False


# Per-editor fragment tracking. unregister_bottombar() unregisters only
# the fragments this module registered so casino / empyre / etc. bottombar
# state is not clobbered on editor exit.
_editor_fragments: list = []


def init_screen() -> None:
    global _screen_initialized
    if not _screen_initialized:
        io.screen.init()
        _screen_initialized = True


def show_help() -> None:
    io.echo("{clear}")
    io.echo("{bold}Editor Help{/bold}")
    io.echo("")
    io.echo("Arrow keys     : Navigate")
    io.echo("Home/End       : Jump to line start/end")
    io.echo("Page Up/Down   : Scroll editor")
    io.echo("Enter          : Split line (hard return)")
    io.echo("Backspace      : Delete char / unwrap line")
    io.echo("Delete         : Delete char at cursor")
    io.echo("F1             : This help")
    io.echo("F2             : View messages")
    io.echo("Ctrl+K x       : Exit editor")
    io.echo("")
    io.echo("Press any key to continue...")


def show_notifications(moniker: str | None) -> None:
    if not moniker:
        return

    io.echo("{clear}")
    try:
        from bbsengine6.io.getch import _show_pending_notifications

        _show_pending_notifications(moniker)
    except Exception:
        io.echo("Notifications unavailable.")
        io.echo("Press any key to continue...")


def exit_prompt(state: EditorState, **kwargs) -> bool:
    if state.test_mode or not state.modified:
        return True

    io.echo("File modified. Save? (Y/n/c): ", end="", flush=True)
    ch = io.getch()
    io.echo("")

    if ch is None:
        return False

    ch_upper = ch.upper() if ch else ""

    if ch_upper == "Y":
        from . import fileops

        if fileops.save_file(state):
            return True
        return False
    elif ch_upper == "N":
        return True
    elif ch_upper == "C":
        return False

    return False


def editor_status_fragment(**kwargs) -> str:
    state: EditorState = kwargs.get("state")
    if state is None:
        return "Editor"

    name = state.filepath if state.filepath else "(new file)"
    prefix = "*" if state.modified else ""

    return f"{prefix}{name} | F1:Help"


def register_bottombar(state: EditorState, **kwargs) -> None:
    def fragment(**kwargs) -> str:
        return editor_status_fragment(state=state)

    bottombar.register_bottombar_fragment(fragment)
    _editor_fragments.append(fragment)


def unregister_bottombar() -> None:
    global _editor_fragments
    for fn in _editor_fragments:
        bottombar.unregister_bottombar_fragment(fn)
    _editor_fragments = []
