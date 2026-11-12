"""The seam's Domain: per-domain kinds, subscriptions, lag, expiry, requests, wire form.

Spec: handbook/specs/front-end-seam.md (sections 5, 7, the wire section, and the thread model).
"""

import dataclasses
import json

import pytest

from bbsengine6.seam import codes, domain as dm, events, kinds, requests, results, wire

pytestmark = pytest.mark.unit


def _event(kind="info", table="t1", text="x", moniker=None):
    return events.Event(kind=kind, table=table, moniker=moniker, payload={"text": text})


# --- per-domain kind registry (approved item 3) ------------------------------

def test_registry_is_per_instance_not_global():
    a = kinds.KindRegistry()
    b = kinds.KindRegistry()
    a.register("card_dealt")
    assert a.known("card_dealt")
    assert not b.known("card_dealt")


def test_registry_rejects_a_message_kind_name():
    with pytest.raises(ValueError):
        kinds.KindRegistry().register("info")


def test_registry_rejects_fragment_as_a_domain_kind():
    with pytest.raises(ValueError):
        kinds.KindRegistry().register("fragment")


def test_kind_registered_in_one_domain_is_rejected_by_another():
    d1 = dm.Domain("casino")
    d2 = dm.Domain("zoidoffice")
    d1.register_kind("card_dealt")
    d1.emit(_event(kind="card_dealt"))  # accepted in d1
    with pytest.raises(ValueError):
        d2.emit(_event(kind="card_dealt"))  # not registered in d2


# --- subscriptions (approved item 1) -----------------------------------------

def test_two_subscribers_each_see_every_event():
    d = dm.Domain("casino")
    s1, s2 = d.subscribe(), d.subscribe()
    d.emit(_event(text="a"))
    d.emit(_event(text="b"))
    assert [e.payload["text"] for e in d.read(s1)] == ["a", "b"]
    assert [e.payload["text"] for e in d.read(s2)] == ["a", "b"]


def test_one_subscriber_draining_does_not_affect_another():
    d = dm.Domain("casino")
    s1, s2 = d.subscribe(), d.subscribe()
    d.emit(_event(text="a"))
    d.read(s1)
    assert [e.payload["text"] for e in d.read(s2)] == ["a"]


def test_read_advances_only_its_own_cursor():
    d = dm.Domain("casino")
    s = d.subscribe()
    d.emit(_event(text="a"))
    assert len(d.read(s)) == 1
    assert d.read(s) == []
    d.emit(_event(text="b"))
    assert [e.payload["text"] for e in d.read(s)] == ["b"]


def test_read_keeps_per_table_order():
    d = dm.Domain("casino")
    s = d.subscribe()
    d.emit(_event(table="t1", text="a"))
    d.emit(_event(table="t2", text="x"))
    d.emit(_event(table="t1", text="b"))
    got = [e.payload["text"] for e in d.read(s) if e.table == "t1"]
    assert got == ["a", "b"]


# --- debug filtering is per subscription (approved item 4: default off) ------

def test_debug_is_off_by_default_for_a_subscription():
    d = dm.Domain("casino")
    s = d.subscribe()
    d.emit(_event(kind="debug", text="d"))
    assert d.read(s) == []


def test_debug_on_for_one_subscription_only():
    d = dm.Domain("casino")
    quiet, loud = d.subscribe(), d.subscribe(debug=True)
    d.emit(_event(kind="debug", text="d"))
    assert d.read(quiet) == []
    assert [e.payload["text"] for e in d.read(loud)] == ["d"]


def test_debug_can_be_toggled_mid_session():
    d = dm.Domain("casino")
    s = d.subscribe()
    d.set_debug(s, True)
    d.emit(_event(kind="debug", text="d"))
    assert len(d.read(s)) == 1


# --- lag (approved item 1 default 1000; item 2 option A: a marker) -----------

def test_log_keeps_at_most_the_buffer_size():
    log = events.EventLog(capacity=5)
    for i in range(12):
        log.append(_event(text=str(i)))
    assert len(log) == 5


def test_lagged_subscriber_gets_a_marker_then_the_head():
    d = dm.Domain("casino", capacity=3)
    s = d.subscribe()
    for i in range(7):
        d.emit(_event(text=str(i)))
    got = d.read(s)
    assert got[0].kind == "lagged"
    assert got[0].payload["missed"] == 4
    assert [e.payload["text"] for e in got[1:]] == ["4", "5", "6"]


def test_lag_is_reported_once_then_reading_resumes_normally():
    d = dm.Domain("casino", capacity=3)
    s = d.subscribe()
    for i in range(7):
        d.emit(_event(text=str(i)))
    d.read(s)
    d.emit(_event(text="7"))
    assert [e.kind for e in d.read(s)] == ["info"]


def test_lag_writes_a_warning_to_the_seam_logger(monkeypatch):
    calls = []
    monkeypatch.setattr(dm, "_log_warning", lambda msg: calls.append(msg))
    d = dm.Domain("casino", capacity=2)
    s = d.subscribe()
    for i in range(5):
        d.emit(_event(text=str(i)))
    d.read(s)
    assert calls and "lagged" in calls[0]


# --- idle expiry (approved item 3, option A: 300 s) --------------------------

def test_idle_subscription_expires_after_the_timeout():
    now = [0.0]
    d = dm.Domain("casino", clock=lambda: now[0])
    s = d.subscribe()
    now[0] = 301.0
    d.expire_idle()
    with pytest.raises(KeyError):
        d.read(s)


def test_active_subscription_does_not_expire():
    now = [0.0]
    d = dm.Domain("casino", clock=lambda: now[0])
    s = d.subscribe()
    now[0] = 200.0
    d.read(s)
    now[0] = 400.0
    d.expire_idle()
    d.read(s)  # still subscribed: last read was 200 s ago


def test_expiry_does_not_trim_events_a_live_subscriber_still_needs():
    now = [0.0]
    d = dm.Domain("casino", capacity=1000, clock=lambda: now[0])
    live = d.subscribe()
    dead = d.subscribe()
    d.emit(_event(text="a"))
    now[0] = 301.0
    d.read(live)  # live reads at 301; dead never reads
    d.expire_idle()
    assert [e.payload["text"] for e in d.read(live)] == []


# --- requests (approved item 2: synchronous, explicit registration) ----------

@dataclasses.dataclass(frozen=True)
class Hit(requests.Request):
    hand_id: int = 0


def test_request_dispatches_to_its_registered_handler():
    d = dm.Domain("casino")
    d.on(Hit, lambda req: results.success({"hand_id": req.hand_id}))
    r = d.request(Hit(table="t1", moniker="bob", hand_id=7))
    assert r.ok and r.code == "ok" and dict(r.data) == {"hand_id": 7}


def test_unknown_request_returns_invalid_action():
    d = dm.Domain("casino")
    r = d.request(Hit(table="t1", moniker="bob", hand_id=7))
    assert r.ok is False and r.code == codes.ErrorCode.INVALID_ACTION.value


def test_handler_must_return_an_action_result():
    d = dm.Domain("casino")
    d.on(Hit, lambda req: "not a result")
    with pytest.raises(TypeError):
        d.request(Hit(table="t1", moniker="bob", hand_id=7))


def test_registering_two_handlers_for_one_request_type_is_an_error():
    d = dm.Domain("casino")
    d.on(Hit, lambda req: results.success())
    with pytest.raises(ValueError):
        d.on(Hit, lambda req: results.success())


# --- wire form (round trip for each type) ------------------------------------

def test_action_result_round_trips_through_json():
    r = results.refusal("insufficient_funds", "Insufficient funds", {"balance": 3})
    back = wire.result_from_wire(json.loads(json.dumps(wire.result_to_wire(r))))
    assert back == r


def test_success_result_round_trips_through_json():
    r = results.success({"amount": 5})
    back = wire.result_from_wire(json.loads(json.dumps(wire.result_to_wire(r))))
    assert back == r


def test_event_round_trips_through_json():
    e = events.Event(kind="card_dealt", table="t1", moniker="bob", payload={"hand_id": 1, "total": 17})
    back = wire.event_from_wire(json.loads(json.dumps(wire.event_to_wire(e))))
    assert back == e


def test_request_round_trips_through_json():
    req = Hit(table="t1", moniker="bob", hand_id=7)
    back = wire.request_from_wire(json.loads(json.dumps(wire.request_to_wire(req))), {"Hit": Hit})
    assert back == req


def test_wire_dicts_use_only_json_types():
    r = results.success({"cards": ["AS", "KD"], "busted": False})
    text = json.dumps(wire.result_to_wire(r))
    assert json.loads(text)["data"]["busted"] is False


def test_wire_result_has_the_documented_fields():
    d = wire.result_to_wire(results.success())
    assert set(d) == {"ok", "code", "message", "data"}


def test_wire_event_has_the_documented_fields():
    d = wire.event_to_wire(_event())
    assert set(d) == {"kind", "table", "moniker", "payload"}


# --- layering: the seam imports no front-end code -----------------------------

def test_seam_modules_do_not_import_io_at_module_level():
    import pathlib
    import re

    seam_dir = pathlib.Path(dm.__file__).parent
    pattern = re.compile(r"^(from|import)\s+(bbsengine6\.io|\.\.io|\.io)\b", re.MULTILINE)
    offenders = [p.name for p in seam_dir.glob("*.py") if pattern.search(p.read_text())]
    assert offenders == []
