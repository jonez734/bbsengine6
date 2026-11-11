"""Server side of the terminal_caps message: validation, storage, and the dispatch round trip."""

import asyncio
import gc

import pytest

from bbsengine6.net import terminal_caps as tc
from bbsengine6.net import transport


class _Socket:
    """A stand-in for a websocket. Weak-referenceable, like the real connection object."""


GOOD = {
    "term": "xterm-256color",
    "color": "truecolor",
    "source": "query",
    "ansi": "\x1b[?62;1;2c",
}


def _server():
    srv = transport.WebSocketServer.__new__(transport.WebSocketServer)
    srv._services = {}
    srv._default_service = None
    srv._pre_dispatch = None
    srv._post_dispatch = None
    return srv


def _dispatch(ws, message):
    return asyncio.run(_server().dispatch_message(ws, "/", message))


# --- validation -------------------------------------------------------------

def test_good_caps_pass_and_are_copied():
    clean = tc.validate_terminal_caps(dict(GOOD))
    assert clean == GOOD


def test_missing_optional_fields_default():
    clean = tc.validate_terminal_caps({"source": "unknown"})
    assert clean == {"source": "unknown", "term": "", "color": None, "ansi": None}


@pytest.mark.parametrize(
    "caps, reason",
    [
        ("not a dict", "object"),
        ({"source": "query", "bogus": 1}, "unknown field"),
        ({"source": "vte"}, "source"),
        ({}, "source"),
        ({"source": "query", "term": "x" * 65}, "term"),
        ({"source": "query", "term": 5}, "term"),
        ({"source": "query", "color": 256}, "color"),
        ({"source": "query", "color": "16777216"}, "color"),
        ({"source": "query", "color": "yes"}, "color"),
        ({"source": "query", "colors": 256}, "unknown field"),
        ({"source": "query", "true_color": True}, "unknown field"),
        ({"source": "query", "color_256": True}, "unknown field"),
        ({"source": "query", "ansi": "x" * 65}, "ansi"),
        ({"source": "query", "ansi": 62}, "ansi"),
    ],
)
def test_bad_caps_are_rejected(caps, reason):
    with pytest.raises(tc.TerminalCapsError, match=reason):
        tc.validate_terminal_caps(caps)


# --- storage ----------------------------------------------------------------

def test_store_replaces_earlier_report():
    ws = _Socket()
    tc.store_terminal_caps(ws, {"source": "unknown"})
    tc.store_terminal_caps(ws, {"source": "query"})
    assert tc.get_terminal_caps(ws) == {"source": "query"}


def test_reports_are_per_connection():
    a, b = _Socket(), _Socket()
    tc.store_terminal_caps(a, {"source": "query"})
    assert tc.get_terminal_caps(b) is None


def test_forget_clears_and_closed_socket_does_not_leak():
    ws = _Socket()
    tc.store_terminal_caps(ws, {"source": "query"})
    tc.forget_terminal_caps(ws)
    assert tc.get_terminal_caps(ws) is None

    gone = _Socket()
    tc.store_terminal_caps(gone, {"source": "query"})
    assert len(tc._store) >= 1
    del gone
    gc.collect()
    assert len(tc._store) == 0


# --- handle_terminal_caps and dispatch round trip ---------------------------

def test_handle_valid_stores_and_acks():
    ws = _Socket()
    ack = tc.handle_terminal_caps(ws, {"request_id": "r1", "caps": dict(GOOD)})
    assert ack == {"type": "terminal_caps_ack", "request_id": "r1", "stored": True}
    assert tc.get_terminal_caps(ws)["source"] == "query"


def test_handle_invalid_acks_with_error_and_stores_nothing():
    ws = _Socket()
    ack = tc.handle_terminal_caps(ws, {"request_id": "r2", "caps": {"source": "query", "x": 1}})
    assert ack["stored"] is False and "unknown field" in ack["error"]
    assert tc.get_terminal_caps(ws) is None


def test_dispatch_round_trip_echoes_request_id():
    ws = _Socket()
    ack = _dispatch(ws, {"type": "terminal_caps", "request_id": "abc", "caps": dict(GOOD)})
    assert ack == {"type": "terminal_caps_ack", "request_id": "abc", "stored": True}
    assert tc.get_terminal_caps(ws)["color"] == "truecolor"


def test_dispatch_bad_field_is_rejected_with_request_id():
    ws = _Socket()
    ack = _dispatch(ws, {"type": "terminal_caps", "request_id": "bad", "caps": {"source": "x"}})
    assert ack["type"] == "terminal_caps_ack"
    assert ack["request_id"] == "bad" and ack["stored"] is False
    assert tc.get_terminal_caps(ws) is None


def test_dispatch_missing_caps_is_rejected():
    ws = _Socket()
    ack = _dispatch(ws, {"type": "terminal_caps", "request_id": "m"})
    assert ack["stored"] is False


@pytest.mark.parametrize("value", ["truecolor", "256", None])
def test_color_accepts_the_three_levels(value):
    clean = tc.validate_terminal_caps({"source": "query", "color": value})
    assert clean["color"] == value
