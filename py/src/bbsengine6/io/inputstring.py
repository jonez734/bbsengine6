import inspect
import re
import threading

from . import terminal

from .const import INPUTSTRING_GETCH_TIMEOUT
from .echo import echo, rendered_length, echo_traceback
from .getch import getch_str as getch
from .common import (
    get_cursor_position,
    _current_stream_lock,
    _terminal_state,
    _input_dirty,
)
from .util import logentry

# --- 0. MANDATORY DEFINITIONS & GLOBALS ---

_inputstring_lock = threading.Lock()

# Compiled regex pattern for word character matching (\w includes letters, digits, underscore)
_WORD_CHAR_PATTERN = re.compile(r"\w")


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

    def __init__(self, get_matches=None, **kwargs):
        """Initialize with optional get_matches function and kwargs.

        Args:
            get_matches: Function that takes prefix and returns list of matches.
            **kwargs: Arbitrary parameters (e.g., conn, pool) passed to get_matches.
        """
        # Only set if explicitly passed - don't override subclass methods
        if get_matches is not None:
            self._get_matches_func = get_matches
        # Store kwargs for use by get_matches in subclass
        self.kwargs = kwargs

    def get_matches(self, prefix, **kwargs):
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

    def __call__(self, buffer, **kwargs):
        """Called by inputstring to get completions.

        Args:
            buffer: Current input buffer
            **kwargs: Additional parameters passed to get_matches (including curpos)

        Returns:
            List of matching strings
        """
        curpos = kwargs.get("curpos", len(buffer))
        prefix, word_start, word_end = get_current_word(buffer, curpos)
        # Get the actual word to match (not the prefix before it)
        word = buffer[word_start:word_end]
        result = self.get_matches(word, **kwargs)
        return result if result is not None else []


yank_buffer = []  # Clipboard
_yank_buffer_lock = threading.Lock()

_key_actions_lock = threading.Lock()


def move_cursor(row, col):
    echo(f"{{curpos:{row},{col}}}", end="", flush=True)


def get_current_word(buffer, curpos):
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


def common_prefix(matches):
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


# --- 1. Global Key Actions Dictionary ---
KEY_ACTIONS = {}


def add_key_mapping(key_string, action_lambda):
    with _key_actions_lock:
        KEY_ACTIONS[key_string] = action_lambda


def remove_key_mapping(key_string):
    with _key_actions_lock:
        if key_string in KEY_ACTIONS:
            del KEY_ACTIONS[key_string]


# --- 2. Helper Functions ---


def handle_left(buffer, curpos, scroll_offset, max_width):
    if curpos > 0:
        curpos -= 1
    else:
        echo("{bell}", end="", flush=True)
    return buffer, curpos, scroll_offset


def handle_right(buffer, curpos, scroll_offset, max_width):
    if curpos < len(buffer):
        curpos += 1
    else:
        echo("{bell}", end="", flush=True)
    return buffer, curpos, scroll_offset


def handle_home(buffer, curpos, scroll_offset, max_width):
    return buffer, 0, 0


def handle_end(buffer, curpos, scroll_offset, max_width):
    curpos = len(buffer)
    return buffer, curpos, scroll_offset


def handle_backspace(buffer, curpos, scroll_offset, max_width):
    if curpos > 0:
        buffer = buffer[: curpos - 1] + buffer[curpos:]
        curpos -= 1
    else:
        echo("{bell}", end="", flush=True)
    return buffer, curpos, scroll_offset


def handle_cuttobol(buffer, curpos, scroll_offset, max_width):
    global yank_buffer
    cut_text = buffer[:curpos]
    with _yank_buffer_lock:
        if cut_text:
            yank_buffer = [cut_text]
    buffer = buffer[curpos:]
    return buffer, 0, 0


def handle_cutpreviousword(buffer, curpos, scroll_offset, max_width):
    global yank_buffer
    word_end = curpos
    while word_end > 0 and not re.match(r"\w", buffer[word_end - 1]):
        word_end -= 1
    word_start = word_end
    while word_start > 0 and re.match(r"\w", buffer[word_start - 1]):
        word_start -= 1
    if word_start == word_end:
        return buffer, curpos, scroll_offset
    cut_text = buffer[word_start:curpos]
    with _yank_buffer_lock:
        if cut_text:
            yank_buffer = [cut_text]
    buffer = buffer[:word_start] + buffer[curpos:]
    return buffer, word_start, scroll_offset


def handle_yank(buffer, curpos, scroll_offset, max_width):
    global yank_buffer
    with _yank_buffer_lock:
        yank_text = "\n".join(yank_buffer)
    buffer = buffer[:curpos] + yank_text + buffer[curpos:]
    return buffer, curpos + len(yank_text), scroll_offset


def handle_help(buffer, curpos, scroll_offset, max_width):
    logentry("handle_help.100: trace")
    return buffer, curpos, scroll_offset


# --- ENTER KEY HANDLER ---


def handle_key_enter(
    buffer,
    curpos,
    scroll_offset,
    max_width,
    *,
    verify,
    args,
    prompt,
    mask,
    start_row,
    start_col,
    input_col_start,
    noneok,
    **kwargs,
):
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

        if curpos >= scroll_offset + max_width:
            scroll_offset = curpos - max_width + 1
        elif curpos < scroll_offset:
            scroll_offset = curpos
        if scroll_offset < 0:
            scroll_offset = 0

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

        if curpos >= scroll_offset + max_width:
            scroll_offset = curpos - max_width + 1
        elif curpos < scroll_offset:
            scroll_offset = curpos
        if scroll_offset < 0:
            scroll_offset = 0

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
    prompt,
    buffer,
    max_len,
    start_row,
    start_col,
    curpos,
    scroll_offset,
    max_width,
    mask=None,
):

    input_col_start = start_col + rendered_length(prompt)

    echo(f"{{curpos:{start_row},{start_col}}}", end="", flush=True)
    echo(prompt, end="", flush=True)
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


def print_matches(matches):
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
add_key_mapping("KEY_F1", handle_help)

# --- 6. MAIN INPUT FUNCTION ---


def inputstring(prompt: str = "> ", oldvalue: str = "", /, **kwargs) -> str:
    global _input_dirty

    max_len: int = kwargs.pop("max_len", 255)
    max_width: int = kwargs.pop("max_width", 80)
    mask: str = kwargs.pop("mask", None)
    completer = kwargs.pop("completer", None)

    verify = kwargs.pop("verify", None)
    args = kwargs.pop("args", None)  # argparse.Namespace()

    noneok = kwargs.pop("noneok", False)

    buffer = oldvalue if oldvalue is not None else ""
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

    with _key_actions_lock:
        KEY_ACTIONS["KEY_ENTER"] = enter_handler

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
                )
                _input_dirty = False
                _current_display_str = None

        display_str = buffer[scroll_offset : scroll_offset + max_width]

        if _current_display_str != display_str:
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
        echo(f"{{curpos:{start_row},{cursor_display_col}}}", end="", flush=True)

        with _current_stream_lock:
            _terminal_state.cursor_row = start_row
            _terminal_state.cursor_col = cursor_display_col

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
                    buffer, curpos, scroll_offset, accepted, need_redraw = result
                    if accepted:
                        return buffer
                    if need_redraw:
                        _current_display_str = None
                    continue

                buffer, curpos, scroll_offset = result
                last_matches = []
                tab_count = 0
            else:
                if len(ch) == 1:
                    if len(buffer) < max_len:
                        buffer = buffer[:curpos] + ch + buffer[curpos:]
                        curpos += 1
                last_matches = []
                tab_count = 0

        if curpos >= scroll_offset + max_width:
            scroll_offset = curpos - max_width + 1
        elif curpos < scroll_offset:
            scroll_offset = curpos
        if scroll_offset < 0:
            scroll_offset = 0

    return buffer
