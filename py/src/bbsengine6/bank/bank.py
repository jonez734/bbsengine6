import logging
from typing import Any, Dict, List

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
        conn: Any = None,
    ) -> Dict[str, Any]:
        """Add funds to an account.

        Args:
            moniker: Account owner moniker.
            amount: Positive integer amount to credit.
            transaction_type: Transaction type label.
            description: Free-text description.
            member_moniker: Originating member moniker (audit trail).
            conn: Optional caller-supplied DB connection. If provided, the
                  caller owns the transaction; the function does not commit
                  or close it. If None, a new connection is acquired via
                  ``database.connect`` and committed on success.
        """
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

        def _work(conn: Any) -> int:
            with database.cursor(conn) as cur:
                # Ensure account exists; race-safe via ON CONFLICT DO NOTHING.
                cur.execute(
                    "INSERT INTO bank.__account (moniker, balance) VALUES (%s, 0) "
                    "ON CONFLICT (moniker) DO NOTHING",
                    (moniker,),
                )
                # Atomic credit (no read-then-write TOCTOU).
                cur.execute(
                    "UPDATE bank.__account SET balance = balance + %s "
                    "WHERE moniker = %s RETURNING balance",
                    (amount, moniker),
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("account vanished after upsert")
                new_balance = int(row["balance"])
                cur.execute(
                    "SELECT id FROM bank.__account WHERE moniker = %s",
                    (moniker,),
                )
                acc = cur.fetchone()
                cur.execute(
                    """INSERT INTO bank.__transaction
                       (accountid, amount, transactiontype, description, membermoniker)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (acc["id"], amount, transaction_type, description, member_moniker),
                )
                return new_balance

        if conn is not None:
            new_balance = _work(conn)
        else:
            with database.connect(self.args) as conn:
                new_balance = _work(conn)

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
        conn: Any = None,
    ) -> Dict[str, Any]:
        """Remove funds from an account.

        Args:
            moniker: Account owner moniker.
            amount: Positive integer amount to debit.
            transaction_type: Transaction type label.
            description: Free-text description.
            member_moniker: Originating member moniker (audit trail).
            conn: Optional caller-supplied DB connection. If provided, the
                  caller owns the transaction; the function does not commit
                  or close it. If None, a new connection is acquired via
                  ``database.connect`` and committed on success.
        """
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

        def _work(conn: Any) -> tuple[bool, int | None, str | None]:
            with database.cursor(conn) as cur:
                # Atomic debit guarded by sufficient balance.
                cur.execute(
                    "UPDATE bank.__account "
                    "SET balance = balance - %s "
                    "WHERE moniker = %s AND balance >= %s "
                    "RETURNING id, balance",
                    (amount, moniker, amount),
                )
                row = cur.fetchone()
                if row is None:
                    # Either no account, or balance < amount.
                    cur.execute(
                        "SELECT balance FROM bank.__account WHERE moniker = %s",
                        (moniker,),
                    )
                    acc = cur.fetchone()
                    if acc is None:
                        return (False, None, "Account not found")
                    return (False, int(acc["balance"]), "Insufficient funds")
                account_id = row["id"]
                new_balance = int(row["balance"])
                cur.execute(
                    """INSERT INTO bank.__transaction
                       (accountid, amount, transactiontype, description, membermoniker)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (account_id, amount, transaction_type, description, member_moniker),
                )
                return (True, new_balance, None)

        if conn is not None:
            ok, new_balance, msg = _work(conn)
        else:
            with database.connect(self.args) as conn:
                ok, new_balance, msg = _work(conn)

        if not ok:
            logentry(
                msg or "remove_funds failed",
                module="bank",
                action="remove_funds_failed",
                moniker=moniker,
                amount=amount,
                balance=new_balance,
            )
            if new_balance is None:
                return {"success": False, "message": msg}
            return {"success": False, "message": f"Insufficient funds. Balance: {new_balance}"}

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

    def list_all(self) -> List[Dict[str, Any]]:
        """List all accounts with balances."""
        from bbsengine6 import database

        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    "SELECT moniker, balance FROM bank.__account ORDER BY moniker"
                )
                return [{"moniker": row["moniker"], "balance": int(row["balance"])} for row in cur]
