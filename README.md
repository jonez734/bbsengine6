# bbsengine6

> **Hybrid Python + PHP engine for the bbsengine.org / zoidtechnologies.com
> stack.**

`bbsengine6` is the engine that powers the BBS and the public web
sites. It is the lowest layer of the stack:

```
bbsengine6  ── engine library (Python + PHP), TUI primitives, DB, net
   ▲
bed         ── WebSocket daemon (auth, lifecycle, signals)
   ▲
zoid6       ── unified BBS module router
   ▲
casino /    ── individual BBS games
empyre / …
```

It is shipped in three forms:

1. **Python package** (`py/`) — the TUI primitives (`io/`),
   `module` registry, `database`, `message`, `net` (transport,
   packets, cryptography, WebSocket server), `bank`, `channel`,
   `session`, `member`, `password`, `services`, `backend`
   (database-staging wizard), `console` (admin CLI), and the SQL
   schema under `sql/`. Console-script entry: `bed`
   (`python -m bbsengine6.bed`).
2. **PHP web library** (`php/`) — the Smarty/HTML_QuickForm2 stack
   that renders `engine.bbsengine.org` and the per-site skins under
   `skin/`. Composer dep: `erusev/parsedown-extra`.
3. **Per-host prod sites** (`www/`) — `com/` and `org/` vhost
   trees that consume the PHP library and the Smarty plugin set.

> **See [`SPEC.md`](SPEC.md)** for the architecture spec, the
> module layout, and the cross-reference map into the handbook.
>
> **`handbook/`** is the user-facing manual (Apache deployment,
> production checklist, security, runtime conversion, router
> guide, JSON handling, net-layer guide, WebSocket/Web-realtime
> plans, per-module specs).
>
> **[`ROBUSTNESS_REVIEW.md`](ROBUSTNESS_REVIEW.md)** is the Phase 0-5
> audit (681 lines) — the canonical record of every Python and
> PHP bug found and fixed in 2026.
>
> **`CHANGELOG.md`** records user-visible changes. **`NOTES.md`** has
> pip-install / build instructions.

## Dependencies

### OS packages

- postgresql (server + libpq)
- python3 (3.9 – 3.12)
- php8.1
- apache2
- PEAR: `html_quickform2`, `Smarty`, `Log`

### PHP extensions

Required for database connectivity:

- `php-pdo`
- `php-pgsql`

### Python packages (runtime)

Declared in `py/pyproject.toml`:

- `argcomplete` — bash completion for the `bed` CLI
- `getdate-next` — datetime input parsing
- `markdown` — Python markdown lib
- `psycopg[binary,pool]` + `psycopg-pool` — PostgreSQL adapter + pool
- `python-dateutil`
- `websockets` — WebSocket transport for `net/transport.py`

### Python packages (dev)

- `pytest`
- `ruff`

### Install

```bash
# system packages (Debian/Ubuntu)
sudo apt-get install postgresql python3 python3-venv php8.1 apache2 \
    php-pdo php-pgsql libapache2-mod-php

# PEAR deps
sudo pear install html_quickform2

# Python package (editable for development)
cd py
pip install -e .

# Composer (PHP)
composer install
```

See `handbook/PRODUCTION_DEPLOYMENT.md`, `handbook/SETUP.md`,
`handbook/QUICKSTART.md`, and `handbook/APACHE_INTEGRATION.md`
for the full deployment sequence.

## What's in this repo

```
bbsengine6/
├── py/                          Python package + tests
│   ├── src/bbsengine6/          The installable package
│   │   ├── backend/             Stage-zero / stage-one DB check-routines
│   │   ├── bank/                Bank ledger + transfer API
│   │   ├── channel/             Channel pub/sub + WebSocket handlers
│   │   ├── console/             Admin CLI (createdb, memberapproval, …)
│   │   ├── ed/                  Terminal-based visual editor
│   │   ├── io/                  TUI primitives (echo, getch, inputstring,
│   │   │                        listbox, inputdate, …)
│   │   ├── member/              Member subsystem + WebSocket handler
│   │   ├── net/                 Network layer (transport, packet, crypto,
│   │   │                        WebSocket server, registry)
│   │   ├── password/            Pluggable password ciphers + storage
│   │   ├── services/            ChannelService, InviteService, MemberService
│   │   ├── session/             Generic SessionManager
│   │   ├── sql/                 ~50 schema files (schema, views, enums,
│   │   │                        SECURITY DEFINER functions,
│   │   │                        owned by the dedicated `zoid6` role)
│   │   ├── startup/             Bring-up + message subscription hook
│   │   ├── examples/            Demos + sample handlers
│   │   ├── tests/               net-layer integration tests
│   │   ├── bed.py               BED shim (delegates to the bed package)
│   │   ├── blurb.py  bottombar.py  common.py  conf.py
│   │   ├── database.py  editor.py  engine.py  folder.py  form.py
│   │   ├── getdate.py  group.py  input.py  inputdate.py  invite.py
│   │   ├── listbox.py  listboxcursor.py  md2tpl.py  menu.py
│   │   ├── message.py  module.py  password_hash.py  pgrole.py
│   │   ├── readfile.py  screen.py  sig.py  util.py
│   │   └── _version.py
│   └── tests/                   pytest suite (~50 modules)
│
├── php/                         PHP web library
│   ├── bootstrap.php            include-path setup
│   ├── database.php  engine.php  folder.php  page.php
│   ├── session.php  util.php  libmember.php  blurb.php  serve-md.php
│   ├── Form/                    HTML_QuickForm2 clone + captcha + rules
│   └── test_*.php               Ad-hoc PHP smoke tests
│
├── engine/                      Web-facing PHP entry points
│   ├── router.php               Handler-registry router
│   ├── login.php  logout.php  join.php  direct.php  simple.php
│   └── standalone.php  test.php  test2.php  serve-md.php
│
├── js/                          Browser-side scripts
│   ├── bbsengine6.js            Singleton (AJAX, CSRF, sanitization)
│   ├── jquery.smoothState.js    Vendored
│   ├── initsmoothstate.js  inittinymce.js  checkcurrentmemberid.js
│   ├── clock.js  redirectpage.js
│   └── topbar.js + topbar-{credits,greetings,join,loginlogout,nav}.js
│
├── skin/                        SCSS + Smarty templates
│   ├── scss/                    ~18 partials + vars/mixins/fonts
│   └── tmpl/                    ~40 templates (page, topbar*, blurb,
│                                sigs, breadcrumbs, notify, …)
│
├── smarty/                      Smarty plugins
│   ├── function.{apidocs,fa,repo,teos}.php
│   └── modifier.{ago,datestamp,filesize,fromnow,linkurl,markdown,
│                 parsedown,summarize,wpprop}.php
│
├── handbook/                    User-facing manual
│   ├── QUICKSTART.md  SETUP.md  PRODUCTION_DEPLOYMENT.md  SECURITY.md
│   ├── APACHE_INTEGRATION.md  APACHE_QUICK_COMPARISON.md  APACHE_UWSGI_SETUP.md
│   ├── RUNTIME_CONVERSION.md  ROUTER.md  JSON_HANDLING_GUIDE.md
│   ├── NET_LAYER_GUIDE.md  WEBSOCKET_REALTIME_PLAN.md  WEBSERVER_REALTIME_PLAN.md
│   ├── specs/                   Per-module design specs (see SPEC.md §9)
│   ├── migrations/              *.sql migrations
│   ├── csrf/                    CSRF markdown docs
│   └── NOTIFY_*.md              Notify migration planning
│
├── www/                         Per-host prod sites
│   ├── com/  org/               vhost trees (config, htaccess, php/, skin/)
│   └── bbsenginedotorg.sql      Production DB export
│
├── vendor/                      Composer-installed deps
│
├── tests/                       Top-level mixed-language tests
│   ├── unit/test_range.py
│   ├── integration/test_stage_one_checkengine.py
│   ├── test_member_transactions.py
│   └── test_*.php               Phase 3 PHP regression tests
│
├── Makefile                     Root build orchestrator
├── composer.json
├── composer.lock
├── README.md  SPEC.md  CHANGELOG.md  NOTES.md
├── ROBUSTNESS_REVIEW.md         Phase 0-5 audit
├── router.md  NET_LAYER.md  NET_LAYER_INDEX.md  FEATURES_NET_LAYER.md
├── module_registration.md  listbox_feature_multicolumn.md
├── map_member_flag.sql
└── TODO*.md                     Working notes (NOT specs)
```

## Quick start

```bash
# 1. Start the BBS in door-mode (Python terminal client)
bed

# 2. Start the WebSocket daemon for browser/CLI clients
bed --router zoid6.api.handler.MessageRouter \
    --config /etc/zoid6/bed.json

# 3. Render the public website (Apache + mod_php)
#    per www/{com,org}/htaccess-prod and config-prod.php

# 4. Stand up the database (idempotent)
python -m bbsengine6.startup
```

## License

GPL-2.0-or-later.
