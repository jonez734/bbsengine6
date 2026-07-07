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

---

## Pass 3 — follow-up: SQL function rename, schema adjustments, startup dispatch, and untracked topbar/alert feature (2026-07-06)

### Status: IN-FLIGHT (working-tree, not yet committed)

Pass 3 is the working-tree work that was on disk at the time the
Pass 1+Pass 2 TODO (`TODO_2026-07-06_review_and_hardening.md`) was
merged into the submodule. It is tracked here so that the next
reviewer can see what was on the working tree in addition to what
made it into `f3ee7fe`. The changes are **not yet committed**; the
intention is to keep them on the working tree until the next
reviewer (or a Pass 4 commit) decides how to land them.

The work falls into four loosely-related buckets. Some of the changes
contradict or regress work described in Pass 1 / Pass 2 / the
`TODO-BOTTOMBAR.md` design; those are called out explicitly.

### Bucket A — SQL function renames and grant-target substitutions

Renames the `checkmemberflag(...)` SQL function (used in
`backfill_pgrole.sql` and `createrol.sql`) to `checkflag(...)`.
The Python-side rename in `py/src/bbsengine6/member.py` and
`py/src/bbsengine6/blurb.py` matches. There is also a
`engine.member_flag` → `engine.flag` rename in
`py/src/bbsengine6/blurb.py`'s SQL string.

- [ ] `py/src/bbsengine6/sql/backfill_pgrole.sql` —
  `engine.checkmemberflag` → `engine.checkflag`.
- [ ] `py/src/bbsengine6/sql/createrol.sql` — same rename in
  three call sites.
- [ ] `py/src/bbsengine6/sql/bbsengine6.sql` — re-enables
  `\i alert.sql` (was commented out, with a note that the legacy
  alert schema was removed in favor of `memberview.sql`). This
  *contradicts* the untracked `py/src/bbsengine6/sql/alert.sql`
  in Bucket D below, which reintroduces the alert schema.
- [ ] `py/src/bbsengine6/sql/grants.sql` — `sysop` → `:sysop`
  (substitution variable).
- [ ] `py/src/bbsengine6/sql/member_flag.sql` — `sysop` → `:sysop`
  and `insert, delete, update` → `all`.
- [ ] `py/src/bbsengine6/sql/refcode.sql` — `sysop` → `:sysop`
  in two grant lines.
- [ ] `py/src/bbsengine6/sql/roles.sql` — comment-only
  `sysop` → `:sysop`.
- [ ] `py/src/bbsengine6/sql/session.sql` — `sysop` → `:sysop`
  in the grant line, and adds an `engine.session` view.
- [ ] `py/src/bbsengine6/sql/member.sql` —
  `create table if not exists` → `create table`. **Schema change:**
  a re-run on an existing database will now fail at the
  `engine.__member` create. Confirm whether the deployment path
  uses idempotent imports or drops first.
- [ ] `py/src/bbsengine6/sql/pgrole.sql` —
  `membermoniker citext` → `memberid bigint references
  engine.__member(id) on delete cascade`. **Schema change:**
  data type and primary key of `engine.pgrole` change. Existing
  data is incompatible. A backfill is required before this can
  be deployed.
- [ ] `py/src/bbsengine6/sql/memberview.sql` — adds four
  alert-count subqueries (`alertcount`, `sentalertcount`,
  `sentdeliveredcount`, `sentreadcount`). These reference
  `engine.alert` and `engine.alert.status`, which depends on
  the `alert.sql` reintroduction (Bucket D).

### Bucket B — `database.py` and `io/screen.py` hardening follow-ups

- [ ] `py/src/bbsengine6/database.py`:
  - `database.create()` narrows `except Exception` →
    `except psycopg.Error` so programming errors are no
    longer reported as "database create failed".
  - `database.get_role_privs()` normalizes return type to
    `dict | None` (was `dict | bool`), removing the
    `False`-on-failure ambiguity.
  - `database.importsql()` adds a `rollback: bool = True`
    kwarg and a `_ALLOWED_PACKAGES` allowlist for the
    `package=` argument. The allowlist prevents a caller
    from reading arbitrary `.sql` resources via
    `util.load_sql(..., package=...)`.

### Bucket C — startup dispatch rework

The `bbsengine6.startup.{stage_zero,stage_one,bank}.py` shims
that re-exported from `bbsengine6.backend.*` are emptied
(empty placeholder file with a comment). Routing now goes
through `startup.lib.runstage(...)` and a new
`BACKEND_STAGE_NAMES` / `BACKEND_STAGES` table that maps each
stage name to its `bbsengine6.backend` package anchor.

- [ ] `py/src/bbsengine6/startup/lib.py` — adds
  `BACKEND_STAGE_NAMES`, `BACKEND_STAGES`, and `runstage(...)`.
- [ ] `py/src/bbsengine6/startup/main.py` —
  - `access()` returns `lib.issysop(args, **kwargs)` (was
    `return True`).
  - `_runstage` uses `lib.runstage(...)` and treats only
    literal `True` as success (was `is not False`, which
    silently treated `None` as success).
  - Iterates `lib.BACKEND_STAGE_NAMES` (was a hard-coded
    tuple of three names).
  - On stage failure, logs the package anchor.
- [ ] `py/src/bbsengine6/startup/__main__.py`:
  - Help-flag detection replaces a fragile
    `in sys.argv` substring check with a proper
    element-by-element scan (`_argv_has_help_flag`).
  - `screen.init()` (was `screen.init(args)`).
  - `lib.runmodule(args, "main")` (no `argv=sys.argv[1:]`).
    The previous `argv=` forwarding caused `module.run` to
    re-parse argv with every submodule's `buildargs`, leaking
    the parent's flag surface into children.
- [ ] `py/src/bbsengine6/startup/bank.py`,
  `py/src/bbsengine6/startup/stage_one.py`,
  `py/src/bbsengine6/startup/stage_zero.py` — emptied
  (replaced by the `module.run(..., package=...)` route).
- [ ] `py/src/bbsengine6/startup/engine.py` — deleted from
  working tree. **Not in `git log`; this deletion is
  independent of any previous `bbsengine6` refactor.** Confirm
  that this is intentional and that no caller still imports
  it.

### Bucket D — untracked topbar / alert feature

Three new files, not yet tracked:

- [ ] `js/topbar-alert.js` (new) — IIFE-wrapped topbar
  component that polls `alert.list` / `alert.count`. Listed
  in `js/bbsengine6.js`'s `VALID_REQUESTS` regex.
- [ ] `py/src/bbsengine6/sql/alert.sql` (new) — reintroduces
  the `engine.__alert` table and presumably an
  `engine.alert` view. **This contradicts `bbsengine6.sql`**
  (Bucket A) which had previously commented out the alert
  schema import with the note "legacy alert schema removed;
  see memberview.sql". The two need to be reconciled before
  the next bootstrap.
- [ ] `skin/tmpl/topbar-alertcount.tmpl` (new) — topbar
  template that renders `notifycount - sentreadcount` for
  the current member.

The complementary wiring is in tracked files:

- [ ] `js/bbsengine6.js` — `VALID_REQUESTS` regex adds
  `alert.list` and `alert.count`.
- [ ] `skin/tmpl/topbar-content.tmpl` — one-line tweak to
  embed the alert template.
- [ ] `handbook/specs/{modules,web,dependencies}.md` —
  documents the new topbar-alert component and the
  `alert.py` console module (the latter references
  `util.py`).

### Bucket E — bottombar / spec / doc inconsistencies

These are *regressions* relative to the design in
`TODO-BOTTOMBAR.md`. They need to be either reverted or
explicitly justified in Pass 4 before the next commit:

- [ ] `py/src/bbsengine6/io/screen.py` (178 lines changed):
  - Removes the `_warn_shim_deprecated(...)` helper and the
    `DeprecationWarning` it emitted.
  - Removes the `from .. import bottombar as _bottombar_mod`
    alias; `_bottombar_fragments` is now a plain `list` again
    (was a `_LockedList` owned by the default
    `FragmentRegistry`).
  - `register_bottombar_fragment` / `unregister_bottombar_fragment`
    are reimplemented against the plain list and a fresh
    `_bottombar_fragments_lock = threading.Lock()` — they no
    longer delegate to `bbsengine6.bottombar`.
  - **This undoes the back-compat shim work that
    `TODO-BOTTOMBAR.md` describes as complete.** The tests
    in `tests/test_bottombar.py` exercise
    `bbsengine6.bottombar` directly, but anything that
    imports through `bbsengine6.io.screen.register_bottombar_fragment`
    (e.g. `casino.auth`, `casino.lib`) will now hit the
    plain-list reimplementation, not the registry.
- [ ] `py/src/bbsengine6/ed/common/ui.py` (14 lines changed):
  - Removes the `_editor_fragments: list` tracking.
  - `unregister_bottombar()` is now
    `screen.clear_bottombar_fragments()` (was an
    `unregister` per fragment). **`clear_bottombar_fragments`
    is exactly the call that the new bottombar design is
    supposed to avoid** — it clobbers every package's
    fragments (casino, empyre, etc.). This is a regression
    relative to `TODO-BOTTOMBAR.md` Phase 3.
- [ ] `py/src/demo_bottombar_stack.py` — the clear step
  uses `screen._bottombar_fragments.clear()` directly
  (bypassing the registry). Acceptable as a test-only
  scratch but the demo should not be teaching the wrong API.
- [ ] `py/src/bbsengine6/io/specs/echo_commands.spec` —
  removes the `{level.fail}` variable and the
  `echo("message", level="fail")` example. The `level.fail`
  color and the `fail` log level exist in code; this is a
  doc-only regression.
- [ ] `py/src/bbsengine6/module.spec` — removes the
  `Cross-package calls via package=` section
  (41 lines). **This contradicts the Pass 2 L change to
  `module.py` that *restores* the `package=` kwarg.** The
  spec was apparently edited before Pass 2 L was applied;
  the spec needs to be restored alongside the code.

### Bucket F — version and miscellaneous

- [ ] `py/src/bbsengine6/_version.py` —
  `0.0.1.dev202607061611` → `0.0.1.dev202606291622`. This
  is a **version rollback** (newer SHA-less timestamp to an
  older one). Confirm whether this is intentional (e.g. a
  rebuild from an older checkout) or a mistake to revert.
- [ ] `py/src/bbsengine6/util.py` — `hr()` loses its
  `color="..."` parameter. The call site in `cli` / `console`
  may still pass a color string; grep for callers.
- [ ] `py/src/bbsengine6/blurb.py` —
  `engine.member_flag` → `engine.flag` in the join string.
  Verify that `engine.flag` is the correct table after
  `member_flag.sql` is applied.
- [ ] `py/src/bbsengine6/member.py` —
  `engine.checkmemberflag` → `engine.checkflag` (matches
  the SQL rename).
- [ ] `py/src/bbsengine6/sql/memberview.sql` — adds the
  alertcount subqueries (see Bucket A).
- [ ] `bbsengine6/TODO.md` and `bbsengine6/TODO_BACKEND.md` —
  trims and cross-references consistent with Pass 1 / Pass 2
  work.
- [ ] `handbook/specs/{architecture,util,web,dependencies,modules}.md` —
  signature updates (`hr()` returns `str` per the diff
  heading — note: code still returns `bool`; the spec may
  be wrong, or the code is mid-edit), and the alert module
  documentation.
- [ ] `py/src/bbsengine6/backend/{bank,checkclasses,checkcreatedb,checkdatabase,checkengine,checkflag,checkfunctions,checknotify,checknotifyd,checkroles,checksuperuser,checkwebserverrole,database,lib,stage_one,stage_zero}.py` —
  these are the Pass 1 follow-ups that were not captured
  in `8a7ac4f`. They include the `issysop` / `_sanitize_sp`
  additions in `backend/lib.py`, SAVEPOINT-wrapping in
  `checkfunctions` / `checkclasses` / `checknotifyd`, and
  the new `checkcreatedb` privilege check. **These are the
  same Pass 1 changes the new TODO claims are COMPLETE;
  they are in fact uncommitted.** A future Pass 4 should
  commit them with the Pass 1 message.

### Out of scope for Pass 3

- `py/src/bbsengine6/io/screen.py`'s `_impl_*` private
  functions (referenced by `py/src/bbsengine6/io/sink.py`
  in Pass 4) are unchanged on disk but are required by
  the bottombar design.
- The Casino / empyre / bed per-package bottombar
  migrations are tracked in `TODO-BOTTOMBAR.md` and are
  *committed* in `casino/`.
