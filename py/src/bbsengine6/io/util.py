from .echo import echo
from .common import terminal_lines, terminal_columns
from .const import MAX_TERMINAL_WIDTH

# ------------------------
# screen related functions
# ------------------------

def screen_init(topmargin=0, bottommargin=1):
  echo("{f6:3}{cursorup:3}", end="", flush=True)
  initbottombar(height=bottommargin)

# -----------
# bottom bar
# -----------
def initbottombar(height:int=1):
  h = terminal_lines() - height
  echo(f"{{savecursor}}{{decstbm:0,{h}}}{{restorecursor}}", flush=True)

#  terminalheight = ttyio.getterminalheight()
#  ttyio.echo(f"{{decsc}}{{decstbm:{topmargin},{terminalheight-bottommargin}}}{{decrc}}") #  % (topmargin, terminalheight-bottommargin)) #  % (topmargin, terminalheight-bottommargin))

  return

def updatebottombar(buf: str) -> None:
    """Render the bottom bar on the last terminal line without line wrapping."""
    echo(f"{{savecursor}}{{bottombarcolor}}{{curpos:{terminal_lines()},0}}{buf}{{restorecursor}}", wordwrap=False, end="", flush=True)
    return

# @since 20230523 copied from bbsengine5
# @since 20250517 rewrite
#from wcwidth import wcswidth, wcwidth
def setbottombar(left, right=None, stack: bool = False, width: int = None, **kwargs):
    global bottombarstack

    wcswidth = len
    wcwidth = len

    terminalwidth = width or kwargs.get("width") or terminal_columns()

    def wc_rjust(text, length, padding=' '):
      # from wcwidth import wcswidth
      return padding * max(0, (length - wcswidth(text))) + text

    def resolve_content(value, default, label):
        if callable(value):
            return value()
        elif isinstance(value, str):
            return value
        elif value is None:
            return default
        else:
            echo(f"setbottombar: Unexpected {label} type: {type(value)}", level="debug")
            return "ERROR"

    def truncate_to_display_width(text: str, max_width: int) -> str:
        """Truncate a string by display width, ignoring ANSI escape sequences."""
        stripped = text # io.strip_commands(text)
        result = ""
        current_width = 0
        for char in stripped:
            char_width = wcwidth(char)
            if char_width < 0:
                char_width = 0
            if current_width + char_width > max_width:
                break
            result += char
            current_width += char_width
        if current_width < wcswidth(stripped):
            if max_width >= 3:
                return result[:-3] + "..."
            else:
                return result
        return result

    # Get values
    left_raw = resolve_content(left, "", "left")
    right_raw = resolve_content(right, "here", "right")

    # Final strings (with formatting)
    left_str = f"{left_raw}"
    right_str = str(right_raw)

    # Strip ANSI for width calculations
    visible_left = left_str # io.strip_commands(left_str)
    visible_right = right_str # io.strip_commands(right_str)

    right_width = wcswidth(visible_right)
    max_total_width = terminalwidth

    # Determine how much space we can give the left
    space_for_left = max_total_width - right_width - 1  # 1 space between left and right

    if space_for_left < 0:
      # Not enough room for left side at all
      buf = f"{right_str.rjust(max_total_width)}"
    else:
      truncated_visible_left = truncate_to_display_width(visible_left, space_for_left)
      visible_truncated_left_width = wcswidth(truncated_visible_left)
      left_padding = " " * (space_for_left - visible_truncated_left_width)
      buf = f"{truncated_visible_left}{left_padding} {right_str} "

#    right_width = wcswidth(visible_right)
#    space_for_left = terminalwidth - right_width - 2
#
#    if space_for_left < 0:
#        buf = f" {right_str} "
#    else:
#        truncated_visible_left = truncate_to_display_width(visible_left, space_for_left)
#        padding = " " * (space_for_left - wcswidth(truncated_visible_left))
#        buf = f" {truncated_visible_left}{padding}{right_str} "

    updatebottombar(f"{{bottombarcolor}}{buf}{{reset}}")

    if stack:
        bottombarstack.insert(0, buf)

# ----------------------------
# Utilities
# ----------------------------
