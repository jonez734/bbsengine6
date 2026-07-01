# bbsengine6/services/invite.py
# InviteService - service wrapper for the generic invite code DAL.
#
# Phase 4 of the bbsengine6 modular architecture. This service exposes
# the engine.__invite DAL to WebSocket routers via a thin wrapper that
# returns the standard {success, message, ...} envelope used elsewhere
# in bbsengine6.services.
#
# WebSocket message types are exposed as class constants so routers can
# reference them by symbol rather than hardcoded strings.

from __future__ import annotations

from argparse import Namespace
from typing import Any, Dict, List, Optional

from bbsengine6 import invite as invite_dal


class InviteService:
    """Service wrapper for the generic invite code system.

    Methods are thin wrappers over the bbsengine6.invite DAL. They return
    the standard {success, message, ...} envelope on write operations
    and pass through on read operations.
    """

    # WebSocket message-type constants.
    MESSAGE_INVITE_CREATE = "invite_create"
    MESSAGE_INVITE_LIST = "invite_list"
    MESSAGE_INVITE_REVOKE = "invite_revoke"
    MESSAGE_INVITE_VALIDATE = "invite_validate"
    MESSAGE_INVITE_USE = "invite_use"

    def __init__(self, args: Namespace):
        self.args = args

    def create_invite(
        self,
        module: str,
        resourceid: str,
        createdbymoniker: str,
        dateexpires: Optional[Any] = None,
        code: Optional[str] = None,
        casinotablemoniker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new invite. See ``bbsengine6.invite.create_invite``."""
        return invite_dal.create_invite(
            self.args,
            module=module,
            resourceid=resourceid,
            createdbymoniker=createdbymoniker,
            dateexpires=dateexpires,
            code=code,
            casinotablemoniker=casinotablemoniker,
        )

    def list_invites(
        self,
        module: str,
        resourceid: str,
        include_revoked: bool = False,
        include_used: bool = False,
    ) -> Dict[str, Any]:
        """List active invites for a resource.

        Returns:
            Dict with success status and the list of invites.
        """
        invites = invite_dal.get_invites(
            self.args,
            module=module,
            resourceid=resourceid,
            include_revoked=include_revoked,
            include_used=include_used,
        )
        return {
            "success": True,
            "message": "OK",
            "invites": invites,
            "count": len(invites),
        }

    def validate_invite(
        self,
        module: str,
        resourceid: str,
        code: str,
    ) -> Dict[str, Any]:
        """Check whether a code is currently valid for a resource.

        Returns:
            Dict with success status and the invite record (or
            ``invite: None`` if invalid).
        """
        invite = invite_dal.validate_invite(
            self.args, module=module, resourceid=resourceid, code=code
        )
        if invite is None:
            return {
                "success": False,
                "message": "Invite is invalid, expired, used, or revoked",
                "invite": None,
            }
        return {
            "success": True,
            "message": "Invite is valid",
            "invite": invite,
        }

    def use_invite(
        self,
        invite_id: int,
        usedbymoniker: str,
    ) -> Dict[str, Any]:
        """Mark an invite as used by ``usedbymoniker``.

        Returns:
            Dict with success status.
        """
        ok = invite_dal.mark_used(
            self.args,
            invite_id=invite_id,
            usedbymoniker=usedbymoniker,
        )
        if not ok:
            return {
                "success": False,
                "message": "Invite is already used, revoked, or does not exist",
            }
        return {"success": True, "message": "Invite marked used"}

    def revoke_invite(self, invite_id: int) -> Dict[str, Any]:
        """Revoke an invite (soft delete via timestamp).

        Returns:
            Dict with success status.
        """
        ok = invite_dal.revoke_invite(self.args, invite_id=invite_id)
        if not ok:
            return {
                "success": False,
                "message": "Invite is already revoked, used, or does not exist",
            }
        return {"success": True, "message": "Invite revoked"}
