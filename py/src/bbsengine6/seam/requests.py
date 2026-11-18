"""Requests: the typed input a front end sends to a domain (front-end-seam.md, section 7).

A request is a frozen dataclass that names the scope and the member, plus its own fields. The
domain dispatches on the request's type, so each request type has exactly one handler.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    scope: str
    moniker: str | None = None


@dataclass(frozen=True)
class LoginRequest(Request):
    """Log a member in. Scope ``auth``: there is no table or room before a login. Both fields are required; a blank
    moniker or password is refused by the handler before any check."""

    scope: str = "auth"
    moniker: str | None = None
    password: str = ""
