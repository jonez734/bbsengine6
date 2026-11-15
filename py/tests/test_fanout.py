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
        asyncio.run(send_to_sessions(server, [1, 2], {"type": "x"}))
        self.assertEqual(server.sent, [(1, {"type": "x"}), (2, {"type": "x"})])

    def test_accepts_string_session_ids_as_bed_stores_them(self):
        server = _Server()
        asyncio.run(send_to_sessions(server, ["3", "4"], {"type": "x"}))
        self.assertEqual([sid for sid, _ in server.sent], [3, 4])

    def test_no_sessions_sends_nothing(self):
        server = _Server()
        asyncio.run(send_to_sessions(server, [], {"type": "x"}))
        self.assertEqual(server.sent, [])

    def test_no_server_sends_nothing(self):
        asyncio.run(send_to_sessions(None, [1], {"type": "x"}))


class TestSendPerSession(unittest.TestCase):
    def test_each_session_gets_its_own_message(self):
        server = _Server()
        asyncio.run(send_per_session(server, {1: {"hand": "a"}, "2": {"hand": "b"}}))
        self.assertEqual(server.sent, [(1, {"hand": "a"}), (2, {"hand": "b"})])

    def test_no_server_sends_nothing(self):
        asyncio.run(send_per_session(None, {1: {"hand": "a"}}))


if __name__ == "__main__":
    unittest.main()
