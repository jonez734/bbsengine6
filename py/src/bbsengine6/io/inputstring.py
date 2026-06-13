import inspect
import re
import threading
from collections import deque
from typing import Any, Callable, Optional, Tuple, List, Union, Deque

from . import terminal

from .const import (
    INPUTSTRING_GETCH_TIMEOUT,
    INPUTSTRING_DEFAULT_HISTORY_SIZE,
    INPUTSTRING_DEFAULT_PAGESIZE,
    INPUTSTRING_INSERT_MODE_INDICATOR,
    INPUTSTRING_OVERWRITE_MODE_INDICATOR,
)
from .echo import echo, rendered_length, echo_traceback
from .getch import getch_str as getch
from .common import (
    get_cursor_position,
    _current_stream_lock,
    _input_dirty,
)


# --- 0. MANDATORY DEFINITIONS & GLOBALS ---

_inputstring_lock = threading.Lock()

# Compiled regex pattern for word character matching (\w includes letters, digits, underscore)
_WORD_CHAR_PATTERN = re.compile(r"\w")

# Type alias for key handler functions
# Regular handlers return (buffer, curpos, scroll_offset)
# Enter handler returns (buffer, curpos, scroll_offset, accepted, need_redraw)
KeyHandler = Callable[
    [str, int, int, int], Union[Tuple[str, int, int], Tuple[str, int, int, bool, bool]]
]


class InputHistory:
    """Thread-safe input history management matching GNU readline behavior.

    Features:
    - Bounded circular buffer (default 500 entries)
    - No duplicate filtering (shell/app handles this)
    - No persistence (in-memory only)
    - UP/DOWN arrow navigation with position tracking

    Thread safety: All public methods protected by internal lock.

    Example:
        history = InputHistory(maxsize=500)
        history.add_entry("some command")
        prev = history.get_previous()  # Navigate UP
        next_val = history.get_next()  # Navigate DOWN
    """

    def __init__(self, maxsize: int = INPUTSTRING_DEFAULT_HISTORY_SIZE):
        """Initialize bounded history with max size.

        Args:
            maxsize: Maximum number of entries to keep (default 500, matches GNU readline)
        """
        self._history: Deque[str] = deque(maxlen=maxsize)
        self._current_index: int = -1  # -1 = at end (new input position)
        self._lock = threading.Lock()

    def add_entry(self, text: str) -> None:
        """Add entry to history. Auto-evicts oldest if at maxsize.

        GNU readline always adds entries (no dedup), shell/app handles HISTCONTROL filtering.
        """
        with self._lock:
            # GNU readline always adds (no dedup), shell handles this
            if text:  # Don't add empty entries
                self._history.append(text)
            # Reset position to "end" for next navigation
            self._current_index = -1

    def get_previous(self) -> Optional[str]:
        """Navigate to previous entry (UP arrow).

        Returns:
            History entry or None if at oldest entry.
        """
        with self._lock:
            if not self._history:
                return None

            # First UP from end (-1) goes to last entry
            if self._current_index == -1:
                self._current_index = len(self._history) - 1
            # Further UPs go backward
            elif self._current_index > 0:
                self._current_index -= 1
            else:
                # Already at oldest, stay there
                return self._history[0]

            return self._history[self._current_index]

    def get_next(self) -> Optional[str]:
        """Navigate to next entry (DOWN arrow).

        Returns:
            History entry or None if at newest/end.
        """
        with self._lock:
            if not self._history or self._current_index == -1:
                return None

            if self._current_index < len(self._history) - 1:
                self._current_index += 1
                return self._history[self._current_index]
            else:
                # At newest, DOWN goes to "end" (new input)
                self._current_index = -1
                return None

    def reset_position(self) -> None:
        """Reset to end of history (called when user types new text)."""
        with self._lock:
            self._current_index = -1

    def get_all(self) -> List[str]:
        """Return copy of all history entries (for debugging/export)."""
        with self._lock:
            return list(self._history)

    def clear(self) -> None:
        """Clear all history entries and reset position."""
        with self._lock:
            self._history.clear()
            self._current_index = -1


class Completer:
    """Callable class for tab completion.

    Usage:
        def get_matches_fn(prefix, **kwargs):
            return ["match1", "match2"]

        completer = Completer(get_matches_fn)
        inputstring("Prompt: ", completer=completer)

    Or with a class method:
        class PlayerCompleter(Completer):
            def get_matches(self, prefix, **kwargs):  # noqa: PLE
                return db.query("SELECT name FROM players WHERE name LIKE ?", prefix + "%", **kwargs)

        inputstring("Select player: ", completer=PlayerCompleter(conn=db_conn))

    Or with database parameters:
        completer = Completer(get_matches_fn, conn=db_conn, pool=thread_pool)
        inputstring("Prompt: ", completer=completer)
    """

    def __init__(
        self,
        get_matches: Optional[Callable[[str], Optional[List[str]]]] = None,
        **kwargs,
    ):
        """Initialize with optional get_matches function and kwargs.

        Args:
            get_matches: Function that takes prefix and returns list of matches.
            **kwargs: Arbitrary parameters (e.g., conn, pool) passed to get_matches.
        """
        # Only set if explicitly passed - don't override subclass methods
        if get_matches is not None:
            self._get_matches_func = get_matches
        # Store kwargs for use by get_matches in subclass
        self.kwargs: dict = kwargs

    def get_matches(self, prefix: str, **kwargs) -> Optional[List[str]]:
        """Override this in subclass or pass function to constructor.

        Args:
            prefix: The text prefix to match against.
            **kwargs: Additional parameters (e.g., conn, pool) passed from inputstring.

        Returns:
            List of matching strings, or None if no matches.
        """
        # Merge stored kwargs with call-time kwargs (call-time takes precedence)
        merged_kwargs = {**self.kwargs, **kwargs}

        # Check for stored function first
        if hasattr(self, "_get_matches_func") and self._get_matches_func is not None:
            if not callable(self._get_matches_func):
                return None

            try:
                sig = inspect.signature(self._get_matches_func)
            except (ValueError, TypeError):
                # If signature inspection fails, try calling with all kwargs
                try:
                    return self._get_matches_func(prefix, **merged_kwargs)
                except TypeError:
                    return None

            # If function has **kwargs, pass everything
            if any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()):
                return self._get_matches_func(prefix, **merged_kwargs)

            # Otherwise, only pass arguments that are in the signature
            filtered_kwargs = {
                k: v for k, v in merged_kwargs.items() if k in sig.parameters
            }
            return self._get_matches_func(prefix, **filtered_kwargs)
        return None

    def __call__(self, buffer: str, **kwargs) -> List[str]:
        """Called by inputstring to get completions.

        Args:
            buffer: Current input buffer
            **kwargs: Additional parameters passed to get_matches (including curpos)

        Returns:
            List of matching strings (never None, returns [] if no matches)
        """
        curpos = kwargs.get("curpos", len(buffer))
        prefix, word_start, word_end = get_current_word(buffer, curpos)
        # Get the actual word to match (not the prefix before it)
        word = buffer[word_start:word_end]
        result = self.get_matches(word, **kwargs)
        return result if result is not None else []


# Clipboard buffer for cut/yank operations. MUST be accessed only within _yank_buffer_lock.
yank_buffer = []
_yank_buffer_lock = threading.Lock()

_key_actions_lock = threading.Lock()


def move_cursor(row: int, col: int) -> None:
    """Move cursor to absolute terminal position (1-indexed).

    Args:
        row: Terminal row (1-indexed)
        col: Terminal column (1-indexed)
    """
    echo(f"{{curpos:{row},{col}}}", end="", flush=True)


def get_current_word(buffer: str, curpos: int) -> Tuple[str, int, int]:
    r"""Returns (prefix, word_start_index, word_end_index).

    Finds the word at the current cursor position and returns:
    - prefix: text before the word
    - word_start: starting index of the word
    - word_end: ending index of the word

    Words are defined as \w+ sequences (alphanumeric and underscore).
    """
    if curpos > len(buffer):
        curpos = len(buffer)

    # Find word boundaries (words are \w+ sequences: letters, digits, underscore)
    word_end = curpos
    while word_end < len(buffer) and _WORD_CHAR_PATTERN.match(buffer[word_end]):
        word_end += 1

    word_start = curpos
    while word_start > 0 and _WORD_CHAR_PATTERN.match(buffer[word_start - 1]):
        word_start -= 1

    prefix = buffer[:word_start]
    return prefix, word_start, word_end


def common_prefix(matches: List[str]) -> str:
    """Find the common prefix of a list of strings.

    Args:
        matches: List of strings.

    Returns:
        The common prefix string, or empty string if no common prefix.
    """
    if not matches:
        return ""
    if len(matches) == 1:
        return matches[0]

    # Find minimum length
    min_len = min(len(m) for m in matches)
    if min_len == 0:
        return ""

    # Find common prefix
    for i in range(min_len):
        c = matches[0][i]
        for m in matches[1:]:
            if m[i] != c:
                return matches[0][:i]

    return matches[0][:min_len]


def adjust_scroll_offset(curpos: int, scroll_offset: int, max_width: int) -> int:
    """Adjust scroll offset to keep cursor visible.

    Ensures the cursor at position `curpos` remains visible in a display window
    of width `max_width` starting at `scroll_offset`.

    Args:
        curpos: Current cursor position in buffer
        scroll_offset: Current start of visible window
        max_width: Width of display window

    Returns:
        Adjusted scroll_offset (guaranteed >= 0)
    """
    if curpos >= scroll_offset + max_width:
        scroll_offset = curpos - max_width + 1
    elif curpos < scroll_offset:
        scroll_offset = curpos
    if scroll_offset < 0:
        scroll_offset = 0
    return scroll_offset


# --- 1. Global Key Actions Dictionary ---
KEY_ACTIONS: dict[str, KeyHandler] = {}


def add_key_mapping(key_string: str, action_lambda: KeyHandler) -> None:
    """Register a key handler function.

    Args:
        key_string: Key name (e.g., 'KEY_LEFT', 'KEY_ENTER')
        action_lambda: Handler function with signature (buffer, curpos, scroll_offset, max_width) -> tuple
    """
    with _key_actions_lock:
        KEY_ACTIONS[key_string] = action_lambda


def remove_key_mapping(key_string: str) -> None:
    """Unregister a key handler function.

    Args:
        key_string: Key name to remove
    """
    with _key_actions_lock:
        if key_string in KEY_ACTIONS:
            del KEY_ACTIONS[key_string]


# --- 2. Helper Functions ---


def handle_left(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Move cursor left one position. Beeps if already at start."""
    if curpos > 0:
        curpos -= 1
    else:
        echo("{bell}", end="", flush=True)
    return buffer, curpos, scroll_offset


def handle_right(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Move cursor right one position. Beeps if already at end."""
    if curpos < len(buffer):
        curpos += 1
    else:
        echo("{bell}", end="", flush=True)
    return buffer, curpos, scroll_offset


def handle_home(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Jump cursor to beginning of line."""
    return buffer, 0, 0


def handle_end(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Jump cursor to end of line."""
    curpos = len(buffer)
    return buffer, curpos, scroll_offset


def handle_backspace(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Delete character before cursor. Beeps if already at start."""
    if curpos > 0:
        buffer = buffer[: curpos - 1] + buffer[curpos:]
        curpos -= 1
    else:
        echo("{bell}", end="", flush=True)
    return buffer, curpos, scroll_offset


def handle_cuttobol(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Cut from beginning of line to cursor and store in yank buffer."""
    global yank_buffer
    cut_text = buffer[:curpos]
    with _yank_buffer_lock:
        if cut_text:
            yank_buffer = [cut_text]
    buffer = buffer[curpos:]
    return buffer, 0, 0


def handle_cutpreviousword(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    r"""Cut the previous word from buffer and store in yank buffer.

    Uses \w word boundary matching (consistent with get_current_word).
    """
    global yank_buffer
    word_end = curpos
    while word_end > 0 and not _WORD_CHAR_PATTERN.match(buffer[word_end - 1]):
        word_end -= 1
    word_start = word_end
    while word_start > 0 and _WORD_CHAR_PATTERN.match(buffer[word_start - 1]):
        word_start -= 1
    if word_start == word_end:
        return buffer, curpos, scroll_offset
    cut_text = buffer[word_start:curpos]
    with _yank_buffer_lock:
        if cut_text:
            yank_buffer = [cut_text]
    buffer = buffer[:word_start] + buffer[curpos:]
    return buffer, word_start, scroll_offset


def handle_yank(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Paste yank buffer contents at cursor position.

    Note: Pasting may cause buffer to exceed max_len - validation happens in main loop.
    """
    global yank_buffer
    with _yank_buffer_lock:
        yank_text = "\n".join(yank_buffer)
    buffer = buffer[:curpos] + yank_text + buffer[curpos:]
    return buffer, curpos + len(yank_text), scroll_offset


def handle_help(
    buffer: str,
    curpos: int,
    scroll_offset: int,
    max_width: int,
    f1_help: str | Callable[[], str] | None = None,
    help: str | Callable[[], str] | None = None,
) -> Tuple[str, int, int]:
    """Display F1 help text as simple vertical list below current input line."""
    help_text = f1_help if f1_help is not None else help
    if help_text is None:
        return buffer, curpos, scroll_offset

    text: str
    if callable(help_text):
        text = help_text()
    else:
        text = str(help_text)

    lines = text.split("\n")
    for line in lines:
        echo(f"{{var:labelcolor}}{line}{{var:inputcolor}}", flush=True)

    _input_dirty = True
    return buffer, curpos, scroll_offset


# --- NEW HANDLERS (Phase 3) ---


def handle_history_previous(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Navigate to previous command in history (UP arrow)."""
    # Will be properly implemented to use InputHistory in the main loop
    # For now, just pass through (no-op until enabled)
    return buffer, curpos, scroll_offset


def handle_history_next(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Navigate to next command in history (DOWN arrow)."""
    # Will be properly implemented to use InputHistory in the main loop
    # For now, just pass through (no-op until enabled)
    return buffer, curpos, scroll_offset


def handle_delete(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Delete character at cursor position (DELETE key).

    Gracefully no-ops if at or past end of buffer.
    """
    if curpos >= len(buffer):
        # At or past end - beep
        echo("{bell}", end="", flush=True)
        return buffer, curpos, scroll_offset

    # Delete character at cursor
    new_buffer = buffer[:curpos] + buffer[curpos + 1 :]
    return new_buffer, curpos, scroll_offset


def handle_insert_toggle(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Toggle between insert and overwrite mode (INSERT key).

    Stores mode in a context variable that will be passed via kwargs.
    """
    # Mode state is managed in the main input loop via kwargs
    # This handler just signals that a redraw is needed
    return buffer, curpos, scroll_offset


def handle_pageup(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Jump cursor backwards by pagesize (PAGE UP key)."""
    # Default pagesize of 10 - will be configurable via kwargs in main loop
    pagesize = 10
    new_curpos = max(0, curpos - pagesize)
    # Adjust scroll offset to keep cursor visible
    if new_curpos < scroll_offset:
        new_scroll = new_curpos
    else:
        new_scroll = scroll_offset
    return buffer, new_curpos, new_scroll


def handle_pagedown(
    buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Jump cursor forwards by pagesize (PAGE DOWN key)."""
    # Default pagesize of 10 - will be configurable via kwargs in main loop
    pagesize = 10
    new_curpos = min(len(buffer), curpos + pagesize)
    # Adjust scroll offset to keep cursor visible
    if new_curpos >= scroll_offset + max_width:
        new_scroll = new_curpos - max_width + 1
    else:
        new_scroll = scroll_offset
    return buffer, new_curpos, new_scroll


def handle_function_key(
    key_name: str, buffer: str, curpos: int, scroll_offset: int, max_width: int
) -> Tuple[str, int, int]:
    """Dispatch function keys (F1-F12) to handlers or custom callbacks.

    F1: Special handling for help display (inline below input)
    F2-F12: Dispatch to function_key_handlers dict if provided
    """
    # This will be called from lambda wrappers in KEY_ACTIONS
    # Actual implementation deferred to main loop where kwargs are available
    return buffer, curpos, scroll_offset


# --- ENTER KEY HANDLER ---


def handle_key_enter(
    buffer: str,
    curpos: int,
    scroll_offset: int,
    max_width: int,
    *,
    verify: Optional[Callable[[str], bool]],
    args: Optional[Any],
    prompt: str,
    mask: Optional[str],
    start_row: int,
    start_col: int,
    input_col_start: int,
    noneok: bool,
    **kwargs: Any,
) -> Tuple[str, int, int, bool, bool]:
    """Process Enter key with optional verification.

    Returns (buffer, curpos, scroll_offset, accepted, need_redraw)

    Args:
        verify: Optional callable that validates input. Signature: verify(buffer, **kwargs) -> bool
        args: Application namespace (passed to verify via kwargs if needed)
        **kwargs: Additional parameters passed to verify
    """
    echo("{f6}", end="", flush=True)

    # No verify → accept immediately
    if not callable(verify):
        return buffer, curpos, scroll_offset, True, True

    # Run verify with buffer and kwargs (pass args through kwargs if provided)
    try:
        verify_kwargs = dict(kwargs)
        if args is not None:
            verify_kwargs["args"] = args
        ok = verify(buffer, **verify_kwargs)
    except Exception as e:
        echo_traceback(f"io.inputstring.handle_key_enter.100: {e}")
        ok = False

    if ok:
        return buffer, curpos, scroll_offset, True, True
    else:
        echo("{BEL}", end="", flush=True)

    # Verification failed — redraw
    redraw_line(
        prompt,
        buffer,
        max_width,
        start_row,
        start_col,
        curpos,
        scroll_offset,
        max_width,
        mask,
    )

    return buffer, curpos, scroll_offset, False, True


# --- 3. Tab Completion Logic ---


def handle_tab_manager(
    buffer,
    curpos,
    scroll_offset,
    max_width,
    completer,
    last_matches,
    tab_count,
    prompt,
    max_len,
    start_row,
    start_col,
    **kwargs,
):

    # Get the word first to determine if we need all matches
    prefix, word_start, word_end = get_current_word(buffer, curpos)
    word = buffer[word_start:word_end]

    # If empty word, try to get all matches by passing empty string
    # Completers should return all matches when called with empty string
    if not word:
        matches = completer("", curpos=curpos, **kwargs)
    else:
        matches = completer(buffer, curpos=curpos, **kwargs)

    if not matches:
        echo("{bell}", end="", flush=True)
        return buffer, curpos, scroll_offset, last_matches, tab_count, start_row

    # If empty word (user pressed tab with nothing typed), show all matches
    if not word:
        if matches == last_matches and tab_count >= 1:
            # Second tab with empty word - ring bell
            echo("{bell}", end="", flush=True)
            return buffer, curpos, scroll_offset, last_matches, tab_count, start_row

        # First tab with empty word - show all matches in columns
        echo("\n")
        lines_printed = print_matches(matches)

        # Adjust start_row if we scrolled
        rows = terminal.lines()
        if start_row + lines_printed > rows:
            start_row -= start_row + lines_printed - rows
        if start_row < 1:
            start_row = 1

        redraw_line(
            prompt,
            buffer,
            max_len,
            start_row,
            start_col,
            curpos,
            scroll_offset,
            max_width,
        )
        return buffer, curpos, scroll_offset, matches, 1, start_row

    # If single match and user presses tab again, ring bell (no other options)
    if matches == last_matches and len(last_matches) == 1 and tab_count >= 1:
        echo("{bell}", end="", flush=True)
        return buffer, curpos, scroll_offset, last_matches, tab_count, start_row

    if len(matches) == 1:
        word = matches[0]
        buffer = buffer[:word_start] + word + buffer[word_end:]
        curpos = word_start + len(word)

        scroll_offset = adjust_scroll_offset(curpos, scroll_offset, max_width)

        redraw_line(
            prompt,
            buffer,
            max_len,
            start_row,
            start_col,
            curpos,
            scroll_offset,
            max_width,
        )
        return buffer, curpos, scroll_offset, matches, 1, start_row

    if matches == last_matches and tab_count == 1:
        echo("\n")
        lines_printed = print_matches(matches)
        echo("\n")

        # Adjust start_row if we scrolled
        rows = terminal.lines()
        # +1 for the extra newline
        total_lines = lines_printed + 1
        if start_row + total_lines > rows:
            start_row -= start_row + total_lines - rows
        if start_row < 1:
            start_row = 1

        redraw_line(
            prompt,
            buffer,
            max_len,
            start_row,
            start_col,
            curpos,
            scroll_offset,
            max_width,
        )
        return buffer, curpos, scroll_offset, [], 0, start_row

    lcp = common_prefix(matches)
    if lcp and lcp != word:
        buffer = buffer[:word_start] + lcp + buffer[word_end:]
        curpos = word_start + len(lcp)

        scroll_offset = adjust_scroll_offset(curpos, scroll_offset, max_width)

        redraw_line(
            prompt,
            buffer,
            max_len,
            start_row,
            start_col,
            curpos,
            scroll_offset,
            max_width,
        )

    return buffer, curpos, scroll_offset, matches, 1, start_row


# --- 4. Display Functions ---


def redraw_line(
    prompt: str,
    buffer: str,
    max_len: int,
    start_row: int,
    start_col: int,
    curpos: int,
    scroll_offset: int,
    max_width: int,
    mask: Optional[str] = None,
    insert_mode: bool = True,
) -> None:
    """Clear and redraw the input line at the specified position.

    Handles both regular and masked (password) input display.

    Args:
        insert_mode: If False, shows [OVR] indicator; if True, shows [INS].
    """
    # NEW: Add mode indicator to prompt
    mode_indicator = ""
    if insert_mode:
        mode_indicator = f" {INPUTSTRING_INSERT_MODE_INDICATOR}"
    else:
        mode_indicator = f" {INPUTSTRING_OVERWRITE_MODE_INDICATOR}"

    full_prompt = prompt + mode_indicator

    input_col_start = start_col + rendered_length(full_prompt)

    echo(f"{{curpos:{start_row},{start_col}}}", end="", flush=True)
    echo(full_prompt, end="", flush=True)
    echo(f"{{curpos:{start_row},{input_col_start}}}", end="", flush=True)

    display_str = buffer[scroll_offset : scroll_offset + max_width]

    if mask is not None:
        echo(f"{mask * len(display_str)}", end="", flush=True)
    else:
        echo(display_str, end="", flush=True, raw=True)

    echo(
        f"{{curpos:{start_row},{input_col_start + (curpos - scroll_offset)}}}",
        end="",
        flush=True,
    )


def print_matches(matches: List[str]) -> int:
    """Print tab completion matches in columns.

    Args:
        matches: List of match strings to display.

    Returns:
        Number of lines printed. Returns 0 if matches is empty or terminal has no width.
    """
    if not matches:
        return 0

    cols = terminal.columns()
    if cols <= 0:
        return 0

    longest = max(len(m) for m in matches) + 2
    per_line = max(1, cols // longest)

    for i, m in enumerate(matches, 1):
        echo(m.ljust(longest), end="")
        if i % per_line == 0:
            echo("{f6}", end="")
    if len(matches) % per_line != 0:
        echo("{f6}", end="")

    return (len(matches) + per_line - 1) // per_line


# --- 5. Initial Key Mappings ---

add_key_mapping("KEY_LEFT", handle_left)
add_key_mapping("KEY_RIGHT", handle_right)
add_key_mapping("KEY_HOME", handle_home)
add_key_mapping("KEY_CTRL_A", handle_home)
add_key_mapping("KEY_END", handle_end)
add_key_mapping("KEY_CTRL_E", handle_end)
add_key_mapping("KEY_BACKSPACE", handle_backspace)
add_key_mapping("KEY_CUTTOBOL", handle_cuttobol)
add_key_mapping("KEY_CTRL_W", handle_cutpreviousword)
add_key_mapping("KEY_YANK", handle_yank)

# NEW: History navigation (Phase 4)
add_key_mapping("KEY_UP", handle_history_previous)
add_key_mapping("KEY_DOWN", handle_history_next)

# NEW: Additional editing keys (Phase 4)
add_key_mapping("KEY_DELETE", handle_delete)
add_key_mapping("KEY_INSERT", handle_insert_toggle)
add_key_mapping("KEY_PAGEUP", handle_pageup)
add_key_mapping("KEY_PAGEDOWN", handle_pagedown)

# Function keys (Phase 4)
# KEY_F1 is handled dynamically with f1_help context per-call, not registered at module load
add_key_mapping("KEY_F2", lambda b, c, s, m: handle_function_key("KEY_F2", b, c, s, m))
add_key_mapping("KEY_F3", lambda b, c, s, m: handle_function_key("KEY_F3", b, c, s, m))
add_key_mapping("KEY_F4", lambda b, c, s, m: handle_function_key("KEY_F4", b, c, s, m))
add_key_mapping("KEY_F5", lambda b, c, s, m: handle_function_key("KEY_F5", b, c, s, m))
add_key_mapping("KEY_F6", lambda b, c, s, m: handle_function_key("KEY_F6", b, c, s, m))
add_key_mapping("KEY_F7", lambda b, c, s, m: handle_function_key("KEY_F7", b, c, s, m))
add_key_mapping("KEY_F8", lambda b, c, s, m: handle_function_key("KEY_F8", b, c, s, m))
add_key_mapping("KEY_F9", lambda b, c, s, m: handle_function_key("KEY_F9", b, c, s, m))
add_key_mapping(
    "KEY_F10", lambda b, c, s, m: handle_function_key("KEY_F10", b, c, s, m)
)
add_key_mapping(
    "KEY_F11", lambda b, c, s, m: handle_function_key("KEY_F11", b, c, s, m)
)
add_key_mapping(
    "KEY_F12", lambda b, c, s, m: handle_function_key("KEY_F12", b, c, s, m)
)

# --- 6. MAIN INPUT FUNCTION ---


def inputstring(
    prompt: str = "> ",
    oldvalue: str = "",
    /,
    history: bool = False,
    pagesize: int = INPUTSTRING_DEFAULT_PAGESIZE,
    beep_on_error: bool = True,
    f1_help: Union[str, Callable[[], str], None] = None,
    help: Union[str, Callable[[], str], None] = None,
    function_key_handlers: Optional[dict] = None,
    **kwargs,
) -> str:
    """Read a line of text from the terminal with full line editing support.

    Args:
        prompt: Display prompt (default: "> ")
        oldvalue: Pre-fill buffer with this value (default: "")
        history: Enable UP/DOWN command history navigation (default: False)
            When True, UP/DOWN arrows navigate through previously entered inputs.
            Implements GNU readline-compatible history (500 entry default).
            Each inputstring() call has independent history.
            No duplicate filtering (app handles via shell or own logic).
            Non-persistent (in-memory only, not saved to disk).
        pagesize: Number of characters PAGE UP/DOWN jump (default: 10)
            PAGE UP: Jump backwards by pagesize chars
            PAGE DOWN: Jump forwards by pagesize chars
        beep_on_error: Beep on errors like DELETE at end of buffer (default: True)
            If False, no beep; if True, beep when error occurs
        f1_help: Help text or function for F1 key (default: None)
            - str: Display as-is inline below prompt
            - callable: Call with no args, display return value
            - None: F1 is no-op
            Help is displayed inline without interrupting input.
        help: Alias for f1_help for consistency with inputchoice (default: None)
        function_key_handlers: Dict mapping KEY_F2-KEY_F12 to callables (default: None)
            Example:
                def handle_f2(buffer, curpos, scroll_offset, max_width):
                    return buffer, curpos, scroll_offset

                inputstring(
                    function_key_handlers={
                        "KEY_F2": handle_f2,
                        "KEY_F3": handle_f3,
                    }
                )
            Each handler receives: (buffer, curpos, scroll_offset, max_width)
            Can return 3-tuple to modify input.
        **kwargs: Additional options
            verify: Callable[(str) -> bool] for input validation
            completer: Completer instance for tab completion
            max_len: Maximum buffer length (default 255)
            max_width: Display width (default 80)
            mask: Character mask for password input
            args: Application namespace (passed to verify)

    Returns:
        Entered text (empty string if cancelled)

    Supported Keys:
        Navigation:
            LEFT, RIGHT: Move cursor one character
            HOME (Ctrl+A): Jump to line start
            END (Ctrl+E): Jump to line end
            PAGE UP/DOWN: Jump by pagesize characters
        History (when history=True):
            UP: Navigate to previous command
            DOWN: Navigate to next command
        Editing:
            BACKSPACE: Delete character before cursor
            DELETE: Delete character at cursor
            INSERT: Toggle insert/overwrite mode
            Ctrl+U: Cut from start of line to cursor
            Ctrl+W: Cut previous word
            Ctrl+Y: Paste cut text
        Submission & Help:
            ENTER: Submit (with optional verify callback)
            TAB: Complete word (with completer)
            F1: Display help (if f1_help provided)
            F2-F12: Custom handlers (if function_key_handlers provided)

    Insert Mode Indicator:
        When INSERT is pressed to toggle modes, prompt shows:
        - "[INS]" when in insert mode (normal)
        - "[OVR]" when in overwrite mode
        This helps users know if typed chars will insert or replace.

    Thread Safety:
        Command history is protected by internal lock.
        Safe to use from multiple threads.

    Backward Compatibility:
        All new parameters are optional with sensible defaults.
        Existing code continues to work unchanged.

    Example:
        # Basic usage (unchanged from original)
        name = inputstring("Enter name: ")

        # With history
        command = inputstring("$ ", history=True)

        # With F1 help
        value = inputstring(
            "Enter value: ",
            f1_help="Enter a number between 1 and 100"
        )
    """
    global _input_dirty

    max_len: int = kwargs.pop("max_len", 255)
    max_width: int = kwargs.pop("max_width", 80)
    mask: str = kwargs.pop("mask", None)
    completer = kwargs.pop("completer", None)

    verify = kwargs.pop("verify", None)
    args = kwargs.pop("args", None)  # argparse.Namespace()

    noneok = kwargs.pop("noneok", False)

    # NEW: Initialize history if enabled
    _history = None
    if history:
        _history = InputHistory(
            maxsize=kwargs.pop("history_maxsize", INPUTSTRING_DEFAULT_HISTORY_SIZE)
        )

    # NEW: Initialize insert mode tracking
    _insert_mode = True  # Start in insert mode

    # NEW: Remove new parameters from kwargs before passing to handlers
    # These are handled separately and shouldn't be passed to verify() or other handlers
    kwargs.pop("history", None)
    kwargs.pop("pagesize", None)
    kwargs.pop("beep_on_error", None)
    kwargs.pop("f1_help", None)
    kwargs.pop("function_key_handlers", None)

    # NEW: Pass function key handlers and other options to kwargs for use in handlers
    kwargs["_history"] = _history
    kwargs["_history_enabled"] = history
    kwargs["_insert_mode"] = _insert_mode
    kwargs["_function_key_callbacks"] = function_key_handlers or {}
    kwargs["f1_help"] = f1_help
    kwargs["pagesize"] = pagesize
    kwargs["beep_on_error"] = beep_on_error

    if oldvalue is None:
        buffer = ""
    elif isinstance(oldvalue, str):
        buffer = oldvalue
    else:
        buffer = str(oldvalue)
    curpos = len(buffer)

    scroll_offset = 0
    last_matches = []
    tab_count = 0

    cursor_pos = get_cursor_position()
    if isinstance(cursor_pos, tuple) and len(cursor_pos) == 2:
        start_row, start_col = int(cursor_pos[0]), int(cursor_pos[1])
    else:
        start_row, start_col = 1, 1

    echo(f"{{curpos:{start_row},{start_col}}}", end="", flush=True)
    echo(prompt, end="", flush=True)

    prompt_len: int = int(rendered_length(prompt))
    input_col_start = start_col + prompt_len

    def enter_handler(buffer, curpos, scroll_offset, max_width):
        return handle_key_enter(
            buffer,
            curpos,
            scroll_offset,
            max_width,
            verify=verify,
            args=args,
            prompt=prompt,
            mask=mask,
            start_row=start_row,
            start_col=start_col,
            input_col_start=input_col_start,
            noneok=noneok,
            **kwargs,
        )

    # NEW: Create closures for handlers that need access to context (history, pagesize, etc.)
    def history_previous_handler(buffer, curpos, scroll_offset, max_width):
        if not _history:
            return buffer, curpos, scroll_offset
        prev_entry = _history.get_previous()
        if prev_entry is not None:
            # Load history entry into buffer
            new_curpos = len(prev_entry)
            return prev_entry, new_curpos, 0
        return buffer, curpos, scroll_offset

    def history_next_handler(buffer, curpos, scroll_offset, max_width):
        if not _history:
            return buffer, curpos, scroll_offset
        next_entry = _history.get_next()
        if next_entry is not None:
            # Load history entry
            new_curpos = len(next_entry)
            return next_entry, new_curpos, 0
        else:
            # At end of history (new input), clear buffer
            return "", 0, 0

    def delete_handler(buffer, curpos, scroll_offset, max_width):
        if curpos >= len(buffer):
            # At or past end - beep if enabled
            if beep_on_error:
                echo("{bell}", end="", flush=True)
            return buffer, curpos, scroll_offset
        # Delete character at cursor
        new_buffer = buffer[:curpos] + buffer[curpos + 1 :]
        return new_buffer, curpos, scroll_offset

    def pageup_handler(buffer, curpos, scroll_offset, max_width):
        new_curpos = max(0, curpos - pagesize)
        # Adjust scroll offset to keep cursor visible
        if new_curpos < scroll_offset:
            new_scroll = new_curpos
        else:
            new_scroll = scroll_offset
        return buffer, new_curpos, new_scroll

    def pagedown_handler(buffer, curpos, scroll_offset, max_width):
        new_curpos = min(len(buffer), curpos + pagesize)
        # Adjust scroll offset to keep cursor visible
        if new_curpos >= scroll_offset + max_width:
            new_scroll = new_curpos - max_width + 1
        else:
            new_scroll = scroll_offset
        return buffer, new_curpos, new_scroll

    def help_handler(buffer, curpos, scroll_offset, max_width):
        return handle_help(
            buffer,
            curpos,
            scroll_offset,
            max_width,
            f1_help=f1_help,
            help=help,
        )

    # NEW: Create closures for function key handlers (F2-F12)
    _function_key_callbacks = function_key_handlers or {}

    def make_function_key_handler(key_name: str):
        """Factory to create closures for F2-F12 handlers."""

        def function_key_handler(
            buffer: str, curpos: int, scroll_offset: int, max_width: int
        ) -> Tuple[str, int, int]:
            if key_name in _function_key_callbacks:
                handler = _function_key_callbacks[key_name]
                # Call the custom handler
                result = handler(buffer, curpos, scroll_offset, max_width)
                if result is not None:
                    return result
            # If no custom handler or handler returns None, return unchanged state
            return buffer, curpos, scroll_offset

        return function_key_handler

    with _key_actions_lock:
        KEY_ACTIONS["KEY_ENTER"] = enter_handler
        # Override history handlers with closures
        if _history:
            KEY_ACTIONS["KEY_UP"] = history_previous_handler
            KEY_ACTIONS["KEY_DOWN"] = history_next_handler
        # Override other new handlers with closures
        KEY_ACTIONS["KEY_DELETE"] = delete_handler
        KEY_ACTIONS["KEY_PAGEUP"] = pageup_handler
        KEY_ACTIONS["KEY_PAGEDOWN"] = pagedown_handler
        KEY_ACTIONS["KEY_F1"] = help_handler
        # NEW: Override function key handlers with closures
        for key_num in range(2, 13):  # F2 through F12
            key_name = f"KEY_F{key_num}"
            KEY_ACTIONS[key_name] = make_function_key_handler(key_name)

    _current_display_str = None
    done = False

    while not done:
        with _current_stream_lock:
            if _input_dirty:
                redraw_line(
                    prompt=prompt,
                    buffer=buffer,
                    max_len=max_width,
                    start_row=start_row,
                    start_col=start_col,
                    curpos=curpos,
                    scroll_offset=scroll_offset,
                    max_width=max_width,
                    mask=mask,
                    insert_mode=_insert_mode,
                )
                _input_dirty = False
                _current_display_str = None

        display_str = buffer[scroll_offset : scroll_offset + max_width]

        if _current_display_str != display_str:
            # Don't hold lock - echo() manages its own locking internally
            # Holding the lock here would deadlock when echo() tries to acquire it again
            echo(
                f"{{curpos:{start_row},{input_col_start}}}{' ' * max_width}",
                end="",
                flush=True,
            )

            echo(f"{{curpos:{start_row},{input_col_start}}}", end="")
            if mask is not None:
                echo(mask * len(display_str), end="", flush=True)
            else:
                echo(display_str, end="", flush=True, raw=True)

            _current_display_str = display_str

        cursor_display_col = input_col_start + (curpos - scroll_offset)
        # Position cursor BEFORE getch() without holding lock during the call
        echo(f"{{curpos:{start_row},{cursor_display_col}}}", end="", flush=True)

        ch = getch(
            timeout=INPUTSTRING_GETCH_TIMEOUT,
            fire_events=False,
            check_notifications=False,
        )
        if ch is None:
            continue

        if ch == "KEY_TAB" and callable(completer):
            buffer, curpos, scroll_offset, last_matches, tab_count, start_row = (
                handle_tab_manager(
                    buffer,
                    curpos,
                    scroll_offset,
                    max_width,
                    completer,
                    last_matches,
                    tab_count,
                    prompt,
                    max_len,
                    start_row,
                    start_col,
                    **kwargs,
                )
            )
            _current_display_str = None

        with _key_actions_lock:
            if ch in KEY_ACTIONS:
                result = KEY_ACTIONS[ch](buffer, curpos, scroll_offset, max_width)

                if ch == "KEY_ENTER":
                    # Enter handler returns 5-tuple; other handlers return 3-tuple
                    buffer, curpos, scroll_offset, accepted, need_redraw = result  # type: ignore[assignment]
                    if accepted:
                        # NEW: Add non-empty input to history (if enabled)
                        if _history and buffer and buffer.strip():
                            _history.add_entry(buffer)
                        return buffer
                    if need_redraw:
                        _current_display_str = None
                    continue

                buffer, curpos, scroll_offset = result  # type: ignore[assignment]
                last_matches = []
                tab_count = 0
            else:
                if len(ch) == 1:
                    if len(buffer) < max_len or _insert_mode is False:
                        # NEW: Support insert/overwrite modes
                        if _insert_mode:
                            # INSERT MODE: Insert character, shift rest right
                            buffer = buffer[:curpos] + ch + buffer[curpos:]
                        else:
                            # OVERWRITE MODE: Replace character at cursor
                            if curpos < len(buffer):
                                buffer = buffer[:curpos] + ch + buffer[curpos + 1 :]
                            else:
                                # At end of buffer in overwrite mode, append
                                buffer = buffer + ch
                        curpos += 1
                last_matches = []
                tab_count = 0

        scroll_offset = adjust_scroll_offset(curpos, scroll_offset, max_width)

    return buffer
