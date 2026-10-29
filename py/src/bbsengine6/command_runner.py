"""Dispatch a typed command against a registry, and launch it through module.run().

A shell (letteredolive) keeps its commands in a :class:`bbsengine6.commands.CommandRegistry`.
This module turns one typed line into an outcome the shell can act on:

* ``run``: an entry was matched; :func:`launch` runs it through ``module.run()``.
* ``not_found``: no available entry matches. Message: ``command not found <name>``.
* ``ambiguous``: more than one available entry matches the prefix. Nothing runs.
  Message: ``ambiguous command <prefix>``.

Neither failure message lists candidates; tab completion and F1 do that.

Launching always goes through ``bbsengine6.module.run()``. That call runs the module's
``access()`` check. This module never calls ``check()`` or ``access()`` itself, and it never
decides visibility from ``access()``: visibility is the registry's availability predicate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from . import commands as _commands

OUTCOME_RUN = "run"
OUTCOME_NOT_FOUND = "not_found"
OUTCOME_AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class Dispatch:
    """What a typed command means. ``entry`` is set only for OUTCOME_RUN."""

    outcome: str
    name: str
    entry: Optional[_commands.Entry] = None

    @property
    def message(self) -> str:
        """The one-line message for a failed outcome, or "" when the command runs."""
        if self.outcome == OUTCOME_NOT_FOUND:
            return f"command not found {self.name}"
        if self.outcome == OUTCOME_AMBIGUOUS:
            return f"ambiguous command {self.name}"
        return ""


def dispatch(registry: _commands.CommandRegistry, name: str, state: Any = None) -> Dispatch:
    """Decide what the typed ``name`` means in ``registry``. Does not run anything."""
    kind, entry = registry.resolve(name, state)
    if kind in (_commands.RESOLVE_EXACT, _commands.RESOLVE_UNIQUE):
        return Dispatch(OUTCOME_RUN, name, entry)
    if kind == _commands.RESOLVE_AMBIGUOUS:
        return Dispatch(OUTCOME_AMBIGUOUS, name)
    return Dispatch(OUTCOME_NOT_FOUND, name)


def launch(entry: _commands.Entry, args: Any, argv: list, **kwargs: Any) -> Any:
    """Run a matched entry through ``module.run()``; return what it returns.

    The entry's ``spec`` must carry ``"prg"``: the module name to run. Failing to find that
    key is a registration error and raises ``KeyError`` before anything runs.
    """
    from . import module  # imported here: module pulls in the whole engine

    prg = entry.spec["prg"]
    return module.run(args, prg, argv=argv, **kwargs)
