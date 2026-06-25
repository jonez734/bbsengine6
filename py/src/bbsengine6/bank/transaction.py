from typing import Any, Dict, List, Optional

from bbsengine6 import database


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
