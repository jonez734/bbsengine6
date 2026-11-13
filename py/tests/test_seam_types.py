"""The UI seam's framework types (handbook/specs/front-end-seam.md, sections 3, 4, 5, 10)."""

import dataclasses

import pytest

from bbsengine6.seam import codes, events, results

pytestmark = pytest.mark.unit


# --- section 4: codes -------------------------------------------------------

GENERIC = {
    "ok", "scope_not_found", "not_in_scope", "invalid_action", "forbidden",
    "not_authenticated", "service_error",
}


def test_generic_codes_are_in_the_enum():
    assert {c.value for c in codes.ErrorCode} >= GENERIC


def test_a_code_is_defined_once():
    values = [c.value for c in codes.ErrorCode]
    assert len(values) == len(set(values))


def test_code_values_are_lowercase_snake_case():
    for c in codes.ErrorCode:
        assert c.value == c.value.lower() and " " not in c.value, c


def test_codes_compare_as_plain_strings():
    # The wire mapping sends codes as strings; the enum must be a str subclass.
    assert codes.ErrorCode.NOT_IN_SCOPE == "not_in_scope"


def test_money_and_wager_codes_are_not_generic():
    # A bet or a balance is an application's concept, not every front end's. Those codes live in
    # the application, not in the seam's enum.
    values = {c.value for c in codes.ErrorCode}
    assert "insufficient_funds" not in values
    assert "invalid_bet" not in values


def test_table_codes_are_renamed_to_scope():
    values = {c.value for c in codes.ErrorCode}
    assert "table_not_found" not in values and "not_at_table" not in values


# --- section 3: ActionResult ------------------------------------------------

def test_action_result_fields():
    names = [f.name for f in dataclasses.fields(results.ActionResult)]
    assert names == ["ok", "code", "message", "data"]


def test_action_result_is_immutable():
    r = results.ActionResult(ok=True, code="ok")
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.ok = False  # type: ignore[misc]


def test_action_result_defaults_are_empty():
    r = results.ActionResult(ok=False, code="invalid_action")
    assert r.message == ""
    assert dict(r.data) == {}


def test_action_result_data_is_not_shared_between_instances():
    a = results.ActionResult(ok=True, code="ok")
    b = results.ActionResult(ok=True, code="ok")
    assert a.data is not b.data or dict(a.data) == dict(b.data) == {}


def test_success_helper_uses_code_ok():
    r = results.success(data={"amount": 5})
    assert r.ok is True and r.code == "ok" and dict(r.data) == {"amount": 5}


def test_refusal_helper_sets_code_and_message():
    r = results.refusal("forbidden", "Operation not permitted")
    assert r.ok is False and r.code == "forbidden" and r.message == "Operation not permitted"


def test_refusal_rejects_an_unknown_code():
    with pytest.raises(ValueError):
        results.refusal("no_such_code", "x")


def test_refusal_rejects_ok_as_a_code():
    # A refusal is never "ok"; "ok" belongs to success().
    with pytest.raises(ValueError):
        results.refusal("ok", "x")


# --- section 5: Event and the queue -----------------------------------------

MESSAGE_KINDS = {"debug", "info", "ok", "warning", "error"}


def test_message_kinds_are_exactly_the_five():
    assert events.MESSAGE_KINDS == MESSAGE_KINDS


def test_warn_is_not_a_message_kind():
    # section 5: "warn" is not used; "warning" is the only spelling.
    assert "warn" not in events.MESSAGE_KINDS


def test_event_is_immutable():
    e = events.Event(kind="info", scope="t1", moniker=None, payload={"text": "hi"})
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.kind = "error"  # type: ignore[misc]


