import os
import re
import sys
import tty
import fcntl
import termios
import threading
import collections

from dataclasses import dataclass, field
from typing import List, Dict, Optional

from .const import MAX_TERMINAL_WIDTH, BEL, ESC

from . import terminal

@dataclass
class Token:
    kind: str                  # e.g., WORD, WHITESPACE, F6, RGB
    value: str = None          # the literal string or command
    args: List = field(default_factory=list)   # positional args
    kwargs: Dict = field(default_factory=dict) # keyword args
    text: str = field(default="") # {f6:3} -> \n*3, {home} -> \033[H, etc
    repeat: int = 1
    raw: Optional[str] = None                  # raw input that generated this token
    def __repr__(self):
        parts = [self.kind]
        if self.value:
            parts.append(f"value={repr(self.value)}") # repr(self.value))
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


#_cursor_row = 1
#_cursor_col = 1

_current_input_stream = sys.stdin

_current_output_stream = sys.stdout

_current_stream_lock = threading.Lock()

def set_output_stream(stream):
    global _current_output_stream
    _current_output_stream = stream

def set_input_stream(stream):
    global _current_input_stream
    _current_input_stream = stream

_input_queue = collections.deque()

def _read_current_input_stream(size:int=1) -> str:
    if _input_queue:
        return _input_queue.popleft()
    return _current_input_stream.read(size)

def read_current_input_stream(size:int=1) -> str:
    with _current_stream_lock:
        return _read_current_input_stream(size)

def _write_current_output_stream(s:str, flush=False):
    _current_output_stream.write(s)
    if flush:
        _current_output_stream.flush()

def write_current_output_stream(s:str, flush=False):
    with _current_stream_lock:
        return _write_current_output_stream(s, flush=flush)

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
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# Regex for DSR reply: ESC [ <row> ; <col> R
DSR_CURPOS_RE = re.compile(r'\x1b\[(\d+);(\d+)R')

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
    import time

    if mode == "curpos":
        code = "6"
        term = "R"
    elif mode == "status":
        code = "5"
        term = "n"
    else:
        raise ValueError

    with _current_stream_lock:
        # drain input and output into queues
        drain_stream_to_queue(_current_input_stream, _input_queue)

        # store original settings
        fd = _current_input_stream.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            # Step 0: set raw mode
            tty.setraw(fd) # _current_input_stream
            # Step 1: send the DSR request
            _write_current_output_stream(f"{ESC}[{code}n", flush=True)

            # Step 2: read the response in a loop until we see the trailing 'R'
            start_time = time.time()
            buffer = ""

            while True:
                # Step 2a: read up to 32 bytes (adjust as needed)
                chunk = _read_current_input_stream(1)
                buffer += chunk

                match = DSR_CURPOS_RE.search(buffer)
                if match:
                    row, col = map(int, match.groups())

                    # Remove the matched DSR from buf and push the rest back into the queue
                    start, end = match.span()
                    leftover = buffer[:start] + buffer[end:]
                    _input_queue.clear()
                    _input_queue.extend(leftover)
                    return (row, col)

                # Step 2c: check for timeout
                if (time.time() - start_time) > timeout:
                    raise TimeoutError(f"DSR response not received in {timeout}s: {buffer!r}")
                    break

            return buffer # .decode(errors="ignore")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)  # restore

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
        if response and response.startswith(CSI) and response.endswith("n"):
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
                queue.append(ch)
            except BlockingIOError:
                break  # would block → stop
    finally:
        # Restore original flags
        fcntl.fcntl(fd, fcntl.F_SETFL, fl)

# save/restore cursor attributes
@dataclass
class TerminalState():
    cursor_row: int = 1
    cursor_col: int = 1
    wordwrap:bool  = True
    has_color:bool = True
    hidden:bool = False
    width:int = 100
    acs:bool = False
    raw:bool = False
    decdhl:bool = False # double height
    decdwl:bool = False
    def __repr__(self):
        return f"TerminalState({self.cursor_row=}, {self.cursor_col=}, {self.wordwrap=}, {self.has_color=}, {self.hidden=}, {self.acs=}, {self.raw=})"

_terminal_state = TerminalState(cursor_row=terminal.lines(), cursor_col=terminal.columns())
_terminal_state_stack = []
_terminal_state_stack_enabled = False

_input_dirty = False
