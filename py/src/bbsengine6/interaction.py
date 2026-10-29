"""Per-interaction state, held in a ContextVar.

The module is named ``interaction`` because ``bbsengine6/session/`` is already the package
for login sessions. A "session" here is the state one shell or host program keeps for its
own interaction: today, the command registry. Phase 3 moves the io state (input queue,
terminal state, key table, and so on) into the same object.

``current_session()`` returns the session for the current context. Without any
``use_session`` call it is a module-level default session, so existing code is unchanged.
A host that wants its own session enters ``use_session(new_session(...))`` for the
duration of its work; another context (another thread, or code run inside the host) sees
its own session, and leaving the block restores the previous one.
"""

from __future__ import annotations

import collections
import contextlib
import contextvars
from typing import Iterator, Optional

from .commands import CommandRegistry, MODE_EXTEND


class Session:
    """The state for one interaction: a command registry, and (later) the io state."""

    def __init__(self, mode: str = MODE_EXTEND, name: str = "") -> None:
        self.name = name
        self.commands = CommandRegistry(mode=mode)
        # io state (moved from io/common.py). Process-wide state (locks, the tty
        # settings, the *_MANAGED flags) stays in its module.
        self.input_stream = None  # None: the io module's default stream (sys.stdin)
        self.output_stream = None  # None: the io module's default stream (sys.stdout)
        self.input_queue = collections.deque()
        self.terminal_state = None  # None: the io module builds its default
        self.terminal_state_stack: list = []
        self.terminal_state_stack_enabled = False
        self.input_dirty = False
        # io/echo.py state. Runtime variables start as None: echo builds the default set
        # (its built-in names and skin) on first read, so each interaction starts the same.
        self.raw = False
        self.previous_token = None  # echo's Token("UNKNOWN") on first use
        self.first_line_after_f6 = False
        self.runtime_vars = None
        self.options: dict = {}
        # io/inputstring.py state. The key table starts as None: inputstring copies the
        # built-in table on first use, so each interaction starts with the same keys.
        self.key_actions = None
        self.key_action_saved = None
        self.key_snapshot_stack: list = []
        self.yank_buffer: list = []
        self.mode_fragment: dict = {"item": None, "insert": True}
        # io/getch.py state: the default reader, the UTF-8 reader's undelivered characters
        # (they belong to one input stream), and the notification status last drawn.
        self.getch_impl = "str"
        self.utf8_pending: collections.deque = collections.deque()
        self.bottombar_status = ""
        # screen.py state: the stack of bottom-bar contents pushed by callers (popbottombar).
        self.bottombarstack: list = []

    def __repr__(self) -> str:
        return f"Session(name={self.name!r}, mode={self.commands.mode!r})"


#: The session used when no ``use_session`` is active. Existing code runs in this one.
_default_session = Session(name="default")

_current: contextvars.ContextVar[Optional[Session]] = contextvars.ContextVar(
    "bbsengine6_session", default=None
)


def current_session() -> Session:
    """The session for the current context."""
    s = _current.get()
    return s if s is not None else _default_session


def new_session(mode: str = MODE_EXTEND, name: str = "") -> Session:
    """A fresh session with an empty registry in ``mode``."""
    return Session(mode=mode, name=name)


@contextlib.contextmanager
def use_session(session: Session) -> Iterator[Session]:
    """Make ``session`` the current session inside the block; restore the previous one after."""
    token = _current.set(session)
    try:
        yield session
    finally:
        _current.reset(token)


# ---------------------------------------------------------------------------
# Read-through module state
# ---------------------------------------------------------------------------
#
# io modules used to keep their per-interaction state in module globals. Phase 3 moves
# that state onto the Interaction, and each module keeps its old names by replacing its
# module object with a subclass whose names are properties. A property reads and writes
# the current interaction's field, so existing code (and tests that assign module
# attributes) keeps working and sees the interaction in effect.

import sys as _sys
import types as _types

_MISSING = object()


class _FieldProxyModule(_types.ModuleType):
    """A module whose listed names are properties over the current interaction.

    ``fields`` maps a module-level name to a field name on ``Interaction``. Anything not
    listed behaves as an ordinary module attribute.
    """

    _fields: dict = {}

    def __getattr__(self, name):  # only called when normal lookup fails
        raise AttributeError(name)


def install_read_through(module_name: str, fields: dict, getters: Optional[dict] = None) -> None:
    """Make the names in ``fields`` read and write the current interaction, in ``module_name``.

    ``fields`` maps module-level names to attribute names on the current interaction. Each
    name is removed from the module's own dict and served by a property on a per-module
    subclass. Everything else stays in the module's ``__dict__``, which is the globals dict
    the module's functions use. (A proxy with a separate dict would not be seen by those
    functions, so writes to the proxy would not take effect.)

    ``getters`` optionally maps a name to a function of the interaction that returns the
    value to read. Use it when the stored value may be ``None`` and the module builds a
    default on first read. Writes always store the field.
    """
    getters = getters or {}
    module = _sys.modules[module_name]
    for name in fields:
        module.__dict__.pop(name, None)
    proxy_cls = type(
        f"_ReadThrough_{module_name.rsplit('.', 1)[-1]}",
        (_types.ModuleType,),
        {},
    )
    for name, field_name in fields.items():
        getter = getters.get(name)
        if getter is None:
            read = lambda self, _f=field_name: getattr(current_session(), _f)
        else:
            read = lambda self, _g=getter: _g(current_session())
        setattr(
            proxy_cls,
            name,
            property(
                read,
                lambda self, value, _f=field_name: setattr(current_session(), _f, value),
                lambda self, _f=field_name: setattr(current_session(), _f, None),
            ),
        )
    # Only the class changes: the module keeps its dict (the functions' globals), and
    # attribute access on the module object goes through the properties above.
    module.__class__ = proxy_cls
