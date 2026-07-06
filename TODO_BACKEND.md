# TODO: `bbsengine6.backend` refactor

Move the engine-init plumbing out of `bbsengine6.console` and
`bbsengine6.startup` (currently byte-identical duplicates and a
broken four-stage orchestrator) into a single canonical home at
`bbsengine6.backend`. Leave thin shims in the two call-site
packages so existing import paths keep resolving.

Decisions captured in this plan (2026-06-30):

- [x] Single source of truth: `bbsengine6.backend.*`
- [x] Console menu UIs stay in `console/`; admin tools are not
      init plumbing.
- [x] Shims use explicit `__all__` (`["init", "access",
      "buildargs", "main"]`), matching `console/__init__.py:1`.
- [x] `startup/main.py` orchestrates via `lib.runmodule(...)`,
      no direct `bbsengine6.backend` imports.
- [x] `startup/lib.runmodule` delegates to `console/lib.runmodule`
      with `package="bbsengine6.startup"`.
- [x] `console/lib.runmodule` gains a `package=` kwarg (default
      `"bbsengine6.console"`); one-line edit, backward compatible.
- [x] Top-level `bbsengine6/startup.py` (file) is left in place
      (shadowed by the new `startup/` package). Cleanup is
      separate.
- [x] `startup/main.py` adds a `util.heading("bbsengine6
      startup")` banner at the top of `_work()`, per the existing
      plan in `TODO.md`.

## Backend package (new)

- [x] Create `py/src/bbsengine6/backend/__init__.py` (empty)
- [x] Create `py/src/bbsengine6/backend/lib.py` with:
      - `from bbsengine6 import io, database, module, screen`
      - `def buildargs(args, **kwargs): return None`
      - `def runmodule(args, submodule, **kwargs)` dispatching
        to `f"bbsengine6.backend.{submodule}"`
      - `def setbottombar(args, left, **kwargs)` (copy from
        `console/lib.py:8-15`)
      - `checkroles`, `checkextensions`, `checkdatabase`,
        `checksuperuser`, `createdatabase`, `checkfunctions`,
        `checkclasses`, `checkflag`, `checknotify`,
        `checknotifyd`, `checkwebserverrole` -- all as `runmodule`
        shims pointing at the `backend` package
        (note: no `checkschema` -- superseded by the `engine`
        startup stage; see `backend/engine.py`)
      - `checkbank` pointing at `bbsengine6.backend.bank` (not
        `bbsengine6.console.bank`, which does not exist)
- [x] Create `py/src/bbsengine6/backend/Makefile` (copy
      `console/Makefile`)
- [x] Move 11 `check*` modules from `startup/` to `backend/`
      (no `checkschema` -- superseded by the `engine` startup stage)
      (currently the working-tree versions, with imports fixed):
      - [x] `checkclasses.py`
      - [x] `checkdatabase.py`
      - [x] `checkextensions.py`
      - [x] `checkflag.py`
      - [x] `checkfunctions.py`
      - [x] `checkloginid.py`
      - [x] `checknotify.py`
      - [x] `checknotifyd.py`
      - [x] `checkroles.py`
      - [x] `checksuperuser.py`
      - [x] `checkwebserverrole.py`
- [x] Move 4 init modules from `startup/` to `backend/`:
      - [x] `stage_zero.py` (add `import psycopg`)
      - [x] `stage_one.py` (add `from bbsengine6 import io, database`)
      - [x] `engine.py` (init `failcount = 0`; read `conn`
            from `kwargs.get("conn")`)
      - [x] `bank.py` (init `failcount = 0`; read `conn` from
            `kwargs.get("conn")`)

## Console shims (11 files, overwrite)

Each shim follows the same template (example for `checkroles.py`):

```python
from bbsengine6.backend.checkroles import init, access, buildargs, main

__all__ = ["init", "access", "buildargs", "main"]
```

- [x] `py/src/bbsengine6/console/checkclasses.py`
- [x] `py/src/bbsengine6/console/checkdatabase.py`
- [x] `py/src/bbsengine6/console/checkextensions.py`
- [x] `py/src/bbsengine6/console/checkflag.py`
- [x] `py/src/bbsengine6/console/checkfunctions.py`
- [x] `py/src/bbsengine6/console/checkloginid.py`
- [x] `py/src/bbsengine6/console/checknotify.py`
- [x] `py/src/bbsengine6/console/checknotifyd.py`
- [x] `py/src/bbsengine6/console/checkroles.py`
- [x] `py/src/bbsengine6/console/checksuperuser.py`
- [x] `py/src/bbsengine6/console/checkwebserverrole.py`

## Console `lib.py` edit (one line)

- [x] Edit `py/src/bbsengine6/console/lib.py:140` to add
      `package=` kwarg:
      ```python
      def runmodule(args, submodule, *, package="bbsengine6.console", **kwargs):
          return module.runmodule(args, f"{package}.{submodule}", **kwargs)
      ```

## Startup shims (4 files, overwrite)

Same template as the console shims, e.g.:

```python
from bbsengine6.backend.stage_zero import init, access, buildargs, main

__all__ = ["init", "access", "buildargs", "main"]
```

- [x] `py/src/bbsengine6/startup/stage_zero.py`
- [x] `py/src/bbsengine6/startup/stage_one.py`
- [x] `py/src/bbsengine6/startup/engine.py`
- [x] `py/src/bbsengine6/startup/bank.py`

## Startup `lib.py` rewrite (shim over `console.lib`)

- [x] Overwrite `py/src/bbsengine6/startup/lib.py` with:
      ```python
      from bbsengine6.console import lib as _console_lib

      buildargs = _console_lib.buildargs
      setbottombar = _console_lib.setbottombar

      def runmodule(args, submodule, **kwargs):
          return _console_lib.runmodule(
              args, submodule, package="bbsengine6.startup", **kwargs
          )
      ```

## Startup `main.py` rewrite

- [x] Overwrite `py/src/bbsengine6/startup/main.py`:
      - [x] Add `from bbsengine6 import io, database, util`
      - [x] Add `from . import lib`
      - [x] Keep `init` / `access` / `buildargs` stubs
      - [x] Rewrite `main()` to loop
            `("stage_zero", "stage_one", "engine", "bank")`
            via `lib.runmodule(args, s, conn=conn, **kwargs)`
      - [x] Initialize `failcount = 0` before the loop
      - [x] On failure: `conn.rollback()`, return `False`
      - [x] On success: `conn.commit()`, return `True`
      - [x] Add `util.heading("bbsengine6 startup")` at the top
            of `_work()`
      - [x] Preserve the existing `conn` / `pool` branching at
            the bottom of `main()`

## Out of scope (this commit)

- [x] Do not delete `py/src/bbsengine6/startup.py` (file). It
      is shadowed by the new `startup/` package but stays in
      the tree per the existing plan in `TODO.md`.
- [x] Do not touch other modified files in the working tree:
      `bbsengine6/__init__.py`, `_version.py`, `pyproject.toml`,
      `console/__main__.py`, `database.py`, `module.py`,
      `util.py`, top-level `startup.py`.
- [x] Do not change `console/main.py`, `console/__main__.py`,
      `console/__init__.py`, or any non-`check*` console module
      (`alert.py`, `createdatabase.py`, `email.py`, `member.py`,
      `memberapproval.py`, `session.py`, `showpgrole.py`).

## Pre-existing issues (deferred)

- [x] `backend/stage_one` did not call `checkengine` against the
      target DB (it only ran in stage_zero against the `postgres`
      maintenance DB), so `engine.*` lookups in
      `checkfunctions` / `importsql` failed with
      `schema "engine" does not exist` on a fresh cluster. Fixed
      by adding `"checkengine"` to the stage 1 module loop in
      `py/src/bbsengine6/backend/stage_one.py:24-31`, positioned
      after `checkextensions` and before `checkfunctions`.
      Covered by
      `tests/integration/test_stage_one_checkengine.py`.
- [x] Once `checkengine` started running in stage 1, the
      `manage_schema_priv` grant loop failed with
      `function manage_schema_priv(unknown, unknown, unknown, unknown)
      does not exist` because stage 1's `checkfunctions` only
      installs `engine.*` functions and never installs the
      `public.*` admin helpers into the target DB. Fixed by
      having `checkengine.main` install `manage_schema_priv.sql`
      via `importsql()` if `functionexists("public.manage_schema_priv")`
      is `False`, before the grant loop. `checkengine` is the
      first module in both stage 0 and stage 1 that needs the
      helper, so owning the install there is more robust than
      trying to coordinate stage 0/1 ordering. Covered by
      `tests/integration/test_stage_one_checkengine.py`
      (`test_main_installs_manage_schema_priv_when_missing` and
      `test_main_returns_false_when_manage_schema_priv_install_fails`).
- [ ] Top-level `bbsengine6/startup.py` is dead code (shadowed
      by the new `startup/` package). Cleanup is a separate
      concern.

## Verification (after the commit is applied)

- [x] `python -c "from bbsengine6.backend import checkroles;
      checkroles.main(None)"` does not raise `NameError` on
      `failcount` / free-variable `conn`
- [x] `python -c "from bbsengine6.console import checkroles;
      checkroles.main(None)"` resolves to the same callable
- [x] `python -c "from bbsengine6.startup.stage_zero import
      main; main is not None"` succeeds
- [x] `python -c "from bbsengine6.startup import main as m;
      m.main(None)"` does not raise (with `pool=None` and
      `conn=None` it short-circuits to "pool is None" without
      touching the DB)
- [x] `git diff py/src/bbsengine6/console/lib.py` shows only
      the `package=` kwarg line
- [x] `git diff py/src/bbsengine6/startup.py` is empty (file
      left untouched)
- [x] `rg -n "from bbsengine6.console.check|import
      bbsengine6.console.check" bbsengine6/ empyre/ casino/
      mistermcfeely/ murdermotel/ zoid6/` shows no broken
      import sites
