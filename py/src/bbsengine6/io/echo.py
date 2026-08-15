# echo.py
# Advanced terminal output system with rich text formatting, command parsing, and terminal state management

"""
bbsengine6.io.echo - Terminal output with inline command processing.

This module provides rich text formatting for terminal output via the echo() function and related
utilities. It supports:

- Inline command syntax: {color}, {bold}, {f6} (newline), {indent:n}, {rgb:#RRGGBB}
- Variable substitution: {var:name}
- Emoji support: :smile:, :fire:, etc.
- ACS (Alternate Character Set) box drawing: {ulcorner}, {hline}, {vline}, etc.
- Terminal state management: cursor position, word wrapping, indentation
- Template loading and rendering
- Thread-safe output to configurable streams

Token Processing Flow:
1. tokenize() - Parse input text into Token objects (WORD, WHITESPACE, COMMAND, EMOJI, etc.)
2. echo_iter() - Process tokens through type-specific handlers
3. Handler functions - Convert commands to ANSI escape sequences or output
4. _write_token() - Write final tokens to output stream

Architecture:
- Token-based: All text is converted to Token objects with metadata
- Generator-based: Uses yield for memory efficiency on large texts
- State-managed: Maintains terminal state (colors, positions, wrapping) in TerminalState
- Thread-safe: Uses locks for shared global state (_raw, _runtime_vars, _emoji, output stream)

Key globals:
- _raw: Whether to output raw text without command processing
- _runtime_vars: User-defined variables for substitution
- _emoji: Custom emoji registry
- _terminal_state: Current terminal state (from common.py)
- _state_lock: Protects _raw, _previous_token, _first_line_after_f6
"""

# ----------------------------
# Token definition
# ----------------------------

# Token attributes:
# kind: WORD, WHITESPACE, F6, COMMAND, ACS, COLOR
# value: string content or command name
# args: positional args (list)
# kwargs: keyword args (dict)
# raw: original matched string
# text: whatever is to be output by _write_token()

import os
import re
import threading
from typing import Optional, Any, Dict, List, Tuple, Generator

from dataclasses import dataclass, field

from .const import CSI, BEL, ESC, ECHO_END

from .common import (
    Token,
    write_current_output_stream,
    get_cursor_position,
    _terminal_state,
    _terminal_state_stack,
    _terminal_state_stack_enabled,
    _current_stream_lock,
    _terminal_state_lock,
    _terminal_state_stack_lock,
    TerminalState,
    DEFAULT_INDENT_CHAR,
)
from .util import logentry
from .palette import c64_palette, get_current_palette, get_palette_entry, rgb

from . import terminal

_runtime_vars_lock = threading.Lock()
_emoji_lock = threading.Lock()
_state_lock = threading.Lock()  # Protects: _raw, _previous_token, _first_line_after_f6

_raw = False  # Global state - whether to output raw (without command processing)
_raw_lock = threading.Lock()
_previous_token = Token("UNKNOWN")
_first_line_after_f6 = False  # Don't reduce width on first line after F6

_skin = {
    "theanswer": 42,
    "engine.title.color": "{bggray}{white}",
    "engine.title.hrcolor": "{darkgreen}",
    "optioncolor": "{white}{bggray}",
    "currentoptioncolor": "{bgwhite}{gray}",
    "bottombarcolor": "{bgwhite}{black}",
    "promptcolor": "{/bgcolor}{white}",  # {lightgray}",
    "inputcolor": "{/bgcolor}{green}",
    "normalcolor": "{/bgcolor}{lightgray}",
    "highlightcolor": "{green}",
    "labelcolor": "{/bgcolor}{lightgray}",
    "valuecolor": "{/bgcolor}{green}",
    "hrcolor": "{/bgcolor}{gray}",
    "acscolor": "{/bgcolor}{gray}",  # @since 20220916
    "sepcolor": "{lightgray}",  # @since 20220924
    "level.debug": "{bglightblue}{blue}",
    "level.warning": "{bgyellow}{black}",
    "level.error": "{bgred}{white}",
    "level.fail": "{bgred}{black}",
    "level.ok": "{bggreen}{black}",
    "level.info": "{bgwhite}{blue}",
    "level.crit": "{bgblue}{white}",
    "boxcolor": "{darkgreen}",
    "titlecolor": "{white}{bggray}",
    # "engine.menu.boxcharcolor": "{bglightgray}{darkgreen}",
    # "engine.menu.color": "{bggray}",
    # "engine.menu.shadowcolor": "{bgdarkgray}",
    # "engine.menu.cursorcolor": "{bglightgray}{blue}",
    # "engine.menu.boxcolor": "{bgblue}{green}",
    # "engine.menu.titlecolor": "{black}{bglightgray}",
    # "engine.menu.disableditemcolor": "{darkgray}",
    # "engine.menu.resultfailedcolor": "{bgred}{white}",
    "listbox.boxcolor": "{darkgreen}",
    "listbox.titlecolor": "{inverse}",
    "listbox.item.normal": "{white}",
    "listbox.item.highlighted": "{listbox.item.normal}{inverse}",
    "listbox.item.disabled": "{darkgray}",
    "listbox.bgcolor": "",
    "message.criticalcolor": "{bgred}{white}",
    "message.urgentcolor": "{orange}",
    "message.importantcolor": "{yellow}",
    "message.routinecolor": "{lightgray}",
    "message.datestampcolor": "{darkgray}",
    "message.recipientcolor": "{cyan}",
}

# Runtime variables dictionary
_runtime_vars = {}

_runtime_vars.update({"cls": "{erasedisplay}{home}"})
_runtime_vars.update({"home": "{curpos:1,1}"})
###_runtime_vars.update({"/all": "{reset}"})

_runtime_vars.update(_skin)


def setvar(name: str, value: Any) -> None:
    """Set a runtime variable for use in {var:<name>} or {<name>} commands."""
    with _runtime_vars_lock:
        _runtime_vars[name] = value


def getvar(name: str, default: Any = None) -> Any:
    """Get a runtime variable by name, returning default if not found."""
    with _runtime_vars_lock:
        return _runtime_vars.get(name, default)


def register_emoji(name: str, value: str) -> None:
    """Register a custom emoji for use with :name: syntax."""
    with _emoji_lock:
        _emoji[name] = value


def register_emojis(emojis: Dict[str, str]) -> None:
    """Register multiple custom emojis at once."""
    with _emoji_lock:
        _emoji.update(emojis)


# ----------------------------
# Command patterns
# ----------------------------
_command_handlers = {
    # cursor movements (repeat n)
    "cuu": r"cup|cuu|cursorup",
    "cud": r"cud|cursordown",
    "cuf": r"cuf|cursorforward|cursorright",
    "cub": r"cub|cursorleft|cursorback|cursorbackward",
    "curpos": r"curpos",
    "decsc": r"decsc|savecursor",
    "decrc": r"decrc|restorecursor",
    "decstbm": r"decstbm",
    "acs": r"acs",
    "f6": r"f6",
    "literalopen": r"\{\{",
    "literalclose": r"\}\}",
    # runtime variables
    "var": r"var",
    "attr": r"attr",
    # rgb color
    "rgb": r"rgb",
    # reset attributes and color
    "reset": r"reset",
    # erase display
    "ed": r"ed|erasedisplay",
    # erase line
    "elo": r"el|eraseline",
    "bel": r"bel|bell",
    # clear fg or bg color
    "slashfgcolor": r"/fgcolor",
    "slashbgcolor": r"/bgcolor",
    # doublewidth
    "decdhl": r"fullwidth|/fullwidth",
    # cursor horizontal absolute @since 20251025
    "cha": r"cha",
    "slashall": r"/all",
    # indent
    "indent": r"indent",
}

_compiled_command_handlers = [
    (kind, re.compile(pattern, re.IGNORECASE))
    for kind, pattern in _command_handlers.items()
]

_whitespace_re = re.compile(r"(\s+)")
_word_re = re.compile(r"[^\s{}]+")
_literal_braces_re = re.compile(r"(\{\{|\}\})")

_command_re = re.compile(
    r"\{(?P<name>/?[a-zA-Z_][a-zA-Z0-9_.]*)(?::?(?P<params>[^}]*))\}", re.IGNORECASE
)
_emoji_re = re.compile(r":(?P<name>[\w _-]+):", re.IGNORECASE)

# ----------------------------
# Aliases / command expansion
# ----------------------------

command_aliases = {}


# ----------------------------
# Tokenizer
# ----------------------------
def tokenize(text: Optional[str], **kwargs) -> Generator[Token, None, None]:
    """Yields Token(kind, value, args, kwargs, raw)"""

    if text is None:
        return

    if not isinstance(text, str):
        logentry(
            f"bbsengine.io.echo.tokenize.100: warning: text is not str", level="warn"
        )
        return

    pos = 0
    while pos < len(text):
        # Whitespace
        m = _whitespace_re.match(text, pos)
        if m:
            # emit a single WHITESPACE token
            token = Token(
                "WHITESPACE",
                value=m.group(1),  # optional semantic info
                repeat=len(m.group(0)),  # total length of run
                text=None,  # to be filled by handler
                raw=m.group(0),
            )
            yield from _handle_whitespace(token)
            pos = m.end()
            continue

        # literal braces {{ and }}
        m = re.match(_literal_braces_re, text[pos:])
        if m:
            raw = m.group(0)
            name = "literalopen" if raw == "{{" else "literalclose"
            tok = Token(kind="COMMAND", value=name, args=(), kwargs={}, raw=raw)
            yield from _handle_command(tok)
            pos += m.end()
            continue

        # commands
        m = re.match(_command_re, text[pos:])
        if m:
            name = m.group("name").lower()
            params = m.group("params") or ""
            args, kwargs = parse_command_params(name, params)

            tok = Token(
                kind="COMMAND",
                value=name,
                args=tuple(args),
                kwargs=kwargs,
                raw=m.group(0),
            )
            yield from _handle_command(tok)
            pos += m.end()
            continue

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
        if c == " ":
            result.append("\u3000")  # Fullwidth space
        elif 0x21 <= code <= 0x7E:
            result.append(chr(code - 0x21 + 0xFF01))
        else:
            result.append(c)
    return "".join(result)


# ----------------------------
# token handlers
# ----------------------------
def _handle_word(token, **kwargs):
    """
    Process a WORD token: handle word wrapping and cursor column tracking.

    Emits an F6 (newline) if word would exceed available width.
    Updates cursor position in terminal state.
    """
    global _terminal_state

    width = kwargs.get("width", terminal.columns())

    # --- normalize token ---
    token.text = token.value
    token.raw = token.value
    token.repeat = 1

    # ACS is a rendering concern → emit before word if needed
    with _raw_lock:
        raw_now = _raw
    if not raw_now:
        yield from _acs_off()

    emit_f6 = False
    emit_token = False
    token_text = token.text

    with _current_stream_lock:
        # DEC double-height line → fullwidth rendering
        if _terminal_state.decdwl:
            token_text = to_fullwidth(token.value)
            _terminal_state.cursor_col += len(token_text)
            emit_token = True
        else:
            word_len = len(token_text)

            if _terminal_state.wordwrap:
                global _first_line_after_f6
                if _terminal_state.cursor_col >= width:
                    _terminal_state.cursor_col = 0
                # Account for indent always (first line gets indent too)
                available_width = width - _terminal_state.indent
                if _terminal_state.cursor_col + word_len > available_width:
                    emit_f6 = True
                    _terminal_state.cursor_col = _terminal_state.indent
                    _first_line_after_f6 = False  # After wrapping, use reduced width

            _terminal_state.cursor_col += word_len
            emit_token = True

    # --- emit AFTER lock release ---

    if emit_f6:
        yield from _handle_f6(token)

    if emit_token:
        token.text = token_text
        yield token


def _handle_whitespace(token):
    """
    Consolidate repeated whitespace characters into tokens.
    For example, a run of 3 newlines becomes:
        Token(kind="WHITESPACE", value="\n", repeat=3, text="\n\n\n")
    """
    with _raw_lock:
        raw_now = _raw
    if not raw_now:
        yield from _acs_off()

    run = token.value
    i = 0
    while i < len(run):
        ch = run[i]
        repeat = 1
        while i + repeat < len(run) and run[i + repeat] == ch:
            repeat += 1
        yield Token(
            "WHITESPACE",
            value=ch,  # the character itself (' ', '\t', or '\n')
            repeat=repeat,  # how many times it repeats
            text=ch,  # string that will be written
            raw=ch,
        )
        i += repeat


# DECSC / DECRC operate on software-defined TerminalState.
# All operations occur under _terminal_state_lock and _terminal_state_stack_lock
# to keep terminal output and state synchronized.
def _handle_decsc(token):
    global _terminal_state_stack, _terminal_state
    cursor_row, cursor_col = get_cursor_position()
    with _terminal_state_lock, _terminal_state_stack_lock:
        if not _terminal_state_stack_enabled and len(_terminal_state_stack) >= 1:
            _terminal_state_stack.pop()
        _terminal_state_stack.append(
            TerminalState(
                cursor_row=cursor_row,
                cursor_col=cursor_col,
                wordwrap=_terminal_state.wordwrap,
                has_color=_terminal_state.has_color,
                hidden=_terminal_state.hidden,
            )
        )


def _handle_decrc(token):
    global _terminal_state, _terminal_state_stack

    with _terminal_state_stack_lock:
        if not _terminal_state_stack:
            return  # VT spec: restore is a no-op if nothing saved

        if _terminal_state_stack_enabled:
            state = _terminal_state_stack.pop()  # pop from stack
        else:
            state = _terminal_state_stack[-1]  # peek, don't pop

    # restore software state
    with _terminal_state_lock:
        _terminal_state.cursor_row = state.cursor_row
        _terminal_state.cursor_col = state.cursor_col
        _terminal_state.wordwrap = state.wordwrap
        _terminal_state.has_color = state.has_color
        _terminal_state.hidden = state.hidden

    # restore hardware cursor
    yield from _handle_curpos(
        Token("CURPOS", args=(_terminal_state.cursor_row, _terminal_state.cursor_col))
    )


# ----------------------------
# ACS characters
# ----------------------------
_acs_map = {
    # Box drawing
    "ulcorner": "l",  # ┌
    "urcorner": "k",  # ┐
    "llcorner": "m",  # └
    "lrcorner": "j",  # ┘
    "hline": "q",  # ─
    "vline": "x",  # │
    "ttee": "w",  # ┬
    "btee": "v",  # ┴
    "ltee": "u",  # ┤
    "rtee": "t",  # ├
    "plus": "n",  # ┼
    #    "ttee":        "\u252C", # ┬
    #    "btee":        "\u2534", # ┴
    #    "ltee":        "\u251C", # ├
    #    "rtee":        "\u2524", # ┤
    #    "cross":       "\u253C", # ┼
    # Other symbols
    "diamond": "`",  # ◆
    "checkerboard": "a",  # ▒
    "ht": "b",  # HT symbol
    "ff": "c",  # FF symbol
    "cr": "d",  # CR symbol
    "lf": "e",  # LF symbol
    "degree": "f",  # °
    "pluminus": "g",  # ±
    "board": "h",  # board of squares
    "lantern": "i",  # lantern / scan line / bell symbol
    "scan1": "o",  # scan line 1
    "scan3": "p",  # scan line 3
    "scan7": "r",  # scan line 7
    "scan9": "s",  # scan line 9
    "lequal": "y",  # ≤
    "gequal": "z",  # ≥
    "pi": "{",  # π
    "nequal": "|",  # ≠
    "sterling": "}",  # £
    "bullet": "~",  # • / ≈
    # Extras sometimes present in DEC tables
    "notdef": "^",  # undefined glyph
    "space": "_",  # blank space
}


def _acs_on():
    global _current_stream_lock, _terminal_state

    token = None

    with _current_stream_lock:
        if not _terminal_state.acs:
            _terminal_state.acs = True
            token = Token(kind="ACS_ON", repeat=1, text=f"{ESC}(0")

    if token is not None:
        yield token


def _acs_off():
    global _current_stream_lock, _terminal_state

    token = None

    with _current_stream_lock:
        if _terminal_state.acs:
            _terminal_state.acs = False
            token = Token(kind="ACS_OFF", repeat=1, text=f"{ESC}(B")

    if token is not None:
        yield token


def _handle_acs(token):
    """
    Process ACS (Alternate Character Set) command for box drawing.

    Converts ACS character names (e.g., 'ulcorner', 'hline') to DEC graphics characters.
    Emits ACS_ON before output and tracks cursor position.
    """
    global _terminal_state

    if token.value == "acs":
        if not token.args:
            raise ValueError("ACS command requires a character name")
        name = token.args[0]
        repeat = int(token.args[1]) if len(token.args) > 1 else 1
    else:
        name = token.value
        repeat = int(token.args[0]) if len(token.args) == 1 else 1

    with _current_stream_lock:
        _terminal_state.cursor_col += repeat

    with _raw_lock:
        raw_now = _raw
    if not raw_now:
        yield from _acs_on()

    token.kind = "ACS_CHAR"
    token.text = _acs_map.get(name, "?")
    token.repeat = repeat

    yield token
    return


def _handle_var(token):
    var_name = token.args[0] if token.args else token.value
    with _runtime_vars_lock:
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


def _handle_curpos(token):
    global _terminal_state

    # parse args outside the lock (no shared state yet)
    try:
        y = int(token.args[0]) if token.args else 1
        x = int(token.args[1]) if len(token.args) > 1 else 1
    except (ValueError, TypeError):
        y, x = 1, 1

    # normalize (VT is 1-based, nonzero)
    y = max(1, y)
    x = max(1, x)

    # update terminal state - no lock needed (local tracking only)
    _terminal_state.cursor_row = y
    _terminal_state.cursor_col = x

    # emit escape
    token.text = f"{CSI}{y};{x}H"
    yield token


def _handle_f6(token):
    global _cursor_col, _cursor_row, _first_line_after_f6

    repeat = int(token.args[0]) if token.args else 1
    token.repeat = repeat
    token.text = "\n"
    token.kind = "F6"

    # Mark that next line is first after F6 (use full width)
    _first_line_after_f6 = True

    yield token

    # After F6 (both word-wrap and explicit): emit indent and start at indent position
    if _terminal_state.indent > 0:
        indent_text = _terminal_state.indent_char * _terminal_state.indent
        yield Token(
            "INDENT",
            value=_terminal_state.indent_char,
            repeat=1,
            text=indent_text,
            raw=indent_text,
        )
    with _current_stream_lock:
        _terminal_state.cursor_col = (
            _terminal_state.indent if _terminal_state.indent > 0 else 0
        )

    return


def _handle_home(token):
    token.text = f"{CSI}H"
    yield token
    return


# erasedisplay
# tobottom = 1, totop = 2, default = 0 = full
def _handle_ed(token):
    ## print(f"**** _handle_ed.100: {token=}")
    mode = int(token.args[0]) if len(token.args) == 1 else 2
    token.text = f"{CSI}{mode}J"
    yield token


# 0 = clear right of cursor
# 1 = clear left of cursor
# 2 = clear whole line
# EL0 – Erase in Line (cursor to end of line)
def _handle_elo(token):
    mode = int(token.args[0]) if len(token.args) == 1 else 0
    token.text = f"{CSI}{mode}K"
    yield token


def _handle_cuu(token):
    if len(token.args) == 0:
        repeat = 1
    else:
        repeat = token.args[0] or 1

    token.repeat = 1
    token.text = f"{CSI}{repeat}A"
    yield token


def _handle_cud(token):
    if len(token.args) == 0:
        repeat = 1
    else:
        repeat = token.args[0] or 1

    token.repeat = 1
    token.text = f"{CSI}{repeat}B"
    yield token
    return


def _handle_cuf(token):
    if len(token.args) == 0:
        repeat = 1
    else:
        repeat = int(token.args[0])

    token.repeat = 1
    token.text = f"{CSI}{repeat}C"
    yield token


def _handle_cub(token):
    if len(token.args) == 0:
        repeat = 1
    else:
        repeat = int(token.args[0])

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

    if len(token.args) != 2:
        raise ValueError(f"{token.args=}")
        return

    t = token.args[0]
    b = token.args[1]

    token.text = f"{CSI}{t};{b}r"
    yield token


def _handle_slashall(token):
    token.kind = "COLOR"
    token.repeat = 1
    token.text = f"{ESC}[0m"
    yield token


def _handle_reset(token):
    if len(token.args) > 0:
        return iter()

    with _raw_lock:
        raw_now = _raw
    if not raw_now:
        yield from _acs_off()

    yield Token("INDENT", value=0, repeat=1, text="", raw="")

    yield from _handle_slashall(token)
    yield from _handle_decstbm(token)


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


def _handle_literalopen(token):
    ## print("literalopen", flush=True)
    token.kind = "WORD"
    token.repeat = 1
    token.text = "{"
    yield token


def _handle_literalclose(token):
    token.kind = "WORD"
    token.repeat = 1
    token.text = "}"
    yield token


def _handle_indent(token):
    global _terminal_state
    indent = int(token.args[0]) if token.args else 0
    max_indent = terminal.columns()
    with _terminal_state_lock:
        _terminal_state.indent = min(indent, max_indent)
        if len(token.args) > 1:
            _terminal_state.indent_char = token.args[1]
        else:
            _terminal_state.indent_char = DEFAULT_INDENT_CHAR


options: Dict[str, Any] = {}


def setoption(opt: str, value: Any) -> Any:
    """Set a global option."""
    global options
    options[opt] = value
    return value


def getoption(opt: str, default: Any = None) -> Any:
    """Get a global option, returning default if not found."""
    global options
    return options[opt] if opt in options else default


PARAM_SPLIT_RE = re.compile(r"[:,]")


def parse_command_params(name: str, params: str) -> Tuple[List[str], Dict[str, str]]:
    """Parse command parameters into positional and keyword arguments."""
    args = []  # [name,]
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
    global \
        _handle_indent, \
        _handle_f6, \
        _handle_reset, \
        _handle_bel, \
        _handle_cha, \
        _handle_curpos, \
        _handle_cuu, \
        _handle_cud, \
        _handle_cuf, \
        _handle_cub, \
        _handle_decsc, \
        _handle_decrc, \
        _handle_decstbm, \
        _handle_ed, \
        _handle_elo, \
        _handle_slashfgcolor, \
        _handle_slashbgcolor, \
        _handle_slashall, \
        _handle_reset, \
        _handle_acs, \
        _handle_var, \
        _handle_rgb, \
        _handle_decdhl, \
        _handle_literalopen, \
        _handle_literalclose

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
    token.text = BEL
    yield token


_unicode = {
    "dblhline": "\u2550",  # ═
    "dblvline": "\u2551",  # ║
    "dblul": "\u2554",  # ╔
    "dblur": "\u2557",  # ╗
    "dblll": "\u255a",  # ╚
    "dbllr": "\u255d",  # ╝
    "arrow": "\u2192",  # →
    "arrow_left": "\u2190",  # ←
    "arrow_up": "\u2191",  # ↑
    "arrow_right": "\u2192",  # →
    "arrow_down": "\u2193",  # ↓
}


def _handle_unicode(token):
    if token.value in _unicode:
        token.text = _unicode[token.value]
        yield token


def _handle_command(token, **kwargs):  # palette=None, vars=None):
    """
    Process a COMMAND token by routing to appropriate handler.

    Handles colors, variables, attributes, ACS characters, emojis, and special commands.
    This is the main dispatcher for all command processing.

    Args:
        token: Token of kind COMMAND from tokenize()
    Yields:
        Processed tokens with text set to ANSI sequences or output
    """
    # command name is lowercase
    cmd = token.value.lower()

    yield from _acs_off()

    # Palette color
    if cmd.lstrip("/") in get_current_palette():
        token.text = get_palette_entry(cmd)
        yield token
        return

    if cmd in _runtime_vars:
        yield from _handle_var(token)
        return

    if cmd.lstrip("/") in ANSI_ATTRS:
        yield from _handle_attr(token)
        return

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


_emoji = {
    "grin": "\U0001f600",  # 😀 @since 20260221
    "smile": "\U0001f642",  # 🙂 @since 20260221
    "rofl": "\U0001f923",  # 🤪 @since 20260221
    "wink": "\U0001f609",  # 😉 @since 20260221
    "thinking": "\U0001f914",  # 🤔 @since 20260221
    "sunglasses": "\U0001f60e",  # 😎 @since 20260221
    "100": "\U0001f4af",  # 💯 @since 20260221
    "thumbup": "\U0001f44d",  # 👍 @since 20260221
    "thumbdown": "\U0001f44e",  # 👎 @since 20260221
    "vulcan": "\U0001f596",  # 🖖 @since 20260221
    "spiral": "\U0001f4ab",  # 💫 @since 20260221
    "fire": "\U0001f525",  # 🔥 @since 20260221
    "bank": "\U0001f3e6",  # 🏦 @since 20260221
    "house": "\U0001f3e0",  # 🏠 @since 20260221
    "military-helmet": "\U0001fa96",  # 🪖 @since 20260221
    "door": "\U0001f6aa",  # 🚪 @since 20260221
    "receipt": "\U0001f9fe",  # 🧾 @since 20260221
    "newspaper": "\U0001f4f0",  # 📰 @since 20260221
    "prince": "\U0001f934",  # 🤴 @since 20260221
    "princess": "\U0001f478",  # 👸 @since 20260221
    "thread": "\U0001f9f5",  # 🧵 @since 20260221
    "ice": "\U0001f9ca",  # 🧊 @since 20260221
    "moneybag": "\U0001f4b0",  # 💰 @since 20260221
    "person": "\U0001f9d1",  # 👤 @since 20260221
    "sun": "\U00002600",  # ☀ @since 20260221
    "thunder-cloud-and-rain": "\U000026c8",  # ⛈ @since 20260221
    "crop": "\U0001f33e",  # 🌾 @since 20260221
    "horse": "\U0001f40e",  # 🐎 @since 20260221
    "cactus": "\U0001f335",  # 🪴 @since 20260221
    "ship": "\U0001f6a2",  # 🚢 @since 20260221
    "wood": "\U0001fab5",  # 🪵 @since 20260221
    "link": "\U0001f517",  # 🔗 @since 20260221
    "anchor": "\U00002693",  # ⚓ @since 20260221
    "ballot-box": "\U0001f5f3",  # 🗳 @since 20260221
    "building": "\U0001f3db",  # 🏛 @since 20260221
    "envelope": "\U00002709",  # ✉ @since 20260221
    "dolphin": "\U0001f42c",  # 🐬 @since 20260221
    "bellhop-bell": "\U0001f6ce",  # 🛎 @since 20260221 for murdermotel
    "hotel": "\U0001f3e8",  # 🏨 @since 20260221 for murdermotel
    "mousetrap": "\U0001faa4",  # 🪤 @since 20260221 for murdermotel
    "waninggibbousmoon": "\U0001f316",  # 🌖 @since 20260221
    "waxinggibbousmoon": "\U0001f314",  # 🌔 @since 20260221
    "waningcrescentmoon": "\U0001f318",  # 🌘 @since 20260221
    "waxingcrescentmoon": "\U0001f312",  # 🌒 @since 20260221
    "lastquartermoon": "\U0001f317",  # 🌗 @since 20260221
    "firstquartermoon": "\U0001f313",  # 🌓 @since 20260221
    "newmoon": "\U0001f311",  # 🌑 @since 20260221
    "fullmoon": "\U0001f315",  # 🌕 @since 20260221
    "sco": "\U0000264f",  # ⛏ @since 20260221
    "sag": "\U00002650",  # ⛐ @since 20260221
    "cap": "\U00002651",  # ⛑ @since 20260221
    "aqu": "\U00002652",  # ⛒ @since 20260221
    "pic": "\U00002653",  # ⛓ @since 20260221
    "ari": "\U00002648",  # ♈ @since 20260221
    "tau": "\U00002649",  # ♉ @since 20260221
    "gem": "\U0000264a",  # ♊ @since 20260221
    "can": "\U0000264b",  # ♋ @since 20260221
    "leo": "\U0000264c",  # ♌ @since 20260221
    "vir": "\U0000264d",  # ♍ @since 20260221
    "lib": "\U0000264e",  # ♎ @since 20260221
    "package": "\U0001f4e6",  # 📦 @since 20220907
    "compass": "\U0001f9ed",  # 🧭 @since 20220907
    "worldmap": "\U0001f5fa",  # 🗺 @since 20220916
    "wolf": "\U0001f43a",  # 🐺 @since 20221002
    "supervillian": "\U0001f9b9",  # 🦹 @since 20221016
    "joker": "\U0001f0cf",  # 🃏 @since 20221127
    "warning": "\U000026a0",  # ⚠ @since 20260221
    "stopsign": "\U0001f6d1",  # 🛑 @since 20260221
    "shopping": "\U0001f6cd",  # 🛍 @since 20240128
    "maint": "\U0001f6e0",  # 🛠 @since 20230827 for empyre, murdermotel
    "axe": "\U0001fa93",  # 🪓 @since 20230827 for murdermotel
    "zap": "\U000026a1",  # ⚡ @since 20240422 for weather
    "palmtree": "\U0001f334",  # 🌴 @since 20260221
    "evergreentree": "\U0001f332",  # 🌲 @since 20260221
    "tophat": "\U0001f3a9",  # 🎩 @since 20260221
    "magicwand": "\U0001fa84",  # 🪄 @since 20260221
    "checkmark": "\U00002714",  # ✅ @since 20260221
    "crossmark": "\U00002718",  # ❌ @since 20260221
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
    with _terminal_state_lock:
        if token.value.startswith("/"):
            _terminal_state.decdhl = False
            token.text = f"{ESC}[5m"  # DECSWL - single-width single-height
        else:
            _terminal_state.decdhl = True
            token.text = f"{ESC}[6m"  # DECDWL - double-width
    yield token


def _write_token(token: Token, flush: bool = True, stream=None):
    """
    Write a Token to the current stream (defaults to sys.stdout), interpreting commands and attributes.
    - WORD/WHITESPACE: printed directly
    - F6: hard newline
    - COMMANDS: processed via _handle_command()
    """
    global _current_output_stream, _current_stream_lock
    ##    print(f"_write_token.100: {token.kind=} {token.repeat=} {token.value=}", flush=True)
    repeat = int(token.repeat) or 1
    with _raw_lock:
        raw_now = _raw
    if not raw_now:
        text = str(token.text) * repeat
    else:
        text = (str(token.raw) or str(token.text)) * repeat
    write_current_output_stream(text, flush=flush)
    return


# ----------------------------
# echo_iter(), echo(), and echo_file()
# ----------------------------
def echo_iter(
    text: str,
    width: Optional[int] = None,
    wordwrap: bool = True,
    palette: Optional[Dict] = None,
    vars: Optional[Dict] = None,
    raw: bool = False,
) -> Generator[Token, None, None]:
    """
    Generator that yields tokens for rendering.
    Handles WORD, WHITESPACE, F6 (hard newline), attributes, and commands.
    """
    global _runtime_vars, _previous_token

    with _raw_lock:
        _raw = raw
    _terminal_state.wordwrap = wordwrap

    if width is None:
        width = terminal.columns()  # default or queried width

    palette = palette or c64_palette
    _runtime_vars = _runtime_vars or {}
    _term_width = width

    for token in tokenize(text):
        if token.kind == "COMMAND":
            yield from _handle_command(token)
        elif token.kind == "WORD":  # in ("WORD", "WHITESPACE"):
            yield from _handle_word(token, width=width)
        elif token.kind == "WHITESPACE":
            with _current_stream_lock:
                _terminal_state.cursor_col += len(token.text)
            yield token
            # After newline whitespace, emit indent if set (but not after INDENT to avoid duplicates)
            if "\n" in token.value and _terminal_state.indent > 0:
                if _previous_token.kind != "INDENT":
                    global _first_line_after_f6
                    indent_str = _terminal_state.indent_char * _terminal_state.indent
                    indent_token = Token(
                        "INDENT",
                        value=_terminal_state.indent_char,
                        repeat=1,
                        text=indent_str,
                        raw=indent_str,
                    )
                    yield indent_token
                    with _current_stream_lock:
                        _terminal_state.cursor_col = _terminal_state.indent
                    _first_line_after_f6 = (
                        True  # First line after newline uses full width
                    )
                    _previous_token = (
                        indent_token  # Track INDENT so next newline doesn't add again
                    )
        elif token.kind == "F6":
            yield token  # Already processed by handler_dispatch path
        elif token.kind == "INDENT":
            if token.value == 0:
                with _terminal_state_lock:
                    _terminal_state.indent = 0
                    _terminal_state.indent_char = DEFAULT_INDENT_CHAR
            yield token
        else:
            # unknown token, yield as-is
            yield token

        _previous_token = token


def echo(
    text: str = "", *, flush: bool = True, end: Optional[str] = ECHO_END, **kwargs
) -> Optional[str]:
    """
    Print text to stdout, interpreting inline commands unless raw=True.
    width: override detected terminal width if not None
    wordwrap: enable/disable word wrapping
    raw: if True, commands are treated as literal text
    flush: if True, flush after writing
    """
    with _raw_lock:
        _raw = kwargs.get("raw", False)

    palette: dict = kwargs.get("palette", None)
    width: int = kwargs.get("width", terminal.width())
    wordwrap: bool = kwargs.get("wordwrap", True)

    level = kwargs.get("level", None)
    original_text = text
    if level is not None:
        prefix = ""
        if level == "debug":
            prefix = "{level.debug}D: "  # {bglightblue}{blue}"
        elif level == "warn" or level == "warning":
            prefix = "{level.warning}W: "  # {bgyellow}{black}"
        elif level == "error":
            prefix = "{level.error}E: "  # {bgred}{white}"
        elif level == "fail":
            prefix = "{level.fail}F: "  # {bgred}{black}"
        elif level == "success" or level == "ok":
            prefix = "{level.ok}"  # {bggreen}{black}"
        elif level == "info":
            prefix = "{level.info}I: "  # {bgwhite}{blue}"

        text = prefix + text + "{/all}"

    for token in echo_iter(
        text, width=width, wordwrap=wordwrap, raw=_raw, palette=palette
    ):
        _write_token(token, flush=flush)

    # Always write the "end" string
    if end:
        write_current_output_stream(end, flush=flush)
        if end == "\n":
            with _terminal_state_lock:
                _terminal_state.cursor_col = 0
                _terminal_state.cursor_row += 1

    if level is not None:
        return logentry(original_text, level=level)


def echo_file(
    filepath: str,
    page_size: int = 20,
    raw: bool = False,
    wordwrap: bool = True,
    end: str = "",
) -> None:
    """Echo contents of a file with optional paging."""
    with open(filepath, "r") as f:
        line_count = 0
        for line in f:
            echo(line, end=end, raw=raw, wordwrap=wordwrap)  # don't add extra newline
            line_count += 1
            if line_count % page_size == 0:
                input("More?")  # wait every page


# @since 20251212
def rendered_length(text: str, **kwargs) -> int:
    """
    Calculates the length of the text as it would be rendered, ignoring
    control sequences, commands, and variable/color expansions.

    This is necessary to correctly determine the cursor position for
    functions like curpos.
    """
    length = 0

    ##    echo(f"{text=}", flush=True)
    for token in echo_iter(text, wordwrap=False, raw=False):
        # Get the effective repeat count, default to 1
        repeat = int(token.repeat) if token.repeat is not None else 1

        # Only count tokens that produce visible text on the terminal:
        ##        print(f"{token=}", flush=True)
        if token.kind == "WORD":
            # WORD: Count visible characters.
            # Note: If {fullwidth} is active, len(token.text) might be
            # the number of full-width characters (e.g., to_fullwidth("A") is "\uFF21"),
            # and it's assumed that each character in token.text is 1 column
            # for calculation here unless double-width is explicitly handled
            # by checking the _decdhl global, which is risky in a pure length calculation.
            # Assuming terminal output width is what we want.
            length += len(token.text) * repeat

        elif token.kind == "EMOJI":
            # Emojis are usually 1 or 2 columns. Assuming 1 for simplicity.
            length += repeat

        elif token.kind == "ACS_CHAR":
            # ACS_CHAR: The actual alternate character, counts as 1 column.
            length += repeat

        # ACS_ON and ACS_OFF are control sequences, not visible - skip them

        elif token.kind == "WHITESPACE":
            # Only count spaces/tabs, ignore newlines ('\n') which don't consume horizontal space.
            # The *actual visible width* is determined by the repeat count.
            if token.value != "\n":
                length += repeat

        elif token.kind == "F6":
            # Hard newline (F6) doesn't consume horizontal space.
            pass

        # All other token kinds (COMMAND, COLOR, ATTR, UNKNOWN) are ignored
        # as they typically represent non-printing control sequences or metadata.

    return length


def echo_traceback(
    message: str = "Traceback (most recent call last):", level: str = "error"
):
    """
    Captures the current exception and outputs the entire stack
    via a single echo() call, using {f6} as the newline separator.
    """
    import traceback as tb

    # Get the formatted traceback string from Python
    raw_traceback = tb.format_exc()

    # Split into lines to filter/process
    lines = raw_traceback.strip().split("\n")

    # Filter out the redundant first line if we provided a custom header
    filtered_lines = [
        line
        for line in lines
        if not line.startswith("Traceback (most recent call last):")
    ]

    # Join everything with your engine's newline code {f6}
    traceback_string = f"{{level.error}}{message}{{/all}}{{f6}}" + "{f6}".join(
        filtered_lines
    )

    # Single call to echo
    echo(traceback_string, level=None)


def exit_on_db_error(message: str = "fatal database error") -> None:
    """Log a database error via echo_traceback and call sys.exit(1).

    Use this in module main() functions to make DB/connection errors fatal.
    The program will print the traceback and exit with status 1.

    Example:
        def main(args, **kwargs):
            try:
                with database.connect(args, pool=pool) as conn:
                    _work(conn)
            except psycopg.OperationalError as e:
                io.exit_on_db_error("mm.lobby.main: DB connection failed")
    """
    import sys

    import psycopg

    try:
        raise
    except (psycopg.OperationalError, psycopg.InterfaceError) as e:
        echo_traceback(f"{message}: {e}")
        sys.exit(1)


def fatal_on_db_error(func):
    """Decorator that makes DB/connection errors fatal (exit 1) in module main().

    Catches psycopg.OperationalError and psycopg.InterfaceError, logs them
    via echo_traceback, and calls sys.exit(1). Other exceptions propagate.

    Use on module main() functions to ensure DB failures cause program exit
    rather than silent failure.

    Example:
        @io.fatal_on_db_error
        def main(args, **kwargs):
            with database.connect(args, pool=pool) as conn:
                _work(conn)
    """
    import functools
    import sys

    import psycopg

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (psycopg.OperationalError, psycopg.InterfaceError) as e:
            echo_traceback(f"{func.__module__}.{func.__name__}: {e}")
            sys.exit(1)

    return wrapper


def _get_template_dirs() -> list:
    """Get list of template directories to search, in priority order."""
    dirs = []

    site_template_dir = getvar("template_dir")
    if site_template_dir:
        dirs.append(site_template_dir)

    builtin_tpl_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tpl")
    if os.path.isdir(builtin_tpl_dir):
        dirs.append(builtin_tpl_dir)

    return dirs


def _load_template(name: str) -> str:
    """Load template file from search paths.

    Searches in order:
    1. Site-specific template_dir (if configured)
    2. Built-in bbsengine6/tpl/ directory

    Args:
        name: Template filename (e.g., "menu.tpl")

    Returns:
        Template content as string

    Raises:
        FileNotFoundError: If template not found in any search path
        ValueError: If name contains path traversal attempts
    """
    import pathlib

    dirs = _get_template_dirs()

    # Prevent path traversal attacks by validating the template name
    template_name = pathlib.Path(name)
    if template_name.is_absolute() or ".." in template_name.parts:
        raise ValueError(f"Invalid template name: {name} (contains path traversal)")

    for d in dirs:
        dir_path = pathlib.Path(d).resolve()
        filepath = (dir_path / name).resolve()

        # Verify resolved path is within the template directory
        try:
            filepath.relative_to(dir_path)
        except ValueError:
            # Path is outside directory, skip it
            continue

        if filepath.is_file():
            with open(filepath, "r") as f:
                return f.read()

    raise FileNotFoundError(f"Template '{name}' not found in {dirs}")


def load_template(name: str, **vars) -> str:
    """Load template and substitute variables.

    Args:
        name: Template filename (e.g., "menu.tpl")
        **vars: Variables to substitute in template

    Returns:
        Rendered template string with variables replaced

    Example:
        >>> template = load_template("menu.tpl", title="Main Menu", item1="Files")
        >>> echo(template)
    """
    content = _load_template(name)

    for key, value in vars.items():
        content = content.replace(f"{{{key}}}", str(value))

    return content


def echo_template(name: str, **vars) -> None:
    """Load template, substitute variables, and output using echo_file().

    Args:
        name: Template filename (e.g., "menu.tpl")
        **vars: Variables to substitute in template

    Keyword Args:
        page_size: If > 0, pause every N lines with "More?" prompt (default: 0, no paging)
        raw: If True, output raw text without interpreting {var:xxx} commands
        wordwrap: Enable/disable word wrapping (default: True)

    Example:
        >>> echo_template("menu.tpl", title="Main Menu", item1="Files", item2="Mail")
        >>> echo_template("long.tpl", page_size=20)  # with paging
    """
    import tempfile
    import os

    page_size = vars.pop("page_size", 0)
    raw = vars.pop("raw", False)
    wordwrap = vars.pop("wordwrap", True)

    template = load_template(name, **vars)

    if page_size > 0:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tpl", delete=False) as tmp:
            tmp.write(template)
            tmp_path = tmp.name
        try:
            echo_file(tmp_path, page_size=page_size, raw=raw, wordwrap=wordwrap, end="")
        finally:
            os.unlink(tmp_path)
    else:
        echo(template, raw=raw, wordwrap=wordwrap)
