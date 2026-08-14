from __future__ import annotations

import argparse
from typing import Any, Dict, Optional

from .account import Account
from .transaction import Transaction
from .transfer import Transfer
from .bank import BankService

__version__ = "202608130000"

__all__ = [
    "Account",
    "Transaction",
    "Transfer",
    "BankService",
    "access",
]


def init(args, **kw) -> bool:
    """Register bbsengine6.bank as a first-class module."""
    from bbsengine6 import register_module

    register_module(
        name="bbsengine6.bank",
        module_path="bbsengine6.bank",
        version=__version__,
        apis={"access": access},
    )
    return True


def buildargs(args, **kw):
    """No bank-specific CLI flags."""
    return None


def main(args, **kw) -> bool:
    """No-op entry point; bed/api/bank.py is the runtime consumer."""
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
    decides how to surface the denial (forbidden envelope, CLI
    error, etc.).

    Convention: ``op`` is a domain verb (the operation the caller
    wants to perform), not the wire-protocol message type. The bed
    WS handler and the bed CLI each maintain their own
    ``message_type -> op`` / ``subcommand -> op`` mapping and call
    this function with the domain verb.

    Recognized op values:
      "balance"     -- read own/other account balance
      "add"         -- credit funds to an account
      "remove"      -- debit funds from an account
      "history"     -- read transaction history for an account
      "transfer"    -- create a pending transfer between two accounts
      "approve"     -- approve a pending transfer
      "reject"      -- reject a pending transfer
      "pending"     -- list pending transfers touching an account
      "list_all"    -- list every account (sysop-only)

    Required kwargs (both optional, both default to "deny"):
      session : bed.api.session.SessionState (or any object with
                ``.moniker: str`` and ``.is_sysop: bool`` attributes),
                or ``None`` for an unbound websocket.
      message : dict, the incoming wire-shaped payload. If the bed
                handler verified a bearer token for this op, the
                decoded claims live under ``message["claims"]``;
                access() uses the claim-derived ``moniker`` /
                ``is_sysop`` instead of the in-memory session
                attributes because they come from a
                cryptographically verified source.

    The function does NOT perform input validation (moniker present,
    amount > 0, transfer_id > 0). That is the caller's job and lives
    next to the wire-envelope shape checks. Mixing validation into
    access() would couple it to wire-protocol codes.
    """
    session = _get_session(kwargs)
    message = _get_message(kwargs)
    claims = _get_claims(message)

    # When the bed handler decoded and verified the session's bearer
    # token, the resulting claims are stashed under message["claims"].
    # Prefer the claim-derived values for authorization because they
    # come from a cryptographically verified source (HMAC + store +
    # expiry + instance-match), not just the in-memory session state.
    # Fall back to session attributes when no claims are supplied.
    auth_moniker = claims.get("moniker") or getattr(session, "moniker", None)
    auth_is_sysop = bool(
        claims.get("is_sysop")
        if "is_sysop" in claims
        else getattr(session, "is_sysop", False)
    )

    # At module-load time (bbsengine6.module.check calls us with op="run"
    # and no extra kwargs), there is no session yet. We allow the module
    # to load for anyone; the per-op rules below only fire when the
    # caller passes a ``session`` kwarg.
    if "session" not in kwargs:
        return True

    # Runtime call: session kwarg was explicitly passed. ``None`` means
    # the websocket is unbound, which is always a denial.
    if session is None:
        return False

    if op in ("balance", "add", "remove", "history", "pending"):
        target = (message.get("moniker") or "").strip()
        if not target:
            return False
        if auth_is_sysop:
            return True
        return _moniker_eq(auth_moniker, target)

    if op == "list_all":
        return auth_is_sysop

    if op == "transfer":
        f = (message.get("from") or "").strip()
        t = (message.get("to") or "").strip()
        if not f or not t:
            return False
        if not auth_is_sysop and not _moniker_eq(auth_moniker, f):
            return False
        rb = (message.get("requested_by") or "").strip()
        if rb and not auth_is_sysop and not _moniker_eq(auth_moniker, rb):
            return False
        return True

    if op in ("approve", "reject"):
        try:
            tid = int(message.get("transfer_id", 0))
        except (TypeError, ValueError):
            return False
        if tid <= 0:
            return False
        rb = (message.get("responded_by") or "").strip()
        if rb and not auth_is_sysop and not _moniker_eq(auth_moniker, rb):
            return False
        return True

    return False
