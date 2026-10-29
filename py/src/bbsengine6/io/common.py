import os
import re
import sys
import select
import tty
import fcntl
import termios
import threading
import collections
import time

from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional

from .const import ESC, CSI

from . import terminal

DEFAULT_INDENT_CHAR = " "


@dataclass
class Token:
    kind: str  # e.g., WORD, WHITESPACE, F6, RGB
    value: str = None  # the literal string or command
    args: List = field(default_factory=list)  # positional args
    kwargs: Dict = field(default_factory=dict)  # keyword args
    text: str = field(default="")  # {f6:3} -> \n*3, {home} -> \033[H, etc
    repeat: int = 1
    raw: Optional[str] = None  # raw input that generated this token

    def __repr__(self):
        parts = [self.kind]
        if self.value:
            parts.append(f"value={repr(self.value)}")  # repr(self.value))
        if self.args:
            parts.append(f"args={self.args}")
        if self.kwargs:
            parts.append(f"kwargs={self.kwargs}")
        if self.repeat:
            parts.append(f"repeat={self.repeat}")
        if self.text:
            parts.append(f"text={repr(self.text)}")
        if self.raw:
            parts.append(f"raw={repr(self.raw)}")
        return f"Token({', '.join(parts)})"


# _cursor_row = 1
# _cursor_col = 1

_current_input_stream = sys.stdin

_current_output_stream = sys.stdout

_current_stream_lock = threading.Lock()
_terminal_state_lock = threading.Lock()


def set_output_stream(stream):
    global _current_output_stream
    with _current_stream_lock:
        _current_output_stream = stream


def set_input_stream(stream):
    global _current_input_stream
    with _current_stream_lock:
        _current_input_stream = stream


_input_queue = collections.deque()
_input_queue_lock = threading.Lock()


def _read_current_input_stream(size: int = 1) -> str:
    with _input_queue_lock:
        if _input_queue:
            return _input_queue.popleft()
    return _current_input_stream.read(size)


def read_current_input_stream(size: int = 1) -> str:
    with _current_stream_lock:
        return _read_current_input_stream(size)


def _write_current_output_stream(s: str, flush=False):
    _current_output_stream.write(s)
    if flush:
        _current_output_stream.flush()


def write_current_output_stream(s: str, flush=False):
    with _current_stream_lock:
        return _write_current_output_stream(s, flush=flush)


# Set by a caller (inputstring) that holds the tty in raw mode for a whole prompt.
# While it is set, _getch_core leaves the tty mode alone: no raw switch, no restore
# between keys. Otherwise the line discipline echoes keys typed between reads.
_session_raw_fd: Optional[int] = None
_session_raw_settings: Optional[Any] = None


def begin_raw_session() -> None:
    """Put the input tty in raw mode and keep it there until end_raw_session().

    Restores nothing between getch() calls, so keys pressed between reads are
    never echoed. Safe to call when stdin is not a tty (then it is a no-op).
    """
    global _session_raw_fd, _session_raw_settings
    if _session_raw_fd is not None:
        return
    try:
        fd = _current_input_stream.fileno()
        settings = termios.tcgetattr(fd)
    except Exception:
        return  # not a terminal
    with _current_stream_lock:
        # Keys already typed are in the cooked line discipline; setraw() would
        # discard them. Queue them first, in arrival order.
        drain_stream_to_queue(_current_input_stream, _input_queue)
        tty.setraw(fd)
    _session_raw_fd = fd
    _session_raw_settings = settings


def end_raw_session() -> None:
    """Restore the tty mode saved by begin_raw_session()."""
    global _session_raw_fd, _session_raw_settings
    if _session_raw_fd is None:
        return
    try:
        termios.tcsetattr(_session_raw_fd, termios.TCSADRAIN, _session_raw_settings)
    except Exception:
        pass
    _session_raw_fd = None
    _session_raw_settings = None


def _restore_cooked(fd: int, old_settings: Any) -> None:
    """Return the tty to its pre-getch mode, unless a raw session owns it."""
    if _in_raw_session():
        return
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _in_raw_session() -> bool:
    return _session_raw_fd is not None

# --------------------------
# DSR (Device Status Report)
# --------------------------


def _read_terminal_response(terminator: str, timeout: float = 1.0) -> str | None:
    """
    Reads characters from the terminal until the specified terminator is received
    or the timeout expires, using a non-blocking select loop.
    """
    fd = _current_input_stream.fileno()

    # 1. Save and set terminal mode
    old_settings = termios.tcgetattr(fd)
    try:
        # Set to cbreak mode (raw-like, but includes signal processing)
        tty.setcbreak(fd)

        response = ""
        for _ in range(10):
            ch = os.read(fd, 1).decode(_current_input_stream.encoding)
            response += ch
            if ch == terminator:
                return response
    finally:
        # 3. Restore terminal settings
        _restore_cooked(fd, old_settings)


# Regex for DSR reply: ESC [ <row> ; <col> R
DSR_CURPOS_RE = re.compile(r"\x1b\[(\d+);(\d+)R")


def get_dsr(mode="curpos", timeout: float = 1.0) -> tuple[int, int] | str:
    """
    Query the terminal for cursor position (DSR) and return the response string.

    Sends ESC[6n and reads raw bytes until the terminating 'R' is received.
    Uses the global _current_stream_lock to prevent interleaved output.

    Args:
        timeout: Optional timeout in seconds for the DSR response.

    Returns:
        Decoded response string, e.g., '\x1b[12;40R'.

    Raises:
        TimeoutError if no complete response is received in time.
    """
    if mode == "curpos":
        code = "6"
    elif mode == "status":
        code = "5"
    else:
        raise ValueError

    # Hold lock only for setup/teardown, not during the full DSR exchange
    with _current_stream_lock:
        drain_stream_to_queue(_current_input_stream, _input_queue)
        fd = _current_input_stream.fileno()
        old_settings = termios.tcgetattr(fd)

    try:
        if not _in_raw_session():
            tty.setraw(fd)
        _write_current_output_stream(f"{ESC}[{code}n", flush=True)

        buffer = ""
        encoding = _current_input_stream.encoding or "utf-8"

        # Use select() for real timeout instead of fixed byte count.
        # Read whatever bytes arrive within the timeout window and look
        # for the DSR terminator ('R' for curpos / 'n' for status).
        terminator = "R" if mode == "curpos" else "n"

        deadline_loops = max(1, int(timeout * 20))  # 50ms polling slices
        while deadline_loops > 0:
            rlist, _, _ = select.select([fd], [], [], 0.05)
            if rlist:
                try:
                    chunk = os.read(fd, 64).decode(encoding, errors="replace")
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk
                if terminator in buffer:
                    break
            deadline_loops -= 1

        if mode == "curpos":
            match = DSR_CURPOS_RE.search(buffer)
            if match:
                row, col = map(int, match.groups())
                start, end = match.span()
                leftover = buffer[:start] + buffer[end:]
                with _input_queue_lock:
                    _input_queue.clear()
                    _input_queue.extend(leftover)
                return (row, col)
            raise TimeoutError(
                f"DSR response not received in {timeout}s: {buffer!r}"
            )
        return buffer
    finally:
        _restore_cooked(fd, old_settings)


##    write_current_output_stream(f"{CSI}{code}n", flush=True)
##    _current_output_stream.flush()
##    return _read_terminal_response(terminator)


def get_cursor_position(timeout: float = 1.0):
    """
    Return the current cursor position as (row, col) integers.

    Args:
        timeout: Optional timeout in seconds for DSR response.

    Returns:
        Tuple (row, col) of cursor position (1-based).

    Raises:
        ValueError if the response cannot be parsed.
        TimeoutError if no response is received in time.
    """
    return get_dsr("curpos", timeout=timeout)


##    # Expect something like: ESC [ row ; col R
##    if not resp.startswith(CSI) or not resp.endswith("R"):
##        raise ValueError(f"Unexpected DSR response: {resp!r}")
##
##    try:
##        body = resp[2:-1]   # strip ESC[ and trailing R
##        row_str, col_str = body.split(";")
##        return int(row_str), int(col_str)
##    except Exception as e:
##        raise ValueError(f"Failed to parse DSR response: {resp!r}") from e


def get_terminal_status():
    """Device Status (DECTST / terminal readiness)

    Query: ESC [ 5 n

    Response: ESC [ 0 n → OK, ESC [ 3 n → error
    """

    with _current_stream_lock:
        response = get_dsr("status")
        if (
            isinstance(response, str)
            and response.startswith(CSI)
            and response.endswith("n")
        ):
            part = int(response[2])
            if part == 0:
                return True
            elif part == 3:
                return False
            else:
                return None


def drain_stream_to_queue(stream, queue):
    """
    Read all available characters from `stream` and append them to `queue`.
    Stops when the stream would block.
    Works with stdin, stdout, or any file-like object with .fileno().
    """
    fd = stream.fileno()

    # Save current flags
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    try:
        # Set non-blocking
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        while True:
            try:
                #                print(BEL, flush=True, end="")
                ch = stream.read(1)
                if not ch:
                    break  # EOF or no more data
                # Cooked mode turns Enter (\r) into \n (ICRNL). Raw mode delivers \r,
                # which the key table maps to KEY_ENTER, so restore it here for
                # every key drained into the input queue.
                if ch == "\n" and queue is _input_queue:
                    ch = "\r"
                # Lock for _input_queue, otherwise assume caller handles it
                if queue is _input_queue:
                    with _input_queue_lock:
                        queue.append(ch)
                else:
                    queue.append(ch)
            except BlockingIOError:
                break  # would block → stop
    finally:
        # Restore original flags
        fcntl.fcntl(fd, fcntl.F_SETFL, fl)


# save/restore cursor attributes
@dataclass
class TerminalState:
    cursor_row: int = 1
    cursor_col: int = 1
    wordwrap: bool = True
    has_color: bool = True
    hidden: bool = False
    width: int = 100
    acs: bool = False
    raw: bool = False
    decdhl: bool = False  # double height
    decdwl: bool = False
    indent: int = 0
    indent_char: str = DEFAULT_INDENT_CHAR

    def __repr__(self):
        return f"TerminalState({self.cursor_row=}, {self.cursor_col=}, {self.wordwrap=}, {self.has_color=}, {self.hidden=}, {self.acs=}, {self.raw=})"


_terminal_state = TerminalState(
    cursor_row=terminal.lines(), cursor_col=terminal.columns()
)
_terminal_state_stack = []
_terminal_state_stack_enabled = False

_terminal_state_stack_lock = threading.Lock()

_input_dirty = False


def get_terminal_state():
    with _terminal_state_lock:
        return _terminal_state


def set_terminal_state(state: TerminalState):
    global _terminal_state
    with _terminal_state_lock:
        _terminal_state = state


# --------------------------
# Mouse reporting state (inputstring)
# --------------------------

# Mouse tracking modes that cause a terminal to capture click-drag selection.
MOUSE_MODES = (1000, 1002, 1003, 1006)

# Module flag: when False, inputstring() leaves the terminal's mouse state alone.
MOUSE_STATE_MANAGED = True

_DECRPM_RE = re.compile(r"\x1b\[\?(\d+);(\d)\$y")


def _query_mouse_modes(timeout: float = 0.5) -> dict[int, bool]:
    """Ask the terminal which mouse modes are set (DECRQM).

    Returns {mode: enabled}. A mode with no reply is reported as disabled,
    which is the fallback the restore logic relies on.
    """
    fd = _current_input_stream.fileno()
    with _current_stream_lock:
        drain_stream_to_queue(_current_input_stream, _input_queue)
        old_settings = termios.tcgetattr(fd)
    replies = ""
    try:
        if not _in_raw_session():
            tty.setraw(fd)
        for mode in MOUSE_MODES:
            _write_current_output_stream(f"{CSI}?{mode}$p", flush=True)
        # Read until every mode has answered AND the terminal has gone quiet.
        # Stopping on the fourth match alone can leave the batch's final bytes
        # in the stream, where they are read as keystrokes.
        deadline = time.time() + timeout
        quiet_until = None
        while time.time() < deadline:
            rlist, _, _ = select.select([fd], [], [], 0.02)
            if rlist:
                replies += os.read(fd, 256).decode("utf-8", errors="replace")
                quiet_until = None
                continue
            if len(_DECRPM_RE.findall(replies)) >= len(MOUSE_MODES):
                if quiet_until is None:
                    quiet_until = time.time() + 0.03
                elif time.time() >= quiet_until:
                    break
    finally:
        _restore_cooked(fd, old_settings)

    # None = the terminal did not answer for this mode (unknown, not "off").
    state = {mode: None for mode in MOUSE_MODES}
    for mode_s, status in _DECRPM_RE.findall(replies):
        mode = int(mode_s)
        if mode in state:
            state[mode] = status in ("1", "3")  # 1 = set, 3 = permanently set

    # Anything typed while the query ran is not a reply: keep it, in order, for
    # the reader. Replies are removed; the rest goes back onto the input queue.
    leftover = _DECRPM_RE.sub("", replies)
    if leftover:
        keys = ["\r" if c == "\n" else c for c in leftover]
        with _input_queue_lock:
            _input_queue.extend(keys)
    return state


def _write_mouse_modes(state: dict[int, bool | None], only_known: bool = False) -> None:
    """Set each mouse mode on or off to match state (h = on, l = off).

    A mode whose state is None (no reply) is left alone. With only_known=False
    every mode gets a write, so None is treated as off. Used when no query was
    answered at all.
    """
    with _current_stream_lock:
        for mode in MOUSE_MODES:
            value = state.get(mode)
            if value is None:
                if only_known:
                    continue
                value = False
            suffix = "h" if value else "l"
            _write_current_output_stream(f"{CSI}?{mode}{suffix}", flush=True)
        _current_output_stream.flush()


def mouse_state_push() -> dict[int, bool] | None:
    """Save the terminal's mouse state and turn mouse reporting off.

    Returns the saved state for mouse_state_pop(), or None when managed
    handling is disabled (MOUSE_STATE_MANAGED is False).
    """
    if not MOUSE_STATE_MANAGED:
        return None
    saved = _query_mouse_modes()
    # Turn off only the modes the terminal reported as on. A mode with no reply
    # is not touched: resetting it could silently disable tracking in a tab that
    # had it enabled.
    to_reset = {mode: False for mode, on in saved.items() if on}
    if to_reset:
        _write_mouse_modes(to_reset, only_known=True)
    return saved


def mouse_state_pop(saved: dict[int, bool] | None) -> None:
    """Restore the mouse state returned by mouse_state_push()."""
    if saved is None:
        return
    # Only modes that were reset on entry (reported on) need restoring. Anything
    # else was never changed, so writing it again could only add noise.
    _write_mouse_modes({mode: True for mode, on in saved.items() if on}, only_known=True)
