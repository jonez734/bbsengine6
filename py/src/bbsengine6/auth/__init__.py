# bbsengine6/auth/__init__.py
# Authorization policy for bed's auth / reconnect / refresh / revoke ops.
#
# Mirrors the bbsengine6.bank pattern: a module-level access() function
# owns the per-op authorization policy, and bed/api/auth.py delegates
# each _handle_auth_* decision to it. The bed handler owns the wire-shape
# gates (token decode, signature, expiry, instance match, store presence)
# because those touch bed's HMAC secret; access() receives the decoded
# claims under message["claims"] so it never has to know the HMAC scheme.

from __future__ import annotations

import argparse
from typing import Any, Dict, Optional


__version__ = "202608130000"


__all__ = ["access"]


def init(args, **kw) -> bool:
    """Register bbsengine6.auth as a first-class module."""
    from bbsengine6 import register_module

    register_module(
        name="bbsengine6.auth",
        module_path="bbsengine6.auth",
        version=__version__,
        apis={"access": access},
    )
    return True


def buildargs(args, **kw):
    """No auth-specific CLI flags."""
    return None


def main(args, **kw) -> bool:
    """No-op entry point; bed/api/auth.py is the runtime consumer."""
    return True


def _moniker_eq(a: Optional[str], b: Optional[str]) -> bool:
    """Case-insensitive moniker comparison after strip."""
    if not a or not b:
        return False
    return a.strip().lower() == b.strip().lower()


def _get_session(kwargs: Dict[str, Any]) -> Optional[Any]:
    return kwargs.get("session")


def _get_message(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    msg = kwargs.get("message")
    return msg if isinstance(msg, dict) else {}


def _get_claims(message: Dict[str, Any]) -> Dict[str, Any]:
    """Return the decoded claims sub-dict, or empty dict if absent/malformed.

    The bed handler decodes the HMAC-signed token before calling
    access() and stuffs the resulting claims under message["claims"].
    access() never reads the raw token.
    """
    claims = message.get("claims")
    return claims if isinstance(claims, dict) else {}


def access(args: argparse.Namespace, op: str, /, **kwargs: Any) -> bool:
    """Authorize ``op`` for the given session/message pair.

    Returns True if the session is allowed to perform ``op`` on the
    target described by ``message``; False otherwise. The caller
    decides how to surface the denial (forbidden envelope,
    not_authenticated envelope, etc.).

    Convention: ``op`` is a domain verb (the operation the caller
    wants to perform), not the wire-protocol message type. The bed
    WS handler maintains its own ``message_type -> op`` mapping and
    calls this function with the domain verb.

    Recognized op values:
      "login"      -- issue a fresh bearer token via moniker/password
      "reconnect"  -- rebind an existing token to a new websocket
      "refresh"    -- rotate the live session's token (must be on
                      the original websocket)
      "revoke"     -- delete a token from the store

    Required kwargs (both optional, both default to "deny"):
      session : bed.api.session.SessionState (or any object with
                ``.moniker: str``, ``.is_sysop: bool`` and
                ``.session_id: str`` attributes), or ``None`` for
                an unbound websocket.
      message : dict, the incoming wire-shaped payload. access()
                reads ``message["claims"]`` for the decoded token
                claims (populated by the bed handler post-verification).

    The function does NOT perform input validation (token signature,
    expiry, instance match, store presence). That is the caller's
    job and lives next to the wire-envelope shape checks. Mixing
    validation into access() would couple it to bed's HMAC scheme.
    """
    session = _get_session(kwargs)
    message = _get_message(kwargs)

    # At module-load time (bbsengine6.module.check calls us with op="run"
    # and no extra kwargs), there is no session yet. We allow the module
    # to load for anyone; the per-op rules below only fire when the
    # caller passes a ``session`` kwarg.
    if "session" not in kwargs:
        return True

    # Runtime call: session kwarg was explicitly passed.

    if op == "login":
        # Anyone may attempt to log in; the credential provider decides.
        return True

    if op == "reconnect":
        # If a live session is bound to the websocket, it must match
        # the token's moniker (or be a sysop). An unbound websocket
        # always passes -- this is the reconnect-after-restart path
        # where the previous socket's session has been cleaned up.
        if session is None:
            return True
        if getattr(session, "is_sysop", False):
            return True
        claims = _get_claims(message)
        return _moniker_eq(getattr(session, "moniker", None), claims.get("moniker"))

    if op == "refresh":
        # The live websocket must be the same session as the token.
        # This is the session-bound gate: refreshing on someone else's
        # websocket is not allowed.
        if session is None:
            return False
        claims = _get_claims(message)
        return getattr(session, "session_id", None) == claims.get("session_id")

    if op == "revoke":
        # Any signature-valid token can be revoked; the handler has
        # already verified the signature before calling access().
        return True

    return False
