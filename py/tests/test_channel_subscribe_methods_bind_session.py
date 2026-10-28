"""The channel subscribe, unsubscribe and get-subscriptions methods run without NameError.

They take the websocket and derive the session id from it. A method that still references an
undefined session_id raises NameError after the authority passes, which the daemon reports as
service_error.
"""

import argparse
import asyncio
from types import SimpleNamespace

from bbsengine6.channel.api.handler import ChannelServiceHandler
from bbsengine6.net.transport import ChannelState


class _Registry:
    def __init__(self, moniker):
        self._moniker = moniker

    def get_by_websocket(self, websocket_id):
        return SimpleNamespace(moniker=self._moniker)

    def get_moniker(self, session_id):
        return self._moniker


def _handler(moniker):
    return ChannelServiceHandler(argparse.Namespace(), _Registry(moniker), channel_state=ChannelState())


def test_subscribe_and_unsubscribe_run_for_an_authenticated_websocket(monkeypatch):
    monkeypatch.setattr(
        "bbsengine6.channel.api.handler.ChannelService.can_subscribe",
        lambda self, channel, moniker: {"allowed": True},
    )
    ws = SimpleNamespace(id=7)
    h = _handler("alice")
    sub = asyncio.run(h._handle_subscribe(ws, {"channel": "casino:table:t1:chat"}))
    assert sub["type"] == "subscribed", sub
    unsub = asyncio.run(h._handle_unsubscribe(ws, {"channel": "casino:table:t1:chat"}))
    assert unsub["type"] != "service_error", unsub


def test_get_subscriptions_runs_for_an_authenticated_websocket():
    ws = SimpleNamespace(id=7)
    out = asyncio.run(_handler("alice")._handle_get_subscriptions(ws))
    assert "error" not in out.get("type", ""), out
