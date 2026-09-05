# channel/api/handler.py
# Standalone WebSocket handler for channel subscription services.

from typing import Any, Dict, List, Optional

from bbsengine6 import io
from bbsengine6.member.lib import (
    is_namespaced_moniker,
    moniker_exists,
    register_module_member,
)
from bbsengine6.net import (
    ChannelState,
    channel_subscribe,
    channel_unsubscribe,
    channel_unsubscribe_all,
    channel_get_session_channels,
)
from bbsengine6.services.channel import ChannelService


from bbsengine6.session import SessionManager


def _resolve_channel_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Pull the channel sub-tree from either flat (bed.json) or nested
    (zoid6.json) config shape.

    bed.json carries a top-level ``channel`` key. zoid6.json nests it under
    ``services.channel``. This helper accepts either, preferring the flat
    form when both are present (defensive against accidental duplication).
    """
    if not isinstance(config, dict):
        return {}
    flat = config.get("channel")
    if isinstance(flat, dict):
        return flat
    nested = config.get("services", {}).get("channel")
    if isinstance(nested, dict):
        return nested
    return {}


def _ensure_daemon_member(args: Any, moniker: str) -> Optional[str]:
    """Return ``moniker`` if the row exists or can be created; else None.

    The bypass path ``register_module_member`` requires a namespaced
    moniker. If the caller passed a flat moniker we warn-and-skip rather
    than fail: the operator can rename the seed entry, or run
    ``con member add`` manually for the flat moniker. Namespacing is the
    structural defense and we don't widen the bypass here.
    """
    if not is_namespaced_moniker(moniker):
        io.echo(
            f"channel auto-seed: creator moniker {moniker!r} is not namespaced; "
            f"skipping. Use a '<module>:<purpose>' moniker (e.g., 'zoid6:casino') "
            f"or pre-create the member manually via 'con member add'.",
            level="warning",
        )
        return None
    if moniker_exists(args, moniker):
        return moniker
    try:
        created = register_module_member(args, moniker)
        if not created:
            io.echo(
                f"channel auto-seed: failed to create daemon member {moniker!r}; "
                f"skipping channel seed. Check DB permissions.",
                level="warning",
            )
            return None
        return created
    except Exception:
        io.echo_traceback(
            f"channel auto-seed: register_module_member({moniker!r}) raised:"
        )
        return None


def _auto_seed_channels(args: Any, channel_cfg: Dict[str, Any]) -> None:
    """Idempotently seed channels declared in ``channel_cfg.auto_seed``.

    For each entry:

    1. Validate ``createdby`` is namespaced (warn-and-skip otherwise).
    2. Ensure the daemon member exists (auto-create via the bypass path).
    3. Call ``ChannelService.create_channel`` and treat "already exists"
       as success.

    Failures are logged at warning level and skipped. This function
    never raises; auto-seed is best-effort and must not prevent the
    daemon from starting.
    """
    seeds = channel_cfg.get("auto_seed", [])
    if not seeds:
        return

    service = ChannelService(args)
    for entry in seeds:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("name") or "").strip()
        if not name:
            continue
        creator = (entry.get("createdby") or "").strip()
        if not creator:
            io.echo(
                f"channel auto-seed: entry {entry!r} missing createdby; skipping",
                level="warning",
            )
            continue
        ready = _ensure_daemon_member(args, creator)
        if ready is None:
            continue
        result = service.create_channel(
            name=name,
            createdby=ready,
            description=entry.get("description"),
            announce_only=bool(entry.get("announce_only", False)),
            announcers=list(entry.get("announcers", []) or []),
        )
        if not result.get("success") and result.get("message") != "Channel already exists":
            io.echo(
                f"channel auto-seed: failed to seed {name!r}: "
                f"{result.get('message')!r}",
                level="warning",
            )


def _session_id_for(websocket: Any) -> int:
    """Return the stable session id for a websocket.

    Prefers ``_bbsengine6_session_id`` allocated by ``WebSocketServer``;
    falls back to ``id(websocket)`` for unit tests that pass mock
    websockets which don't allow attribute assignment.
    """
    return getattr(websocket, "_bbsengine6_session_id", id(websocket))


class BaseService:
    """Base class for message handlers."""

    def __init__(self, args: Any, session_manager: SessionManager):
        self.args = args
        self.sessions = session_manager

    async def handle_message(
        self, server: Any, websocket: Any, path: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class ChannelServiceHandler(BaseService):
    """Handle channel subscription messages."""

    def __init__(
        self, args: Any, session_manager: SessionManager, channel_state: ChannelState
    ):
        super().__init__(args, session_manager)
        self.channel_state = channel_state

    async def handle_message(
        self, server: Any, websocket: Any, path: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        msg_type = message.get("type")
        session_id = _session_id_for(websocket)

        if msg_type == "subscribe_channel":
            return await self._handle_subscribe(session_id, message)
        elif msg_type == "unsubscribe_channel":
            return await self._handle_unsubscribe(session_id, message)
        elif msg_type == "get_subscriptions":
            return await self._handle_get_subscriptions(session_id)

        return None

    async def _handle_subscribe(
        self, session_id: int, message: Dict[str, Any]
    ) -> Dict[str, Any]:
        moniker = self.sessions.get_moniker(session_id)
        if not moniker:
            return {"type": "error", "code": "not_authenticated"}

        channel = message.get("channel", "").strip()
        if not channel:
            return {
                "type": "error",
                "code": "invalid_request",
                "message": "channel required",
            }

        channel_subscribe(self.channel_state, session_id, channel)

        return {
            "type": "subscribed",
            "channel": channel,
            "message": f"Subscribed to {channel}",
        }

    async def _handle_unsubscribe(
        self, session_id: int, message: Dict[str, Any]
    ) -> Dict[str, Any]:
        moniker = self.sessions.get_moniker(session_id)
        if not moniker:
            return {"type": "error", "code": "not_authenticated"}

        channel = message.get("channel", "").strip()
        if not channel:
            return {
                "type": "error",
                "code": "invalid_request",
                "message": "channel required",
            }

        channel_unsubscribe(self.channel_state, session_id, channel)

        return {
            "type": "unsubscribed",
            "channel": channel,
            "message": f"Unsubscribed from {channel}",
        }

    async def _handle_get_subscriptions(self, session_id: int) -> Dict[str, Any]:
        moniker = self.sessions.get_moniker(session_id)
        if not moniker:
            return {"type": "error", "code": "not_authenticated"}

        channels = channel_get_session_channels(self.channel_state, session_id)

        return {
            "type": "subscriptions",
            "channels": list(channels),
        }


class MessageRouter:
    """Main message handler for channel WebSocket services.

    Reads an optional ``config`` kwarg to discover the channel section.
    Both flat (bed.json ``"channel": {...}``) and nested (zoid6.json
    ``"services": {"channel": {...}}``) shapes are accepted; see
    :func:`_resolve_channel_config`.

    When ``channel_cfg.auto_seed`` is populated, the seed step runs once
    at register time. Namespaced daemon members (e.g. ``zoid6:casino``)
    are auto-created via :func:`bbsengine6.member.lib.register_module_member`
    so operators don't need to bootstrap them by hand.
    """

    def __init__(
        self,
        args: Any,
        channel_state: Optional[ChannelState] = None,
        server: Any = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.args = args
        self.sessions = SessionManager()
        # Accept a shared state from the caller (typically BED) so that
        # server.publish(...) and ChannelServiceHandler see the same
        # subscriptions. Falls back to a private state for callers that
        # don't share (legacy behavior, but in that case publishes
        # through server.publish will not reach these subscribers).
        self.channel_state = (
            channel_state if channel_state is not None else ChannelState()
        )
        self.server = server
        self.channel_cfg = _resolve_channel_config(config)
        self.channel_service = ChannelServiceHandler(
            args, self.sessions, self.channel_state
        )

    def register_all(self, server: Any) -> None:
        """Register all services with the WebSocketServer.

        Honors ``channel_cfg.enabled`` (default True). When False, the
        router is a no-op so callers can disable channel services via
        config without touching code.
        """
        if not self.channel_cfg.get("enabled", True):
            return
        server.register_service(
            self.channel_service,
            [
                "subscribe_channel",
                "unsubscribe_channel",
                "get_subscriptions",
            ],
        )
        # Allow the server to call back on disconnect for cleanup.
        if self.server is None:
            self.server = server
        server.register_router(self)
        # Best-effort auto-seed; never raises.
        _auto_seed_channels(self.args, self.channel_cfg)

    def unregister_session(self, session_id: int) -> None:
        """Clean up session on disconnect.

        Unsubscribes from all channels and removes the session record
        so the connection no longer holds any pub/sub state.
        """
        channel_unsubscribe_all(self.channel_state, session_id)
        self.sessions.unregister_session(session_id)
