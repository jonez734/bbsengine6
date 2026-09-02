# TODO: `datedelivered` audit completion + `deliverymethod` for `__notify_recipient`

> **STATUS (2026-07-22): SUPERSEDED.** The notify→message.py migration
> is complete. The `bbsengine6/notify/` and `bbsengine6/message_delivery/`
> packages, the `engine.__notify*` tables, the `engine.notify` view,
> the `engine._append_delivery_method` SQL helper, and the
> `checknotify.py` / `checknotifyd.py` backend modules have all been
> deleted in Phase 7 of `TODO-message-migration.md`. Every item below
> this banner is therefore moot: the columns, views, and stored
> procedures it describes no longer exist.
>
> The work item is preserved here for historical reference only. The
> new notification system lives in `bbsengine6/message.py` and is
> documented in `TODO-message-migration.md` Phase 8.
>
> **Phase 11 note (DAL extraction, see
> `TODO-message-migration.md`):** the underlying
> `bbsengine6/message.py` referenced above is now a layered
> package; `bbsengine6.message.lib` is a facade. The package
> surface is unchanged.

Work item: add per-recipient delivery-method audit fields to the notify
subsystem and clean up the dead `should_persist` parameter. No rename
of the `message_delivery` module.

Decisions captured in plan (2026-07-06, revised after encryption
discussion):

- [x] No rename of `message_delivery/`. The "direct message" use case
      is already supported via `send(recipients=[...])`.
- [x] `datedelivered` already exists on `__notify_recipient`; complete
      its plumbing through `mark_delivered()` and the live-queue path.
- [x] `deliverymethod` is a new column on `__notify_recipient`,
      comma-separated alphabetical token set, populated via the SQL
      helper `engine._append_delivery_method(existing, new_method)`.
- [x] Helper function lives in a new SQL file
      `sql/notify_recipient_deliverymethod_helpers.sql`.
- [x] SQL changes are made directly in existing files
      (`notify.sql`, `notify_recipient.sql`, `notifyview.sql`) — no
      migration script.
- [x] FK from `__notify_recipient.notify_id` to `__notify.id` changes
      from `on delete cascade` to `on delete set null` so audit rows
      survive `expunge()`.
- [x] `should_persist` parameter and column removed cleanly (no
      deprecation period, no BC). The `should_persist` column is
      dropped from `engine.__notify` and removed from the view.
      `should_persist` parameter is removed from `send()`,
      `NotifyIntegration.send()`, and `send_with_internet()`.
- [x] Helper function loader added to `backend/checknotify.py:main()`.
      The conftest gets the new SQL file in its ordered
      `_get_notify_sql_files()` list.
- [x] Production `checkengine.py` notify import un-comment is
      **out of scope** for this PR (separate refactor; the file's
      deprecation comment makes clear the re-enablement is
      intentionally paused).
- [x] Sort order of tokens in `deliverymethod` is alphabetical
      (deterministic for tests/display; insertion order would
      require schema changes).
- [x] Tokens stored verbatim from `handler.handler_name` (no
      normalization enum).
- [x] `engine.notify` view already exposes local-tz variants
      for date columns (`datedeliveredlocal`, `datereadlocal`,
      `datecreatedlocal`) via
      `timezone(currentmember.tz, <column>)`, matching the
      pattern in `actionlog.sql`, `invite.sql`, `refcode.sql`,
      and `session_view.sql`. These are not being added in this
      PR — they already exist. The Phase 1 view edit verifies
      they remain present after the `should_persist` removal
      and `deliverymethod` add. The new `deliverymethod`
      column is a string and has no local/epoch variant.
- [x] `*epoch` columns (`datedeliveredepoch`, etc.) are
      redundant with their source `timestamptz` columns.
      The audit PR does NOT remove them. The codebase-wide
      removal is tracked in **Phase 8** of this file as
      a follow-up PR. The `*local` columns are
      per-row/context-dependent and are kept.
- [x] `Notification.should_persist` field removed from the
      dataclass (clean break; no deprecation warning).
- [x] Privacy goal will be served by GnuPG signing/encryption
      (separate TODO at `TODO-notify-encryption.md`). The
      `should_persist` clean-break in this PR is a side effect
      — the parameter is being replaced by `signed: bool` and
      `encrypted: bool` parameters on a future `send()`
      signature. Privacy is **not** served by skipping the DB;
      the body will be stored as ciphertext.

## Phase 0 — read-only verification (start of implementation turn)

- [ ] Confirm `engine._append_delivery_method` is unique in the
      `engine` schema (no `pg_proc` name collision).
- [ ] Verify `web`, `sysop`, `term` can `execute` functions in the
      `engine` schema (check `sql/grants.sql` and `sql/manage_*.sql`).
- [ ] Audit every `__notify_recipient` JOIN for NULL-tolerance on
      `notify_id`. Inner joins must naturally exclude orphan audit
      rows from view results — confirm.
- [ ] Confirm no trigger or rule references `should_persist` (now
      that the column is being dropped, this is a sanity check).
- [ ] Confirm `database.functionexists()` resolves
      `engine._append_delivery_method` correctly (splits on `.`,
      queries `pg_proc` + `pg_namespace`).

## Phase 1 — SQL files (direct edits, no migration script)

- [ ] Edit `sql/notify.sql`:
  - [ ] Drop the `should_persist` column from the `__notify` table
        definition (line 22).
- [ ] Edit `sql/notify_recipient.sql`:
  - [ ] Add `"deliverymethod" text,` column after the `datedelivered`
        line.
  - [ ] Change `notify_id bigint not null` to `notify_id bigint`
        (drop `NOT NULL`).
  - [ ] Change FK `on delete cascade` to `on delete set null`.
- [ ] Edit `sql/notifyview.sql`:
  - [ ] Add `nr.deliverymethod as deliverymethod,` to the column list
        between `datedelivered` and `dateread`. No epoch/local
        variants.
  - [ ] Remove `n.should_persist,` from the column list (line 16).
  - [ ] **Verify local-tz variants are present for date columns.**
        The view already exposes `datedeliveredlocal`,
        `datereadlocal`, and `datecreatedlocal` (lines 26-28)
        via `timezone(currentmember.tz, ...)`, matching the
        pattern used in `actionlog.sql`, `invite.sql`,
        `refcode.sql`, and `session_view.sql`. Confirm all
        three `*local` columns remain in the view after the
        edit. They are not being added in this PR — they
        already exist — but the implementer should confirm
        they are not accidentally removed.
- [ ] Create `sql/notify_recipient_deliverymethod_helpers.sql`:
  - [ ] Define `engine._append_delivery_method(existing text, new_method text) returns text`
        with `language sql immutable`.
  - [ ] `grant execute on function engine._append_delivery_method(text, text) to web, sysop, term;`
  - [ ] Verify file is idempotent (`create or replace`, no DDL that
        fails on re-run).

## Phase 1.5 — Backend imports

- [ ] Edit `tests/conftest.py:_get_notify_sql_files()`:
  - [ ] Add `"notify_recipient_deliverymethod_helpers.sql"` to the
        files list, positioned after `"notify_recipient.sql"` and
        before `"notify_block.sql"`.
  - [ ] Update the docstring above the function (lines 99-119) to
        list the new file in the bulleted summary.
- [ ] Edit `backend/checknotify.py`:
  - [ ] Add `funclist` constant in the module body:
        `(("engine._append_delivery_method", "notify_recipient_deliverymethod_helpers.sql"),)`.
  - [ ] In `main()`, add a new loop after the existing classlist loop
        (currently ends at line 115) that iterates the funclist,
        checks `database.functionexists(args, name, conn=conn)`,
        and on miss calls `database.importsql(args, sql_file, conn=conn, rollback=False)`
        inside a savepoint, modeled on the classlist loop.
  - [ ] Update the module docstring (line 4-8) to note that the
        helper function loader is intentionally present despite
        the deprecation status, for when the production notify
        schema loader is eventually re-enabled.

## Phase 2 — Python in `message_delivery/lib.py`

- [ ] Remove `should_persist` field from `Notification` dataclass
      (line 121).
- [ ] Remove `should_persist: bool = True` parameter from `send()`
      signature (line 545).
- [ ] Remove `should_persist` column and parameter from both
      `INSERT INTO engine.__notify` blocks (lines 625-644 and
      645-663).
- [ ] Remove `should_persist=should_persist` from the `Notification(...)`
      return value at line 715.
- [ ] Remove the two hardcoded `should_persist=True` literals at
      lines 752 and 908.
- [ ] Update `send()` docstring (line 549) to drop the `should_persist`
      mention.
- [ ] Add `delivery_methods: Set[str] = field(default_factory=set)`
      to the `Notification` dataclass, next to `delivered_to`
      (line 118).
- [ ] Extend `get_notifications()` SELECT (around line 850): add
      `nr.deliverymethod,` to the column list.
- [ ] In the `get_notifications()` row-build section, populate
      `delivery_methods` by splitting `row["deliverymethod"]` on
      `,`, stripping whitespace, and discarding empty tokens.
- [ ] Extend `mark_delivered()` (line 1032) with
      `method: Optional[str] = None` parameter.
- [ ] Replace the `mark_delivered()` UPDATE body with one that calls
      `engine._append_delivery_method(deliverymethod, %s)`.
- [ ] Replace the inline UPDATE at lines 763-769 with a call to
      `mark_delivered(notify_id, moniker, method="inmemory", args=args, pool=pool, conn=conn)`.
      Preserve the surrounding `try/except` (line 757-773) that
      swallows pool/conn errors.

## Phase 3 — Python in `message_delivery_handlers.py`

- [ ] In `DeliveryManager.publish_to_channel()` (line 311), after
      `handler.deliver(...)` returns True, add a guarded call to
      `mark_delivered(notify_id, recipient, method=handler_name, args=message.get("_args"))`
      where `notify_id = message.get("id")` and the call is skipped
      if `notify_id` is `None`.
- [ ] Use a lazy `from .lib import mark_delivered` import inside the
      method to avoid circular-import issues.

## Phase 4 — Python in `net/integration.py`

- [ ] Remove `should_persist: bool = True` parameter from
      `NotifyIntegration.send()` (line 69).
- [ ] Remove `should_persist: bool = True` parameter from
      `send_with_internet()` (line 229).
- [ ] Remove the `should_persist=should_persist` argument from the
      inner `notify_module.send(...)` call (line 129).
- [ ] Update the docstrings for both functions to drop the
      `should_persist` mention.

## Phase 5 — Tests

- [ ] `tests/test_notify_schema_columns.py`:
  - [ ] Add `"deliverymethod"` to the expected column list for
        `__notify_recipient`.
  - [ ] Remove `"should_persist"` from the expected column list
        for `__notify` (column is being dropped).
- [ ] New tests (in `tests/test_notify_lib.py` or a new
      `tests/test_delivery_method.py`):
  - [ ] `test_mark_delivered_sets_method` — call with `method="email"`,
        SELECT row, assert `deliverymethod == "email"` and
        `datedelivered IS NOT NULL`.
  - [ ] `test_mark_delivered_accumulates_methods` — call with
        `"email"`, then `"sms"`, assert `deliverymethod == "email,sms"`.
  - [ ] `test_mark_delivered_idempotent` — call twice with `"email"`,
        assert still `"email"`.
  - [ ] `test_mark_delivered_no_method` — call without `method`
        kwarg, assert `datedelivered` set, `deliverymethod` NULL.
  - [ ] `test_mark_delivered_method_omitted_skips_helper` — when
        `method is None`, helper returns `''` and the column is
        unchanged.
  - [ ] `test_get_notifications_exposes_delivery_methods` — after
        stamping two methods, `Notification.delivery_methods ==
        {"email", "sms"}`.
  - [ ] `test_publish_to_channel_persists_method` — mock
        `DeliveryHandler.deliver()` returns True, call
        `publish_to_channel`, assert recipient row's
        `deliverymethod == mock_name` and `datedelivered IS NOT NULL`.
  - [ ] `test_append_delivery_method_alphabetical` — direct SQL
        test: `SELECT engine._append_delivery_method('sms,email', 'inmemory')`
        returns `'email,inmemory,sms'`.
  - [ ] `test_append_delivery_method_dedup` — `SELECT engine._append_delivery_method('email', 'email')`
        returns `'email'`.
  - [ ] `test_append_delivery_method_null_safe` — `SELECT engine._append_delivery_method(NULL, 'sms')`
        returns `'sms'`.
  - [ ] `test_recipient_audit_survives_notify_expunge` — create
        `__notify` + `__notify_recipient`, call
        `mark_delivered(method="email")`, then call `expunge()`,
        assert `__notify_recipient` row still exists with
        `deliverymethod == "email"` and `notify_id IS NULL` (FK
        `set null` behavior).
- [ ] `should_persist` test cleanup:
  - [ ] Drop `should_persist=True` from all 48 test callsites
        across 6 files.
  - [ ] Drop `assert notif.should_persist is True` at
        `tests/test_notify.py:87`.
- [ ] Verify the test conftest `_get_notify_sql_files()` order is
      correct after the new file insertion (run the test suite
      from a clean DB).

## Phase 6 — Docs

- [ ] Edit `message_delivery/SPEC.md`:
  - [ ] Add a "Delivery Audit" section after "Rate Limiting"
        documenting `deliverymethod`, the
        `engine._append_delivery_method` helper, the values
        currently emitted by handlers (`inmemory` is the only one
        wired today), and the `Notification.delivery_methods`
        accessor. Document the three forms `datedelivered` is
        exposed in via `engine.notify`: raw `timestamptz`,
        `datedeliveredepoch` (epoch seconds), and
        `datedeliveredlocal` (current_user's timezone, computed
        via `timezone(currentmember.tz, ...)`).
  - [ ] Document the FK `on delete set null` behavior in the same
        section: audit rows survive `expunge()` but are excluded
        from `get_notifications()` view results.
  - [ ] Update the public API listing — `mark_delivered` adds a
        `method` kwarg; `send()` no longer accepts `should_persist`.
  - [ ] Update the `engine.__notify_recipient` schema description
        to include `deliverymethod text` and the FK change.
  - [ ] Update the `__notify` schema description — `should_persist`
        column is being dropped entirely; remove from the schema
        table.
  - [ ] Update the `engine.notify` view description — `should_persist`
        is no longer exposed; `deliverymethod` is now exposed;
        confirm `datedeliveredlocal`, `datereadlocal`, and
        `datecreatedlocal` are documented as the local-tz
        variants computed via
        `timezone(currentmember.tz, <column>)`. This matches
        the pattern in `actionlog.sql`, `invite.sql`,
        `refcode.sql`, and `session_view.sql` — the local-tz
        columns are computed per-row using the current
        session's `engine.__member.tz` (resolved via the
        `current_user` role). The new `deliverymethod`
        column is a string and has no local/epoch variant.
  - [ ] Add a "Privacy" section pointing to `TODO-notify-encryption.md`
        for the future GnuPG signing/encryption work.
  - [ ] Add a "Known issues" section flagging the latent `notifyd`
        bug (`recipient=` vs `recipients=` in
        `daemon/notification.py:96, 169`) as out of scope for
        this PR.

## Phase 7 — Re-enable notify tables in `startup` (follow-up PR)

The audit work in Phases 1-6 makes the notify schema correct on
disk and the helper function loadable, but production bootstrap
stages do not actually load it. The notify table imports in
`backend/checkengine.py:110-115` are commented out per the
deprecation note in `backend/checknotify.py:4-7` ("notify schema
is being moved to the message_delivery subsystem. This module
will be removed once console has migrated its callers. Until
then the access() and savepoint plumbing is kept current; the
SQL imports remain commented out in checkengine.py.").

Re-enabling the production loader is a separate PR. It is a
prerequisite for the encryption follow-up (`TODO-notify-encryption.md`),
which needs `engine.__member.gpg_fingerprint` and the new
`engine.__notify` columns installed on a fresh database bootstrap,
not just loaded by the test conftest.

### Phase 7 work items

- [ ] Decide where the notify schema import belongs in the
      bootstrap stage ordering. Options:
  - [ ] **A. Uncomment the existing entries in
        `backend/checkengine.py` lines 110-115.** Restores the
        pre-deprecation behavior. Simplest. Same module that
        installs `__member`, `__session`, etc.
  - [ ] **B. Move the notify schema import into its own
        backend module** (e.g. `backend/checknotify.py` already
        exists, currently no-op; uncomment and use it as the
        loader home). Cleaner separation; matches the existing
        `checknotifyd.py` pattern for the daemon tables.
  - [ ] **C. Move the notify schema import into a new
        `backend/checknotify_schema.py`** that runs after
        `checkengine` and after `checkclasses` (since the
        notify tables depend on `__member` and `__session`
        which are installed by those). Most isolated; most
        code.
  - [ ] **Recommendation: A or B.** B if you want to keep
        `checkengine` focused on the core engine schema (member,
        session, role, refcode) and have notify be a clearly
        separated concern. A if you want minimal change.
- [ ] Update the `backend/checknotify.py` deprecation comment
      (lines 4-8) to reflect the new state once the loader is
      active. The deprecation is no longer accurate if
      `checknotify` becomes the active loader (option B) or
      if `checkengine` becomes the active loader (option A).
- [ ] Decide whether to add `notify_recipient_deliverymethod_helpers.sql`
      (the new helper file from Phase 1) to the same loader, or
      keep its loading logic in `checknotify.py:main()` (per
      Phase 1.5) and have the stage loader call `checknotify.main()`
      in addition to the table import. Recommendation: have
      the stage loader call `checknotify.main()` so the function
      loader from Phase 1.5 runs in production.
- [ ] Update `backend/stage_one.py` (line 24-31, the module loop)
      to include the chosen loader module. If option A, no
      change to `stage_one.py` is needed (the loader is already
      in `checkengine` which is in the loop). If option B or C,
      add the new module to the loop.
- [ ] Update `backend/stage_zero.py` (line 38-47, the module
      loop) similarly. The notify schema is in the per-database
      `engine` schema, so the loader must run against the target
      database, not the admin `postgres` database. Verify which
      stage is the right one — likely `stage_one` (the target
      database stage) since `checkengine` runs there.
- [ ] Add a `checknotify.main()` invocation to the appropriate
      stage. Currently `checknotify.main()` exists but is not
      called by any stage. Wire it up.
- [ ] Test on a fresh database: run `stage_zero` and `stage_one`
      with the new loader enabled, verify all notify tables,
      the view, and the helper function are installed.
- [ ] Test on an existing database: run the loader against a
      database that already has the notify tables (from the
      test conftest path) and verify it is a no-op (tables
      already exist, function already exists).
- [ ] Update `tests/conftest.py:_get_notify_sql_files()` if it
      becomes redundant with the production loader. Currently
      the conftest is the only loader that runs. After Phase 7,
      production runs the same loader. Decide: keep the conftest
      loader (defensive, doesn't hurt), or remove it (DRY).
      Recommendation: keep the conftest loader — it ensures
      tests can run against a database that wasn't bootstrapped
      via the production stages, which is the common case in CI.

### Phase 7 dependencies

- **Blockers:** none. Phase 7 is independent of Phases 1-6 from
  a code perspective (it touches different files). However, the
  helper function from Phase 1.5 only exists after Phase 1 lands,
  so the loader from Phase 1.5 should not be activated in
  production until the audit PR is merged.
- **Unblocks:** the encryption follow-up
  (`TODO-notify-encryption.md`). The encryption work needs the
  notify schema to be installed on fresh bootstraps, which
  requires the production loader to be active.

### Phase 7 risks

- [ ] **Re-enabling a previously-deprecated code path is a
      re-merge point.** The notify tables were intentionally
      unhooked from the production stages during a previous
      refactor. Re-enabling them may surface latent issues
      that were masked by the deprecation (e.g. the
      `recipient=` vs `recipients=` bug in `notifyd` daemon,
      which currently doesn't run in production because the
      schema isn't installed).
- [ ] **Stage ordering matters.** The notify tables depend on
      `__member` and `__session` (via FKs in
      `notify_recipient.sql`). The notify loader must run
      after the member and session loaders. Verify the
      chosen loader location runs in the right order relative
      to `checkclasses` and `checkengine`.
- [ ] **The conftest and production loader should converge.**
      If they diverge (different file lists, different function
      loaders), the test environment will not match production.
      Document the single source of truth in SPEC.md.

## Phase 8 — Drop `*epoch` columns from views (codebase-wide follow-up PR)

Across the codebase, every view that exposes a `timestamptz`
column also exposes a matching `*epoch` column (a derived
`extract(epoch from ...)` value). The `*epoch` columns are
redundant: `timestamptz` is an absolute point in time
(internally UTC microseconds since the epoch), so any client
can compute the epoch value from the source `timestamptz`
in a single line. The `*epoch` columns add storage cost
(~8 bytes per row) and a "two columns, one fact" drift risk
without carrying information the source column doesn't
already carry.

The `*local` columns are different — they are
**per-row, context-dependent** (computed via
`timezone(currentmember.tz, ...)` using the current
session's `engine.__member.tz`) and are NOT redundant.
They are kept.

This phase is a separate, codebase-wide follow-up PR. It is
not part of the audit PR because:

- The convention is established across 6 view files, not
  notify-specific. Treating it as a notify-only change
  would create inconsistency.
- The audit PR is already meaningful scope. Mixing in a
  codebase-wide column convention change expands the diff
  and review surface unnecessarily.
- The cost of keeping `*epoch` is small (~8 bytes per row,
  no measurable CPU on read). The change can land later
  without time pressure.

### Phase 8 work items

- [ ] Drop the 19 `*epoch` columns across 6 view files:
  - [ ] `sql/notifyview.sql` — drop `datecreatedepoch`
        (line 23), `datedeliveredepoch` (line 24),
        `datereadepoch` (line 25).
  - [ ] `sql/bank_account_view.sql` — drop `createdepoch`
  - [ ] `sql/bank_transaction_view.sql` — drop `datepostedepoch`
  - [ ] `sql/bank_transfer_view.sql` — drop `requestedatepoch`, `respondedatepoch`
  - [ ] `sql/blurbview.sql` — drop `datecreatedepoch`
        (line 6), `dateupdatedepoch` (line 7),
        `dateapprovedepoch` (line 8).
  - [ ] `sql/invite.sql` — drop `datecreatedepoch`
        (line 68), `dateexpiresepoch` (line 69),
        `dateusedepoch` (line 70), `revokedepoch`
        (line 71).
  - [ ] `sql/memberview.sql` — drop `datecreatedepoch`
        (line 23), `lastloginepoch` (line 24),
        `dateupdatedepoch` (line 26). Lines 4-6 and 25
        are already commented out — leave them as-is.
  - [ ] `sql/session_view.sql` — drop `expiryepoch`
        (line 4), `lastactivityepoch` (line 5).
- [ ] Audit Python consumers for `*epoch` column references.
  Search for the column names across `py/src/bbsengine6/`
  and `py/tests/`. For each match, decide:
  - [ ] If the consumer is reading a `*epoch` value,
        switch to `extract(epoch from <source_timestamptz>)`
        in SQL, or compute the epoch in Python from the
        `timestamptz` value.
  - [ ] If the consumer is only displaying the column,
        remove the reference (the `timestamptz` value
        formats naturally in any client).
- [ ] Audit any templates, JS, or WWW code that may
  reference `*epoch` columns. (Quick grep across `js/`,
  `php/`, `smarty/`, `skin/`.)
- [ ] Run the test suite. Add a test that fails if any
  `*epoch` column reappears in a view (regex match on
  the `sql/*.sql` files in a CI check, or a runtime
  introspection test that queries the view schema and
  asserts no `*epoch` columns exist).
- [ ] Update SPEC.md and any docs that reference the
  removed columns.

### Phase 8 risks

- [ ] **External consumers** of the views (any code outside
      this repo that queries `engine.notify`, `engine.bank`,
      `engine.blurb`, `engine.invite`, `engine.member`,
      `engine.session` views directly) will break if they
      reference `*epoch` columns. Per the audit PR's
      "no BC concerns" stance, this is acceptable, but
      flag the change in release notes.
- [ ] **Some clients prefer epoch values** for cross-language
      serialization (a Unix timestamp is unambiguous across
      all timezones and language ecosystems). Removing the
      `*epoch` columns means those clients must compute the
      epoch themselves. This is a one-line operation in any
      language but is a real change for downstream code.
- [ ] **Performance**: `extract(epoch from ...)` is cheap
      on `timestamptz` (one division by 1e6), but
      computing it in the client requires either a
      `SELECT extract(epoch from ...)` in a subquery or
      post-processing the returned `timestamptz` in code.
      Both are fine in practice; the cost difference is
      negligible.
- [ ] **The "two columns, one fact" drift risk** is
      theoretical: nothing in the codebase writes to
      `*epoch` columns directly (they are derived in the
      view definition). They cannot drift from their
      source. The risk is purely conceptual, not a
      real bug.

## Risks / open items

- [ ] **FK change to `set null` is a behavior change.** Inner joins
      in the existing view naturally exclude orphan audit rows;
      confirmed desired behavior. Verify no query relies on
      `notify_id NOT NULL` (Phase 0 check).
- [ ] **`should_persist` clean break is API-breaking** for the
      `send()` and `NotifyIntegration.send()` public API, and
      is a schema-breaking change for `engine.__notify` (column
      drop) and `engine.notify` (view). External integrations
      that reference the column or pass the kwarg will break.
      Acceptable per user decision — no BC concerns.
- [ ] **No production notify schema loader today.** The helper
      function is loaded by tests but not by `stage_one`/
      `stage_zero`. Production deploys that run the bootstrap
      stages will not install the function until the
      **Phase 7 follow-up** (Re-enable notify tables in
      `startup`) lands. Known and accepted gap for this PR.
- [ ] **Helper runs on every `mark_delivered` call.** Marked
      `language sql immutable` so Postgres can cache repeated
      (existing, new_method) pairs. Non-issue for typical use.
- [ ] **Dropping `should_persist` mid-flight is risky** if any
      in-flight `send()` is mid-transaction when the schema
      changes. Standard DBA caveat for live schema changes.

## Out of scope

- Renaming `message_delivery` to `directmessage` or anything else.
- Adding a `WebSocketDeliveryHandler` for real-time per-user channel
  push.
- Re-enabling the production notify schema loader in
  `checkengine.py` (lines 110-115). Tracked in **Phase 7** of
  this file as a follow-up PR.
- Dropping the `*epoch` columns from views codebase-wide.
  Tracked in **Phase 8** of this file as a follow-up PR.
- Normalizing `sql/*.sql` filenames to use consistent
  underscore separators (e.g. `notifyview.sql` →
  `notify_view.sql`). Tracked in `TODO-sql-filenames.md`
  as a next-quarter refactor.
- Fixing the `notifyd` `recipient=` vs `recipients=` bug in
  `daemon/notification.py`.
- Renaming the `engine.notify` SQL view.
- GnuPG signing/encryption (see `TODO-notify-encryption.md`).
- Skipping the DB for ephemeral/private messages (privacy is
  delivered via encryption, not by skipping persistence).
- The "ephemeral" / "fire and forget" message feature (not
  currently requested).
