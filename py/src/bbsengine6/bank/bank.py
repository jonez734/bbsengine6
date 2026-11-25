import logging
from typing import Any, Dict, List

from ..util import logentry
from .account import Account
from .transaction import Transaction
from .transfer import Transfer


#: Balance a new member's bank account starts with (bed.json: bank.starting_balance).
DEFAULT_STARTING_BALANCE = 100

_CONFIG: dict = {"starting_balance": DEFAULT_STARTING_BALANCE}


def configure(*, starting_balance: int = DEFAULT_STARTING_BALANCE) -> None:
    """Set the bank policy. Called at startup from bed.json (bank.starting_balance).

    Must be a non-negative integer. A bool is refused even though it is an int subclass.
    """
    if isinstance(starting_balance, bool) or not isinstance(starting_balance, int):
        raise ValueError("bank.starting_balance must be an integer")
    if starting_balance < 0:
        raise ValueError("bank.starting_balance must be >= 0")
    _CONFIG["starting_balance"] = starting_balance


def get_starting_balance() -> int:
    """The balance a new bank account starts with."""
    return _CONFIG["starting_balance"]


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

    def exchange(
        self,
        moniker: str,
        amount: int,
        *,
        to: str,
        ratio: tuple,
        token_moniker: str,
    ) -> Dict[str, Any]:
        """Convert ``amount`` between credits and tokens at ``ratio`` = (num, den) tokens per den credits, in one transaction.

        ``to="tokens"``: credits are debited from ``moniker``, tokens credited to ``token_moniker``.
        ``to="credits"``: tokens are debited from ``moniker``, credits credited to ``token_moniker``.

        ``amount`` must be a positive integer. The conversion must be a whole number; otherwise the call is refused with no
        change. Both account rows are locked ``FOR UPDATE`` in ascending id order, so two opposing exchanges cannot deadlock.
        Each side writes a transaction row (``exchange_out`` / ``exchange_in``).
        """
        from bbsengine6 import database

        if to not in ("tokens", "credits"):
            return {"success": False, "message": "to must be 'tokens' or 'credits'"}
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            return {"success": False, "message": "Amount must be a positive whole number"}
        num, den = ratio
        if not (isinstance(num, int) and isinstance(den, int) and num > 0 and den > 0):
            return {"success": False, "message": "ratio must be two positive whole numbers"}

        if to == "tokens":
            scaled, out_side, in_side = amount * num, moniker, token_moniker
        else:
            scaled, out_side, in_side = amount * den, moniker, token_moniker
        if scaled % (den if to == "tokens" else num):
            return {
                "success": False,
                "message": f"{amount} does not convert to a whole number at ratio {num}:{den}",
            }
        received = scaled // (den if to == "tokens" else num)

        def _work(conn: Any) -> Dict[str, Any]:
            with database.cursor(conn) as cur:
                cur.execute(
                    "INSERT INTO bank.__account (moniker, balance) VALUES (%s, 0), (%s, 0) "
                    "ON CONFLICT (moniker) DO NOTHING",
                    (out_side, in_side),
                )
                # Lock both rows in ascending id order so opposing exchanges cannot deadlock.
                cur.execute(
                    "SELECT id, moniker, balance FROM bank.__account "
                    "WHERE moniker IN (%s, %s) ORDER BY id FOR UPDATE",
                    (out_side, in_side),
                )
                rows = {r["moniker"]: r for r in cur.fetchall()}
                if out_side not in rows or in_side not in rows:
                    raise RuntimeError("exchange account missing after upsert")
                out_row, in_row = rows[out_side], rows[in_side]
                if out_row["balance"] < amount:
                    return {"success": False, "message": "Insufficient funds"}

                cur.execute(
                    "UPDATE bank.__account SET balance = balance - %s WHERE id = %s RETURNING balance",
                    (amount, out_row["id"]),
                )
                out_new = int(cur.fetchone()["balance"])
                cur.execute(
                    "UPDATE bank.__account SET balance = balance + %s WHERE id = %s RETURNING balance",
                    (received, in_row["id"]),
                )
                in_new = int(cur.fetchone()["balance"])
                cur.execute(
                    """INSERT INTO bank.__transaction
                       (accountid, amount, transactiontype, description, membermoniker)
                       VALUES (%s, %s, 'exchange_out', %s, %s), (%s, %s, 'exchange_in', %s, %s)""",
                    (
                        out_row["id"], amount, f"exchange to {to}", moniker,
                        in_row["id"], received, f"exchange from {moniker}", moniker,
                    ),
                )
                return {"success": True, "out_new": out_new, "in_new": in_new}

        with database.connect(self.args) as conn:
            outcome = _work(conn)
        if not outcome.get("success"):
            return outcome

        result: Dict[str, Any] = {
            "success": True,
            "message": f"Exchanged {amount} {'credits' if to == 'tokens' else 'tokens'} for {received} "
                       f"{'tokens' if to == 'tokens' else 'credits'}",
            "new_balance": outcome["out_new"],
        }
        result["tokens" if to == "tokens" else "credits"] = received
        return result

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
