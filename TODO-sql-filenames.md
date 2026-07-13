# TODO: Consistent underscore separators in `sql/*.sql` filenames (next-quarter refactor)

Work item: normalize the `sql/*.sql` filename convention so that
multi-word names use `_` (underscore) as the word separator
consistently across the directory. Update the backend modules that
load these files to match.

## The inconsistency today

The `sql/` directory mixes two patterns:

- **Single-word files** (no separator needed): `actionlog.sql`,
  `bank.sql`, `member.sql`, `invite.sql`, `notify.sql`, etc.
- **Multi-word files, sometimes with underscore, sometimes without.**
  Examples of the inconsistency:
  - `notifyview.sql` (no separator) vs `session_view.sql` (with
    separator). Both are views.
  - `blurbview.sql`, `memberview.sql`, `folderview.sql` (no
    separator) vs `session_view.sql` (with separator). All views.
  - `createrol.sql` (no separator) vs `manage_database_priv.sql`
    (with separator). Both are role-management functions.
  - `memberinet.sql` (no separator) vs `member_flag.sql` (with
    separator).
  - `notifyd.sql` (no separator; arguably a daemon table, but
    the convention is unclear).
  - `blurb_flag.sql`, `blurb_read.sql`, `notify_block.sql`,
    `notify_group.sql`, `notify_rate_limit.sql`, `notify_recipient.sql`,
    `notify_type.sql`, `map_group_member.sql`, `map_member_flag.sql`,
    `map_sigop_sigpath.sql`, `get_role_privs.sql`,
    `manage_database_priv.sql`, `manage_role_privs.sql`,
    `manage_schema_priv.sql`, `manage_secondary_role.sql`,
    `message_groups.sql`, `tagmap.sql` — all use underscore
    consistently within their group.

The two patterns coexist because the directory grew organically
over time. Some files were added by developers who preferred the
concatenated form (`notifyview`), others by developers who
preferred the underscored form (`session_view`). Neither is
wrong in isolation; the problem is the mix.

## Counts (current state)

- 45 single-word files (no underscores)
- 10 files with one underscore
- 9 files with two underscores

Total: 64 `.sql` files in the directory.

## Decisions captured (2026-07-06)

- [x] **Target convention: underscore-separated.** Multi-word
      filenames use `_` as the word separator. So
      `notifyview.sql` becomes `notify_view.sql`,
      `createrol.sql` becomes `create_rol.sql`,
      `memberinet.sql` becomes `member_inet.sql`. Single-word
      filenames are unchanged (`bank.sql` stays `bank.sql`).

      **Later update (2026-07-09):** `bank.sql` was split into
      `bank_schema.sql`, `bank_account.sql`, `bank_transaction.sql`,
      `bank_transfer.sql` as part of a separate refactor, so it no
      longer exists as a single file. The rename plan for the remaining
      single-word files is unchanged.
- [x] **This is a next-quarter refactor.** Not part of the audit
      PR or any in-flight work. Touching it requires updating
      every `(class, filename)` tuple in the backend, the
      conftest, the test files, and any consumer code. It's
      also a rename of git-tracked files, which will show up
      in every future blame until the rename settles.
- [x] **No BC concerns.** The SQL files are not externally
      referenced by name (they're internal to the BBS engine).
      Renames only affect the codebase itself.
- [x] **No semantic changes.** The rename is purely cosmetic.
      Schema objects (`engine.__notify`, `engine.notify_view`,
      etc.) keep their existing names — only the `.sql` file
      names change.

## Work items (next-quarter, to be detailed when this TODO is activated)

### Renames (target → source mapping)

The renames below assume the target convention is "underscore
separates words." A rename script or manual `git mv` will be
needed.

- [ ] `notifyview.sql` → `notify_view.sql`
- [ ] `createrol.sql` → `create_rol.sql`
- [ ] `memberinet.sql` → `member_inet.sql`
- [ ] `notifyd.sql` → `notify_d.sql` (debatable — this is a
      daemon schema file; the `d` suffix is a long-standing
      convention. Decision needed: rename to
      `notify_daemon.sql` for clarity, or keep as
      `notify_d.sql` for backwards-blame-readability, or
      leave as-is since `notifyd` is the established
      shortform. **Recommendation: rename to
      `notify_daemon.sql`** for full descriptiveness.)
- [ ] `blurbview.sql` → `blurb_view.sql`
- [ ] `memberview.sql` → `member_view.sql`
- [ ] `folderview.sql` → `folder_view.sql`
- [ ] `createschema.sql` → `create_schema.sql`
- [ ] `buildsiguri.sql` → `build_sig_uri.sql` (debatable —
      this is a build helper for signature URIs. Could also
      be `build_siguri.sql`. Decision: prefer
      `build_sig_uri.sql` for full word separation.)
- [ ] `checkmemberflag.sql` → `check_member_flag.sql`
- [ ] `getflags.sql` → `get_flags.sql`
- [ ] `getmemberflags.sql` → `get_member_flags.sql`
- [ ] `getsubblurbs.sql` → `get_subblurbs.sql` (debatable —
      `subblurbs` is itself a compound. Could be
      `get_sub_blurbs.sql` for full word separation. Decision
      needed.)
- [ ] `flagdata.sql` → `flag_data.sql`
- [ ] `member_flag.sql` (already underscored — unchanged)
- [ ] All other underscored files — unchanged.

### Backend updates required

- [ ] `backend/checkclasses.py` — update `classlist` tuple
      (line 26-29) with new filenames for `memberview.sql`.
- [ ] `backend/checkengine.py` — update `classes` tuple
      (line 101-121) with new filenames for `memberview.sql`,
      `member_flag.sql` (no change), `map_member_flag.sql`
      (no change), `session_view.sql` (no change).
- [ ] `backend/bank.py` — update `classlist` (line 67-72) if
      any bank-related file is renamed (none currently in
      scope; all bank files are single-word).
- [ ] `backend/checkflag.py` — update `importsql` calls
      (line 32, 46, 65) with new filenames.
- [ ] `backend/checkfunctions.py` — the function name → file
      name mapping at line 53-55 (`engine.X` → `X.sql`) means
      any renamed function file needs a manual mapping. The
      current scheme strips `engine.` and adds `.sql`; renamed
      files that don't follow `function_name.sql` will need
      explicit handling. Audit each function in the stage 0
      and stage 1 funclist and confirm the existing auto-derivation
      still works after rename.
- [ ] `backend/checknotify.py` — `enumlist` and `classlist`
      (line 30-43) need updates for renamed notify files.
- [ ] `backend/checknotifyd.py` — `classlist` (line 26-29)
      needs update if `notifyd.sql` is renamed.

### Test conftest updates

- [ ] `tests/conftest.py:_get_notify_sql_files()` (line 265-294)
      — update the `files` list with new filenames. The
      function name and the order are unchanged; only the
      filenames in the list need updating.
- [ ] `tests/test_console_checknotifyd.py` — if it references
      `notifyd.sql` directly, update to the new name.
- [ ] Any other test that imports or references a renamed
      SQL file by name. (Likely a small set; most tests go
      through `database.importsql()` which takes a filename
      argument.)

### Documentation updates

- [ ] `sql/upgrades.md` — add an entry listing the renames.
- [ ] `message_delivery/SPEC.md` and other docs that
      reference SQL file names — update references.
- [ ] `TODO-notify.md` — update references to renamed files
      (e.g. `notify_recipient_deliverymethod_helpers.sql`
      in the Phase 1 work items, if applicable).
- [ ] `bbsengine6/README.md` if it lists SQL files.

### Tools and CI

- [ ] Add a CI check that fails if any new SQL file is added
      with a non-conforming name. (Regex: `^[a-z]+(_[a-z]+)*\.sql$`.)
      This prevents the inconsistency from re-emerging.
- [ ] Update any Makefile or shell script that hardcodes
      SQL file names. (`sql/Makefile` is currently empty
      beyond `all:` and `clean:`, so likely nothing to
      update.)
- [ ] Add a pre-commit hook that lints SQL filenames.

### Rename execution

- [ ] Use `git mv` for each rename so git tracks the rename
      (vs. delete+add, which loses history).
- [ ] Verify the rename with `git log --follow` on a sample
      file to confirm history follows the rename.
- [ ] Run the test suite on a clean database to confirm the
      bootstrap stages still load all the renamed files.
- [ ] Run the test suite against an existing database (one
      that was bootstrapped with the old filenames) to confirm
      the loader is idempotent. (This should already be true
      because `classexists()` and `functionexists()` check
      schema, not filenames; the filenames are only used to
      locate the SQL source.)

## Risks

- [ ] **Large diff for a small change.** Even though the
      rename is purely cosmetic, it touches many files. The
      diff will be noisy. Mitigation: do it as its own
      dedicated PR with no other changes, so reviewers can
      focus on the rename in isolation.
- [ ] **Git rename detection threshold.** By default git
      treats a file as renamed if more than 50% of its
      content matches the new file. Pure renames of `.sql`
      files (which have unique content) will be detected
      as renames. If the threshold is too strict, git
      may show them as delete+add, losing blame history.
      Mitigation: `git mv` (preserves rename intent) and
      `git config diff.renames true` (default is true).
- [ ] **External references.** Any code or docs outside this
      repo that reference the old filenames will break.
      Mitigation: search widely before the rename (e.g.
      grep across `dist/`, `vendor/`, any sister repos that
      pull in bbsengine6 SQL files).
- [ ] **The convention is not actually wrong.** The mix of
      patterns is ugly but functional. The benefit of this
      refactor is purely aesthetic and consistency-driven,
      not a bug fix. Make sure the case for the rename is
      strong enough to justify the diff size and review
      effort.

## Out of scope

- Renaming the schema objects themselves
  (`engine.__notify` → `engine._notify`, etc.). Schema
  renames are a much larger refactor and are not part of
  this work.
- Renaming the table-class convention (`__notify` →
  `_notify` for a "private" prefix, vs no prefix for
  public views). Out of scope.
- Renaming the SQL function names (`engine._append_delivery_method`
  → `engine._append_delivery_method` is already
  underscore-separated). No change needed.
- Renaming the Python modules (`message_delivery`,
  `backend`, etc.). Out of scope; not a SQL filename
  concern.

## Relationship to other TODOs

- **`TODO-notify.md`**: the audit PR adds a new file
  `sql/notify_recipient_deliverymethod_helpers.sql`
  (already underscore-separated, so no change needed).
  After the audit PR lands, the rename work in this file
  will rename `notifyview.sql` → `notify_view.sql` in
  the conftest and backend references, but won't touch
  the new helper file.
- **`TODO-notify-encryption.md`**: future GnuPG work may
  add new SQL files (e.g. for the `__member_gpg_key`
  table). The new files should follow the underscore
  convention from the start, so this refactor should
  land *before* the encryption work's new files are
  added. Or: the encryption PR can use underscore names
  for new files even before the codebase-wide rename,
  setting the convention for new code.

## Recommended execution order

1. Land the audit PR (`TODO-notify.md` Phases 1-6).
2. Land the `*epoch` removal PR (`TODO-notify.md` Phase 8).
3. Land the notify startup re-enable PR
   (`TODO-notify.md` Phase 7).
4. Land the GnuPG encryption PR Part 1 (schema additions
   only) — new SQL files use underscore convention.
5. **Land this rename PR** (codebase-wide SQL filename
   normalization). It is a clean, low-risk change at this
   point because the audit work is done and the encryption
   work's new files are already using the convention.
6. Continue with GnuPG encryption PR Parts 2-5.
