import functools
import json
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

_current_stream_lock = threading.Lock()
_terminal_state_lock = threading.Lock()


def _in_stream():
    return _get_input_stream()


def _out_stream():
    return _get_output_stream()


def _queue():
    return _interaction().input_queue


def _interaction():
    """The interaction in effect for this context (see bbsengine6.interaction)."""
    from ..interaction import current_session

    return current_session()


def _get_input_stream():
    v = _interaction().input_stream
    return sys.stdin if v is None else v


def _get_output_stream():
    v = _interaction().output_stream
    return sys.stdout if v is None else v


def _get_input_queue():
    return _interaction().input_queue


def _terminal_state_of(it):
    """The interaction's terminal state, built from the terminal size on first read."""
    if it.terminal_state is None:
        it.terminal_state = _default_terminal_state()
    return it.terminal_state


def _get_terminal_state():
    st = _interaction().terminal_state
    if st is None:
        st = _default_terminal_state()
        _interaction().terminal_state = st
    return st


def _get_terminal_state_stack():
    return _interaction().terminal_state_stack


def _get_terminal_state_stack_enabled():
    return _interaction().terminal_state_stack_enabled


def _set_terminal_state_stack_enabled(value):
    _interaction().terminal_state_stack_enabled = bool(value)


def _get_input_dirty():
    return _interaction().input_dirty


def _set_input_dirty(value):
    _interaction().input_dirty = bool(value)


def set_output_stream(stream):
    with _current_stream_lock:
        _interaction().output_stream = stream


def set_input_stream(stream):
    with _current_stream_lock:
        _interaction().input_stream = stream


_input_queue_lock = threading.Lock()

#: A complete DA1 or DA2 reply in the queue: ESC [ ? digits/; c, or ESC [ > digits/; c.
_DA_REPLY_QUEUE_RE = re.compile(r"\x1b\[[?>][0-9;]*c")
#: A complete XTGETTCAP reply (DCS 0/1 + r, hex name, optional =hex value, ST).
_XTGETTCAP_QUEUE_RE = re.compile(r"\x1bP[01]\+r[0-9A-Fa-f]+(?:=[0-9A-Fa-f]*)?\x1b\\")


def discard_da_replies() -> int:
    """Remove complete DA1/DA2 replies from the input queue. Return how many were removed.

    A reply is not a keypress. The input reader calls this before reading, so a reply is kept
    out of the typed input. Each removed reply is also recorded in the interaction's
    ``da_replies`` list, so a non-blocking probe can collect its answer later. Only whole
    replies are removed: a partial sequence is left alone until its final byte arrives.
    """
    with _input_queue_lock:
        queue = _queue()
        if not queue:
            return 0
        text = "".join(queue)
        found = _DA_REPLY_QUEUE_RE.findall(text) + _XTGETTCAP_QUEUE_RE.findall(text)
        if not found:
            return 0
        cleaned = _XTGETTCAP_QUEUE_RE.sub("", _DA_REPLY_QUEUE_RE.sub("", text))
        queue.clear()
        queue.extend(cleaned)
        session = _interaction()
        for reply in found:
            # A reply for a probe that already timed out is late: note it, and it is still dropped.
            # DA1 and DA2 replies are told apart by their marker ("?" or ">").
            name = _probe_name_for(reply)
            if name is not None and name in session.da_timed_out:
                session.da_timed_out.discard(name)
                session.late_da_replies.append((name, reply))
            else:
                session.da_replies.append(reply)
        return len(found)


def _probe_name_for(reply: str) -> str | None:
    """The probe name a DA or XTGETTCAP reply answers: "da1", "da2", or "rgb". None if unknown."""
    if reply.startswith("\x1b[?"):
        return "da1"
    if reply.startswith("\x1b[>"):
        return "da2"
    if reply.startswith("\x1bP"):
        return "rgb"
    return None


def _read_current_input_stream(size: int = 1) -> str:
    with _input_queue_lock:
        if _queue():
            return _queue().popleft()
    return _in_stream().read(size)


def read_current_input_stream(size: int = 1) -> str:
    with _current_stream_lock:
        return _read_current_input_stream(size)


def _write_current_output_stream(s: str, flush=False):
    _out_stream().write(s)
    if flush:
        _out_stream().flush()


def write_current_output_stream(s: str, flush=False):
    with _current_stream_lock:
        _record_sgr(s)
        return _write_current_output_stream(s, flush=flush)


def _record_sgr(s: str) -> None:
    """Track the SGR colour and attributes as escape text is written, for {decsc}/{decrc}."""
    if "\x1b[" not in s:
        return
    from . import sgr_state

    st = _get_terminal_state()
    with _terminal_state_lock:
        base = st.sgr or sgr_state.EMPTY
        st.sgr = sgr_state.apply(base, s)


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
        fd = _in_stream().fileno()
        settings = termios.tcgetattr(fd)
    except Exception:
        return  # not a terminal
    with _current_stream_lock:
        # Keys already typed are in the cooked line discipline; setraw() would
        # discard them. Queue them first, in arrival order.
        drain_stream_to_queue(_in_stream(), _queue())
        _enter_raw(fd)
        # setraw() also clears OPOST, which turns off the tty's LF-to-CRLF translation.
        # Without it, a bare "\n" (from {f6}, and so from the Enter key) moves the cursor
        # down without returning to column 0. Input stays raw: only the output flag changes.
        attrs = termios.tcgetattr(fd)
        attrs[1] |= termios.OPOST | termios.ONLCR
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
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


def _enter_raw(fd: int) -> None:
    """Switch the tty to raw mode without discarding unread input.

    tty.setraw() defaults to TCSAFLUSH, which throws away keys still in the kernel buffer.
    A keypress typed just before a read was lost that way. TCSANOW changes the mode and keeps
    the input.
    """
    mode = termios.tcgetattr(fd)
    new = list(mode)
    tty.cfmakeraw(new)
    termios.tcsetattr(fd, termios.TCSANOW, new)


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
    fd = _in_stream().fileno()

    # 1. Save and set terminal mode
    old_settings = termios.tcgetattr(fd)
    try:
        # Set to cbreak mode (raw-like, but includes signal processing)
        tty.setcbreak(fd)

        response = ""
        for _ in range(10):
            ch = os.read(fd, 1).decode(_in_stream().encoding)
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
        drain_stream_to_queue(_in_stream(), _queue())
        fd = _in_stream().fileno()
        old_settings = termios.tcgetattr(fd)

    try:
        if not _in_raw_session():
            _enter_raw(fd)
        _write_current_output_stream(f"{ESC}[{code}n", flush=True)

        buffer = ""
        encoding = _in_stream().encoding or "utf-8"

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
                # Keys read alongside the reply were typed after anything already queued
                # (drain_stream_to_queue ran first), so they go to the back, in order.
                with _input_queue_lock:
                    _queue().extend(leftover)
                return (row, col)
            # No reply: the bytes read are typed input. Keep them, after the queued keys.
            with _input_queue_lock:
                _queue().extend(buffer)
            raise TimeoutError(
                f"DSR response not received in {timeout}s: {buffer!r}"
            )
        return buffer
    finally:
        _restore_cooked(fd, old_settings)


##    write_current_output_stream(f"{CSI}{code}n", flush=True)
##    _out_stream().flush()
##    return _read_terminal_response(terminator)


#: Extra time after the timeout (or after a match) during which the tty is still read, so a
#: reply that arrives late is consumed here and is not left in the tty for the input reader.
QUERY_SETTLE_SECONDS = 0.25


def strip_echoed_request(text: str, request: str) -> str:
    """Remove every echo of ``request`` from ``text``.

    A terminal that does not answer a query can echo the query back. That text is ours, not typed
    input, so it is taken out before the rest is kept as keys. A terminal may draw the request with
    its control bytes dropped, so the ESC that opens it and the ESC \\ that closes it are optional
    in the match: "ESC P + q 524742 ESC \\" is removed as well when it is drawn as "P+q524742".
    """
    if request.startswith("\x1b") and request.endswith("\x1b\\"):
        inner = request[1:-2]
    else:
        inner = request
    # The closing ST may be drawn as ESC \\ or as the backslash alone.
    pattern = re.compile(r"(?:\x1b)?" + re.escape(inner) + r"(?:\x1b?\\)?")
    return pattern.sub("", text)


def query_terminal(request: str, reply_re: "re.Pattern[str]", timeout: float = 0.5) -> str | None:
    """Send ``request`` to the terminal and return the first reply matching ``reply_re``.

    Same exchange as :func:`get_dsr`: pending input is drained into the queue first, the tty
    is put in raw mode (unless a raw session owns it), the request is written, and the reply
    is read with ``select`` until ``timeout``. Then the tty is read for ``QUERY_SETTLE_SECONDS``
    more, so a late reply is consumed here and does not reach the input reader as keystrokes.
    Typed bytes that are not the reply go back on the input queue, in order. The tty is
    restored in every case.

    Returns the matched text, or None when no reply matched in time. A reply that arrives
    after the settle window is not consumed here; the caller must treat it as not received.
    """
    with _current_stream_lock:
        drain_stream_to_queue(_in_stream(), _queue())
        fd = _in_stream().fileno()
        old_settings = termios.tcgetattr(fd)

    buffer = ""
    match = None
    try:
        if not _in_raw_session():
            _enter_raw(fd)
        _write_current_output_stream(request, flush=True)
        encoding = _in_stream().encoding or "utf-8"

        def _read_until(deadline: float) -> None:
            nonlocal buffer, match
            while time.time() < deadline and match is None:
                rlist, _, _ = select.select([fd], [], [], 0.02)
                if not rlist:
                    continue
                try:
                    chunk = os.read(fd, 64).decode(encoding, errors="replace")
                except OSError:
                    return
                if not chunk:
                    return
                buffer += chunk
                match = reply_re.search(buffer)

        _read_until(time.time() + timeout)
        # Keep reading briefly even when nothing has matched, to catch a late reply.
        if match is None:
            _read_until(time.time() + QUERY_SETTLE_SECONDS)
    finally:
        _restore_cooked(fd, old_settings)

    if match:
        leftover = buffer[: match.start()] + buffer[match.end() :]
        matched = match.group(0)
    else:
        leftover = buffer
        matched = None
    leftover = strip_echoed_request(leftover, request)
    if leftover:
        with _input_queue_lock:
            _queue().extend("\r" if c == "\n" else c for c in leftover)
    return matched


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
                if ch == "\n" and queue is _queue():
                    ch = "\r"
                # Lock for _queue(), otherwise assume caller handles it
                if queue is _queue():
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
    #: The SGR colour and attributes in effect at the cursor (see sgr_state). Saved and restored
    #: with the cursor, so {decrc} puts the terminal back in the colour that was active at {decsc}.
    sgr: Any = None

    def __repr__(self):
        return f"TerminalState({self.cursor_row=}, {self.cursor_col=}, {self.wordwrap=}, {self.has_color=}, {self.hidden=}, {self.acs=}, {self.raw=})"


_terminal_state_stack_lock = threading.Lock()


def _default_terminal_state() -> TerminalState:
    return TerminalState(cursor_row=terminal.lines(), cursor_col=terminal.columns())


def get_terminal_state():
    with _terminal_state_lock:
        return _get_terminal_state()


def set_terminal_state(state: TerminalState):
    with _terminal_state_lock:
        _interaction().terminal_state = state


# --------------------------
# Bracketed paste (inputstring)
# --------------------------

# Module flag: when False, inputstring() does not ask the terminal to wrap pastes.
BRACKETED_PASTE_MANAGED = True


def bracketed_paste_on() -> bool:
    """Ask the terminal to wrap pasted text in ESC[200~ ... ESC[201~.

    Returns True when enabled (so bracketed_paste_off() should follow), False
    when disabled or not a terminal. A terminal that does not know the mode
    ignores the request and pastes as plain keys, which the paste-batch rules
    still handle.
    """
    if not BRACKETED_PASTE_MANAGED:
        return False
    try:
        _write_current_output_stream(f"{CSI}?2004h", flush=True)
    except Exception:
        return False
    return True


def bracketed_paste_off(enabled: bool) -> None:
    """Turn bracketed paste off again, if bracketed_paste_on() enabled it."""
    if not enabled:
        return
    try:
        _write_current_output_stream(f"{CSI}?2004l", flush=True)
    except Exception:
        pass


# --------------------------
# Mouse reporting state (inputstring)
# --------------------------

# Mouse tracking modes that cause a terminal to capture click-drag selection.
MOUSE_MODES = (1000, 1002, 1003, 1006)

# Module flag: when False, inputstring() leaves the terminal's mouse state alone.
MOUSE_STATE_MANAGED = True

_DECRPM_RE = re.compile(r"\x1b\[\?(\d+);(\d)\$y")


@functools.lru_cache(maxsize=1)
def _decrqm_terms() -> frozenset:
    """TERM names known to answer DECRQM, from io/data/decrqm_terminals.json."""
    from importlib import resources

    text = resources.files("bbsengine6").joinpath("io/data/decrqm_terminals.json").read_text(encoding="utf-8")
    return frozenset(json.loads(text)["terms"])


def _decrqm_capable() -> bool:
    """True when the terminal named by TERM is known to answer DECRQM.

    A terminal not on the list is never sent a mode query: one that does not answer draws the
    trailing "p" of each query as text. The match is the whole TERM name, exactly as listed.
    """
    term = os.environ.get("TERM", "")
    return term in _decrqm_terms()


def _query_mouse_modes(timeout: float = 0.5) -> dict[int, bool]:
    """Ask the terminal which mouse modes are set (DECRQM).

    Returns {mode: enabled}. A mode with no reply is reported as disabled,
    which is the fallback the restore logic relies on.
    """
    if not _decrqm_capable():
        return {}
    fd = _in_stream().fileno()
    with _current_stream_lock:
        drain_stream_to_queue(_in_stream(), _queue())
        old_settings = termios.tcgetattr(fd)
    replies = ""
    try:
        if not _in_raw_session():
            _enter_raw(fd)
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

    _mouse_trace(f"query raw replies {replies!r}")
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
            _queue().extend(keys)
    return state


def _write_mouse_modes(state: dict[int, bool | None], only_known: bool = False) -> None:
    """Set each mouse mode on or off to match state (h = on, l = off).

    A mode whose state is None (no reply) is left alone. With only_known=False
    every mode gets a write, so None is treated as off. Used when no query was
    answered at all.
    """
    written = []
    with _current_stream_lock:
        for mode in MOUSE_MODES:
            value = state.get(mode)
            if value is None:
                if only_known:
                    continue
                value = False
            suffix = "h" if value else "l"
            _write_current_output_stream(f"{CSI}?{mode}{suffix}", flush=True)
            written.append(f"{mode}{suffix}")
        _out_stream().flush()
    _mouse_trace(f"write {' '.join(written) or '(none)'}")


def mouse_state_push() -> dict[int, bool] | None:
    """Save the terminal's mouse state and turn mouse reporting off.

    Returns the saved state for mouse_state_pop(), or None when managed
    handling is disabled (MOUSE_STATE_MANAGED is False).
    """
    if not MOUSE_STATE_MANAGED:
        return None
    saved = _query_mouse_modes()
    _mouse_trace(f"push: query replies {saved}")
    # Reset every managed mode, whatever the query said. A terminal can report a mode
    # off (or not answer) while tracking is in fact on, and then selection stays
    # blocked for the whole prompt. Resetting a mode that is already off is harmless.
    _write_mouse_modes({mode: False for mode in MOUSE_MODES})
    _mouse_trace("push: reset all managed modes")
    return saved


def mouse_state_pop(saved: dict[int, bool] | None) -> None:
    """Restore the mouse state returned by mouse_state_push()."""
    if saved is None:
        return
    # Restore the modes the terminal reported on at entry. Modes that were off, or did
    # not answer, stay off: that is the state a prompt leaves a tab in.
    on = {mode: True for mode, state in saved.items() if state}
    _write_mouse_modes(on, only_known=True)
    _mouse_trace(f"pop: restored {sorted(on)}")


_MOUSE_TRACE_ENV = "BBSENGINE_MOUSE_TRACE"


def _mouse_trace(message: str) -> None:
    """Append a line to the file named by BBSENGINE_MOUSE_TRACE, when it is set.

    Off by default. Used to see what the terminal answers and what the prompt writes.
    """
    path = os.environ.get(_MOUSE_TRACE_ENV)
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%H:%M:%S')} {message}\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Per-interaction names: read through the current interaction (Phase 3).
#
# These names used to be module globals. Each one is now a property over the current
# interaction, so `common.<name>` reads and writes the interaction in effect, and existing
# callers (echo, getch, inputstring, and tests that assign module attributes) are unchanged.
# The process-wide names above (locks, the tty settings, the *_MANAGED flags) are not here.
# ---------------------------------------------------------------------------
from ..interaction import install_read_through as _install_read_through  # noqa: E402

_install_read_through(
    __name__,
    {
        "_current_input_stream": "input_stream",
        "_current_output_stream": "output_stream",
        "_input_queue": "input_queue",
        "_terminal_state": "terminal_state",
        "_terminal_state_stack": "terminal_state_stack",
        "_terminal_state_stack_enabled": "terminal_state_stack_enabled",
        "_input_dirty": "input_dirty",
    },
    getters={
        "_current_input_stream": lambda it: sys.stdin if it.input_stream is None else it.input_stream,
        "_current_output_stream": lambda it: sys.stdout if it.output_stream is None else it.output_stream,
        "_terminal_state": lambda it: _terminal_state_of(it),
    },
)
