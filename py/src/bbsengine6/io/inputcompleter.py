"""
bbsengine6.io.inputcompleter - readline-style completer for zoidoffice.

`customer.lib.inputcustomercode` (and other zoidoffice.input*code helpers)
expect ``io.inputcompleter(conn, args, table, column)`` to return an object
whose ``.completer(text, state)`` method is suitable for ``readline.set_completer``.

The completer reads distinct values from the named table/column on each
keystroke, optionally constrained by a LIKE prefix.
"""

from typing import Any, List, Optional


class InputCompleter(object):
    """Wrap a database connection with a readline-style completer.

    The ``.completer`` method has the signature readline expects:
    ``completer(text, state) -> str | None``.
    """

    def __init__(self, conn: Any, args: Any, table: str, column: str) -> None:
        self.conn = conn
        self.args = args
        self.table = table
        self.column = column
        self._matches: List[str] = []

    def _refresh(self, text: str) -> None:
        from . import database
        from psycopg import sql

        try:
            with database.cursor(self.conn) as cur:
                q = sql.SQL(
                    "select distinct {col} from {tbl} where {col} is not null "
                    "and {col} like %s order by {col}"
                ).format(
                    col=sql.Identifier(self.column),
                    tbl=sql.Identifier(self.table),
                )
                cur.execute(q, (text + "%",))
                rows = cur.fetchall()
        except Exception:
            self._matches = []
            return
        self._matches = [
            r[self.column] for r in rows if r[self.column].startswith(text)
        ]

    def completer(self, text: str, state: int) -> Optional[str]:
        """Return the ``state``-th match for ``text``, or None when exhausted."""
        if state == 0:
            self._refresh(text)
        if state < len(self._matches):
            return self._matches[state]
        return None


def inputcompleter(
    conn: Any, args: Any, table: str, column: str
) -> InputCompleter:
    """Return an ``InputCompleter`` for the given table/column."""
    return InputCompleter(conn, args, table, column)
