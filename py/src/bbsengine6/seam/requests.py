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
