"""Channel subscribe resolves the subscriber through bed's SessionRegistry.

bed binds a login in SessionRegistry under the websocket id (str(websocket.id)), and has no
get_moniker. The channel handler must still find the moniker, or every subscribe is refused as
not_authenticated.
"""

from types import SimpleNamespace

from bbsengine6.channel.api.handler import _moniker_for


class _Registry:
    """A minimal stand-in for bed's SessionRegistry: lookup by websocket id only."""

    def __init__(self):
        self._by_ws = {}

    def bind(self, websocket_id, moniker):
        self._by_ws[websocket_id] = SimpleNamespace(moniker=moniker)

    def get_by_websocket(self, websocket_id):
        return self._by_ws.get(websocket_id)


def test_bound_websocket_resolves_to_its_moniker():
    reg = _Registry()
    reg.bind("42", "bjbed_b")
    assert _moniker_for(reg, SimpleNamespace(id=42)) == "bjbed_b"


def test_unbound_websocket_resolves_to_none():
    reg = _Registry()
    assert _moniker_for(reg, SimpleNamespace(id=99)) is None


def test_store_with_get_moniker_is_still_used():
    class _Manager:
        def get_moniker(self, session_id):
            return "alice" if session_id is not None else None

    assert _moniker_for(_Manager(), SimpleNamespace(id=1)) == "alice"
