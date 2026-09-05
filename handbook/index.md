# BBSEngine Documentation

Welcome to the BBSEngine documentation handbook. This is the central
repository for all technical documentation, specifications, and
guides related to the BBSEngine project.

## Quick Navigation

### Getting Started

- [README](../README.md) — project overview, install, repo tree, quick start
- [Quick Start](QUICKSTART.md) — five-minute first-run
- [Deployment](DEPLOYMENT.md) — production deployment (Apache mod_proxy_uwsgi,
  mod_wsgi, gunicorn)
- [Handbook Serving](HANDBOOK_SERVING.md) — runtime conversion vs. pre-built
  static, the Flask app, `convert_markdown.py`
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

- [CSRF Protection](csrf/README.md) — CSRF security implementation
- [Phase 0-5 audit](../ROBUSTNESS_REVIEW.md) — every finding, every fix,
  every regression test

## Documentation Structure

```
handbook/
├── index.md                 # this file
├── QUICKSTART.md            # five-minute first-run
├── DEPLOYMENT.md            # Apache deployment paths
├── HANDBOOK_SERVING.md      # runtime vs. static handbook serving
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
├── csrf/                    # CSRF implementation docs (in scope)
└── migrations/              # *.sql migrations
```

## Development

The handbook is written in plain Markdown. Two ways to serve it under
Apache (see [HANDBOOK_SERVING.md](HANDBOOK_SERVING.md)):

```bash
# Runtime conversion (recommended)
cd handbook && python3 app.py        # dev only
# Production: mod_proxy_uwsgi → uwsgi → wsgi.py → app.py

# Pre-built static HTML
cd handbook && make convert           # writes <file>/index.html
```

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
