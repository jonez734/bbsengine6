# BBSEngine Documentation

Welcome to the BBSEngine documentation handbook. This is the central
repository for all technical documentation, specifications, and
guides related to the BBSEngine project.

## Quick Navigation

### Getting Started

- [README](../README.md) — project overview, install, repo tree, quick start
- [Quick Start](QUICKSTART.md) — five-minute first-run
- [Security](SECURITY.md) — security overview and links to the Phase 0-5
  hardening audit
- [Router](ROUTER.md) — `/engine/router.php` operation and post-mortems

### Specifications

The canonical design specs live in [`specs/`](specs/). Each
subsystem has one document; ADRs and end-to-end flows have their
own:

- [Architecture](specs/architecture.md)
- [Decisions (ADRs)](specs/decisions.md)
- [Dependencies](specs/dependencies.md)
- [Flows](specs/flows.md) — end-to-end message / request flows
- [Database](specs/database.md) — pool, DSN, contextvars, SECURITY DEFINER
- [Util](specs/util.md) — display, dates, logging, input, ranges, passwords
- [Member](specs/member.md) — member subsystem + WebSocket handler
- [Auth → Bank](specs/auth-bank.md) — WS login + bank authorization flow
- [PG ident auth](specs/pg-ident-auth.md) — per-member `l_<loginid>` / `m_<moniker>` roles
- [Best practices](specs/bestpractices.md) — `io.echo` f-string rule, JSONB
  boundary
- [Messaging](specs/messaging.md) — `bbsengine6.message` (Phase 11 layered package)
- [Net layer](specs/net-layer.md) — `bbsengine6.net` (transport, packets, registry)
- [Console](specs/console.md) — admin CLI
- [Module](specs/module.md) — `bbsengine6.module` registry / plugin loader
- [Listbox](specs/listbox.md) — TUI listbox widget contract
- [Blurb](specs/blurb.md) — content entity
- [Folder](specs/folder.md) — ltree-backed folder hierarchy
- [Bottombar](specs/bottombar.md) — fragment registry
- [md2tpl](specs/md2tpl.md) — markdown → Smarty `.tmpl` converter

### Security

- [Phase 0-5 audit](../ROBUSTNESS_REVIEW.md) — every finding, every fix,
  every regression test

## Documentation Structure

```
handbook/
├── index.md                 # this file
├── QUICKSTART.md            # five-minute first-run
├── SECURITY.md              # security overview + audit links
├── ROUTER.md                # /engine/router.php operation
├── specs/                   # per-subsystem design specs
│   ├── index.md             # spec directory TOC
│   ├── architecture.md
│   ├── decisions.md
│   ├── dependencies.md
│   ├── flows.md
│   ├── database.md
│   ├── util.md
│   ├── member.md
│   ├── auth-bank.md
│   ├── pg-ident-auth.md
│   ├── bestpractices.md
│   ├── messaging.md
│   ├── net-layer.md
│   ├── console.md
│   ├── module.md
│   ├── listbox.md
│   ├── blurb.md
│   ├── folder.md
│   ├── bottombar.md
│   └── md2tpl.md
└── modules.md               # placeholder; content forthcoming
```

## Development

The handbook is written in plain Markdown. Chapters are rendered
at request time by `www/org/php/handbook.php` via the shared
`\bbsengine6\markdown\parseDocument` primitive (matching teos's
`teospath` path). The handbook `Makefile` `stage` target rsyncs
the `.md` tree to `WWWSTAGE/handbook/<v>/`, where Apache +
`mod_php` + the rewrite in `www/org/htaccess-prod` route every
`/handbook/<v>/...` request to `handbook.php` for read-time
rendering. The `make convert-tmpl` developer helper converts
chapters into Smarty `.tmpl` snippets for embedding inside
other templates (e.g. chapter summaries on the org-site
front page).

### Contributing

When adding new documentation:

1. Create Markdown files in the appropriate subdirectory.
2. Use clear, descriptive headings.
3. Include code examples where relevant.
4. Update the spec TOC in [`specs/index.md`](specs/index.md) and the
   links in [this file](index.md) when adding a new doc.

## Viewing Documentation

Documentation is best viewed through the web interface at:

- `https://bbsengine.org/handbook/`

Or read the Markdown files directly on GitHub.

## Contact & Support

For questions about documentation or to suggest improvements:

- Check existing documentation and specs first
- Review the architecture guides
- Consult the module documentation
- Open an issue on the project tracker
