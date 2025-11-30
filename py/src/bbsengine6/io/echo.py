# ----------------------------
# Token definition
# ----------------------------

# kind: WORD, WHITESPACE, F6, COMMAND, ACS, COLOR
# value: string content or command name
# args: positional args (list)
# kwargs: keyword args (dict)
# raw: original matched string
# text: whatever is to be output by _write_token()

import re

from dataclasses import dataclass, field
from typing import List, Dict, Optional

from .const import CSI, BEL, ESC, ECHO_END

from .common import Token, write_current_output_stream, get_cursor_position, _cursor_row, _cursor_col
from ..common import logentry

from . import terminal

from .palette import c64_palette, get_current_palette, get_palette_entry, rgb

_previous_token = Token("UNKNOWN")

_skin = {
"theanswer": 42,
"engine.title.color": "{bggray}{white}",
"engine.title.hrcolor": "{darkgreen}",

"optioncolor": "{white}{bggray}",
"currentoptioncolor": "{bgwhite}{gray}",
"bottombarcolor": "{bggray}{white}",
"promptcolor": "{/bgcolor}{white}", # {lightgray}",
"inputcolor": "{/bgcolor}{green}",
"normalcolor": "{/bgcolor}{lightgray}",
"highlightcolor": "{green}",
"labelcolor": "{/bgcolor}{lightgray}",
"valuecolor": "{/bgcolor}{green}",
"hrcolor": "{/bgcolor}{gray}",
"acscolor": "{/bgcolor}{gray}", # @since 20220916
"sepcolor": "{lightgray}", # @since 20220924

"level.debug": "{bglightblue}{blue}",
"level.warning": "{bgyellow}{black}",
"level.error": "{bgred}{black}",
"level.ok": "{bggreen}{black}",
"level.info": "{bgwhite}{blue}",
"level.crit": "{bgblue}{white]",

"boxcolor": "{darkgreen}",
"titlecolor": "{white}{bggray}",

#"engine.menu.boxcharcolor": "{bglightgray}{darkgreen}",
#"engine.menu.color": "{bggray}",
#"engine.menu.shadowcolor": "{bgdarkgray}",
#"engine.menu.cursorcolor": "{bglightgray}{blue}",
#"engine.menu.boxcolor": "{bgblue}{green}",
#"engine.menu.titlecolor": "{black}{bglightgray}",
#"engine.menu.disableditemcolor": "{darkgray}",
#"engine.menu.resultfailedcolor": "{bgred}{white}",
}

_box = {
  "ulcorner": "{acs:ulcorner}",
  "hline"   : "{{acs:hline:{width}}}",
  "llcorner": "{acs:llcorner}",
  "lrcorner": "{acs:lrcorner}",
  "vline"   : "{acs:vline}",
  "urcorner": "{acs:urcorner}",
  "ulcorner": "{acs:ulcorner}",
}

# Runtime variables dictionary
_runtime_vars = {}

_runtime_vars.update({"cls": "{erasedisplay}{home}"})
_runtime_vars.update({"home": "{curpos:1,1}"})
_runtime_vars.update({"/all": "{reset}"})

_runtime_vars.update(_skin)

def setvar(name, value):
    """Set a runtime variable for use in {var:<name>} or {<name>} commands."""
    _runtime_vars[name] = value

def getvar(name, default=None):
    return _runtime_vars.get(name, default)

# ----------------------------
# Command patterns
# ----------------------------
_command_handlers = {
    # cursor movements (repeat n)
    "cuu":     r'cup|cuu|cursorup',
    "cud":     r'cud|cursordown',
    "cuf":     r'cuf|cursorforward|cursorright',
    "cub":     r'cub|cursorleft|cursorback|cursorbackward',
    "curpos":  r'curpos',

    "decsc":   r'decsc|savecursor',
    "decrc":   r'decrc|restorecursor',

    "decstbm": r'decstbm',

    "acs":     r'acs',
    "f6":      r'f6',

    # runtime variables
    "var": r'var',
    "attr": r'attr',

    # rgb color
    "rgb": r'rgb',

    # reset attributes and color
    "reset": r'reset',

    # erase display
    "ed": r'ed|erasedisplay',

    # erase line
    "elo": r'el|eraseline',
    "bel": r'bel|bell',

    # clear fg or bg color
    "slashfgcolor": r'/fgcolor',
    "slashbgcolor": r'/bgcolor',

    # doublewidth
    "decdhl": r'fullwidth|/fullwidth',

    # cursor horizontal absolute @since 20251025
    "cha": r'cha',
}

_compiled_command_handlers = [(kind, re.compile(pattern, re.IGNORECASE)) for kind, pattern in _command_handlers.items()]

_whitespace_re = re.compile(r'(\s+)')
_word_re = re.compile(r'[^\s{}]+')

_command_re = re.compile(r"\{(?P<name>/?[a-zA-Z_][a-zA-Z0-9_]*)(?::?(?P<params>[^}]*))\}", re.IGNORECASE)
_emoji_re = re.compile(r":(?P<name>[\w _-]+):", re.IGNORECASE)

# ----------------------------
# Aliases / command expansion
# ----------------------------

command_aliases = {}
##command_aliases = {
##    "cls": "{erasedisplay}{home}",
##    "reset": "{/reset}",
##}

# ----------------------------
# Tokenizer
# ----------------------------
def tokenize(text):
    """Yields Token(kind, value, args, kwargs, raw)"""
    pos = 0
    while pos < len(text):
        # Whitespace
        m = _whitespace_re.match(text, pos)
        if m:
            # emit a single WHITESPACE token
            token = Token("WHITESPACE",
              value=m.group(1),       # optional semantic info
              repeat=len(m.group(0)), # total length of run
              text=None,              # to be filled by handler
              raw=m.group(0)
            )
##            print(f"tokenize.100: {tok=}")
            yield from _handle_whitespace(token)
            pos = m.end()
            continue

        # commands
        m = re.match(_command_re, text[pos:])
        if m:
            name = m.group("name").lower()
            params = m.group("params") or ""
            args, kwargs = parse_command_params(name, params)

##            print(f"tokenize.200: {name=} {args=} {m.group(0)=}")

            tok = Token(kind="COMMAND", value=name, args=tuple(args), kwargs=kwargs, raw=m.group(0))
            yield from _handle_command(tok)
            pos += m.end()
            continue

#        m = re.match(_compiled_command_handlers[1], m.group("name").lower())
#        if m:
#            tok = Token(_compiled_command_handler[0], raw=m.group(0))

        m = re.match(_emoji_re, text[pos:])
        if m:
            name = m.group("name").lower()
            token = Token(kind="EMOJI", value=name, raw=m.group(0))
            yield from _handle_emoji(token)
            pos += m.end()
            continue

        # word
        m = re.match(_word_re, text[pos:])
        if m:
            # WORD: span until next whitespace or command
            end = pos + 1
            while end < len(text) and not text[end].isspace() and text[end] != "{":
                end += 1
            yield Token("WORD", text[pos:end], [], {}, text[pos:end])
            pos = end
            continue

        run = text[pos:]
        yield Token("UNKNOWN", value=run, text=run)
        pos += len(text[pos:])

def to_fullwidth(s: str) -> str:
    """
    Convert a string to its fullwidth Unicode equivalent.
    ASCII 0x21–0x7E are mapped to U+FF01–U+FF5E.
    Space (0x20) maps to U+3000.
    Other characters are left unchanged.
    """
    result = []
    for c in s:
        code = ord(c)
        if c == ' ':
            result.append('\u3000')  # Fullwidth space
        elif 0x21 <= code <= 0x7E:
            result.append(chr(code - 0x21 + 0xFF01))
        else:
            result.append(c)
##    print(f"{result=}")
    return ''.join(result)

# ----------------------------
# token handlers
# ----------------------------
def _handle_word(token, **kwargs):
    global _acs, _raw, _decdhl, _wordwrap, _cursor_col

    width = kwargs.get("width", terminal.columns())

    token.text = token.value
    token.raw = token.value
    token.repeat = 1
    
    if not _raw:
      yield from _acs_off()

##    print(f"_handle_word.100: {_decdhl=}")
    if _decdhl: # and not _wordwrap:
      token.text = to_fullwidth(token.value)
      yield token
      return

    word_len = len(token.text)

    if _wordwrap and _cursor_col + word_len > width - 1:
        # insert hard newline before this word/space
        yield Token("F6", raw="{f6}", text="\n")
        _cursor_col = 0

    _cursor_col += word_len
    yield token

def _handle_whitespace(token):
    """
    Consolidate repeated whitespace characters into tokens.
    For example, a run of 3 newlines becomes:
        Token(kind="WHITESPACE", value="\n", repeat=3, text="\n\n\n")
    """
    global _acs, _raw

    if not _raw:
      yield from _acs_off()

    run = token.value
    i = 0
    while i < len(run):
        ch = run[i]
        repeat = 1
        while i + repeat < len(run) and run[i + repeat] == ch:
            repeat += 1
        yield Token("WHITESPACE",
            value=ch,           # the character itself (' ', '\t', or '\n')
            repeat=repeat,       # how many times it repeats
            text=ch,    # string that will be written
            raw=ch
        )
        i += repeat

# save/restore cursor attributes
@dataclass
class TerminalState():
    cursor_row = 1
    cursor_col = 1
    wordwrap  = True
    has_color = True
    hidden = False
    def __repr__(self):
        return f"TerminalState({self.cursor_row=} {self.cursor_col=})"

_terminal_states = []

_wordwrap = True
_color = True
_acs = False
_raw = False
_decdhl = False
_term_width = None

def _handle_decsc(token):
    global _terminal_states

    (row, col) = get_cursor_position()
    state = TerminalState()
    state.cursor_row = row
    state.cursor_col = col
    state.wordwrap = _wordwrap
    state.color = _color
    _terminal_states.append(state)

##    print(f"_handle_decsc.120: {state=} {_terminal_states=}")
    return iter(())

def _handle_decrc(token):
    global _color, _cursor_col, _cursor_row, _wordwrap, _terminal_states
    
    logentry(f"_handle_decrc.100: {_terminal_states=}")
    if len(_terminal_states) == 0:
      logentry("_handle_decrc.120: _terminal_states length of 0, decsc called?")
    if len(token.args) == 1:
        state = _terminal_states.pop()
    else:
        state = _terminal_states[0]

    yield Token("CURPOS", args=(state.cursor_row, state.cursor_col), text=f"{CSI}{state.cursor_row};{state.cursor_col}H")
    yield Token("WORDWRAP", raw=token.raw, text=f"") # [WORDWRAP: {_wordwrap}]")
    _color = state.color
    _cursor_row = state.cursor_row
    _cursor_col = state.cursor_col
    _wordwrap = state.wordwrap

# ----------------------------
# ACS characters
# ----------------------------
_acs_map = {
    # Box drawing
    "ulcorner": "l",    # ┌
    "urcorner": "k",    # ┐
    "llcorner": "m",    # └
    "lrcorner": "j",    # ┘
    "hline":    "q",    # ─
    "vline":    "x",    # │
    "ttee":     "w",    # ┬
    "btee":     "v",    # ┴
    "ltee":     "u",    # ┤
    "rtee":     "t",    # ├
    "plus":     "n",    # ┼
#    "ttee":        "\u252C", # ┬
#    "btee":        "\u2534", # ┴
#    "ltee":        "\u251C", # ├
#    "rtee":        "\u2524", # ┤
#    "cross":       "\u253C", # ┼

    # Other symbols
    "diamond":      "`",  # ◆
    "checkerboard": "a",  # ▒
    "ht":           "b",  # HT symbol
    "ff":           "c",  # FF symbol
    "cr":           "d",  # CR symbol
    "lf":           "e",  # LF symbol
    "degree":       "f",  # °
    "pluminus":     "g",  # ±
    "board":        "h",  # board of squares
    "lantern":      "i",  # lantern / scan line / bell symbol
    "scan1":        "o",  # scan line 1
    "scan3":        "p",  # scan line 3
    "scan7":        "r",  # scan line 7
    "scan9":        "s",  # scan line 9
    "lequal":       "y",  # ≤
    "gequal":       "z",  # ≥
    "pi":           "{",  # π
    "nequal":       "|",  # ≠
    "sterling":     "}",  # £
    "bullet":       "~",  # • / ≈

    # Extras sometimes present in DEC tables
    "notdef":       "^",  # undefined glyph
    "space":        "_",  # blank space
}

def _acs_on():
  global _acs

  if not _acs:
    _acs = True
##    yield Token(kind="ACS", repeat=1, text=f"{ESC}(0")
##    print("ACSON")
  return iter(())

def _acs_off():
  global _acs

  if _acs:
    _acs = False
    yield Token(kind="ACS", repeat=1, text=f"{ESC}(B")
  return

def _handle_acs(token):
    global _raw, _cursor_col

    if token.value == "acs":
        name = token.args[0]
        repeat = int(token.args[1]) if len(token.args) > 1 else 1
    else:
        name = token.value
        repeat = int(token.args[0]) if len(token.args) == 1 else 1

    _cursor_col += repeat

    if not _raw:
      yield from _acs_on()

    token.kind = "ACS"
    token.text = _acs_map.get(name, "?")
    token.repeat = repeat

    yield token
    return

def _handle_var(token):
    var_name = token.args[0] if token.args else token.value
    var_val = _runtime_vars.get(var_name, "")
    # recursively tokenize the value of the variable
    for t in tokenize(var_val):
        yield t
    return

def _handle_rgb(token):
##    print(f"_handle_rgb.100: {token=}")
    if len(token.args) == 2:
        mode = 38 if token.args[0] == "fg" else 48
        token.text = rgb(mode, token.args[1])
        yield token
        return
    elif len(token.args) == 1:
        token.text = rgb(38, token.args[0])
        yield token
        return

    raise ValueError("Argument Error")
    return

def _handle_curpos(token):
    global _cursor_col, _cursor_row

##    print(f"_handle_curpos.100: foo")
    y = int(token.args[0]) if token.args else 1
    x = int(token.args[1]) if len(token.args) > 1 else 1
    token.text = f"{CSI}{y};{x}H"
    yield token
    _cursor_col = x
    _cursor_row = y
    
def _handle_f6(token):
    global _cursor_col

    repeat = int(token.args[0]) if token.args else 1
    token.repeat = repeat
    token.text = "\n"
    token.kind = "F6"

    yield token

    _cursor_col = 0

    return

def _handle_home(token):
    token.text = f"{CSI}H"
    yield token
    return

# erasedisplay
# tobottom = 1, totop = 2, default = 0 = full
def _handle_ed(token):
    print(f"**** _handle_ed.100: {token=}")
    mode = int(token.args[0]) if len(token.args) == 1 else 2
    token.text = f"{CSI}{mode}J"
    yield token

# 0 = clear right of cursor
# 1 = clear left of cursor
# 2 = clear whole line
# EL0 – Erase in Line (cursor to end of line)
def _handle_elo(token):
    print(f"**** _handle_ed.100: {token=}")
    mode = int(token.args[0]) if len(token.args) == 1 else 0
    token.text = f"{CSI}{mode}K"
    yield token

def _handle_cuu(token):
    repeat = token.args[0] or 1
    token.repeat = repeat
    token.text = f"{CSI}{repeat}A"
    yield token

def _handle_cud(token):
    repeat = token.args[0] or 1
    token.repeat = 1
    token.text = f"{CSI}{repeat}B"
    yield token
    return

def _handle_cuf(token):
    token.repeat = int(token.args[0]) or 1
    token.text = f"{CSI}{repeat}C"
    yield token

def _handle_cub(token):
    repeat = int(token.args[0]) or 1
    print(f"_handle_cub.100: {token=}")
    token.repeat = 1
    token.text = f"{CSI}{repeat}D"
    yield token
    return

def _handle_decstbm(token):
    token.repeat = 1
    if len(token.args) == 0:
        token.text = f"{CSI}r"
        yield token
        return

    t = token.args[0]
    b = token.args[1]
    if t == "0" and b == "0":
        token.text = f"{CSI}r"
    else:
        token.text = f"{CSI}{t};{b}r"
    yield token
    return

def _handle_reset(token):
  global _raw

  mode = "color" if len(token.args) == 0 else token.args[0]
  if mode == "color":
    token.repeat = 1
    token.text = f"{ESC}[0m" # reset fg and bg color
    yield token
  
  if not _raw:
    yield from _acs_off()
  
  if mode == "all":
    yield from _handle_decstbm(token)

  return

def _handle_unknown(token):
    token.text = f"{token.kind=}: no registered handler"
    yield token

def _handle_slashfgcolor(token):
  if len(token.args) > 0:
    raise ValueError
  token.text = f"{CSI}39m"
  yield token

def _handle_slashbgcolor(token):
  if len(token.args) > 0:
    raise ValueError
  token.text = f"{CSI}49m"
  yield token

def _handle_cha(token):
  repeat = token.args[0] if len(token.args) == 1 else 1
  token.kind = "CURSOR"
  token.repeat = 1
  token.text = f"{CSI}{repeat}G"
  yield token

options = {}
def setoption(opt:str, value):
  global options
  options[opt] = value
  return value

def getoption(opt:str, default=None):
  global options

  return options[opt] if opt in options else default

def _handle_box(token):
    """
    Handle box drawing tokens like:
      {hline:10} → repeat ACS hline 10 times
      {ulcorner} → ACS upper-left corner
    """
    # determine repeat count (default 1)
    repeat = int(token.args[0]) if len(token.args) == 1 else 1
##    print(f"_handle_box.100: {repeat=}", flush=True)

    # map ACS and fallback ASCII chars
#    box_acs = {
#        "ulcorner": "l",
#        "urcorner": "k",
#        "llcorner": "m",
#        "lrcorner": "j",
#        "hline":    "q",    # ─
#        "vline":    "x",    # │
#
#        "ttee":  "w",    # ┬
#        "btee":  "v",    # ┴
#        "ltee":  "u",    # ┤
#        "rtee":  "t",    # ├
#        "plus":  "n",    # ┼
#
#    }

#    box_ascii = {
#        "ulcorner": "+",
#        "urcorner": "+",
#        "llcorner": "+",
#        "lrcorner": "+",
#        "hline": "-",
#        "vline": "|",
#    }

    name = token.value
    acs_char = _acs_map.get(name, "?")
#    ascii_char = box_ascii.get(name, "?")


    # enter ACS mode if needed
    if not _raw:
      yield from _acs_on()

    token.kind = "ACS"
    token.repeat = repeat
    token.text = acs_char
    yield token
    return

PARAM_SPLIT_RE = re.compile(r"[:,]")
def parse_command_params(name, params):
    args = [] # [name,]
    kwargs = {}
    if not params:
        return args, kwargs

    for part in PARAM_SPLIT_RE.split(params):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            kwargs[k.strip()] = v.strip()
        elif part:
            args.append(part)
    return args, kwargs

def handler_dispatch(token):
    """Yield from the appropriate handler given a token."""

    cmd = token.value.lower()

    for kind, regex in _compiled_command_handlers:
        if regex.fullmatch(cmd):
            handler_name = f"_handle_{kind}"
            handler = globals().get(handler_name)
            if callable(handler):
                result = handler(token)
                if result is None:
                    return

                if hasattr(result, "__iter__") and not isinstance(result, str):
                    yield from result
                    return
                break
    token.text = str(token.raw)
    yield token
    return False

def _handle_bel(token):
    token.text = BELL
    yield token

_unicode = {
##    "ulcorner":    "\u250C", # ┌
##    "urcorner":    "\u2510", # ┐
##    "llcorner":    "\u2514", # └
##    "lrcorner":    "\u2518", # ┘
##    "hline":       "\u2500", # ─
##    "vline":       "\u2502", # │
##    "ttee":        "\u252C", # ┬
##    "btee":        "\u2534", # ┴
##    "ltee":        "\u251C", # ├
##    "rtee":        "\u2524", # ┤
##    "cross":       "\u253C", # ┼
    "dblhline":    "\u2550", # ═
    "dblvline":    "\u2551", # ║
    "dblul":       "\u2554", # ╔
    "dblur":       "\u2557", # ╗
    "dblll":       "\u255A", # ╚
    "dbllr":       "\u255D", # ╝
    "arrow":       "\u2192", # →
    "arrow_left":  "\u2190", # ←
    "arrow_up":    "\u2191", # ↑
    "arrow_right": "\u2192", # →
    "arrow_down":  "\u2193", # ↓
}

def _handle_unicode(token):
  if token.kind in _unicode:
    token.text = _unicode[token.kind]
    yield token

def _handle_command(token, **kwargs): # palette=None, vars=None):
    """
    Processes a single command token and yields one or more Tokens.
    
    Args:
        token: Token of kind COMMAND from tokenize()
        _runtime_vars: optional dict of runtime variables
    Yields:
        Token instances (WORD, WHITESPACE, F6, etc.)
    """
    global _acs

    # command name is lowercase
    cmd = token.value.lower()
    args = token.args
    kwargs = token.kwargs
    raw  = token.raw
    repeat = token.repeat

    yield from _acs_off()

    # Palette color
    if cmd.lstrip('/') in get_current_palette():
        token.text = get_palette_entry(cmd)
        yield token
        return

    if cmd in _runtime_vars:
        yield from _handle_var(token)
        return

    if cmd.lstrip('/') in ANSI_ATTRS:
        yield from _handle_attr(token)
        return

##    if cmd in _box:
##        yield from _handle_box(token)
##        return

    if cmd in _acs_map:
        yield from _handle_acs(token)
        return
      
    if cmd in _unicode:
        yield from _handle_unicode(token)
        return

    if cmd in _emoji:
        yield from _handle_emoji(token)
        return

    yield from handler_dispatch(token)
    return

    # CHA
    if cmd == "cha":
        col = int(token.args[0]) if token.args else 1
        yield Token("CHA", args=(col,))
        return

_emoji = {
  "grin":                   "\U0001f600",
  "smile":                  "\U0001f642",
  "rofl":                   "\U0001f923",
  "wink":                   "\U0001f609",
  "thinking":               "\U0001f914",
  "sunglasses":             "\U0001f60e",
  "100":                    "\U0001f4af",
  "thumbup":                "\U0001f44d",
  "thumbdown":              "\U0001f44e",
  "vulcan":                 "\U0001f596",
  "spiral":                 "\U0001f4ab",
  "fire":                   "\U0001f525",
  "bank":                   "\U0001f3e6",
  "house":                  "\U0001f3e0",
  "military-helmet":        "\U0001fa96",
  "door":                   "\U0001f6aa",
  "receipt":                "\U0001f9fe",
  "newspaper":              "\U0001f4f0",
  "prince":                 "\U0001f934",
  "princess":               "\U0001f478",
  "thread":                 "\U0001f9f5",
  "ice":                    "\U0001f9ca",
  "moneybag":               "\U0001f4b0",
  "person":                 "\U0001f9d1",
  "sun":                    "\U00002600", # @see https://emojipedia.org/sun/
  "thunder-cloud-and-rain": "\U000026C8", # @see https://emojipedia.org/cloud-with-lightning-and-rain/
  "crop":                   "\U0001F33E", # @see https://emojipedia.org/sheaf-of-rice/
  "horse":                  "\U0001F40E", # @see https://emojipedia.org/horse/
  "cactus":                 "\U0001F335", # @see https://emojipedia.org/cactus/
  "ship":                   "\U0001F6A2", # @see https://emojipedia.org/ship/
  "wood":                   "\U0001FAB5", # @see https://emojipedia.org/wood/
  "link":                   "\U0001F517", # @see https://emojipedia.org/link/
  "anchor":                 "\U00002693", # @see https://emojipedia.org/anchor/
  "ballot-box":             "\U0001F5F3", # @see https://emojipedia.org/ballot-box-with-ballot/ @blacklist breaks monospace font
  "building":               "\U0001F3DB", # @see https://emojipedia.org/classical-building/
  "envelope":               "\U00002709", # @see https://emojipedia.org/envelope/
  "dolphin":                "\U0001F42C", # @see https://emojipedia.org/dolphin/
  "bellhop-bell":           "\U0001F6CE", # @see https://emojipedia.org/bellhop-bell/
  "hotel":                  "\U0001F3E8", # @see https://emojipedia.org/hotel/
  "mousetrap":              "\U0001FAA4", # @see https://emojipedia.org/mouse-trap/

  "waninggibbousmoon":      "\U0001F316",
  "waxinggibbousmoon":      "\U0001F314",
  "waningcrescentmoon":     "\U0001F318",
  "waxingcrescentmoon":     "\U0001F312",
  "lastquartermoon":        "\U0001F317",
  "firstquartermoon":       "\U0001F313",
  "newmoon":                "\U0001F311",
  "fullmoon":               "\U0001F315",

  "sco":                    "\U0000264F", # @see https://emojipedia.org/search/?q=zodiac
  "sag":                    "\U00002650",
  "cap":                    "\U00002651",
  "aqu":                    "\U00002652",
  "pic":                    "\U00002653",
  "ari":                    "\U00002648",
  "tau":                    "\U00002649",
  "gem":                    "\U0000264A",
  "can":                    "\U0000264B",
  "leo":                    "\U0000264C",
  "vir":                    "\U0000264D",
  "lib":                    "\U0000264E",

  "package":                "\U0001F4E6", # @since 20220907 @see https://emojipedia.org/package/
  "compass":                "\U0001F9ED", # @since 20220907
  "worldmap":               "\U0001F5FA", # @since 20220916

  "wolf":                   "\U0001F43A", # @since 20221002
  "person":                 "\U0001F9D1",

  "supervillian":           "\U0001F9B9", # @since 20221016
  "joker":                  "\U0001F0CF", # @since 20221127

  "warning":                "\U000026A0",
  "stopsign":               "\U0001F6D1",

  "dragon":                 "\U0001F409", # @since 20230716 for empyre
  "tree":                   "\U0001F333", # @since 20230824 for empyre
  "wood":                   "\U0001FAB5", # @since 20230824 for empyre

  "cityscape":              "\U0001F3D9", # @since 20230827 for empyre
  "maint":                  "\U0001F6E0", # @since 20230827 for empyre, mm
  "axe":                    "\U0001FA93", # @since 20230827 for mm

  "desert":                 "\U0001F3DC", # @since 20240107 for empyre

  "shopping":               "\U0001F6CD", # @since 20240128

  "farmer":                 "\U0001F9D1", # @since 20240415 for empyre

  "zap":                    "\U000026A1", # @since 20240422 for weather

  "palmtree":               "\U0001F334",
  "evergreentree":          "\U0001F332",

  "tophat":                 "\U0001F3A9",
  "magicwand":              "\U0001FA84",

  "mercenary":				u"\U0001F977",

  "checkmark":              u"\U00002714", #u"\U00002705",
  "crossmark":              u"\U00002718", #u"\U0000274E",
}

def _handle_emoji(token):
    if token.value in _emoji:
        token.text = _emoji[token.value]
    else:
        token.text = token.raw
    yield token

@dataclass
class Attr:
    start: str
    end: str
    state: bool = field(default=None)

# Global stack of active attributes
## ATTR_STACK: list[Attr] = []

ANSI_ATTRS = {
    "bold": Attr(start=f"{CSI}1m", end=f"{CSI}22m"),
    "italic": Attr(start=f"{CSI}3m", end=f"{CSI}23m"),
    "underline": Attr(start=f"{CSI}4m", end=f"{CSI}24m"),
    "strike": Attr(start=f"{CSI}9m", end=f"{CSI}29m"),
    "code": Attr(start=f"{CSI}7m", end=f"{CSI}27m"),  # inverse
    "inverse": Attr(start=f"{CSI}7m", end=f"{CSI}27m"),  # inverse
}

## ATTR_RE = re.compile(r"(/?\w+)")

def _handle_attr(token: Token):
    """
    Mutate a Token containing {attr} or {/attr} to emit corresponding ANSI sequence(s).
    Each ANSI sequence is yielded as a separate Token.
    """

##    print(f"_handle_attr.100: {token.kind=} {token.value=}")

    name = token.value.lstrip("/")
    attr = ANSI_ATTRS.get(name)

    # closing {/bold}
    if token.value.startswith("/"):
        # closing attribute
        attr.state = False
        token.kind = "ATTR"
        token.text = attr.end
        yield token
        return

    # opening attribute {bold}
    attr.state = True
    token.kind = "ATTR"
    token.text = attr.start
    yield token
    return

def _handle_decdhl(token):
    global _decdhl

    if token.value.startswith("/"):
      _decdhl = False
    else:
      _decdhl = True
    return iter(())

def _write_token(token: Token, flush: bool=True, stream=None):
    """
    Write a Token to the current stream (defaults to sys.stdout), interpreting commands and attributes.
    - WORD/WHITESPACE: printed directly
    - F6: hard newline
    - COMMANDS: processed via _handle_command()
    """
    global _raw, _current_output_stream, _current_stream_lock
##    print(f"_write_token.100: {token.kind=} {token.repeat=} {token.value=}", flush=True)
    repeat = int(token.repeat) or 1
    if not _raw:
      text = str(token.text) * repeat
    else:
      text = (str(token.raw) or str(text)) * repeat
    write_current_output_stream(text, flush=flush)
    return

# ----------------------------
# echo_iter(), echo(), and echo_file()
# ----------------------------
def echo_iter(text, width=None, wordwrap=True, palette=None, vars=None, raw=False):
    """
    Generator that yields tokens for rendering.
    Handles WORD, WHITESPACE, F6 (hard newline), attributes, and commands.
    """
    global _runtime_vars, _cursor_col, _raw, _wordwrap, _previous_token
    
    _raw = raw

    if width is None:
        width = terminal.columns()  # default or queried width
    
    palette = palette or c64_palette
    _runtime_vars = _runtime_vars or {}
    _term_width = width

    for token in tokenize(text):
        if token.kind == "COMMAND":
            yield from _handle_command(token)
        elif token.kind == "WORD": # in ("WORD", "WHITESPACE"):
            yield from _handle_word(token)
##            word_len = len(token.text)
##
##           if _wordwrap and _cursor_col + word_len > width - 1:
##                # insert hard newline before this word/space
##                yield Token("F6", raw="{f6}", text="\n")
##                _cursor_col = 0
##
##            _cursor_col += word_len
##            yield token
        elif token.kind == "WHITESPACE":
            if _previous_token.kind == "F6" and token.text == " ":
                continue
            _cursor_col += len(token.text)
            yield token
        elif token.kind == "F6":
            yield from _handle_f6(token)
        else:
            # unknown token, yield as-is
            yield token

        _previous_token = token

def echo(text="", *, palette:dict=None, width:int=None, wordwrap:bool=True, raw:bool=False, flush:bool=True, end=ECHO_END, **kwargs):
    """
    Print text to stdout, interpreting inline commands unless raw=True.
    width: override detected terminal width if not None
    wordwrap: enable/disable word wrapping
    raw: if True, commands are treated as literal text
    flush: if True, flush after writing
    """
    global _raw, _cursor_col, _acs
    
    _raw = raw

    level = kwargs.get("level", None)
    if level is not None:
      return logentry(text, level=level)

    for token in echo_iter(text, width=width, wordwrap=wordwrap, raw=raw, palette=palette):
        _write_token(token, flush=flush)

    # Always write the "end" string
    if end:
        write_current_output_stream(end, flush=flush)
        if end == "\n":
          _cursor_col = 0

def echo_file(filepath, page_size=20, raw=False):
    with open(filepath, 'r') as f:
        line_count = 0
        for line in f:
            echo(line, end='', raw=raw)  # don't add extra newline
            line_count += 1
            if line_count % page_size == 0:
                input("More?")  # wait every page
