# bbsengine6 robustness and transactional hardening (2026-07-06)

## Status: COMPLETE (both passes)

This TODO consolidates two review passes on the bbsengine6 codebase
performed 2026-07-06. It supersedes
`TODO_2026-07-06_startup_backend_hardening.md` and
`TODO_2026-07-06_console_transactional_hardening.md`.

- **Pass 1** — startup/backend: authorization (Q1) and SAVEPOINT-based
  transaction safety (Q3). **COMPLETE.**
- **Pass 2** — console + bank + module: review of `bbsengine6/console/`
  for robustness and completeness, with the rule that no DB writes
  happen until the user confirms. **COMPLETE.**

---

## Pass 1 — startup/backend hardening

### 1. Authorization (Q1)

- [x] Add `bbsengine6.backend.lib.issysop(args, **kwargs) -> bool`
      that returns True if `current_user` is a member of the `sysop`
      role, OR is `rolsuper` (bootstrap fallback).
- [x] Add `bbsengine6.backend.lib._sanitize_sp(name, prefix="")` helper
      for savepoint name generation.
- [x] Replace `return True` in `access()` of 14 modules with
      `return lib.issysop(args, **kwargs)`.
- [x] Keep `return True` (no auth gate) in `checkcreatedb`,
      `checkdatabase`, `checkextensions` (stage 0 pre-sysop).
- [x] Mark `bbsengine6.backend.checknotify` deprecated via
      `DeprecationWarning` + `DEPRECATED:` docstring line.
- [x] Add deprecation note to `backend.lib.checknotify` shim.

### 2. SAVEPOINT-based transaction safety (Q3)

- [x] Add `rollback: bool = True` kwarg to `database.importsql`;
      honor it on the `psycopg.errors.Error` and outer `Exception`
      failure paths.
- [x] Wrap class/enum imports in `checkclasses` with SAVEPOINT per
      item; single `conn.commit()` at end on success.
- [x] Wrap class imports in `checknotifyd` with SAVEPOINT per item.
- [x] Wrap function imports in `checkfunctions` (both stages) with
      SAVEPOINT per item; use original (un-stripped) function name
      as savepoint source.
- [x] Wrap enum + class imports in `checknotify` with SAVEPOINT per
      item; disjoint namespaces via `enum_` / `class_` prefix.
- [x] Add defensive `conn.autocommit = False` at top of each
      savepoint-wrapped `_work()`.

### 3. Out of scope (intentionally, Pass 1)

- [x] `bbsengine6.startup.{stage_zero,stage_one,bank}.py` left as
      placeholders (per user direction; implementations live in
      `bbsengine6.backend.*`).
- [x] `bbsengine6.console.checknotify` left untouched at the time of
      Pass 1 (would surface the new `DeprecationWarning` from
      `backend.checknotify` via its re-export). **Removed in Pass 2**
      along with the other 11 `console/check*.py` shims.
- [x] `GRANT sysop TO <os_user>` NOT added to `checkroles` (per user
      direction; this is handled by `console`, not by startup).

### 4. Pass 1 operator-visible behavior changes

**Pre-change**
- Any module `access()` returned `True`; any caller (with valid
  signature per `module.check`) could run the module.
- A partial DDL import failure mid-class-list left the schema
  half-imported (the original review issue #3).

**Post-change**
- Modules refuse to run unless `current_user` is in `sysop` or is
  `rolsuper`. `console` is responsible for the `GRANT sysop`
  (per design decision). On a fresh install by a non-superuser OS
  user who has not yet been granted `sysop` by console, every
  `access()` returns `False` and `module.check()` prints
  "access check failed."
- A partial DDL import failure rolls back to the savepoint; on
  `failcount == 0` the entire loop commits atomically; on
  `failcount > 0` the whole transaction rolls back.
- `bbsengine6.backend.checknotify` emits a one-shot
  `DeprecationWarning` on first import.

### 5. Pass 1 files modified (16)

1. `bbsengine6/py/src/bbsengine6/database.py`
2. `bbsengine6/py/src/bbsengine6/backend/lib.py`
3. `bbsengine6/py/src/bbsengine6/startup/main.py`
4. `bbsengine6/py/src/bbsengine6/backend/stage_zero.py`
5. `bbsengine6/py/src/bbsengine6/backend/stage_one.py`
6. `bbsengine6/py/src/bbsengine6/backend/database.py`
7. `bbsengine6/py/src/bbsengine6/backend/bank.py`
8. `bbsengine6/py/src/bbsengine6/backend/checkengine.py`
9. `bbsengine6/py/src/bbsengine6/backend/checkroles.py`
10. `bbsengine6/py/src/bbsengine6/backend/checksuperuser.py`
11. `bbsengine6/py/src/bbsengine6/backend/checkwebserverrole.py`
12. `bbsengine6/py/src/bbsengine6/backend/checkfunctions.py`
13. `bbsengine6/py/src/bbsengine6/backend/checkclasses.py`
14. `bbsengine6/py/src/bbsengine6/backend/checkflag.py`
15. `bbsengine6/py/src/bbsengine6/backend/checknotify.py`
16. `bbsengine6/py/src/bbsengine6/backend/checknotifyd.py`

---

## Pass 2 — console + bank + module hardening

### Constraints (locked by user)

- No DB writes until the user confirms the add/edit.
- Loginid renames in `edit()` are refused with a clear error; future
  `ALTER ROLE ... RENAME TO` support tracked as a TODO.
- `bank.BankService.add_funds`/`remove_funds` must accept `conn=` so
  the funds grant shares the same transaction as the member insert.
- `__main__.py` should use `parse_args()` (not `parse_known_args()`)
  so flags can appear anywhere on the command line.
- `memberapproval.py` should use a single connection per call.

### A. Bank: transactional support

- [x] Add `conn: Any = None` to `bank.BankService.add_funds(...)` and
      `remove_funds(...)`. If `conn is not None`, run on the caller's
      connection; otherwise acquire a new one (existing behavior).

### B. `console/` deletions

- [x] Delete the 12 `console/check*.py` shims. Their routing is now
      done directly via `bbsengine6.backend.<subcommand>`.
- [x] Delete `console/alert.py` and `console/email.py`. Both are
      broken stubs that reference undefined names.

### C. `console/lib.py`

- [x] Remove `SQLDIR` (dead constant).
- [x] Remove `_discovered_modules_cache` and the dynamic discovery
      helpers; replace `build_subcommand_parser` with a fixed list of
      console subcommands: `createdatabase, member, memberapproval,
      session, showpgrole`.
- [x] Delete the top-level `checkroles`/`checkextensions`/etc. helpers
      in `console/lib.py` (lines 156-197). They duplicate
      `backend/lib.py` and have no callers.
- [x] Replace `handle_subcommand()` with a dispatcher that routes
      known backend subcommands (`checkclasses`, `checkcreatedb`,
      `checkdatabase`, `checkengine`, `checkextensions`, `checkflag`,
      `checkfunctions`, `checkloginid`, `checknotify`, `checknotifyd`,
      `checkroles`, `checksuperuser`, `checkwebserverrole`,
      `createdatabase`, `bank`) to `bbsengine6.backend.<subcommand>`
      and all other subcommands to `bbsengine6.console.<subcommand>`.
- [x] Consolidate `build_subcommand_parser` and `buildargs`: both
      call `database.buildargs(...)` and add `--require-registration`.

### D. `console/__init__.py`

- [x] Update `__all__` to `["member", "session", "showpgrole",
      "createdatabase", "memberapproval", "lib"]`.

### E. `console/main.py`

- [x] Remove `import psycopg` (line 1, dead).
- [x] Fix `args.database` -> `args.databasename` (line 53, was
      `AttributeError` on every menu render).
- [x] Pass `conn=conn` to `session.getcurrentsessionid` and
      `session.updatelastactivity` (lines 45-47).
- [x] Add `'A'` to the choice string in `io.inputchoice` (line 61).

### F. `console/__main__.py`

- [x] Switch to `parse_args()` (was `parse_known_args()`).
- [x] On dispatch failure, `sys.exit(1)`.
- [x] Guard the `finally` block against `io.terminal.height() is None`.
- [x] Set `prog="console"` (was `zoidoffice`) in
      `lib.build_subcommand_parser`.
- [x] Update docstring to use `console <subcommand>` (was
      `zoidoffice <subcommand>`).
- [x] Update `module.is_importable` docstring example from
      `zoidoffice.project` to `console.member`.

### G. `console/session.py`

- [x] Use `io.echo_traceback` in the `except` (line 82-83).
- [x] Remove the unused `pool` local.
- [x] Update the module docstring to drop the "manage" promise.

### H. `console/showpgrole.py`

- [x] Add a `sys.stdin.isatty()` guard around the welcome/osuser
      prompts so the module is safe in non-TTY contexts.

### I. `console/createdatabase.py`

- [x] Add a one-line module docstring so it shows up in
      `console --help`.

### J. `console/member.py`

- [x] Delete `showui()` (dead; duplicated inline in `help`).
- [x] Remove the unused `pool` local in `_edit()`.
- [x] Rename `help()` to `render_member()` to avoid shadowing the
      `help=` kwarg passed to `io.inputchoice` (line 250). Update
      call sites.
- [x] Update `editflags()` docstring: "Mutates `member['flags']` in
      memory; persistence is the caller's responsibility after user
      confirmation." Drop the "TODO" comment. No inline `setflag` call.
- [x] In `add()`: restructure so the `[Y/n] add member?` prompt
      happens *first* in the side-effect block. All DB writes
      (`libmember.insert`, `bank_service.add_funds`,
      `configurerole`, `pgrole.ensure_role_for_member`,
      `pgrole.sync_groups`) sit between the prompt and `conn.commit()`.
      Pass `conn=conn` to `bank_service.add_funds`.
- [x] In `add()`: check the return of `libmember.insert(...)` and
      abort (return False, no commit) on failure.
- [x] In `edit()`: capture `_baseline_flags`, `_baseline_loginid`,
      and `_baseline_email` after `libmember.build()` returns,
      *before* `_edit()` runs.
- [x] In `edit()`: restructure so the `[Y/n] save changes?` prompt
      happens *first* in the side-effect block.
- [x] In `edit()`: refuse loginid rename. If
      `m["loginid"] != _baseline_loginid`, log a clear error, return
      False. `# TODO: support rename via
      database.renamerole(args, old, new, conn=conn)`.
- [x] In `edit()`: wrap the side-effect block in `try/except`; on
      failure, `io.echo_traceback`, `conn.rollback()`, return False.
- [x] In `edit()`: if `m["email"] != _baseline_email`, call
      `libmember.setflag(args, "EMAILVERIFIED", False, moniker=...,
      conn=conn)` after `libmember.update(...)`.
- [x] In `main()`: add `elif ch == "A":` branch dispatching to
      `memberapproval`. Check the return of `showpgrole.main(...)`.
- [x] In `_edit()`: replace `alerts(args)` (referenced undefined
      `console/alert.py`) with a no-op comment.

### K. `console/memberapproval.py` — full single-conn rewrite

- [x] Open one outer `with database.connect(args, auto_commit=False)
      as conn:` block. No per-record inner `txn_conn` blocks.
- [x] Replace `cur.fetchmany()` (default arraysize 1) with
      `cur.fetchall()`.
- [x] Pass `conn=conn` to `member.getbymoniker`, `member.checkflag`,
      `member.setflag`, `member.update`, `pgrole.ensure_role_for_member`.
- [x] Symmetrize verified-yes and verified-no branches: both update
      `dateemailverified` and `emailverifiedbymoniker`.
- [x] For the approve branch, drop the full `member.update(m, ...)`
      call; use only `setflag` and targeted `database.update` on the
      audit columns to avoid the stale-dict overwrite.
- [x] Wrap each record's flow in `try/except`; rollback and return
      False on failure.
- [x] Add module-level docstrings to `init`/`buildargs`/`main`.

### L. `module.py` — restore `package=` kwarg

- [x] Restore `package: Optional[str] = None` to `load()`,
      `get()`, `check()`, and `run()`. The prior WIP pass had
      removed this plumbing, which broke cross-package dispatch
      like `module.run(args, "checkfunctions",
      package="bbsengine6.backend")`.
- [x] Restore the PEP 328 helpers `_absolute_package_from_relative()`
      and `_caller_package()`.
- [x] In `run()`, pop `package` from `**kwargs` before forwarding
      to inner callbacks so it never leaks into
      `init()`/`access()`/`buildargs()`/`main()`.

### M. `tests/test_console_checknotifyd.py`

- [x] `TestNotifydModuleFunctions.test_module_can_be_imported`:
      import from `bbsengine6.backend.checknotifyd` (the shim
      `bbsengine6.console.checknotifyd` was deleted in Pass 2).
- [x] `test_access_returns_true` renamed to
      `test_access_returns_false_without_conn` to match the new
      backend semantics (access() calls `lib.issysop()` which
      requires a conn/pool).

### N. Pass 2 files modified

- `bbsengine6/py/src/bbsengine6/bank/bank.py` (A)
- `bbsengine6/py/src/bbsengine6/console/__init__.py` (D)
- `bbsengine6/py/src/bbsengine6/console/__main__.py` (F)
- `bbsengine6/py/src/bbsengine6/console/createdatabase.py` (I)
- `bbsengine6/py/src/bbsengine6/console/lib.py` (C)
- `bbsengine6/py/src/bbsengine6/console/main.py` (E)
- `bbsengine6/py/src/bbsengine6/console/member.py` (J)
- `bbsengine6/py/src/bbsengine6/console/memberapproval.py` (K)
- `bbsengine6/py/src/bbsengine6/console/session.py` (G)
- `bbsengine6/py/src/bbsengine6/console/showpgrole.py` (H)
- `bbsengine6/py/src/bbsengine6/module.py` (L)
- `bbsengine6/py/tests/test_console_checknotifyd.py` (M)

### O. Pass 2 files deleted

- 12x `bbsengine6/py/src/bbsengine6/console/check*.py`
- `bbsengine6/py/src/bbsengine6/console/alert.py`
- `bbsengine6/py/src/bbsengine6/console/email.py`

---

## Combined verification

- [x] `python3 -m py_compile` on every modified file.
- [x] `python3 -c "import bbsengine6.console.member"` and
      `python3 -c "import bbsengine6.console.memberapproval"`.
- [x] `ruff check bbsengine6/console/ bbsengine6/bank/
      bbsengine6/module.py` — All checks passed.
- [x] Trace `add()`: no `libmember.insert`/`bank_service.add_funds`/
      `configurerole`/`pgrole.*` calls occur before the user
      confirmation prompt.
- [x] Trace `edit()`: same; loginid rename is refused.
- [x] `tests/test_module_package_kwarg.py` — 9/9 passed (proves
      `package=` plumbing works end-to-end).
- [x] `tests/test_console_checknotifyd.py` — 18/18 passed.
- [x] `tests/test_bank.py` — 25/25 passed (proves `conn=` is honored
      and the no-conn path is unchanged).
- [x] `tests/test_buildrec.py` + `tests/test_database_create.py`
      (minus one pre-existing failure unrelated to this work) — all
      passed.

### Pre-existing test failures (out of scope)

The following test failures exist on `main` independent of this work
and are caused by other WIP changes in the working tree (not in the
files modified here):

- `tests/test_bottombar.py::TestScreenShimRoutesThroughBottombar::test_screen_register_calls_bottombar`
  — `screen.py` had a pre-existing local modification that removed
  the bottombar shim delegation; the test was written for the
  shimmed version.
- `tests/test_database_create.py::TestCreate::test_no_options_omits_with_keyword`
  — pre-existing; the test expects a string that the current
  renderer does not produce.
- `tests/test_module_package_kwarg.py` and
  `tests/test_startup_zoid6_missing.py` — these were failing
  pre-merge because the WIP-mod `module.py` had dropped the
  `package=` kwarg; this TODO's Pass 2 L fixes them.
- `tests/test_folder_create.py` — pre-existing setup errors.
- `tests/test_notify_message_demo_*` — schema-availability
  failures (notify tables not bootstrapped in the test environment).
