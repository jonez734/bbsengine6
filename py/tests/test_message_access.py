"""
Unit tests for ``bbsengine6.message.access``.

Pins every (op, session, message) branch of the access decision
matrix. These are unit-only: no DB connection required. Run with
``pytest -m unit tests/test_message_access.py``.

After the bank/auth/casino-standard upgrade, ``access()`` prefers
claim-derived ``moniker`` / ``is_sysop`` (from ``message["claims"]``)
over the in-memory session attributes. The "claim-aware" cases below
pin that contract; the "no-claims" cases pin the legacy fallback so
callers that didn't run the token gate keep their semantics.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from bbsengine6.message import access as message_access

pytestmark = pytest.mark.unit


def _session(moniker: str | None = None, *, is_sysop: bool = False):
    """Build a session-like object with .moniker and .is_sysop."""
    return SimpleNamespace(moniker=moniker, is_sysop=is_sysop)


def _claims(moniker: str | None = None, *, is_sysop: bool = False, **extra):
    """Build a claims dict the bed handler stashes on ``message['claims']``.

    Mirrors the schema AuthService._mint_record emits: the bed handler
    decodes the HMAC-signed token and stuffs the resulting JSON
    payload here before calling access().
    """
    claims = {
        "moniker": moniker,
        "is_sysop": bool(is_sysop),
        "session_id": extra.get("session_id", "s1"),
        "issued_at": extra.get("issued_at", 0.0),
        "expires_at": extra.get("expires_at", 9999999999.0),
    }
    claims.update(extra)
    return claims


# ---------- module-load time ----------


def test_no_session_kwarg_returns_true():
    """bbsengine6.module.check() calls access() with no session kwarg at
    module-load time; access() must return True so the module loads."""
    assert message_access(None, "run") is True


# ---------- subscribe / unsubscribe / list_pending (self-or-sysop) ----------


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_self_ops_allowed_when_session_owns_target(op):
    s = _session("alice", is_sysop=False)
    msg = {"moniker": "alice"}
    assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_self_ops_denied_on_other_target(op):
    s = _session("alice", is_sysop=False)
    msg = {"moniker": "bob"}
    assert message_access(None, op, session=s, message=msg) is False


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_self_ops_allowed_on_other_target_when_sysop(op):
    s = _session("sysop", is_sysop=True)
    msg = {"moniker": "alice"}
    assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_self_ops_case_insensitive_match(op):
    s = _session("Alice", is_sysop=False)
    msg = {"moniker": "alice"}
    assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
@pytest.mark.parametrize("moniker", ["", None])
def test_self_ops_denied_when_target_missing(op, moniker):
    s = _session("alice", is_sysop=False)
    msg = {"moniker": moniker}
    assert message_access(None, op, session=s, message=msg) is False


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_self_ops_denied_when_session_is_none(op):
    """Unbound websocket -> always deny (mirrors bank.list_all rule).
    Claims alone (without a bound session) cannot grant access: the
    defense-in-depth contract is "the server-side session registry
    also recognizes this caller". The bed handler's lazy-bind
    fallback synthesizes a session before invoking access()."""
    msg = {"moniker": "alice", "claims": _claims("alice")}
    assert message_access(None, op, session=None, message=msg) is False


# ---------- claim-aware: claim moniker overrides session moniker ----------


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_claim_moniker_overrides_session_for_self_target(op):
    """Session says alice, claims say alice -- self-or-sysop rule
    passes. Used as a sanity check that claims don't accidentally
    deny a legitimate self subscription."""
    s = _session("alice", is_sysop=False)
    msg = {"moniker": "alice", "claims": _claims("alice")}
    assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_claim_moniker_overrides_session_for_other_target_when_same(op):
    """Session says bob, claims say bob -- self-or-sysop rule passes.
    Sanity check that a session whose claims happen to match the
    target gets through (same as before)."""
    s = _session("bob", is_sysop=False)
    msg = {"moniker": "bob", "claims": _claims("bob")}
    assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_claim_moniker_differs_from_session_uses_claim(op):
    """Defense-in-depth path: session is alice (stale), claims say
    bob (verified). The wire says subscribe to alice's stream but
    the claim-derived moniker is bob, so the self-or-sysop rule
    denies. The claim is truth because it came from an HMAC-verified
    token, not from the (potentially stale) session snapshot."""
    s = _session("alice", is_sysop=False)
    msg = {"moniker": "alice", "claims": _claims("bob")}
    assert message_access(None, op, session=s, message=msg) is False


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_claim_moniker_overrides_session_to_allow_when_match(op):
    """Defense-in-depth: session is bob (stale), claims say alice.
    Wire says subscribe to alice's stream. Claims match the target
    so the rule passes -- a stale session can't block a legitimate
    subscription."""
    s = _session("bob", is_sysop=False)
    msg = {"moniker": "alice", "claims": _claims("alice")}
    assert message_access(None, op, session=s, message=msg) is True


# ---------- claim-aware: claim is_sysop overrides session is_sysop ----------


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_claim_is_sysop_true_allows_other_target(op):
    """Session says non-sysop alice, claims say is_sysop=True. Wire
    says subscribe to bob's stream. Claim-derived is_sysop wins,
    access() allows (mirrors the bank service claim-bypass rule)."""
    s = _session("alice", is_sysop=False)
    msg = {"moniker": "bob", "claims": _claims("alice", is_sysop=True)}
    assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_claim_is_sysop_false_denies_other_target(op):
    """Session says sysop root, claims say is_sysop=False (e.g.
    demoted). Wire says subscribe to alice's stream. Claim-derived
    is_sysop=False wins -- the demoted user can't escalate back."""
    s = _session("root", is_sysop=True)
    msg = {"moniker": "alice", "claims": _claims("root", is_sysop=False)}
    assert message_access(None, op, session=s, message=msg) is False


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_claim_is_sysop_false_session_sysop_falls_back_to_claim(op):
    """Sanity check: when claims explicitly say is_sysop=False
    (even if the legacy session attribute would say True), the
    claim wins. The ``"is_sysop" in claims`` branch is what
    :func:`_auth_is_sysop` uses to detect "claim was present". """
    s = _session("alice", is_sysop=True)  # session attribute True
    msg = {"moniker": "bob", "claims": _claims("alice", is_sysop=False)}
    assert message_access(None, op, session=s, message=msg) is False


# ---------- claim-aware: malformed / missing claims fall back to session ----------


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_missing_claims_dict_falls_back_to_session(op):
    """No ``claims`` key in the message -> fall back to session attrs."""
    s = _session("alice", is_sysop=False)
    msg = {"moniker": "alice"}
    assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_empty_claims_dict_falls_back_to_session(op):
    """Empty ``claims`` dict -> fall back to session attrs."""
    s = _session("alice", is_sysop=False)
    msg = {"moniker": "alice", "claims": {}}
    assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_malformed_claims_dict_falls_back_to_session(op):
    """Non-dict ``claims`` value (e.g. a list, string) -> fall back
    to session attrs. The :func:`_get_claims` helper defensively
    coerces."""
    s = _session("alice", is_sysop=False)
    for bad in (None, "not-a-dict", [1, 2, 3], 42):
        msg = {"moniker": "alice", "claims": bad}
        assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_claims_without_moniker_falls_back_to_session_moniker(op):
    """Claims present but with empty ``moniker`` -> fall back to
    session moniker for the self-or-sysop comparison."""
    s = _session("alice", is_sysop=False)
    msg = {"moniker": "alice", "claims": _claims(moniker="")}
    assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_claims_without_is_sysop_key_falls_back_to_session_sysop(op):
    """Claims present but missing the ``is_sysop`` key -> fall back
    to session.is_sysop. The :func:`_auth_is_sysop` helper only
    takes the claim when ``"is_sysop" in claims`` is True."""
    s = _session("root", is_sysop=True)
    msg = {"moniker": "alice", "claims": {"moniker": "root"}}
    assert message_access(None, op, session=s, message=msg) is True


@pytest.mark.parametrize(
    "op", ["subscribe", "unsubscribe", "list_pending"]
)
def test_claim_is_sysop_false_explicit_key_uses_claim(op):
    """Claims present with ``is_sysop: False`` (explicit) -> claim
    wins even if session would have been a sysop. The defensive
    ``"is_sysop" in claims`` test matters here: missing key vs
    explicit False have different semantics."""
    s = _session("root", is_sysop=True)
    msg = {"moniker": "alice", "claims": {"moniker": "root", "is_sysop": False}}
    assert message_access(None, op, session=s, message=msg) is False


# ---------- unknown op ----------


def test_unknown_op_returns_false():
    s = _session("alice", is_sysop=True)
    assert message_access(None, "frobnicate", session=s, message={"moniker": "alice"}) is False


def test_unknown_op_with_sysop_claims_returns_false():
    """Claims say sysop but op is unknown -> still deny. Defense in
    depth doesn't grant new ops; it only re-derives existing ones."""
    s = _session("alice", is_sysop=False)
    msg = {"moniker": "alice", "claims": _claims("alice", is_sysop=True)}
    assert message_access(None, "frobnicate", session=s, message=msg) is False
