# bbsengine6/bank.py
# Generic bank/accounting module

from typing import Any, Dict, List, Optional

from bbsengine6 import database


class Account:
    """Bank account for a member."""
    
    def __init__(self, args: Any):
        self.args = args
    
    def get_or_create(self, moniker: str, initial_balance: int = 0) -> Dict[str, Any]:
        """Get existing account or create new one."""
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute("SELECT * FROM bank.__account WHERE moniker = %s", (moniker,))
                row = cur.fetchone()
                if row:
                    return self._row_to_dict(row)
                
                cur.execute(
                    """INSERT INTO bank.__account (moniker, balance) VALUES (%s, %s)
                       RETURNING *""",
                    (moniker, initial_balance)
                )
                row = cur.fetchone()
                return self._row_to_dict(row)
    
    def get(self, moniker: str) -> Optional[Dict[str, Any]]:
        """Get account by moniker."""
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute("SELECT * FROM bank.__account WHERE moniker = %s", (moniker,))
                row = cur.fetchone()
                if row:
                    return self._row_to_dict(row)
                return None
    
    def get_by_id(self, account_id: int) -> Optional[Dict[str, Any]]:
        """Get account by ID."""
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute("SELECT * FROM bank.__account WHERE id = %s", (account_id,))
                row = cur.fetchone()
                if row:
                    return self._row_to_dict(row)
                return None
    
    def get_balance(self, moniker: str) -> int:
        """Get current balance for an account."""
        account = self.get(moniker)
        return int(account["balance"]) if account else 0
    
    def update_balance(self, moniker: str, new_balance: int) -> bool:
        """Update account balance."""
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    "UPDATE bank.__account SET balance = %s WHERE moniker = %s",
                    (new_balance, moniker)
                )
                return cur.rowcount > 0
    
    def update_settings(self, moniker: str, **settings) -> Optional[Dict[str, Any]]:
        """Update account settings (minbalance, maxtransfer, attrs)."""
        allowed = {"minbalance", "maxtransfer", "attrs"}
        updates = {k: v for k, v in settings.items() if k in allowed}
        
        if not updates:
            return self.get(moniker)
        
        set_clauses = []
        values = []
        for k, v in updates.items():
            set_clauses.append(f"{k} = %s")
            values.append(v)
        
        values.append(moniker)
        
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                sql = f"UPDATE bank.__account SET {', '.join(set_clauses)} WHERE moniker = %s RETURNING *"
                cur.execute(sql, values)
                row = cur.fetchone()
                if row:
                    return self._row_to_dict(row)
                return None
    
    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "moniker": row["moniker"],
            "balance": int(row["balance"]) if row["balance"] else 0,
            "minbalance": int(row["minbalance"]) if row["minbalance"] else 0,
            "maxtransfer": int(row["maxtransfer"]) if row["maxtransfer"] else 1000,
            "attrs": row["attrs"] or {},
            "created": row["created"],
        }


class Transaction:
    """Account transaction ledger."""
    
    def __init__(self, args: Any):
        self.args = args
    
    def add(
        self,
        account_moniker: str,
        amount: int,
        transaction_type: str,
        description: str = "",
        related_moniker: str = "",
        member_moniker: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Add a transaction record."""
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    "SELECT id FROM bank.__account WHERE moniker = %s",
                    (account_moniker,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                account_id = row["id"]
                
                cur.execute(
                    """INSERT INTO bank.__transaction
                       (accountid, amount, transactiontype, description, relatedmoniker, membermoniker)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       RETURNING *""",
                    (account_id, amount, transaction_type, description, related_moniker, member_moniker)
                )
                row = cur.fetchone()
                return self._row_to_dict(row)
    
    def get_history(self, moniker: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history for an account."""
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    """SELECT t.* FROM bank.__transaction t
                       JOIN bank.__account a ON a.id = t.accountid
                       WHERE a.moniker = %s
                       ORDER BY t.dateposted DESC
                       LIMIT %s""",
                    (moniker, limit)
                )
                return [self._row_to_dict(row) for row in cur]
    
    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "accountid": row["accountid"],
            "amount": int(row["amount"]),
            "transactiontype": row["transactiontype"],
            "description": row["description"],
            "relatedmoniker": row["relatedmoniker"],
            "membermoniker": row["membermoniker"],
            "dateposted": row["dateposted"],
        }


class Transfer:
    """Pending transfers between accounts."""
    
    def __init__(self, args: Any):
        self.args = args
    
    def create(
        self,
        from_moniker: str,
        to_moniker: str,
        amount: int,
        requested_by: str,
    ) -> Dict[str, Any]:
        """Create a pending transfer request."""
        if from_moniker == to_moniker:
            return {"success": False, "message": "Cannot transfer to same account"}
        
        if amount <= 0:
            return {"success": False, "message": "Amount must be positive"}
        
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute("SELECT id, balance, maxtransfer FROM bank.__account WHERE moniker = %s", (from_moniker,))
                from_row = cur.fetchone()
                if not from_row:
                    return {"success": False, "message": "Source account not found"}
                
                if from_row["balance"] < amount:
                    return {"success": False, "message": f"Insufficient funds. Balance: {from_row['balance']}"}
                
                if amount > from_row["maxtransfer"]:
                    return {"success": False, "message": f"Amount exceeds max transfer limit: {from_row['maxtransfer']}"}
                
                cur.execute("SELECT id FROM bank.__account WHERE moniker = %s", (to_moniker,))
                to_row = cur.fetchone()
                if not to_row:
                    return {"success": False, "message": "Destination account not found"}
                
                cur.execute(
                    """INSERT INTO bank.__transfer (fromaccountid, toaccountid, amount, requestedby, status)
                       VALUES (%s, %s, %s, %s, 'pending')
                       RETURNING id""",
                    (from_row["id"], to_row["id"], amount, requested_by)
                )
                row = cur.fetchone()
                
                return {
                    "success": True,
                    "message": f"Transfer request created. ID: {row['id']}",
                    "transfer_id": row["id"],
                }
    
    def approve(self, transfer_id: int, responded_by: str) -> Dict[str, Any]:
        """Approve a pending transfer."""
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    """SELECT t.*, a1.moniker as from_moniker, a1.balance as from_balance, a2.moniker as to_moniker, a2.balance as to_balance
                       FROM bank.__transfer t
                       JOIN bank.__account a1 ON a1.id = t.fromaccountid
                       JOIN bank.__account a2 ON a2.id = t.toaccountid
                       WHERE t.id = %s AND t.status = 'pending'""",
                    (transfer_id,)
                )
                row = cur.fetchone()
                if not row:
                    return {"success": False, "message": "Transfer not found or already processed"}
                
                from_balance = int(row["from_balance"])
                to_balance = int(row["to_balance"])
                amount = int(row["amount"])
                
                if from_balance < amount:
                    cur.execute(
                        "UPDATE bank.__transfer SET status = 'rejected', respondedby = %s, respondedat = now() WHERE id = %s",
                        (responded_by, transfer_id)
                    )
                    return {"success": False, "message": "Insufficient funds"}
                
                new_from_balance = from_balance - amount
                new_to_balance = to_balance + amount
                
                cur.execute("UPDATE bank.__account SET balance = %s WHERE id = %s", (new_from_balance, row["fromaccountid"]))
                cur.execute("UPDATE bank.__account SET balance = %s WHERE id = %s", (new_to_balance, row["toaccountid"]))
                
                cur.execute(
                    """INSERT INTO bank.__transaction (accountid, amount, transactiontype, description, relatedmoniker, membermoniker)
                       VALUES (%s, %s, 'debit', 'Transfer out', %s, %s)""",
                    (row["fromaccountid"], amount, row["to_moniker"], responded_by)
                )
                cur.execute(
                    """INSERT INTO bank.__transaction (accountid, amount, transactiontype, description, relatedmoniker, membermoniker)
                       VALUES (%s, %s, 'credit', 'Transfer in', %s, %s)""",
                    (row["toaccountid"], amount, row["from_moniker"], responded_by)
                )
                
                cur.execute(
                    "UPDATE bank.__transfer SET status = 'approved', respondedby = %s, respondedat = now() WHERE id = %s",
                    (responded_by, transfer_id)
                )
                
                return {
                    "success": True,
                    "message": f"Transfer of {amount} approved",
                    "from_balance": new_from_balance,
                    "to_balance": new_to_balance,
                }
    
    def reject(self, transfer_id: int, responded_by: str) -> Dict[str, Any]:
        """Reject a pending transfer."""
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    "SELECT * FROM bank.__transfer WHERE id = %s AND status = 'pending'",
                    (transfer_id,)
                )
                row = cur.fetchone()
                if not row:
                    return {"success": False, "message": "Transfer not found or already processed"}
                
                cur.execute(
                    "UPDATE bank.__transfer SET status = 'rejected', respondedby = %s, respondedat = now() WHERE id = %s",
                    (responded_by, transfer_id)
                )
                
                return {"success": True, "message": f"Transfer {transfer_id} rejected"}
    
    def get_pending(self, moniker: str = "", is_sysop: bool = False) -> List[Dict[str, Any]]:
        """Get pending transfers."""
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                if is_sysop:
                    cur.execute(
                        """SELECT t.*, a1.moniker as from_moniker, a2.moniker as to_moniker
                           FROM bank.__transfer t
                           JOIN bank.__account a1 ON a1.id = t.fromaccountid
                           JOIN bank.__account a2 ON a2.id = t.toaccountid
                           WHERE t.status = 'pending'
                           ORDER BY t.requestedat DESC"""
                    )
                elif moniker:
                    cur.execute(
                        """SELECT t.*, a1.moniker as from_moniker, a2.moniker as to_moniker
                           FROM bank.__transfer t
                           JOIN bank.__account a1 ON a1.id = t.fromaccountid
                           JOIN bank.__account a2 ON a2.id = t.toaccountid
                           WHERE (a1.moniker = %s OR a2.moniker = %s) AND t.status = 'pending'
                           ORDER BY t.requestedat DESC""",
                        (moniker, moniker)
                    )
                else:
                    return []
                
                return [self._row_to_dict(row) for row in cur]
    
    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "fromaccountid": row["fromaccountid"],
            "toaccountid": row["toaccountid"],
            "from_moniker": row.get("from_moniker", ""),
            "to_moniker": row.get("to_moniker", ""),
            "amount": int(row["amount"]),
            "status": row["status"],
            "requestedby": row["requestedby"],
            "requestedat": row["requestedat"],
            "respondedby": row["respondedby"],
            "respondedat": row["respondedat"],
        }


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
        if amount <= 0:
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
        if amount <= 0:
            return {"success": False, "message": "Amount must be positive"}
        
        account = self.account.get(moniker)
        if not account:
            return {"success": False, "message": "Account not found"}
        
        if account["balance"] < amount:
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
        return self.transfer_obj.create(from_moniker, to_moniker, amount, requested_by)
    
    def approve_transfer(self, transfer_id: int, responded_by: str) -> Dict[str, Any]:
        """Approve a transfer."""
        return self.transfer_obj.approve(transfer_id, responded_by)
    
    def reject_transfer(self, transfer_id: int, responded_by: str) -> Dict[str, Any]:
        """Reject a transfer."""
        return self.transfer_obj.reject(transfer_id, responded_by)
    
    def get_history(self, moniker: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history."""
        return self.transaction.get_history(moniker, limit)
    
    def get_pending_transfers(self, moniker: str = "", is_sysop: bool = False) -> List[Dict[str, Any]]:
        """Get pending transfers."""
        return self.transfer_obj.get_pending(moniker, is_sysop)
