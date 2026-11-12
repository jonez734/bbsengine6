"""Timing and size settings for bbsengine6.io, read from a config block.

A host passes the ``io`` section of its config to ``configure``. Each setting has a default, the value
the module used before it was configurable. ``get`` reads the current value, so a setting changed after
import still takes effect at the next use. Unknown keys and bad values raise ValueError before anything
changes. Keys starting with "_" are comments.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

# name: (default, kind). kind is "seconds" (positive number), "count" (positive int), or "bytes" (positive int).
_SPECS: Dict[str, tuple] = {
    "query_settle_seconds": (0.25, "seconds"),
    "esc_tail_wait_seconds": (0.05, "seconds"),
    "inputstring_getch_timeout_seconds": (0.015, "seconds"),
    "inputstring_history_size": (500, "count"),
    "inputstring_pagesize": (10, "count"),
    "paste_max_bytes": (65536, "bytes"),
}

_values: Dict[str, Any] = {}


def reset() -> None:
    _values.clear()


def get(name: str) -> Any:
    if name not in _SPECS:
        raise KeyError(f"unknown io setting: {name!r}")
    return _values.get(name, _SPECS[name][0])


def _check(name: str, value: Any) -> Any:
    kind = _SPECS[name][1]
    if kind == "seconds":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"io.{name} must be a positive number of seconds")
        return float(value)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"io.{name} must be a positive integer")
    return value


def configure(section: Mapping[str, Any] | None) -> None:
    """Apply the settings in ``section`` (the config's ``io`` object). ``None`` or empty keeps the defaults.

    The argument is the section itself, for example ``{"inputstring_pagesize": 4}``, not the whole
    config file.
    """
    if not section:
        return
    if not isinstance(section, Mapping):
        raise ValueError("io must be an object")
    changes = {k: v for k, v in section.items() if not str(k).startswith("_")}
    checked = {}
    for name, value in changes.items():
        if name not in _SPECS:
            raise ValueError(f"unknown io setting: {name!r}")
        checked[name] = _check(name, value)
    _values.update(checked)
