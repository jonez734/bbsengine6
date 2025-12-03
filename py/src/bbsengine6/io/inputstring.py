import sys
from . import terminal # New import to fix terminal.columns() access
from asimov.io.echo import echo
from asimov.io.getch import getch_str as getch
from asimov.io.common import get_cursor_position, _current_stream_lock, _cursor_row, _cursor_col
from asimov.io.util import setbottombar, screen_init, terminal_lines
from ..common import logentry
import re # Added for word boundary finding in handle_cutpreviousword

# --- 0. MANDATORY MISSING DEFINITIONS & GLOBALS ---

# Global variable for clipboard content, stored as a list of strings (lines).
yank_buffer = []

# Stub for missing cursor movement utility (essential for redraw_line)
def move_cursor(row, col):
    """Placeholder for actual cursor movement utility."""
    echo(f"{{curpos:{row},{col}}}", end="", flush=True)

# Stubs for missing completion utilities
def get_current_word(buffer, curpos):
    """Stub: Returns (prefix, word_start_index, word_end_index)."""
    # Simple stub assumes completion happens at the end of the line
    return buffer, 0, len(buffer)

def common_prefix(matches):
    """Stub: Returns the longest common prefix string."""
    if not matches: return ""
    return matches[0] # Simplistic stub

# --- 1. Global Key Actions Dictionary ---
KEY_ACTIONS = {}

def add_key_mapping(key_string, action_lambda):
    """Adds or updates a key mapping."""
    KEY_ACTIONS[key_string] = action_lambda

def remove_key_mapping(key_string):
    """Removes a key mapping."""
    if key_string in KEY_ACTIONS:
        del KEY_ACTIONS[key_string]

# --- 2. Helper Functions (State Logic) ---

def handle_left(buffer, curpos, scroll_offset, max_width):
    if curpos > 0:
        curpos -= 1
    return buffer, curpos, scroll_offset

def handle_right(buffer, curpos, scroll_offset, max_width):
    if curpos < len(buffer):
        curpos += 1
    else:
        echo(f"{{bell}}", end="")
    return buffer, curpos, scroll_offset

def handle_home(buffer, curpos, scroll_offset, max_width):
    # Home resets cursor and scroll offset
    return buffer, 0, 0

def handle_end(buffer, curpos, scroll_offset, max_width):
    # End moves cursor to the end of the buffer
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
    """
    Cuts the text from the current cursor position back to the beginning of the line (Ctrl+U).
    The cut text is saved to the yank_buffer.
    """
    global yank_buffer

    # Text to cut (from start of buffer up to the cursor)
    cut_text = buffer[:curpos]

    # 1. Save the cut text to the yank buffer
    # If this is part of a consecutive cut, append the text. Otherwise, start a new yank buffer.
    if cut_text:
        yank_buffer = [cut_text]

    # 2. Update the buffer: keep only the text from the cursor position onward
    buffer = buffer[curpos:]

    # 3. Reset cursor and scroll offset
    curpos = 0
    scroll_offset = 0

    return buffer, curpos, scroll_offset

def handle_cutpreviousword(buffer, curpos, scroll_offset, max_width):
    """
    Cuts the word immediately preceding the cursor (Ctrl+W).
    The cut text is saved to the yank_buffer.
    """
    global yank_buffer

    # Use regular expression to find the previous word boundary
    # This finds the position where the word starts
    word_end = curpos

    # 1. Find the first non-word character (whitespace or punctuation) to the left
    # This loop handles trailing whitespace/non-word characters
    while word_end > 0 and not re.match(r'\w', buffer[word_end-1]):
        word_end -= 1

    # 2. Find the start of the preceding word
    word_start = word_end
    while word_start > 0 and re.match(r'\w', buffer[word_start-1]):
        word_start -= 1

    # If no text was found to cut, return current state
    if word_start == word_end:
        return buffer, curpos, scroll_offset

    cut_text = buffer[word_start:curpos]

    # 3. Save the cut text to the yank buffer
    if cut_text:
        yank_buffer = [cut_text]

    # 4. Update the buffer: remove the cut text
    buffer = buffer[:word_start] + buffer[curpos:]
    curpos = word_start

    # Update scroll offset if cursor moved left
    if curpos < scroll_offset:
        scroll_offset = curpos

    return buffer, curpos, scroll_offset

def handle_copy(buffer, curpos, scroll_offset, max_width):
    """Copies the entire current line buffer to the yank_buffer."""
    global yank_buffer
    # Store the entire line as a single item in the list
    yank_buffer = [buffer]
    return buffer, curpos, scroll_offset

def handle_cut(buffer, curpos, scroll_offset, max_width):
    """Cuts the entire current line buffer to the yank_buffer and clears the line."""
    global yank_buffer
    # 1. Copy the current line to the yank buffer
    yank_buffer = [buffer]

    # 2. Clear the line buffer and reset cursor/scroll state
    buffer = ""
    curpos = 0
    scroll_offset = 0

    return buffer, curpos, scroll_offset

def handle_yank(buffer, curpos, scroll_offset, max_width):
    """Pastes the content of yank_buffer into the current line."""
    global yank_buffer

    # If yank_buffer is a list of lines, rejoin them with newlines for pasting
    yank_text = "\n".join(yank_buffer)

    # 1. Insert the yanked text at the cursor position
    buffer = buffer[:curpos] + yank_text + buffer[curpos:]

    # 2. Move the cursor past the inserted text
    curpos += len(yank_text)

    return buffer, curpos, scroll_offset

def handle_help(buffer, curpos, scroll_offset, max_width):
    logentry("handle_help.100: trace")
    return buffer, curpos, scroll_offset

# --- 3. Tab Completion Logic (Separated for clarity) ---

def handle_tab_manager(buffer, curpos, scroll_offset, max_width, completer, last_matches, tab_count, prompt, max_len, start_row, start_col):
    matches = completer(buffer, curpos)

    if not matches:
        return buffer, curpos, scroll_offset, last_matches, tab_count

    prefix, word_start, word_end = get_current_word(buffer, curpos)

    if len(matches) == 1:
        word = matches[0]
        buffer = buffer[:word_start] + word + buffer[word_end:]
        curpos = word_start + len(word)

        # --- Recalculate scroll_offset after completion (New logic) ---
        if curpos >= scroll_offset + max_width:
            scroll_offset = curpos - max_width + 1
        elif curpos < scroll_offset:
            scroll_offset = curpos
        if scroll_offset < 0:
            scroll_offset = 0
        # ----------------------------------------------------

        # Pass the new scroll state to redraw_line
        redraw_line(prompt, buffer, max_len, start_row, start_col, curpos, scroll_offset, max_width)
        tab_count = 0
        last_matches = []
    else:
        if matches == last_matches and tab_count == 1: # Second tab press
            echo("\n")
            print_matches(matches)
            # Restore line, respecting the current scroll position
            redraw_line(prompt, buffer, max_len, start_row, start_col, curpos, scroll_offset, max_width)
            tab_count = 0
        else:
            lcp = common_prefix(matches)
            if lcp and lcp != prefix:
                buffer = buffer[:word_start] + lcp + buffer[word_end:]
                curpos = word_start + len(lcp)

                # --- Recalculate scroll_offset after LCP insertion (New logic) ---
                if curpos >= scroll_offset + max_width:
                    scroll_offset = curpos - max_width + 1
                elif curpos < scroll_offset:
                    scroll_offset = curpos
                if scroll_offset < 0:
                    scroll_offset = 0
                # ----------------------------------------------------

                # Pass the new scroll state to redraw_line
                redraw_line(prompt, buffer, max_len, start_row, start_col, curpos, scroll_offset, max_width)

            last_matches = matches
            tab_count = 1

    return buffer, curpos, scroll_offset, last_matches, tab_count


# --- 4. Display Functions ---

def redraw_line(prompt, buffer, max_len, start_row, start_col, curpos, scroll_offset, max_width):
    """
    Clears and redraws only the visible portion of the line.
    This is used primarily for cleaning up after printing tab matches.
    """
    input_col_start = start_col + len(prompt)

    # 1. Clear the old line from the prompt start
    echo(f"\r{prompt}{' ' * max_width}", end="", flush=True)

    # 2. Calculate and print the displayable part
    display_str = buffer[scroll_offset : scroll_offset + max_width]

    echo(f"{{curpos:{start_row},{input_col_start}}}", end="")
    echo(f"{display_str}", end="", flush=True, raw=True)

    # 3. Position the cursor
    move_cursor(start_row, input_col_start + (curpos - scroll_offset))


def print_matches(matches: list[str]):
    """Print matches in neat rows/columns depending on terminal width."""
    # Uses the local import `terminal`
    cols = terminal.columns()
    longest = max(len(m) for m in matches) + 2
    per_line = max(1, cols // longest)

    for i, m in enumerate(matches, 1):
        echo(m.ljust(longest))
        if i % per_line == 0:
            echo("{f6}", end="")
    if len(matches) % per_line != 0:
        echo("{f6}", end="")

# --- 5. Initial Mapping Setup ---
add_key_mapping("KEY_LEFT",      handle_left)
add_key_mapping("KEY_RIGHT",     handle_right)
add_key_mapping("KEY_HOME",      handle_home)
add_key_mapping("KEY_CTRL_A",    handle_home)
add_key_mapping("KEY_END",       handle_end)
add_key_mapping("KEY_CTRL_E",    handle_end)
add_key_mapping("KEY_BACKSPACE", handle_backspace)

# Mapped to Ctrl+U - Now correctly saves cut text to yank_buffer
add_key_mapping("KEY_CUTTOBOL",  handle_cuttobol)
# Mapped to Ctrl+W - New function to cut the previous word
add_key_mapping("KEY_CTRL_W",    handle_cutpreviousword)

# Other key mappings (Commented out Ctrl+C and Ctrl+X as requested)
# add_key_mapping("KEY_CTRL_C",    handle_copy)
# add_key_mapping("KEY_CTRL_X",    handle_cut)
add_key_mapping("KEY_YANK",      handle_yank)
add_key_mapping("KEY_F1",        handle_help)

# --- 6. Main Input Function (Fixed) ---

def inputstring(prompt="> ", max_len:int=255, max_width=80, mask:str=None, completer=None):
    buffer = ""
    curpos = 0
    scroll_offset = 0

    # Initialize tab completion state variables
    last_matches = []
    tab_count = 0

    (start_row, start_col) = get_cursor_position()

    prompt_len = len(prompt)
    echo(f"{{curpos:{start_row},{start_col}}}{prompt}", end="", flush=True)

    input_col_start = start_col + prompt_len

    # State variable to track the *visible* part of the line.
    _current_display_str = None
    cursor_display_col = input_col_start + (curpos - scroll_offset)

    done = False
    while not done:
        # 1. Redraw the input area
        display_str = buffer[scroll_offset : scroll_offset + max_width]

        # Optimization: Only redraw the visible text if it has changed
        if _current_display_str != display_str:
            # Clear the old input area for clean redraw
            echo(f"{{curpos:{start_row},{input_col_start}}}{' ' * max_width}", end="", flush=True)

            # Print the current viewable part of the buffer
            echo(f"{{curpos:{start_row},{input_col_start}}}", end="")
            if mask is not None:
                echo(f"{mask*len(display_str)}", end="", flush=True)
            else:
                echo(f"{display_str}", end="", flush=True, raw=True)

            _current_display_str = display_str

        # Calculate and position the cursor
        cursor_display_col = input_col_start + (curpos - scroll_offset)
        echo(f"{{curpos:{start_row},{cursor_display_col}}}", end="", flush=True)

        _cursor_row = start_row
        _cursor_col = cursor_display_col
        
        # 2. get input
        ch = getch(timeout=0.015)
        if ch == "KEY_ENTER":
            echo("{f6}", end="", flush=True) # Reset terminal state/colors on Enter
            return buffer
        elif ch is None:
            continue

        # 3. Handle Tab Completion
        if ch == "KEY_TAB" and callable(completer):
            # The manager now handles scroll_offset recalculation and passes it to redraw_line
            buffer, curpos, scroll_offset, last_matches, tab_count = handle_tab_manager(
                buffer, curpos, scroll_offset, max_width, completer, last_matches, tab_count,
                prompt, max_len, start_row, start_col
            )
            # Redraw is handled inside the manager for efficiency,
            # but we still reset the display string cache here.
            _current_display_str = None

        # 4. Execute Mapped Action (Special Keys)
        elif ch in KEY_ACTIONS:
            buffer, curpos, scroll_offset = KEY_ACTIONS[ch](
                buffer, curpos, scroll_offset, max_width
            )
            # Reset tab completion state on any non-tab key action
            last_matches = []
            tab_count = 0

        elif len(ch) == 1:
            if len(buffer) < max_len:
                # Insert the character
                buffer = buffer[:curpos] + ch + buffer[curpos:]
                curpos += 1
            # Reset tab completion state on character insertion
            last_matches = []
            tab_count = 0

        # 5. Handle Scrolling Logic (Key Requirement)
        if curpos >= scroll_offset + max_width:
            scroll_offset = curpos - max_width + 1
        elif curpos < scroll_offset:
            scroll_offset = curpos

        if scroll_offset < 0:
            scroll_offset = 0

    return buffer
