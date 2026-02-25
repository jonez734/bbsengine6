import os
import tty
import select
import fcntl
import termios


from .common import _current_input_stream, _current_stream_lock, _input_queue, _read_current_input_stream
from .util import logentry
from .keymap import KEY_MAP
from .const import ESC, ETX, EOF

#def _read():
#    if _input_queue:
#        return _input_queue.popleft()
#    return _current_input_stream.read(1)

def _proc_char(char:str, debug:bool=False) -> str | None:
    # 3. Handle Control Characters
    if char == "\x01":
        return "KEY_CTRL_A"
    if char == ETX:  # Ctrl+C (ETX)
        raise KeyboardInterrupt
    if char == EOF:  # Ctrl+D (EOF)
        raise EOFError
    if char == '\x05': # ctrl-e (EOL)
        return "KEY_CTRL_E"
    if char in ('\x7f', '\x08'):
        return "KEY_BACKSPACE"
    if char == '\r':
        return "KEY_ENTER"
    if char == '\x15': # ctrl-u
        return "KEY_CUTTOBOL"
    if char == '\t':
        return "KEY_TAB"

    # 4. Handle Escape Sequences and Plain ESC
    if char == ESC: # ESCAPE
        sequence = char
        # Read subsequent bytes without blocking to check for a sequence
        # Wait a short period, then check up to a maximum number of bytes (e.g., 10)

        # The critical logic: read more bytes *until* BlockingIOError *or* 10 bytes read
        for _ in range(10):
            try:
                # Reading one byte at a time is safest for sequential parsing
                next_char = _read_current_input_stream()
                sequence += next_char
            except BlockingIOError:
                break # Sequence transmission stopped

        # A. Check for plain ESC
        if len(sequence) == 1:
             return "KEY_ESC" # Plain ESC key was pressed (as no other bytes followed)

        # B. Check for known escape sequences
        # Sort keys by length descending to match longest possible sequence first
        for code, name in sorted(KEY_MAP.items(), key=lambda item: len(item[0]), reverse=True):
            if sequence.endswith(code):
                return name

        # C. Unknown escape sequence
        if debug:
            logentry(f"unknown escape sequence: {sequence!r}")
            return None
        return sequence

    # 5. Return a regular character
    return char

def getch_str(timeout: float | None = None, debug: bool = False, **kwargs) -> str | None:
    """Reads a single keypress without blocking and handles control/extended keys.
    
    Args:
        timeout: Seconds to wait for input (default: None, blocks indefinitely)
        debug: If True, log unknown escape sequences and return None
    """
    
    with _current_stream_lock:
        if _input_queue:
            char = _input_queue.popleft()
            return _proc_char(char, debug=debug)
        else:
            fd = _current_input_stream.fileno()
            old_settings = termios.tcgetattr(fd)
            old_flags = None

            try:
                # 1. Set Terminal to Raw/Cbreak Mode
                tty.setraw(fd)

                # --- INITIAL READ SETUP ---
                # Use select to wait for the first byte with the specified timeout
                # select() will block until data is available or the timeout is reached.
                ready, _, _ = select.select([_current_input_stream], [], [], timeout)

                if timeout is not None and not ready:
                        # Timeout occurred before the first character was available
                        return None

                # 2. Set Non-Blocking I/O
                # Save old flags and set O_NONBLOCK flag on the file descriptor
                old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)

                try:
                    # Attempt to read a single byte
                    char = _read_current_input_stream()
                except BlockingIOError:
                    # If nothing is available, return None immediately
                    return None

                return _proc_char(char)
            
            finally:
                # 6. Restore Terminal Settings (CRUCIAL!)
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                # Restore old flags (blocking?)
                if old_flags:
                    fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)
