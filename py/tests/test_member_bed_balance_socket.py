"""_bed_balance closes its bed socket once, on the loop that opened it, with no ResourceWarning.

The socket is released through bed's `async with` (its aclose), not by a hand-written close, so
the receive task and the websocket are both shut down.
"""

import asyncio
import gc
import warnings
from unittest.mock import patch

import pytest

from bbsengine6.member import lib as member_lib


class _Ws:
    def __init__(self):
        self.closes = 0
        self.close_loop = None

    async def close(self):
        self.closes += 1
        self.close_loop = asyncio.get_running_loop()


class _Conn:
    """A bed connection with the async-with contract: __aexit__ awaits aclose()."""

    def __init__(self):
        self._ws = _Ws()
        self.ws = self._ws
        self.aclose_calls = 0

    async def aclose(self):
        self.aclose_calls += 1
        ws, self._ws = self._ws, None
        if ws is not None:
            await ws.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.aclose()
        return False


ARGS = type("A", (), {"token": "tok", "token_file": None})()


def _call(conn):
    async def fake_request(self, msg):
        return {"balance": 7, "account": True}

    with warnings.catch_warnings(record=True) as rec, \
         patch("bed.client.get_bed_connection", return_value=conn), \
         patch("bed.client.bank.BedBankClient._request", fake_request), \
         patch.object(member_lib, "_resolve_bed_token", return_value="tok"):
        warnings.simplefilter("always")
        result = member_lib._bed_balance(ARGS, "alice")
        gc.collect()
    return result, [w for w in rec if issubclass(w.category, ResourceWarning)]


@pytest.mark.unit
def test_bed_balance_closes_the_websocket_exactly_once():
    conn = _Conn()
    _call(conn)
    assert conn.ws.closes == 1


@pytest.mark.unit
def test_bed_balance_releases_the_connection_through_aclose():
    # The hand-written close never calls the connection's aclose, so the receive task is not
    # stopped. The fix must go through aclose (bed's async-with contract).
    conn = _Conn()
    _call(conn)
    assert conn.aclose_calls == 1


@pytest.mark.unit
def test_bed_balance_closes_on_the_loop_of_the_request():
    conn = _Conn()
    _call(conn)
    assert conn.ws.close_loop is not None


@pytest.mark.unit
def test_bed_balance_leaves_no_resource_warning():
    _, leaks = _call(_Conn())
    assert leaks == [], [str(w.message) for w in leaks]


@pytest.mark.unit
def test_bed_balance_still_returns_the_balance():
    result, _ = _call(_Conn())
    assert result["balance"] == 7
    assert result["account"] is True
