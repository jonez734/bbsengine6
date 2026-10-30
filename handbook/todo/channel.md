# channel — remaining work

Spec: [`../specs/channel.md`](../specs/channel.md). This file tracks what is still open.
The rollout's completed phases are recorded in the spec's "Migration history".

## Operator follow-up

Moved from `TODO_BBSENGINE6_CHANNEL.md`. Both need a deployed database, so they are not
automated.

- [ ] Smoke test prod bootstrap: `python -m bbsengine6 startup --databasename zoid6dev --databaseuser $USER` (2026-10-09)
- [ ] Smoke test `con`: `python -m bbsengine6 con channel-list --databasename zoid6dev --databaseuser $USER --moniker alice` (2026-10-09)

## Pool lifetime

The pool lifetime rule (`database.context_pool` yields the process's cached pool and never closes
it) is in [`../../../specs/CONN_POOL_PATTERN.md`](../../../specs/CONN_POOL_PATTERN.md), under
"Pool Lifetime". bbsengine6 holds the rule in code as `context_pool`.

- [x] `bbsengine6.console.main` uses `context_pool` in place of `with getpool`.
- [x] The `demo_article2_givenyear`, `demo_listbox_cursor`, and `demo_listbox_masterdetail`
      scripts use `context_pool`.
- [x] `bbsengine6.message.service` calls `getpool(args).connection()` as a connection scope. It
      does not close the pool, so it already satisfies the rule and is unchanged.
- [ ] Other projects still wrap `getpool` in a `with` block. Tracked in each project's TODO, not
      here: `empyre`, `murdermotel`, `asimov`, `letteredolive` (done), `achilles`, and `teos`.

## Pre-existing test failures

Both fail on HEAD as well as on the working tree. Not caused by the pool work.

- [ ] `tests/test_console_member_add_edit.py::TestConfigureRoleSuperuserGuard::test_skips_privs_when_role_is_superuser`
- [ ] `tests/test_console_member_add_edit.py::TestConfigureRoleSuperuserGuard::test_runs_privs_when_role_is_not_superuser`

## Related

- [`../specs/channel.md`](../specs/channel.md) — the channel spec, including "Shout and
  announcements".
- [`menu_next.md`](menu_next.md) — menus, which announce through channels.
