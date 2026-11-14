"""ActionResult: what an application method returns (front-end-seam.md, section 3).

``ok`` and ``code`` are the contract. ``message`` is display text and is never branched on. ``data``
is the method's typed payload, fixed by the application's section in its own spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from .codes import ErrorCode


def _frozen(data: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(data or {}))


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    code: str
    message: str = ""
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # A read-only view, so a caller cannot change a result after it is returned.
        object.__setattr__(self, "data", _frozen(self.data))


# Codes an application registered for its own refusals (see register_code). The generic enum is fixed.
_APP_CODES: set[str] = set()


def register_code(code: str) -> str:
    """Register an application's refusal code. A generic code, or ``ok``, cannot be registered."""
    if code == ErrorCode.OK.value or code in {c.value for c in ErrorCode}:
        raise ValueError(f"{code!r} is a generic code and cannot be registered by an application")
    if not isinstance(code, str) or not code.strip():
        raise ValueError("a result code must be a non-empty string")
    _APP_CODES.add(code)
    return code


def _known(code: str) -> str:
    if code in {c.value for c in ErrorCode} or code in _APP_CODES:
        return code
    raise ValueError(f"unknown result code: {code!r}")


def success(data: Mapping[str, Any] | None = None) -> ActionResult:
    """A successful result. The code is always ``ok``."""
    return ActionResult(ok=True, code=ErrorCode.OK.value, data=data or {})


def refusal(code: str, message: str = "", data: Mapping[str, Any] | None = None) -> ActionResult:
    """A refused action. ``code`` must be a known code other than ``ok``."""
    if code == ErrorCode.OK.value:
        raise ValueError("a refusal cannot carry the code 'ok'; use success()")
    return ActionResult(ok=False, code=_known(code), message=message, data=data or {})
