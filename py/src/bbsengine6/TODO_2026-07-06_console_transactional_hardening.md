# bbsengine6 console/transactional hardening (2026-07-06)

## Status: PLANNED

This TODO captures the second review pass on the bbsengine6 codebase,
focused on `bbsengine6.console` and the surrounding transactional
boundaries. The first pass is tracked in
`TODO_2026-07-06_startup_backend_hardening.md` and is COMPLETE.

This second pass addresses the following classes of issues:

1. Console modules bypass the `backend/` subpackage or import `psycopg`
   directly.
2. Console member-add/member-edit flows can leave orphaned psql roles,
   leaked bank grants, and flag state out-of-sync with what the user
   confirmed.
3. Confirmation prompts run *after* side-effecting DB writes, so a
   "no" leaves partial state.
4. Console routes to subcommands via a hardcoded if-ladder that does
   not match the dynamic discovery.
5. Stub modules (`alert.py`, `email.py`) reference undefined names and
   are unrecoverable on import.
6. The 12 `console/check*.py` shims duplicate the routing the
   `backend.check*` modules can do natively.

## Constraints (locked by user)

- No DB writes until the user confirms the add/edit.
- Loginid renames in `edit()` are refused with a clear error; future
  `ALTER ROLE ... RENAME TO` support tracked as a TODO.
- `bank.BankService.add_funds`/`remove_funds` must accept `conn=` so
  the funds grant shares the same transaction as the member insert.
- `__main__.py` should use `parse_args()` (not `parse_known_args()`)
  so flags can appear anywhere on the command line.
- `memberapproval.py` should use a single connection per call.

## Implementation plan

### A. Bank: transactional support (prerequisite)

- [ ] Add `conn: Any = None` to `bank.BankService.add_funds(...)` and
      `remove_funds(...)`. If `conn is not None`, run on the caller's
      connection; otherwise acquire a new one (existing behavior).

### B. `console/` deletions

- [ ] Delete the 12 `console/check*.py` shims. Their routing is now
      done directly via `bbsengine6.backend.<subcommand>`.
- [ ] Delete `console/alert.py` and `console/email.py`. Both are
      broken stubs that reference undefined names.

### C. `console/lib.py`

- [ ] Remove `SQLDIR` (dead constant).
- [ ] Remove `_discovered_modules_cache` and the dynamic discovery
      helpers; replace `build_subcommand_parser` with a fixed list of
      console subcommands: `createdatabase, member, memberapproval,
      session, showpgrole`.
- [ ] Delete the top-level `checkroles`/`checkextensions`/etc. helpers
      in `console/lib.py` (lines 156-197). They duplicate
      `backend/lib.py` and have no callers.
- [ ] Replace `handle_subcommand()` with a dispatcher that routes
      known backend subcommands (`checkclasses`, `checkcreatedb`,
      `checkdatabase`, `checkengine`, `checkextensions`, `checkflag`,
      `checkfunctions`, `checkloginid`, `checknotify`, `checknotifyd`,
      `checkroles`, `checksuperuser`, `checkwebserverrole`,
      `createdatabase`, `bank`) to `bbsengine6.backend.<subcommand>`
      and all other subcommands to `bbsengine6.console.<subcommand>`.
- [ ] Consolidate `build_subcommand_parser` and `buildargs`: both
      call `database.buildargs(...)` and add `--require-registration`.

### D. `console/__init__.py`

- [ ] Update `__all__` to `["member", "session", "showpgrole",
      "createdatabase", "memberapproval", "lib"]`.

### E. `console/main.py`

- [ ] Remove `import psycopg` (line 1, dead).
- [ ] Fix `args.database` -> `args.databasename` (line 53, currently
      raises `AttributeError`).
- [ ] Pass `conn=conn` to `session.getcurrentsessionid` and
      `session.updatelastactivity` (lines 45-47).
- [ ] Add `'A'` to the choice string in `io.inputchoice` (line 61).

### F. `console/__main__.py`

- [ ] Switch to `parse_args()` (was `parse_known_args()`).
- [ ] On dispatch failure, `sys.exit(1)`.
- [ ] Guard the `finally` block against `io.terminal.height() is None`.

### G. `console/session.py`

- [ ] Use `io.echo_traceback` in the `except` (line 82-83).
- [ ] Remove the unused `pool` local.
- [ ] Update the module docstring to drop the "manage" promise.

### H. `console/showpgrole.py`

- [ ] Add a `sys.stdin.isatty()` guard around the welcome/osuser
      prompts so the module is safe in non-TTY contexts.

### I. `console/createdatabase.py`

- [ ] Add a one-line module docstring so it shows up in
      `zoidoffice --help`.

### J. `console/member.py` (largest change)

- [ ] Delete `showui()` (dead; duplicated inline in `help`).
- [ ] Remove the unused `pool` local in `_edit()`.
- [ ] Rename `help()` to `render_member()` to avoid shadowing the
      `help=` kwarg passed to `io.inputchoice` (line 250). Update
      call sites.
- [ ] Update `editflags()` docstring: "Mutates `member['flags']` in
      memory; persistence is the caller's responsibility after user
      confirmation." Drop the "TODO" comment. No inline `setflag` call.
- [ ] In `add()`: restructure so the `[Y/n] add member?` prompt
      happens *first* in the side-effect block. All DB writes
      (`libmember.insert`, `bank_service.add_funds`,
      `configurerole`, `pgrole.ensure_role_for_member`,
      `pgrole.sync_groups`) sit between the prompt and `conn.commit()`.
      Pass `conn=conn` to `bank_service.add_funds` (now supported
      per item A).
- [ ] In `add()`: check the return of `libmember.insert(...)` and
      abort (return False, no commit) on failure.
- [ ] In `edit()`: capture `_baseline_flags` and `_baseline_loginid`
      after `libmember.build()` returns, *before* `_edit()` runs.
- [ ] In `edit()`: restructure so the `[Y/n] save changes?` prompt
      happens *first* in the side-effect block.
- [ ] In `edit()`: refuse loginid rename. If
      `m["loginid"] != _baseline_loginid`, log a clear error, return
      False. Add `# TODO: support rename via
      database.renamerole(args, old, new, conn=conn)`.
- [ ] In `edit()`: wrap the side-effect block in `try/except`; on
      failure, `io.echo_traceback`, `conn.rollback()`, return False.
- [ ] In `edit()`: if `m["email"] != _baseline_email`, call
      `libmember.setflag(args, "EMAILVERIFIED", False, moniker=...,
      conn=conn)` after `libmember.update(...)`.
- [ ] In `main()`: add `elif ch == "A":` branch dispatching to
      `memberapproval`. Check the return of `showpgrole.main(...)`.

### K. `console/memberapproval.py` (full single-conn rewrite)

- [ ] Open one outer `with database.connect(args, auto_commit=False)
      as conn:` block. No per-record inner `txn_conn` blocks.
- [ ] Replace `cur.fetchmany()` (default arraysize 1) with
      `cur.fetchall()`.
- [ ] Pass `conn=conn` to `member.getbymoniker`, `member.checkflag`,
      `member.setflag`, `member.update`, `pgrole.ensure_role_for_member`.
- [ ] Symmetrize verified-yes and verified-no branches: both update
      `dateemailverified` and `emailverifiedbymoniker`.
- [ ] For the approve branch, drop the full `member.update(m, ...)`
      call; use only `setflag` and `setattrs` to avoid the
      stale-dict overwrite.
- [ ] Wrap each record's flow in `try/except`; rollback and return
      False on failure.
- [ ] Add module-level docstrings to `init`/`buildargs`/`main`.

## Verification

- [ ] `python3 -m py_compile` on every modified file.
- [ ] `python3 -c "import bbsengine6.console.member"` and
      `python3 -c "import bbsengine6.console.memberapproval"`.
- [ ] `ruff check bbsengine6/console/ bbsengine6/bank/`.
- [ ] Trace `add()`: no `libmember.insert`/`bank_service.add_funds`/
      `configurerole`/`pgrole.*` calls occur before the user
      confirmation prompt.
- [ ] Trace `edit()`: same; loginid rename is refused.

## Files modified

- `bbsengine6/py/src/bbsengine6/bank/bank.py` (A)
- `bbsengine6/py/src/bbsengine6/console/__init__.py` (D)
- `bbsengine6/py/src/bbsengine6/console/lib.py` (C)
- `bbsengine6/py/src/bbsengine6/console/main.py` (E)
- `bbsengine6/py/src/bbsengine6/console/__main__.py` (F)
- `bbsengine6/py/src/bbsengine6/console/session.py` (G)
- `bbsengine6/py/src/bbsengine6/console/showpgrole.py` (H)
- `bbsengine6/py/src/bbsengine6/console/createdatabase.py` (I)
- `bbsengine6/py/src/bbsengine6/console/member.py` (J)
- `bbsengine6/py/src/bbsengine6/console/memberapproval.py` (K)

## Files deleted

- 12x `bbsengine6/py/src/bbsengine6/console/check*.py`
- `bbsengine6/py/src/bbsengine6/console/alert.py`
- `bbsengine6/py/src/bbsengine6/console/email.py`
