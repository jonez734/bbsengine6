"""The channel router's disconnect cleanup reaches a registry that drops by websocket.

A bed SessionRegistry has drop_by_websocket and no unregister_session, so the cleanup must use it
when the registry has it, and keep the SessionManager path (unregister_session by int id).
"""

from bbsengine6.channel.api import handler as ch


class _BedLike:
    def __init__(self):
        self.dropped = []

    def drop_by_websocket(self, websocket_id):
        self.dropped.append(websocket_id)


class _ManagerLike:
    def __init__(self):
        self.unregistered = []

    def unregister_session(self, session_id):
        self.unregistered.append(session_id)


def _handler(sessions):
    h = ch.MessageRouter.__new__(ch.MessageRouter)
    h.sessions = sessions
    h.channel_state = ch.ChannelState() if hasattr(ch, "ChannelState") else None
    return h


def test_disconnect_drops_by_websocket_on_a_bed_registry():
    reg = _BedLike()
    h = _handler(reg)
    h.unregister_session(7, websocket_id="ws-7")
    assert reg.dropped == ["ws-7"]


def test_disconnect_still_unregisters_by_int_on_a_session_manager():
    mgr = _ManagerLike()
    h = _handler(mgr)
    h.unregister_session(7)
    assert mgr.unregistered == [7]


def test_disconnect_without_websocket_id_on_bed_registry_is_safe():
    reg = _BedLike()
    h = _handler(reg)
    h.unregister_session(7)
    assert reg.dropped == []
