from . import io
#import ttyio6 as ttyio

bottombarstack = []

# updatebottombar() - imported from bbsengine
# @since 20210222
# @since 20230512 copied from bbsengine5

def updatebottombar(buf: str) -> None:
    """Render the bottom bar on the last terminal line without line wrapping."""
    terminal_height = io.getterminalheight()
    io.echo(
        f"{{decsc}}{{/all}}{{curpos:{terminal_height},0}}{buf}{{eraseline}}{{decrc}}",
        wordwrap=False,
        end=""
    )
    return

# @since 20230512 copied from bbsengine5
def initbottombar(height:int=1):
  terminalheight = io.getterminalheight()
  io.echo("{decsc}{decstbm:0,%d}{decrc}" % (terminalheight-height))

# @since 20230512 copied from bbsengine5
def init(topmargin=0, bottommargin=1):
  io.echo("{f6:3}{cursorup:3}", end="", flush=True)
  initbottombar(height=bottommargin)

#  terminalheight = ttyio.getterminalheight()
#  ttyio.echo(f"{{decsc}}{{decstbm:{topmargin},{terminalheight-bottommargin}}}{{decrc}}") #  % (topmargin, terminalheight-bottommargin)) #  % (topmargin, terminalheight-bottommargin))

  return

# @since 20230523 copied from bbsengine5
# @since 20250517 rewrite
#from wcwidth import wcswidth, wcwidth
def setbottombar(left, right=None, stack: bool = False, width: int = None, **kwargs):
    global bottombarstack

    wcswidth = len
    wcwidth = len

    terminalwidth = width or kwargs.get("width") or io.getterminalwidth() - 2

    def wc_rjust(text, length, padding=' '):
      # from wcwidth import wcswidth
      return padding * max(0, (length - wcswidth(text))) + text

#    def strip_ansi(s: str) -> str:
#      """Remove ANSI escape sequences from a string for display width measurement."""
#      import re
#      return re.sub(r'\x1b\[[0-9;]*m', '', s)

    def resolve_content(value, default, label):
        if callable(value):
            return value()
        elif isinstance(value, str):
            return value
        elif value is None:
            return default
        else:
            io.echo(f"setbottombar: Unexpected {label} type: {type(value)}", level="debug")
            return "ERROR"

    def truncate_to_display_width(text: str, max_width: int) -> str:
        """Truncate a string by display width, ignoring ANSI escape sequences."""
        stripped = io.strip_commands(text)
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
    left_str = f"S: {left_raw}"
    right_str = str(right_raw)

    # Strip ANSI for width calculations
    visible_left = io.strip_commands(left_str)
    visible_right = io.strip_commands(right_str)

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

    updatebottombar(f"{{bottombarcolor}}{buf}{{/all}}")

    if stack:
        bottombarstack.insert(0, buf)

# @since 20240708
# @since 20240517
# setarea = setbottombar

# @since 20230523 copied from bbsengine5
def popbottombar():
  global bottombarstack

  if len(bottombarstack) == 0:
    return

  terminalwidth = io.getterminalwidth()

  if len(bottombarstack) > 0:
    buf = bottombarstack.pop()
    if buf != "":
      updatebottombar(f"{{var:areacolor}}{buf}{{/all}}")
      # updatebottombar(f"{{var:areacolor}}{buf.ljust(terminalwidth-2, '')}{{/all}}")

  return

# @since 20240708
poparea = popbottombar

# @since 20230523
def title(buf):
  return io.terminal.title(buf)

# @since 20210301
# @see https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
# @since 20240102 copied to bbsengine6
def updateprogress(iteration, total, fill="#"):
  terminalwidth = io.terminal.width()
  decimals = 0
  length = terminalwidth-20
  percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
  filledLength = length * iteration // total
  bar = fill * filledLength + '.' * (length - filledLength)
  buf = f"{{var:labelcolor}}Progress [{{var:valuecolor}}{percent:3s}%{{var:labelcolor}}]: [{bar}]{{/fgcolor}}"
  updatebottombar(buf)
  return
