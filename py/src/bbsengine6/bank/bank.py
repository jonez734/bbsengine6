import logging
from typing import Any, Dict, List, Optional

from ..util import logentry
from .account import Account
from .transaction import Transaction
from .transfer import Transfer


class BankService:
    """Main bank service combining account, transaction, and transfer operations."""

    def __init__(self, args: Any):
        self.args = args
        self.account = Account(args)
        self.transaction = Transaction(args)
        self.transfer_obj = Transfer(args)

    def get_balance(self, moniker: str) -> int:
        """Get account balance."""
        return self.account.get_balance(moniker)

    def add_funds(
        self,
        moniker: str,
        amount: int,
        transaction_type: str = "credit",
        description: str = "",
        member_moniker: str = "",
    ) -> Dict[str, Any]:
        """Add funds to an account."""
        from bbsengine6 import database

        if amount <= 0:
            logentry(
                "amount must be positive",
                module="bank",
                action="add_funds_failed",
                moniker=moniker,
                amount=amount,
            )
            return {"success": False, "message": "Amount must be positive"}

        account = self.account.get_or_create(moniker)
        new_balance = account["balance"] + amount

        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    "UPDATE bank.__account SET balance = %s WHERE moniker = %s",
                    (new_balance, moniker)
                )

                cur.execute(
                    """INSERT INTO bank.__transaction
                       (accountid, amount, transactiontype, description, membermoniker)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (account["id"], amount, transaction_type, description, member_moniker)
                )

        logentry(
            description or f"credit {transaction_type}",
            module="bank",
            action="add_funds",
            moniker=moniker,
            amount=amount,
            newbalance=new_balance,
        )

        return {
            "success": True,
            "message": f"Added {amount} to {moniker}",
            "new_balance": new_balance,
        }

    def remove_funds(
        self,
        moniker: str,
        amount: int,
        transaction_type: str = "debit",
        description: str = "",
        member_moniker: str = "",
    ) -> Dict[str, Any]:
        """Remove funds from an account."""
        from bbsengine6 import database

        if amount <= 0:
            logentry(
                "amount must be positive",
                module="bank",
                action="remove_funds_failed",
                moniker=moniker,
                amount=amount,
            )
            return {"success": False, "message": "Amount must be positive"}

        account = self.account.get(moniker)
        if not account:
            logentry(
                "account not found",
                module="bank",
                action="remove_funds_failed",
                moniker=moniker,
                amount=amount,
            )
            return {"success": False, "message": "Account not found"}

        if account["balance"] < amount:
            logentry(
                "insufficient funds",
                module="bank",
                action="remove_funds_failed",
                moniker=moniker,
                amount=amount,
                balance=account["balance"],
            )
            return {"success": False, "message": f"Insufficient funds. Balance: {account['balance']}"}

        new_balance = account["balance"] - amount

        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    "UPDATE bank.__account SET balance = %s WHERE moniker = %s",
                    (new_balance, moniker)
                )

                cur.execute(
                    """INSERT INTO bank.__transaction
                       (accountid, amount, transactiontype, description, membermoniker)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (account["id"], amount, transaction_type, description, member_moniker)
                )

        logentry(
            description or f"debit {transaction_type}",
            module="bank",
            action="remove_funds",
            moniker=moniker,
            amount=amount,
            newbalance=new_balance,
        )

        return {
            "success": True,
            "message": f"Removed {amount} from {moniker}",
            "new_balance": new_balance,
        }

    def transfer(
        self,
        from_moniker: str,
        to_moniker: str,
        amount: int,
        requested_by: str,
    ) -> Dict[str, Any]:
        """Create a transfer request."""
        result = self.transfer_obj.create(from_moniker, to_moniker, amount, requested_by)

        if result.get("success"):
            logentry(
                f"requested by {requested_by}",
                module="bank",
                action="transfer_request",
                moniker=from_moniker,
                amount=amount,
                to=to_moniker,
                transferid=result.get("transfer_id"),
            )
        else:
            logentry(
                result.get("message", "transfer failed"),
                module="bank",
                action="transfer_failed",
                moniker=from_moniker,
                amount=amount,
                to=to_moniker,
                level=logging.WARNING,
            )

        return result

    def approve_transfer(self, transfer_id: int, responded_by: str) -> Dict[str, Any]:
        """Approve a transfer."""
        result = self.transfer_obj.approve(transfer_id, responded_by)

        if result.get("success"):
            logentry(
                "approved transfer",
                module="bank",
                action="transfer_approve",
                moniker=responded_by,
                transferid=transfer_id,
                amount=result.get("amount", 0),
                frombalance=result.get("from_balance"),
                tobalance=result.get("to_balance"),
            )
        else:
            logentry(
                result.get("message", "approval failed"),
                module="bank",
                action="transfer_approve_failed",
                moniker=responded_by,
                transferid=transfer_id,
                level=logging.WARNING,
            )

        return result

    def reject_transfer(self, transfer_id: int, responded_by: str) -> Dict[str, Any]:
        """Reject a transfer."""
        result = self.transfer_obj.reject(transfer_id, responded_by)

        if result.get("success"):
            logentry(
                "rejected transfer",
                module="bank",
                action="transfer_reject",
                moniker=responded_by,
                transferid=transfer_id,
            )
        else:
            logentry(
                result.get("message", "rejection failed"),
                module="bank",
                action="transfer_reject_failed",
                moniker=responded_by,
                transferid=transfer_id,
                level=logging.WARNING,
            )

        return result

    def get_history(self, moniker: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history."""
        return self.transaction.get_history(moniker, limit)

    def get_pending_transfers(self, moniker: str = "", is_sysop: bool = False) -> List[Dict[str, Any]]:
        """Get pending transfers."""
        return self.transfer_obj.get_pending(moniker, is_sysop)
