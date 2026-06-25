from typing import Any, Dict, Optional

from bbsengine6.bank import BankService
from bbsengine6 import database


class SessionManager:
    """Manages WebSocket sessions and authentication state."""

    def __init__(self):
        self._sessions: Dict[int, Dict[str, Any]] = {}

    def register_session(self, session_id: int, moniker: str, is_sysop: bool = False) -> None:
        self._sessions[session_id] = {
            "moniker": moniker,
            "is_sysop": is_sysop,
        }

    def unregister_session(self, session_id: int) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)

    def get_moniker(self, session_id: int) -> Optional[str]:
        session = self._sessions.get(session_id)
        return session.get("moniker") if session else None

    def get_is_sysop(self, session_id: int) -> bool:
        session = self._sessions.get(session_id)
        return session.get("is_sysop", False) if session else False


class BaseService:
    """Base class for message handlers."""

    def __init__(self, args: Any, session_manager: SessionManager):
        self.args = args
        self.sessions = session_manager

    async def handle_message(
        self, server: Any, websocket: Any, path: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class BankServiceHandler(BaseService):
    """Handle bank operations via WebSocket."""

    def __init__(self, args: Any, session_manager: SessionManager):
        super().__init__(args, session_manager)
        self.bank_service = BankService(args)

    async def handle_message(
        self, server: Any, websocket: Any, path: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        msg_type = message.get("type")

        if msg_type == "bank_balance":
            return await self._handle_balance(id(websocket), message)
        elif msg_type == "bank_add":
            return await self._handle_add(id(websocket), message)
        elif msg_type == "bank_remove":
            return await self._handle_remove(id(websocket), message)
        elif msg_type == "bank_transfer_request":
            return await self._handle_transfer_request(id(websocket), message)
        elif msg_type == "bank_transfer_approve":
            return await self._handle_transfer_approve(id(websocket), message)
        elif msg_type == "bank_transfer_reject":
            return await self._handle_transfer_reject(id(websocket), message)
        elif msg_type == "bank_pending":
            return await self._handle_pending(id(websocket), message)
        elif msg_type == "bank_history":
            return await self._handle_history(id(websocket), message)
        elif msg_type == "bank_list_all":
            return await self._handle_list_all(id(websocket), message)

        return None

    async def _handle_balance(self, session_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        moniker = message.get("moniker")
        if not moniker:
            return {"type": "error", "code": "invalid_request", "message": "moniker required"}

        balance = self.bank_service.get_balance(moniker)
        account = self.bank_service.account.get(moniker)

        return {
            "type": "bank_balance",
            "moniker": moniker,
            "balance": balance,
            "max_transfer": int(account["maxtransfer"]) if account else 1000,
        }

    async def _handle_add(self, session_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        moniker = message.get("moniker")
        if not moniker:
            return {"type": "error", "code": "invalid_request", "message": "moniker required"}

        amount = message.get("amount", 0)
        if amount <= 0:
            return {"type": "error", "code": "invalid_request", "message": "amount must be positive"}

        description = message.get("description", "credit")
        session = self.sessions.get_session(session_id)
        member_moniker = session.get("moniker") if session else ""

        result = self.bank_service.add_funds(
            moniker,
            amount,
            transaction_type="credit",
            description=description,
            member_moniker=member_moniker,
        )

        if result["success"]:
            return {
                "type": "bank_add",
                "moniker": moniker,
                "amount": amount,
                "new_balance": result.get("new_balance", 0),
            }
        return {"type": "error", "code": "operation_failed", "message": result.get("message", "Failed to add funds")}

    async def _handle_remove(self, session_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        moniker = message.get("moniker")
        if not moniker:
            return {"type": "error", "code": "invalid_request", "message": "moniker required"}

        amount = message.get("amount", 0)
        if amount <= 0:
            return {"type": "error", "code": "invalid_request", "message": "amount must be positive"}

        description = message.get("description", "debit")
        session = self.sessions.get_session(session_id)
        member_moniker = session.get("moniker") if session else ""

        result = self.bank_service.remove_funds(
            moniker,
            amount,
            transaction_type="debit",
            description=description,
            member_moniker=member_moniker,
        )

        if result["success"]:
            return {
                "type": "bank_remove",
                "moniker": moniker,
                "amount": amount,
                "new_balance": result.get("new_balance", 0),
            }
        return {"type": "error", "code": "operation_failed", "message": result.get("message", "Failed to remove funds")}

    async def _handle_transfer_request(self, session_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        from_moniker = message.get("from")
        to_moniker = message.get("to")
        amount = message.get("amount", 0)

        if not from_moniker or not to_moniker:
            return {"type": "error", "code": "invalid_request", "message": "from and to are required"}

        if amount <= 0:
            return {"type": "error", "code": "invalid_request", "message": "amount must be positive"}

        session = self.sessions.get_session(session_id)
        requested_by = session.get("moniker", "unknown") if session else "unknown"

        result = self.bank_service.transfer(from_moniker, to_moniker, amount, requested_by)

        if result.get("success"):
            return {
                "type": "bank_transfer_request",
                "transfer_id": result.get("transfer_id"),
                "message": result.get("message"),
            }
        return {"type": "error", "code": "operation_failed", "message": result.get("message", "Transfer failed")}

    async def _handle_transfer_approve(self, session_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        transfer_id = message.get("transfer_id")
        if not transfer_id:
            return {"type": "error", "code": "invalid_request", "message": "transfer_id required"}

        session = self.sessions.get_session(session_id)
        if not session:
            return {"type": "error", "code": "not_authenticated"}

        responded_by = session.get("moniker", "unknown")

        result = self.bank_service.approve_transfer(transfer_id, responded_by)

        if result.get("success"):
            return {
                "type": "bank_transfer_approve",
                "transfer_id": transfer_id,
                "from_balance": result.get("from_balance"),
                "to_balance": result.get("to_balance"),
            }
        return {"type": "error", "code": "operation_failed", "message": result.get("message", "Approval failed")}

    async def _handle_transfer_reject(self, session_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        transfer_id = message.get("transfer_id")
        if not transfer_id:
            return {"type": "error", "code": "invalid_request", "message": "transfer_id required"}

        session = self.sessions.get_session(session_id)
        if not session:
            return {"type": "error", "code": "not_authenticated"}

        responded_by = session.get("moniker", "unknown")

        result = self.bank_service.reject_transfer(transfer_id, responded_by)

        if result.get("success"):
            return {
                "type": "bank_transfer_reject",
                "transfer_id": transfer_id,
            }
        return {"type": "error", "code": "operation_failed", "message": result.get("message", "Rejection failed")}

    async def _handle_pending(self, session_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        session = self.sessions.get_session(session_id)
        if not session:
            return {"type": "error", "code": "not_authenticated"}

        moniker = session.get("moniker", "")
        is_sysop = session.get("is_sysop", False)

        pending = self.bank_service.get_pending_transfers(moniker, is_sysop)

        return {
            "type": "bank_pending",
            "transfers": pending,
        }

    async def _handle_history(self, session_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        moniker = message.get("moniker")
        if not moniker:
            return {"type": "error", "code": "invalid_request", "message": "moniker required"}

        limit = message.get("limit", 50)
        history = self.bank_service.get_history(moniker, limit)

        return {
            "type": "bank_history",
            "moniker": moniker,
            "transactions": history,
        }

    async def _handle_list_all(self, session_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        session = self.sessions.get_session(session_id)
        if not session or not session.get("is_sysop"):
            return {"type": "error", "code": "permission_denied", "message": "sysop only"}

        accounts = []
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute("SELECT * FROM bank.__account ORDER BY moniker")
                for row in cur:
                    accounts.append({
                        "id": row["id"],
                        "moniker": row["moniker"],
                        "balance": int(row["balance"]) if row["balance"] else 0,
                        "minbalance": int(row["minbalance"]) if row["minbalance"] else 0,
                        "maxtransfer": int(row["maxtransfer"]) if row["maxtransfer"] else 1000,
                    })

        return {
            "type": "bank_list_all",
            "accounts": accounts,
        }


class MessageRouter:
    """Main message handler for bank WebSocket services."""

    def __init__(self, args: Any):
        self.args = args
        self.sessions = SessionManager()
        self.bank_service = BankServiceHandler(args, self.sessions)

    def register_all(self, server: Any) -> None:
        """Register all services with the WebSocketServer."""
        server.register_service(self.bank_service, [
            "bank_balance", "bank_add", "bank_remove",
            "bank_transfer_request", "bank_transfer_approve", "bank_transfer_reject",
            "bank_pending", "bank_history", "bank_list_all"
        ])

    def unregister_session(self, session_id: int) -> None:
        """Clean up session on disconnect."""
        self.sessions.unregister_session(session_id)
