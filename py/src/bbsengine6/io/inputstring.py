from . import terminal, screen

from .echo import echo, rendered_length
from .getch import getch_str as getch
from .common import get_cursor_position, _current_stream_lock, _cursor_row, _cursor_col
from ..common import logentry
import re

# --- 0. MANDATORY DEFINITIONS & GLOBALS ---

yank_buffer = []  # Clipboard

def move_cursor(row, col):
    """Placeholder for actual cursor movement utility."""
    echo(f"{{curpos:{row},{col}}}", end="", flush=True)

def get_current_word(buffer, curpos):
    """Stub: Returns (prefix, word_start_index, word_end_index)."""
    return buffer, 0, len(buffer)

def common_prefix(matches):
    if not matches: return ""
    return matches[0]

# --- 1. Global Key Actions Dictionary ---
KEY_ACTIONS = {}

def add_key_mapping(key_string, action_lambda):
    KEY_ACTIONS[key_string] = action_lambda

def remove_key_mapping(key_string):
    if key_string in KEY_ACTIONS:
        del KEY_ACTIONS[key_string]

# --- 2. Helper Functions ---

def handle_left(buffer, curpos, scroll_offset, max_width):
    if curpos > 0:
        curpos -= 1
    else:
        echo(f"{{bell}}", end="", flush=True)
    return buffer, curpos, scroll_offset

def handle_right(buffer, curpos, scroll_offset, max_width):
    if curpos < len(buffer):
        curpos += 1
    else:
        echo(f"{{bell}}", end="", flush=True)
    return buffer, curpos, scroll_offset

def handle_home(buffer, curpos, scroll_offset, max_width):
    return buffer, 0, 0

def handle_end(buffer, curpos, scroll_offset, max_width):
    curpos = len(buffer)
    return buffer, curpos, scroll_offset

def handle_backspace(buffer, curpos, scroll_offset, max_width):
    if curpos > 0:
        buffer = buffer[:curpos-1] + buffer[curpos:]
        curpos -= 1
    else:
        echo("{bell}", end="", flush=True)
    return buffer, curpos, scroll_offset

def handle_cuttobol(buffer, curpos, scroll_offset, max_width):
    global yank_buffer
    cut_text = buffer[:curpos]
    if cut_text:
        yank_buffer = [cut_text]
    buffer = buffer[curpos:]
    return buffer, 0, 0

def handle_cutpreviousword(buffer, curpos, scroll_offset, max_width):
    global yank_buffer
    word_end = curpos
    while word_end > 0 and not re.match(r'\w', buffer[word_end-1]):
        word_end -= 1
    word_start = word_end
    while word_start > 0 and re.match(r'\w', buffer[word_start-1]):
        word_start -= 1
    if word_start == word_end:
        return buffer, curpos, scroll_offset
    cut_text = buffer[word_start:curpos]
    if cut_text:
        yank_buffer = [cut_text]
    buffer = buffer[:word_start] + buffer[curpos:]
    return buffer, word_start, scroll_offset

def handle_yank(buffer, curpos, scroll_offset, max_width):
    global yank_buffer
    yank_text = "\n".join(yank_buffer)
    buffer = buffer[:curpos] + yank_text + buffer[curpos:]
    return buffer, curpos + len(yank_text), scroll_offset

def handle_help(buffer, curpos, scroll_offset, max_width):
    logentry("handle_help.100: trace")
    return buffer, curpos, scroll_offset

# --- ENTER KEY HANDLER ---

def handle_key_enter(buffer, curpos, scroll_offset, max_width,
                     *, verify, args, prompt, mask,
                     start_row, start_col, input_col_start):
    """
    Returns (buffer, curpos, scroll_offset, accepted, need_redraw)
    """

    echo("{f6}", end="", flush=True)

    # No verify → accept immediately
    if not callable(verify):
        return buffer, curpos, scroll_offset, True, True

    # Run verify as: verify(buffer, *, args=args)
    try:
        ok = verify(buffer, args=args)
    except TypeError as e:
        echo(f"\n[verify ERROR: {e}]{bel}", end="", flush=True, level="error")
        ok = False

    if ok:
        return buffer, curpos, scroll_offset, True, True

    # Verification failed — redraw
    refresh_input_view(
        prompt, buffer, mask,
        start_row, start_col, input_col_start,
        curpos, scroll_offset, max_width
    )

    return buffer, curpos, scroll_offset, False, True

# --- 3. Tab Completion Logic ---

def handle_tab_manager(buffer, curpos, scroll_offset, max_width,
                       completer, last_matches, tab_count,
                       prompt, max_len, start_row, start_col):

    matches = completer(buffer, curpos)
    if not matches:
        return buffer, curpos, scroll_offset, last_matches, tab_count

    prefix, word_start, word_end = get_current_word(buffer, curpos)

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

        redraw_line(prompt, buffer, max_len, start_row, start_col,
                    curpos, scroll_offset, max_width)
        return buffer, curpos, scroll_offset, [], 0

    if matches == last_matches and tab_count == 1:
        echo("\n")
        print_matches(matches)
        redraw_line(prompt, buffer, max_len, start_row, start_col,
                    curpos, scroll_offset, max_width)
        return buffer, curpos, scroll_offset, [], 0

    lcp = common_prefix(matches)
    if lcp and lcp != prefix:
        buffer = buffer[:word_start] + lcp + buffer[word_end:]
        curpos = word_start + len(lcp)

        if curpos >= scroll_offset + max_width:
            scroll_offset = curpos - max_width + 1
        elif curpos < scroll_offset:
            scroll_offset = curpos
        if scroll_offset < 0:
            scroll_offset = 0

        redraw_line(prompt, buffer, max_len, start_row, start_col,
                    curpos, scroll_offset, max_width)

    return buffer, curpos, scroll_offset, matches, 1

# --- 4. Display Functions ---

def redraw_line(prompt, buffer, max_len, start_row, start_col,
                curpos, scroll_offset, max_width):

    input_col_start = start_col + rl

    echo(f"{cha}{prompt}{' ' * max_width}", end="", flush=True)

    display_str = buffer[scroll_offset : scroll_offset + max_width]

    echo(f"{{curpos:{start_row},{input_col_start}}}", end="", flush=True)
    echo(display_str, end="", flush=True, raw=True)

    move_cursor(start_row, input_col_start + (curpos - scroll_offset))

def print_matches(matches):
    cols = terminal.columns()
    longest = max(len(m) for m in matches) + 2
    per_line = max(1, cols // longest)

    for i, m in enumerate(matches, 1):
        echo(m.ljust(longest))
        if i % per_line == 0:
            echo("{f6}", end="")
    if len(matches) % per_line != 0:
        echo("{f6}", end="")

def refresh_input_view(prompt, buffer, mask,
                       start_row, start_col, input_col_start,
                       curpos, scroll_offset, max_width):

    echo(f"{{curpos:{start_row},{start_col}}}{prompt}", end="", flush=True)
    display_str = buffer[scroll_offset:scroll_offset+max_width]

    echo(f"{{curpos:{start_row},{input_col_start}}}{' ' * max_width}",
         end="", flush=True)

    if mask is not None:
        echo(f"{{curpos:{start_row},{input_col_start}}}"
             f"{mask * len(display_str)}",
             end="", flush=True)
    else:
        echo(f"{{curpos:{start_row},{input_col_start}}}", end="", flush=True, raw=False)
        echo(f"{display_str}", end="", flush=True, raw=True)

    echo(f"{{curpos:{start_row},{input_col_start + (curpos - scroll_offset)}}}",
         end="", flush=True)

# --- 5. Initial Key Mappings ---

add_key_mapping("KEY_LEFT",      handle_left)
add_key_mapping("KEY_RIGHT",     handle_right)
add_key_mapping("KEY_HOME",      handle_home)
add_key_mapping("KEY_CTRL_A",    handle_home)
add_key_mapping("KEY_END",       handle_end)
add_key_mapping("KEY_CTRL_E",    handle_end)
add_key_mapping("KEY_BACKSPACE", handle_backspace)
add_key_mapping("KEY_CUTTOBOL",  handle_cuttobol)
add_key_mapping("KEY_CTRL_W",    handle_cutpreviousword)
add_key_mapping("KEY_YANK",      handle_yank)
add_key_mapping("KEY_F1",        handle_help)

# --- 6. MAIN INPUT FUNCTION ---

def inputstring(prompt="> ", oldvalue="", **kwargs):
    max_len:int = kwargs.get("max_len", 255)
    max_width:int = kwargs.get("max_width", 80)
    mask:str = kwargs.get("mask", None)
    completer = kwargs.get("completer", None)

    verify = kwargs.pop("verify", None)
    args = kwargs.pop("args", None)  # argparse.Namespace()

    buffer = oldvalue if oldvalue is not None else ""
    curpos = len(buffer)

    scroll_offset = 0
    last_matches = []
    tab_count = 0

    (start_row, start_col) = get_cursor_position()

    echo(f"{{curpos:{start_row},{start_col}}}{prompt}", end="", flush=True)

    prompt_len = rendered_length(prompt)
    input_col_start = start_col + prompt_len

    # --- CLEAN INLINE ENTER HANDLER (no partial, no class) ---

    def enter_handler(buffer, curpos, scroll_offset, max_width):
        return handle_key_enter(
            buffer, curpos, scroll_offset, max_width,
            verify=verify,
            args=args,
            prompt=prompt,
            mask=mask,
            start_row=start_row,
            start_col=start_col,
            input_col_start=input_col_start,
        )

    KEY_ACTIONS["KEY_ENTER"] = enter_handler

    _current_display_str = None
    done = False

    while not done:
        display_str = buffer[scroll_offset:scroll_offset+max_width]

        if _current_display_str != display_str:
            echo(f"{{curpos:{start_row},{input_col_start}}}{' ' * max_width}",
                 end="", flush=True)

            echo(f"{{curpos:{start_row},{input_col_start}}}", end="")
            if mask is not None:
                echo(mask * len(display_str), end="", flush=True)
            else:
                echo(display_str, end="", flush=True, raw=True)

            _current_display_str = display_str

        cursor_display_col = input_col_start + (curpos - scroll_offset)
        echo(f"{{curpos:{start_row},{cursor_display_col}}}", end="", flush=True)

        _cursor_row = start_row
        _cursor_col = cursor_display_col

        ch = getch(timeout=0.015)
        if ch is None:
            continue

        if ch == "KEY_TAB" and callable(completer):
            buffer, curpos, scroll_offset, last_matches, tab_count = \
                handle_tab_manager(buffer, curpos, scroll_offset, max_width,
                                   completer, last_matches, tab_count,
                                   prompt, max_len, start_row, start_col)
            _current_display_str = None

        elif ch in KEY_ACTIONS:
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

        elif len(ch) == 1:
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
