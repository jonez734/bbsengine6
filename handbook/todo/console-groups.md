# console-groups — remaining work

Spec: [`../specs/console.md#member-management`](../specs/console.md#member-management). This file tracks
what is still open. Nothing in the console or the specs manages OS users or groups yet, so every item
below is new work.

## Goal

When the console saves a new or edited user, it creates or edits the Unix groups the user needs
(for example `letteredolive`, `zoid6`, `sysop`) and sets their membership from the form.

## Sysop rule

- **Sysop** means both: the database check `issysop` (the DB `sysop` role or `rolsuper`) AND membership
  in the OS group `sysop`.
- If the database cannot be reached, the answer is **deny**. A database outage never grants sysop.
- Only a sysop may save user or group changes. A non-sysop gets "sysop only." and no change, the same
  as the `K` action in `console/main.py`.

## Confirmation: once per save

- Every change in one save is listed in a single confirmation, shown before anything runs: user
  create or edit, group create, membership add or remove, and sysop-flag changes.
- The operator answers yes or no once. No means nothing in that save is applied.

## Sysop flag changes

- Granting the DB sysop flag asks whether to add the user to OS group `sysop`.
- Revoking the DB sysop flag asks whether to remove the user from OS group `sysop`.
- A "no" still applies the DB change. The console then shows a persistent warning on every
  sysop-related screen until the two agree. Rule (c) denies sysop in that state, so the mismatch is
  safe.

## Seeding the `sysop` group

- When the `sysop` group is first created, the console seeds its membership from current DB sysops.
- The seed list is part of the same once-per-save confirmation, one line per member it would add.

## Tasks

- [ ] Managed-groups list: the groups the console may create or edit (`letteredolive`, `zoid6`,
      `sysop`). Refuse any other group name.
- [ ] Sysop check: DB `issysop` AND OS `sysop` membership; deny on DB outage.
- [ ] One confirmation per save, listing every change before anything runs.
- [ ] Sysop-flag grant and revoke prompts, with the warn-and-keep-DB-change mismatch handling.
- [ ] Seed the `sysop` group from DB sysops on first creation, inside the same confirmation.
- [ ] Run group and user commands through sudo, never as root in the console process. The sudo rule
      lists only: `groupadd`, `groupmod`, `groupdel`, `gpasswd`, `useradd`, `usermod`.
- [ ] Tests with the OS commands mocked (no real group or user changes in CI):
      - non-sysop refused, nothing run
      - sysop declines the confirmation, nothing run
      - sysop confirms, sudo called with the exact command
      - DB unreachable denies sysop
      - sysop-flag revoke with a "no" keeps the DB change and shows the mismatch warning

## Operator follow-up

These need root and are not run by the console:

- [x] Create the `sysop` group. (No separate `letteredolive` group: access is through `zoid6`.)
- [x] Add `lo_test` to `zoid6` for read access to `/home/zoid6/venv`.
- [x] Set `/home/zoid6/venv` and `/home/zoid6/dist-wheels` to owner `zoid6`, group `zoid6`, mode `755`.
      Only `zoid6` writes. `jam` deploys with `sudo -u zoid6`, which prompts for a password.
- [ ] Install the sudoers drop-in for the group and user commands above.
- [ ] Symlink `/usr/local/bin/letteredolive` to `/home/zoid6/venv/bin/letteredolive`.
- [ ] Run `sudo -u zoid6 deploy letteredolive.venv` (or `make venv` as `zoid6`), then check a real `lo_test` login.

## Open questions

- **Managed-groups list:** config file, or database table editable in the console? A config file is
  auditable; a table is editable from the console. Pick one before the first task above.
- **Sudo scope:** should the console user be restricted to the exact argument forms (for example only
  `groupadd -- <name>`), or only the command names? Command names alone allow any argument.
