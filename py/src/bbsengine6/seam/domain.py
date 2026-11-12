"""Domain: the back end's object for one application (front-end-seam.md, sections 5, 7, thread model).

A domain owns its kind registry, its event log, its subscriptions, and its request handlers. A front
end subscribes to read events, and sends requests with ``request()``. The domain never calls a front
end, so no domain code runs on a front end's thread.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Type

from . import codes, events, kinds
from .kinds import LAGGED_KIND
from .requests import Request
from .results import ActionResult, refusal

IDLE_SECONDS = 300.0
LOGGER_NAME = "bbsengine6.seam"


def _log_warning(message: str) -> None:
    # Imported here so the seam's module import does not pull in the terminal layer (io).
    from ..util import logentry
    import logging

    logentry(message, level=logging.WARNING, logger_name=LOGGER_NAME)


class Domain:
    def __init__(
        self,
        name: str,
        *,
        capacity: int = events.DEFAULT_CAPACITY,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.name = name
        self.kinds = kinds.KindRegistry()
        self._log = events.EventLog(capacity)
        self._clock = clock
        self._subs: Dict[int, events.Subscription] = {}
        self._next_id = 0
        self._handlers: Dict[type, Callable[[Any], ActionResult]] = {}
        self._lock = threading.Lock()

    # --- kinds -------------------------------------------------------------

    def register_kind(self, name: str) -> str:
        return self.kinds.register(name)

    # --- events ------------------------------------------------------------

    def emit(self, event: events.Event) -> None:
        if event.kind == "warn":
            raise ValueError("'warn' is not a kind; use 'warning'")
        if not self.kinds.known(event.kind):
            raise ValueError(f"unknown event kind for domain {self.name!r}: {event.kind!r}")
        self._log.append(event)

    def subscribe(self, *, debug: bool = False) -> int:
        with self._lock:
            sid = self._next_id
            self._next_id += 1
            self._subs[sid] = events.Subscription(self._log.head, debug=debug, now=self._clock())
            return sid

    def set_debug(self, sid: int, on: bool) -> None:
        self._sub(sid).debug = on

    def read(self, sid: int) -> List[events.Event]:
        sub = self._sub(sid)
        sub.last_read = self._clock()
        missed, batch = self._log.since(sub.cursor)
        sub.cursor = self._log.head
        out: List[events.Event] = []
        if missed:
            _log_warning(f"{self.name}: subscription {sid} lagged, missed {missed} events")
            out.append(events.Event(LAGGED_KIND, "", None, {"missed": missed}))
        for e in batch:
            if e.kind == "debug" and not sub.debug:
                continue
            out.append(e)
        return out

    def expire_idle(self, idle_seconds: float = IDLE_SECONDS) -> List[int]:
        now = self._clock()
        with self._lock:
            gone = [sid for sid, s in self._subs.items() if now - s.last_read > idle_seconds]
            for sid in gone:
                del self._subs[sid]
        for sid in gone:
            _log_warning(f"{self.name}: subscription {sid} expired after {idle_seconds:.0f}s idle")
        return gone

    def _sub(self, sid: int) -> events.Subscription:
        try:
            return self._subs[sid]
        except KeyError:
            raise KeyError(f"no subscription {sid} (expired or never created)") from None

    # --- requests ----------------------------------------------------------

    def on(self, request_type: Type[Request], handler: Callable[[Any], ActionResult]) -> None:
        if request_type in self._handlers:
            raise ValueError(f"a handler is already registered for {request_type.__name__}")
        self._handlers[request_type] = handler

    def request(self, req: Request) -> ActionResult:
        handler = self._handlers.get(type(req))
        if handler is None:
            return refusal(codes.ErrorCode.INVALID_ACTION.value, f"no handler for {type(req).__name__}")
        result = handler(req)
        if not isinstance(result, ActionResult):
            raise TypeError(f"handler for {type(req).__name__} must return ActionResult")
        return result
