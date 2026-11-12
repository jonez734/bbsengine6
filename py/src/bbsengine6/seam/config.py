"""Settings for the seam: event capacity, idle expiry, and the logger name.

A consumer sets them once at startup with ``configure``, from its config's ``bbsengine6`` section
(zoid6 gets them through bed's config loader). Only the keys given are changed. A value a domain or
log has already been built with keeps its value; new domains and logs use the current settings.
"""

from __future__ import annotations

from typing import Any, Dict

DEFAULT_CAPACITY = 1000
DEFAULT_IDLE_SECONDS = 300.0
DEFAULT_LOGGER_NAME = "bbsengine6.seam"

_settings: Dict[str, Any] = {}


def reset() -> None:
    _settings.clear()


def get_capacity() -> int:
    return _settings.get("capacity", DEFAULT_CAPACITY)


def get_idle_seconds() -> float:
    return _settings.get("idle_seconds", DEFAULT_IDLE_SECONDS)


def get_logger_name() -> str:
    return _settings.get("logger_name", DEFAULT_LOGGER_NAME)


def _positive_int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _positive_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{name} must be a positive number of seconds")
    return float(value)


def _logger(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("logger_name must be a non-empty string")
    return value.strip()


_VALIDATORS = {
    "capacity": lambda v: _positive_int("capacity", v),
    "idle_seconds": lambda v: _positive_number("idle_seconds", v),
    "logger_name": _logger,
}


def configure(**changes: Any) -> None:
    """Set the given keys. An unknown key or a bad value raises ValueError, before anything changes."""
    checked = {}
    for key, value in changes.items():
        if key not in _VALIDATORS:
            raise ValueError(f"unknown seam setting: {key!r}")
        checked[key] = _VALIDATORS[key](value)
    _settings.update(checked)
