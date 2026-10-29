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

import contextlib
import contextvars
from typing import Iterator, Optional

from .commands import CommandRegistry, MODE_EXTEND


class Session:
    """The state for one interaction: a command registry, and (later) the io state."""

    def __init__(self, mode: str = MODE_EXTEND, name: str = "") -> None:
        self.name = name
        self.commands = CommandRegistry(mode=mode)

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
