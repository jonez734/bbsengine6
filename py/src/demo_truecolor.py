"""Show off 24-bit (true) colour: a hue sweep for the foreground and background.

Each cell is a fixed-width label drawn with a foreground and a background colour. Across a row the
foreground hue turns through the wheel; down the rows the background hue turns in the opposite
direction. Every colour is a full 0-255 triplet, so the terminal has to be truecolor to show all of
them. Each cell is labelled with its foreground hex, so you can read the values back.
"""

import colorsys

from bbsengine6 import io
from bbsengine6.io.palette import rgb_to_hex

COLS = 16
ROWS = 8
CELL_WIDTH = 9


def hue_rgb(fraction: float, value: float = 1.0, saturation: float = 1.0) -> tuple[int, int, int]:
    """A colour on the hue wheel as a 0-255 triplet. fraction is 0..1 around the wheel."""
    r, g, b = colorsys.hsv_to_rgb(fraction % 1.0, saturation, value)
    return round(r * 255), round(g * 255), round(b * 255)


def cell(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> str:
    label = rgb_to_hex(*fg).center(CELL_WIDTH)
    return f"{{rgb:fg,{fg[0]},{fg[1]},{fg[2]}}}{{rgb:bg,{bg[0]},{bg[1]},{bg[2]}}}{label}"


io.echo("{/all}")
for row in range(ROWS):
    line = []
    bg_fraction = row / ROWS
    bg = hue_rgb(-bg_fraction, value=0.35)
    for col in range(COLS):
        fg = hue_rgb(col / COLS)
        line.append(cell(fg, bg))
    io.echo("".join(line) + "{/all}")
io.echo("{/all}")
