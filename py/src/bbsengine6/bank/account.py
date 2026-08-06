from typing import Any, Dict, Optional

from bbsengine6 import database


class Account:
    """Bank account for a member."""

    def __init__(self, args: Any):
        self.args = args

    def get_or_create(self, moniker: str, initial_balance: int = 0) -> Dict[str, Any]:
        """Get existing account or create new one."""
        with database.connect(self.args) as conn, database.cursor(conn) as cur:
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
        with database.connect(self.args) as conn, database.cursor(conn) as cur:
            cur.execute("SELECT * FROM bank.__account WHERE moniker = %s", (moniker,))
            row = cur.fetchone()
            if row:
                return self._row_to_dict(row)
            return None

    def get_by_id(self, account_id: int) -> Optional[Dict[str, Any]]:
        """Get account by ID."""
        with database.connect(self.args) as conn, database.cursor(conn) as cur:
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
        with database.connect(self.args) as conn, database.cursor(conn) as cur:
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
