"""Track the current SGR state (foreground, background and attributes) from the escape text the
engine writes, so {savecursor} can save it and {restorecursor} can re-emit it.

The state is a dataclass of the SGR parameters that are in effect. ``apply`` reads one SGR sequence
(``ESC[...m``) and returns the updated state. ``emit`` returns the SGR text that sets a state from
nothing, so a restore leaves the terminal in the saved colour.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from .const import CSI

_SGR = re.compile(r"\x1b\[([0-9;]*)m")

# Basic colour codes: foreground 30-37 / 90-97, background 40-47 / 100-107.
_BASIC_FG = set(range(30, 38)) | set(range(90, 98))
_BASIC_BG = set(range(40, 48)) | set(range(100, 108))

# Attribute on/off pairs: on -> attribute name, off codes -> attribute name.
_ATTR_ON = {1: "bold", 3: "italic", 4: "underline", 7: "inverse", 9: "strike"}
_ATTR_OFF = {22: "bold", 23: "italic", 24: "underline", 27: "inverse", 29: "strike"}


@dataclass(frozen=True)
class SgrState:
    #: Foreground as the SGR parameters that set it (for example ``("38", "2", "r", "g", "b")``).
    fg: tuple = ()
    #: Background as the SGR parameters that set it (for example ``("48", "2", "r", "g", "b")``).
    bg: tuple = ()
    attrs: frozenset = field(default_factory=frozenset)


def _params_of(text: str):
    """Yield the SGR parameter lists in ``text``, one list per ``ESC[...m`` sequence."""
    for m in _SGR.finditer(text):
        raw = m.group(1)
        yield [int(p) if p.isdigit() else p for p in raw.split(";")] if raw else [0]


def apply(state: SgrState, text: str) -> SgrState:
    """The state after the SGR sequences in ``text`` are written."""
    for params in _params_of(text):
        state = _apply_one(state, params)
    return state


def _apply_one(state: SgrState, params: list) -> SgrState:
    fg, bg, attrs = state.fg, state.bg, set(state.attrs)
    i = 0
    while i < len(params):
        p = params[i]
        if p == 0:
            fg, bg, attrs = (), (), set()
        elif p in _ATTR_ON:
            attrs.add(_ATTR_ON[p])
        elif p in _ATTR_OFF:
            attrs.discard(_ATTR_OFF[p])
        elif p in _BASIC_FG:
            fg = (str(p),)
        elif p in _BASIC_BG:
            bg = (str(p),)
        elif p in (38, 48) and i + 1 < len(params):
            # Extended colour: 38;5;n (256-colour) or 38;2;r;g;b (truecolour).
            mode = params[i + 1]
            width = 3 if mode == 5 else 5 if mode == 2 else 1
            chunk = tuple(str(x) for x in params[i : i + width + 1])
            if p == 38:
                fg = chunk
            else:
                bg = chunk
            i += width
        elif p == 39:
            fg = ()
        elif p == 49:
            bg = ()
        i += 1
    return SgrState(fg=fg, bg=bg, attrs=frozenset(attrs))


def emit(state: SgrState) -> str:
    """The SGR text that sets ``state`` from a clean slate: reset, then the saved colour and attributes."""
    parts = ["0"]
    parts += sorted(_attr_on_code(a) for a in state.attrs)
    if state.fg:
        parts.append(";".join(state.fg))
    if state.bg:
        parts.append(";".join(state.bg))
    return f"{CSI}{';'.join(parts)}m"


def _attr_on_code(name: str) -> str:
    return str(next(code for code, n in _ATTR_ON.items() if n == name))


EMPTY = SgrState()
