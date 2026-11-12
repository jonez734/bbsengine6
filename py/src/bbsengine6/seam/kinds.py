"""Per-domain registry of event kinds (front-end-seam.md, section 5).

Each domain owns one registry. A kind registered in one domain is unknown to another, so two
domains in one process cannot share kinds by accident.
"""

from __future__ import annotations

from typing import Set

MESSAGE_KINDS = frozenset({"debug", "info", "ok", "warning", "error"})
FRAGMENT_KIND = "fragment"
LAGGED_KIND = "lagged"


class KindRegistry:
    def __init__(self) -> None:
        self._kinds: Set[str] = set()

    def register(self, name: str) -> str:
        if name in MESSAGE_KINDS or name in (FRAGMENT_KIND, LAGGED_KIND):
            raise ValueError(f"domain kind {name!r} reuses a generic kind")
        if name == "warn":
            raise ValueError("'warn' is not a kind; use 'warning'")
        self._kinds.add(name)
        return name

    def known(self, name: str) -> bool:
        return name in MESSAGE_KINDS or name in (FRAGMENT_KIND, LAGGED_KIND) or name in self._kinds
