# member/api/handler.py
# Standalone WebSocket handler for member profile, tier, and referral services.

from typing import Any, Dict, Optional

from bbsengine6.services.member import MemberService


from bbsengine6.session import SessionManager


class BaseService:
    """Base class for message handlers."""

    def __init__(self, args: Any, session_manager: SessionManager):
        self.args = args
        self.sessions = session_manager

    async def handle_message(
        self, server: Any, websocket: Any, path: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class MemberServiceHandler(BaseService):
    """Handle member profile, tier, and referral messages."""

    def __init__(self, args: Any, session_manager: SessionManager):
        super().__init__(args, session_manager)
        self.member_service = MemberService(args)

    async def handle_message(
        self, server: Any, websocket: Any, path: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        msg_type = message.get("type")

        if msg_type == "member_profile":
            return await self._handle_profile(message)
        elif msg_type == "member_update":
            return await self._handle_update(message)
        elif msg_type == "member_tier":
            return await self._handle_tier(message)
        elif msg_type == "member_referral_code":
            return await self._handle_referral_code(message)
        elif msg_type == "member_referrals":
            return await self._handle_referrals(message)

        return None

    async def _handle_profile(self, message: Dict[str, Any]) -> Dict[str, Any]:
        moniker = message.get("moniker", "")
        if not moniker:
            return {"type": "error", "code": "invalid_request", "message": "Moniker required"}

        profile = self.member_service.get_profile(moniker)
        if profile:
            return {"type": "member_profile_result", "success": True, "profile": profile}
        return {"type": "member_profile_result", "success": False, "message": "Member not found"}

    async def _handle_update(self, message: Dict[str, Any]) -> Dict[str, Any]:
        moniker = message.get("moniker", "")
        attrs = message.get("attrs", {})

        if not moniker:
            return {"type": "error", "code": "invalid_request", "message": "Moniker required"}

        result = self.member_service.update_profile(moniker, attrs)
        return {"type": "member_update_result", **result}

    async def _handle_tier(self, message: Dict[str, Any]) -> Dict[str, Any]:
        action = message.get("action", "get")
        moniker = message.get("moniker", "")

        if action == "get":
            if not moniker:
                return {"type": "error", "code": "invalid_request", "message": "Moniker required"}
            tier = self.member_service.get_tier(moniker)
            return {"type": "member_tier_result", "success": True, "moniker": moniker, "tier": tier}
        elif action == "set":
            tier = message.get("tier", "")
            if not moniker or not tier:
                return {"type": "error", "code": "invalid_request", "message": "Moniker and tier required"}
            success = self.member_service.set_tier(moniker, tier)
            return {"type": "member_tier_result", "success": success, "moniker": moniker, "tier": tier if success else None}

        return {"type": "error", "code": "invalid_action", "message": "Invalid action"}

    async def _handle_referral_code(self, message: Dict[str, Any]) -> Dict[str, Any]:
        moniker = message.get("moniker", "")
        if not moniker:
            return {"type": "error", "code": "invalid_request", "message": "Moniker required"}

        refcode = self.member_service.get_referral_code(moniker)
        return {"type": "member_referral_code_result", "success": True, "moniker": moniker, "refcode": refcode}

    async def _handle_referrals(self, message: Dict[str, Any]) -> Dict[str, Any]:
        moniker = message.get("moniker", "")
        if not moniker:
            return {"type": "error", "code": "invalid_request", "message": "Moniker required"}

        referrals = self.member_service.get_referrals(moniker)
        return {"type": "member_referrals_result", "success": True, "moniker": moniker, "referrals": referrals}


class MessageRouter:
    """Main message handler for member WebSocket services."""

    def __init__(self, args: Any):
        self.args = args
        self.sessions = SessionManager()
        self.member_service = MemberServiceHandler(args, self.sessions)

    def register_all(self, server: Any) -> None:
        """Register all services with the WebSocketServer."""
        server.register_service(self.member_service, [
            "member_profile", "member_update", "member_tier",
            "member_referral_code", "member_referrals",
        ])

    def unregister_session(self, session_id: int) -> None:
        """Clean up session on disconnect."""
        self.sessions.unregister_session(session_id)
