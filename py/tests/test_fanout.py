"""Generic fan-out: one message to many sessions, or a different message to each session.

A table, a room, or a game sends each player or watcher their own view, or the same view to a set of
sessions. These helpers are domain-neutral: they know sessions and messages, not games.
"""

import asyncio
import unittest

from bbsengine6.net.fanout import send_per_session, send_to_sessions


class _Server:
    """Stands in for the transport: records each per-session send."""

    def __init__(self):
        self.sent = []

    async def send_to_session(self, session_id, message):
        self.sent.append((session_id, message))


class TestSendToSessions(unittest.TestCase):
    def test_sends_the_same_message_to_each_session(self):
        server = _Server()
        asyncio.run(send_to_sessions(server, ["c1", "c2"], {"type": "x"}))
        self.assertEqual(server.sent, [("c1", {"type": "x"}), ("c2", {"type": "x"})])

    def test_routes_connection_ids_as_given_never_as_ints(self):
        server = _Server()
        cid = "f71e380e-211c-4a88-98b7-e305fb0a00d7"
        asyncio.run(send_to_sessions(server, [cid], {"type": "x"}))
        self.assertEqual(server.sent, [(cid, {"type": "x"})])

    def test_no_sessions_sends_nothing(self):
        server = _Server()
        asyncio.run(send_to_sessions(server, [], {"type": "x"}))
        self.assertEqual(server.sent, [])

    def test_no_server_sends_nothing(self):
        asyncio.run(send_to_sessions(None, [1], {"type": "x"}))


class TestSendPerSession(unittest.TestCase):
    def test_each_session_gets_its_own_message(self):
        server = _Server()
        asyncio.run(send_per_session(server, {"c1": {"hand": "a"}, "c2": {"hand": "b"}}))
        self.assertEqual(server.sent, [("c1", {"hand": "a"}), ("c2", {"hand": "b"})])

    def test_no_server_sends_nothing(self):
        asyncio.run(send_per_session(None, {1: {"hand": "a"}}))


if __name__ == "__main__":
    unittest.main()
