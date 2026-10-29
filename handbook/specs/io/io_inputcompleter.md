# bbsengine6.io.inputcompleter Specification

## Overview

`inputcompleter.py` provides a readline-style completer backed by a database table.
It is for callers that set `readline.set_completer` and want completions taken from
distinct values in one table column.

It is a different class from `Completer` in `inputstring.py`. `inputstring()` takes a
`completer=` callable that receives the word under the cursor; `InputCompleter` is a
readline `completer(text, state)` method. Do not pass one where the other is expected.

## Dependencies

- `bbsengine6.database` (`bbsengine6/database.py`): `cursor(conn)` for the query
- `psycopg.sql`: builds the query with quoted identifiers

## Public API

```python
inputcompleter(conn, args, table: str, column: str) -> InputCompleter
```

Returns an `InputCompleter` for the given table and column. Equivalent to
`InputCompleter(conn, args, table, column)`.

```python
class InputCompleter:
    def __init__(self, conn, args, table: str, column: str) -> None: ...
    def completer(self, text: str, state: int) -> Optional[str]: ...
```

`completer` has the signature readline expects. It returns the `state`-th match for
`text`, or `None` when there are no more.

## Behaviour

- On `state == 0` the matches are read from the database and kept on the object.
  For later `state` values the kept list is used, so one completion request costs one
  query.
- The query selects `distinct` non-null values of `column` from `table` that begin
  with `text` (SQL `LIKE text%`), ordered by the column. Identifiers are quoted with
  `psycopg.sql.Identifier`, so `table` and `column` are not interpolated as text.
- Matches are filtered again in Python to those that start with `text`.
- The query runs inside a `try` block: a database error clears the match list and
  `completer` returns `None`, with no report to the caller. See Known defect below for
  an error that is raised before that block (the import error, now fixed).
- `args` is stored but not used by the completer.

**Correction to the module docstring:** it says the completer reads on each keystroke.
It reads once per completion request (on `state == 0`), as above.

## Fixed defect

`_refresh` used a relative import (`from . import database`), which resolved to
`bbsengine6.io.database`, a module that does not exist. Every completion raised
`ImportError` before the `try` block. It now imports `bbsengine6.database` by its
absolute name. `tests/test_inputcompleter.py` covers it and fails on the old code.

**Not yet fixed in the callers:** zoidoffice calls `io.inputcompleter` from
`invoice/invoiceflow.py` and `customer/lib.py`, which are a separate project and are
deferred to a later session. Nothing in bbsengine6 uses `inputcompleter` outside its
own export.

## Limits

- `table` and `column` come from the caller. They are quoted, but the caller should
  still pass only trusted names.
- Errors are swallowed, so a broken connection looks like "no matches".

## See also

- [`io_inputstring.md`](io_inputstring.md): the `completer=` callable used by `inputstring()`.
- [`index.md`](index.md): the io package index.
