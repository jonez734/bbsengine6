from .const import CSI, DEFAULT_PALETTE_NAME


# ----------------------------
# ANSI / C64 color palettes
# ----------------------------
def _clamp_int(x):
    return max(0, min(255, int(round(x))))


def _parse_rgb(rgb):
    """Convert either #RRGGBB string or tuple/list to (r,g,b)"""
    if isinstance(rgb, str) and rgb.startswith("#") and len(rgb) == 7:
        r = int(rgb[1:3], 16)
        g = int(rgb[3:5], 16)
        b = int(rgb[5:7], 16)
        return r, g, b
    elif isinstance(rgb, (tuple, list)) and len(rgb) in (3, 4):
        return rgb[:3]
    else:
        raise ValueError(f"Invalid RGB spec: {rgb!r}")


def darken(prefix, rgb, percentage):
    """
    prefix: 38 (foreground) or 48 (background)
    rgb: tuple/list (r,g,b) or (r,g,b,a) with 0-255 or #RRGGBB string
    percentage: fraction 0..1
    """
    if not (0.0 <= percentage <= 1.0):
        raise ValueError("percentage must be between 0.0 and 1.0")

    r, g, b = _parse_rgb(rgb)

    r = _clamp_int(r * (1 - percentage))
    g = _clamp_int(g * (1 - percentage))
    b = _clamp_int(b * (1 - percentage))

    return f"{CSI}{prefix};2;{r};{g};{b}m"


def rgb(fgbg, triplet):
    """Return ANSI SGR sequence for foreground (38) or background (48). Spec can be #RRGGBB or (r,g,b)"""
    r, g, b = _parse_rgb(triplet)
    return f"{CSI}{fgbg};2;{r};{g};{b}m"


# ANSI palette (foreground)
ansi_palette = {
    "black": f"{CSI}30m",
    "red": f"{CSI}31m",
    "green": f"{CSI}32m",
    "yellow": f"{CSI}33m",
    "blue": f"{CSI}34m",
    "magenta": f"{CSI}35m",
    "cyan": f"{CSI}36m",
    "white": f"{CSI}37m",
    # Light colors
    "lightblack": f"{CSI}90m",
    "lightred": f"{CSI}91m",
    "lightgreen": f"{CSI}92m",
    "lightyellow": f"{CSI}93m",
    "lightblue": f"{CSI}94m",
    "lightmagenta": f"{CSI}95m",
    "lightcyan": f"{CSI}96m",
    "lightwhite": f"{CSI}97m",
    ##    # Reset
    ##    "reset":        f"{CSI}0m",
}

# C64 palette
c64_palette = {
    "black": rgb(38, "#000000"),
    "white": rgb(38, "#ffffff"),
    "red": rgb(38, "#880000"),
    "cyan": rgb(38, "#aaffee"),
    "purple": rgb(38, "#cc44cc"),
    "green": rgb(38, "#00cc55"),
    "blue": rgb(38, "#0000aa"),
    "yellow": rgb(38, "#eeee77"),
    "orange": rgb(38, "#dd8855"),
    "brown": rgb(38, "#664400"),
    "lightred": rgb(38, "#ff7777"),
    "lightcyan": rgb(38, "#33ffff"),
    "lightpurple": rgb(38, "#ff77ff"),
    "lightgreen": rgb(38, "#aaff66"),
    "lightblue": rgb(38, "#0088ff"),
    "lightgray": rgb(38, "#c6c6c6"),
    "gray": rgb(38, "#989898"),
    "darkgray": rgb(38, "#6b6b6b"),
    "darkgreen": darken(38, "#00cc55", 0.20),  # not official c64 color
}


def set_palette(palette_name):
    global _current_palette
    if palette_name == "ansi":
        _current_palette = ansi_palette
    elif palette_name == "c64":
        _current_palette = c64_palette


def get_palette(name=DEFAULT_PALETTE_NAME):
    if name == "c64":
        return c64_palette
    elif name == "ansi":
        return ansi_palette
    return None


def get_current_palette():
    return _current_palette


def get_palette_entry(name):
    global _current_palette
    if _current_palette is None:
        print(f"setting _current_palette")
        set_palette(DEFAULT_PALETTE_NAME)

    return _current_palette[name]


# Background color aliases
def make_bg(palette):
    bg = {}
    for k, v in palette.items():
        bg[f"bg{k}"] = v.replace("38", "48")
    return bg


c64_palette.update(make_bg(c64_palette))

_current_palette = get_palette(DEFAULT_PALETTE_NAME).copy()
