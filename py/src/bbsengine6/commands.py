"""Command registry: the names a shell or host program accepts, by tier.

A registry maps typed command names (and their aliases) to entries. Entries come in three
tiers:

- ``protected``: always present. A session cannot remove or override them.
- ``default``: the shell's own list. A session may override one by name.
- ``session``: added by a host for its own session. A session may override a default
  entry or another session entry.

An entry's name and its aliases belong together. Overriding a name replaces every alias
of the old entry, so nothing is left pointing at the old meaning.

Matching (``resolve``) is shared by tab completion and dispatch:

- an exact name or alias always wins;
- otherwise a prefix resolves when exactly one *available* entry starts with it;
- several matches resolve to ``ambiguous`` and nothing runs;
- an entry whose availability predicate is false takes no part in matching.

``resolve`` never returns the candidate list to the dispatcher. Callers that want to show
candidates (tab completion, help) ask ``candidates``.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import io

TIER_PROTECTED = "protected"
TIER_DEFAULT = "default"
TIER_SESSION = "session"
TIERS = (TIER_PROTECTED, TIER_DEFAULT, TIER_SESSION)

#: Override mode for a session: "extend" keeps the default entries; "replace" drops them.
MODE_EXTEND = "extend"
MODE_REPLACE = "replace"
MODES = (MODE_EXTEND, MODE_REPLACE)

RESOLVE_EXACT = "exact"
RESOLVE_UNIQUE = "unique"
RESOLVE_AMBIGUOUS = "ambiguous"
RESOLVE_NONE = "none"


class CommandError(Exception):
    """Raised for a registry rule that a caller broke (removing or overriding protected)."""


@dataclass
class Entry:
    """One command.

    ``name`` is the typed name. ``aliases`` are further typed names for the same entry.
    ``spec`` is whatever the caller uses to run it (for example ``{"prg": "casino"}``); the
    registry does not interpret it. ``available`` is an optional predicate taking the
    session state; when it returns False the entry is hidden and does not match.
    """

    name: str
    tier: str
    spec: Dict[str, Any] = field(default_factory=dict)
    aliases: Tuple[str, ...] = ()
    available: Optional[Callable[[Any], bool]] = None

    def names(self) -> Tuple[str, ...]:
        return (self.name,) + tuple(self.aliases)


class CommandRegistry:
    """The commands visible to one session. Thread-safe for registration and lookup."""

    def __init__(self, mode: str = MODE_EXTEND) -> None:
        if mode not in MODES:
            raise ValueError(f"unknown registry mode {mode!r}")
        self.mode = mode
        self._entries: Dict[str, Entry] = {}  # typed name (or alias) -> entry
        self._lock = threading.RLock()

    # ---- registration -------------------------------------------------

    def register(
        self,
        name: str,
        tier: str,
        spec: Optional[Dict[str, Any]] = None,
        *,
        aliases: Tuple[str, ...] = (),
        available: Optional[Callable[[Any], bool]] = None,
    ) -> Entry:
        """Add a command at ``tier``.

        Raises CommandError when the name (or an alias) is already taken by an entry the
        rules do not allow this registration to replace.
        """
        if tier not in TIERS:
            raise CommandError(f"unknown tier {tier!r}")
        entry = Entry(name, tier, dict(spec or {}), tuple(aliases), available)
        with self._lock:
            for typed in entry.names():
                existing = self._entries.get(typed)
                if existing is None:
                    continue
                self._check_replaceable(existing, entry)
            # Replacing: remove every name of each entry being replaced, then add the new one.
            for typed in entry.names():
                existing = self._entries.get(typed)
                if existing is not None:
                    self._remove_entry(existing)
                    _log_override(existing, entry)
            for typed in entry.names():
                self._entries[typed] = entry
        return entry

    def _check_replaceable(self, existing: Entry, new: Entry) -> None:
        if existing.tier == TIER_PROTECTED:
            raise CommandError(f"{existing.name!r} is protected and cannot be overridden")
        if new.tier == TIER_PROTECTED:
            # Protected entries are added by the shell itself, before any host runs.
            return
        if self.mode == MODE_REPLACE and existing.tier == TIER_DEFAULT and new.tier == TIER_SESSION:
            # In replace mode default entries are dropped; overriding one is the same as
            # removing it and adding the session entry. Allowed.
            return
        if new.tier == TIER_DEFAULT:
            raise CommandError(f"default {new.name!r} may not replace an existing {existing.tier} entry")

    def _remove_entry(self, entry: Entry) -> None:
        for typed in entry.names():
            if self._entries.get(typed) is entry:
                del self._entries[typed]

    def unregister(self, name: str) -> None:
        """Remove the entry that owns ``name``. Protected entries cannot be removed."""
        with self._lock:
            entry = self._entries.get(name)
            if entry is None:
                return
            if entry.tier == TIER_PROTECTED:
                raise CommandError(f"{entry.name!r} is protected and cannot be removed")
            self._remove_entry(entry)

    # ---- lookup -------------------------------------------------------

    def lookup(self, name: str) -> Optional[Entry]:
        """The entry for an exact typed name or alias, regardless of availability."""
        with self._lock:
            return self._entries.get(name)

    def entries(self) -> List[Entry]:
        """Every distinct entry, in registration order, regardless of availability."""
        with self._lock:
            seen: Dict[int, Entry] = {}
            for entry in self._entries.values():
                seen.setdefault(id(entry), entry)
            return list(seen.values())

    def visible(self, state: Any = None) -> List[Entry]:
        """Entries whose availability predicate passes for ``state``, by name."""
        out = [e for e in self.entries() if _available(e, state)]
        return sorted(out, key=lambda e: e.name)

    def candidates(self, prefix: str, state: Any = None) -> List[str]:
        """Typed names of available entries starting with ``prefix``, for completion and help.

        The result is for display only. Dispatch uses ``resolve``.
        """
        names: List[str] = []
        for entry in self.visible(state):
            for typed in entry.names():
                if typed.startswith(prefix):
                    names.append(typed)
        return sorted(set(names))

    def resolve(self, text: str, state: Any = None) -> Tuple[str, Optional[Entry]]:
        """Decide what a typed word means.

        Returns ``(kind, entry)``: ``exact`` or ``unique`` with the entry to run;
        ``ambiguous`` or ``none`` with ``None``. Nothing is returned for the candidates.
        """
        with self._lock:
            exact = self._entries.get(text)
            if exact is not None and _available(exact, state):
                return RESOLVE_EXACT, exact
            matches: Dict[int, Entry] = {}
            for typed, entry in self._entries.items():
                if typed.startswith(text) and _available(entry, state):
                    matches.setdefault(id(entry), entry)
        if not text:
            return RESOLVE_NONE, None
        if len(matches) == 1:
            return RESOLVE_UNIQUE, next(iter(matches.values()))
        if len(matches) > 1:
            return RESOLVE_AMBIGUOUS, None
        return RESOLVE_NONE, None


def _available(entry: Entry, state: Any) -> bool:
    if entry.available is None:
        return True
    try:
        return bool(entry.available(state))
    except Exception:
        # A broken predicate hides the entry rather than breaking the prompt.
        io.echo_traceback(f"commands: availability check for {entry.name!r} failed")
        return False


def _log_override(old: Entry, new: Entry) -> None:
    if old is new:
        return
    io.echo(f"commands: {new.tier} {new.name!r} overrides {old.tier} {old.name!r}", level="debug")


def protected_entry_names(registry: CommandRegistry) -> List[str]:
    """Names of protected entries, for tests and for the shell's own checks."""
    return sorted(e.name for e in registry.entries() if e.tier == TIER_PROTECTED)
