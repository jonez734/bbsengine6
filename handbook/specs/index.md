# bbsengine6 Specifications — Index

> **Status:** canonical. Updated 2026-09-04.
> This directory is the single source of truth for subsystem
> design specs. The 2026-02-23 baseline (`architecture.md`,
> `decisions.md`, `dependencies.md`, `flows.md`) was rewritten
> for Phase 11; per-subsystem specs were promoted out of the
> handbook root and `handbook/specs/console/` was collapsed into
> a single [`console.md`](./console.md). The 10
> `BBSENGINE6_NOTIFYD_*.md` specs are HISTORICAL and were
> superseded by [`messaging.md`](./messaging.md).

## Architecture and process

- [architecture.md](./architecture.md) — layered architecture, package
  tree, domain organization, cross-layer flows, module system,
  diagrams
- [decisions.md](./decisions.md) — 15 architectural decision records
- [dependencies.md](./dependencies.md) — cross-package dependency
  matrix, layer edges, external dependencies, coupling notes
- [flows.md](./flows.md) — end-to-end workflows (bootstrap, login,
  message send, bank transfer, module execution, navigation, web
  request) with sequence diagrams

## Database and core

- [database.md](./database.md) — `bbsengine6.database` pool, DSN,
  contextvars role management, SECURITY DEFINER ownership, DB-API
  2.0 wrapper
- [util.md](./util.md) — display, dates, logging, input, ranges,
  password hashing, ANSI stripping, at-rest encryption
- [member.md](./member.md) — member subsystem + WebSocket handler,
  with notify-era recipient-validation retained
- [bestpractices.md](./bestpractices.md) — `io.echo` f-string rule
  and JSONB-at-the-database-boundary rule
- [auth-bank.md](./auth-bank.md) — WS login + bank authorization flow
- [pg-ident-auth.md](./pg-ident-auth.md) — per-member `l_<loginid>`
  / `m_<moniker>` roles, `pg_hba.conf` + `pg_ident.conf`, `[P]`
  psql credentials flow

## Messaging and net layer

- [messaging.md](./messaging.md) — `bbsengine6.message` Phase 11
  layered package (Service / DAL / State / Domain)
- [net-layer.md](./net-layer.md) — `bbsengine6.net` SMTP-style
  addressing, transport, packets, integration
- [channel.md](./channel.md) — `bbsengine6.channel` in-process
  pub/sub with announce-only enforcement; subscription + admin
  WebSocket handlers; `con channel` CLI; auto-seed algorithm;
  namespacing convention for module-owned daemon identities

## UI, modules, content

- [console.md](./console.md) — admin CLI: interactive menu,
  subcommand dispatch, member CRUD, member approval, psql role
  display, database creation
- [module.md](./module.md) — `bbsengine6.module` four-function
  contract, registry, signature validation, execution lifecycle
- [listbox.md](./listbox.md) — TUI listbox widget
- [blurb.md](./blurb.md) — content entity (filesystem-based)
- [folder.md](./folder.md) — ltree-backed folder hierarchy
- [bottombar.md](./bottombar.md) — fragment registry + Phase 5b
  wire-push plan

## Build / templating

- [md2tpl.md](./md2tpl.md) — Markdown → Smarty `.tmpl` converter

## Out of scope (HISTORICAL)

The following files were deleted as part of the 2026-09-04
consolidation. They are referenced only from the migration
changelogs:

- `BBSENGINE6_NOTIFYD_*.md` (10 files) — superseded by
  [`messaging.md`](./messaging.md); the notify subsystem was
  deleted 2026-07-22 (Phase 7 of `TODO-message-migration.md`).
- `notify.md`, `NOTIFY_MESSAGING.md`, `NET_LAYER_SPEC.md` —
  folded into [`messaging.md`](./messaging.md) /
  [`net-layer.md`](./net-layer.md).
- `web.md` (1342 lines) — folded into
  [`architecture.md`](./architecture.md) §3.8 "Web domain".
- `modules.md` (1678 lines) — folded into
  [`module.md`](./module.md).
- `BLURB_SPEC.md`, `FOLDER_SPEC.md` — canonical content kept in
  [`blurb.md`](./blurb.md) / [`folder.md`](./folder.md).
- All `console/*.md` files (13 files) — folded into
  [`console.md`](./console.md).
