"""The JSON form of the seam types (front-end-seam.md, the wire section).

A front end on another runtime (a mobile client) speaks this form. Only JSON types appear: strings,
numbers, booleans, null, lists, and objects. ``data`` and ``payload`` are plain dicts on the wire.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Type

from .events import Event
from .requests import Request
from .results import ActionResult


def result_to_wire(r: ActionResult) -> Dict[str, Any]:
    return {"ok": r.ok, "code": r.code, "message": r.message, "data": dict(r.data)}


def result_from_wire(d: Mapping[str, Any]) -> ActionResult:
    return ActionResult(ok=d["ok"], code=d["code"], message=d.get("message", ""), data=d.get("data", {}))


def event_to_wire(e: Event) -> Dict[str, Any]:
    return {"kind": e.kind, "scope": e.scope, "moniker": e.moniker, "payload": dict(e.payload)}


def event_from_wire(d: Mapping[str, Any]) -> Event:
    return Event(kind=d["kind"], scope=d["scope"], moniker=d.get("moniker"), payload=d.get("payload", {}))


def request_to_wire(req: Request) -> Dict[str, Any]:
    body = {k: v for k, v in vars(req).items()}
    return {"type": type(req).__name__, "fields": body}


def request_from_wire(d: Mapping[str, Any], types: Mapping[str, Type[Request]]) -> Request:
    cls = types[d["type"]]
    return cls(**d["fields"])
