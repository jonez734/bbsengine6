from typing import Any, Dict, List

from bbsengine6 import database


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
