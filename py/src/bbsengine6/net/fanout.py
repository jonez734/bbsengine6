"""Generic fan-out to sessions: one message to many sessions, or a different message to each.

A table, a room, or a game sends its players and watchers their own views, or the same view to a set of
sessions. These helpers know sessions and messages, not games, so any program on the transport can use
them. Session ids are connection ids (the string form of the websocket id a session records); they are routed as
given.
"""

from typing import Any, Dict, Iterable, Union

SessionId = Union[str, Any]


def _as_session_id(session_id: SessionId) -> str:
    # Connection ids are UUIDs (strings); they are routed as they are, never converted to an int.
    return str(session_id)


async def send_to_sessions(server: Any, session_ids: Iterable[SessionId], message: Dict[str, Any]) -> None:
    """Send ``message`` to each session in ``session_ids``. A session with no live socket is skipped.

    ``server`` is the transport (anything with ``send_to_session``). With no server, nothing is sent.
    """
    if server is None:
        return
    for session_id in session_ids:
        await server.send_to_session(_as_session_id(session_id), message)


async def send_per_session(server: Any, messages: Dict[SessionId, Dict[str, Any]]) -> None:
    """Send each session its own message: ``messages`` maps a session id to the message for that session.

    Used when every player's view differs (each sees their own hand). With no server, nothing is sent.
    """
    if server is None:
        return
    for session_id, message in messages.items():
        await server.send_to_session(_as_session_id(session_id), message)
