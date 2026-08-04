# bbsengine6 — Specification

> **Last updated:** 2026-08-03.
> **Status:** v1 stable for the Python engine, the PHP web layer, and
> the SQL schema. Phase 0-5 hardening (see
> [`ROBUSTNESS_REVIEW.md`](ROBUSTNESS_REVIEW.md)) shipped
> 2026-08-02.

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [Architecture](#2-architecture)
3. [Python package layout](#3-python-package-layout)
4. [PHP web layer](#4-php-web-layer)
5. [SQL schema](#5-sql-schema)
6. [Handbook cross-reference](#6-handbook-cross-reference)
7. [Phase 0-5 hardening summary](#7-phase-05-hardening-summary)
8. [Test layout](#8-test-layout)
9. [Authoritative file index](#9-authoritative-file-index)
10. [Out of scope](#10-out-of-scope)

---

## 1. Purpose & Scope

`bbsengine6` is the lowest layer of the bbsengine.org /
zoidtechnologies.com stack. It owns:

- The Python TUI primitives (`io/`).
- The Python database layer (`database.py`, `pgrole.py`,
  `password/`).
- The Python module-registry / plugin system (`module.py`).
- The Python message pub/sub with channel persistence (`message.py`,
  `channel/`).
- The Python network layer (`net/` — TCP/UDP/WebSocket transports,
  packets, crypto, server registry).
- The Python bank ledger (`bank/`).
- The Python session manager (`session/`).
- The Python member subsystem (`member/`).
- The Python console admin tools (`console/`).
- The Python backend staging wizard (`backend/`).
- The Python password hashing (`password_hash.py`, `password/`).
- The SQL schema under `sql/` (engines, member, bank, message,
  channel, …).
- The PHP web layer (Smarty/HTML_QuickForm2 under `php/` and
  `skin/`).
- The browser-side JS (`js/`, vendored jquery.smoothState.js,
  custom `bbsengine6.js`).

It does **not** own:

- Authentication wire-protocol (bed's `AuthService` does).
- Daemon lifecycle (bed does).
- Per-game logic (each game ships its own `MessageRouter`).

## 2. Architecture

```
                    ┌─────────────────────────────────────────┐
                    │ bbsengine6  (Python + PHP engine)        │
                    │                                         │
   browser  ───────►│  Apache + mod_php  ──►  php/  ──► Smarty│
                    │       ▲                                 │
   wscat    ───────►│       └────►  net/WebSocketServer        │
   door     ───────►│                 ▲     ▲                 │
                    │                 │     │                 │
                    │             io/    database              │
                    │                 │     │                 │
                    │           module  message                │
                    │                 │     │                 │
                    │                 ▼     ▼                 │
                    │           ┌───  bank / member / channel ─┤
                    │           │                            │
                    │           └───  session / password ────┤
                    │                                         │
                    │  SQL:  sql/*.sql  (engine, member,      │
                    │        bank, message, channel, …)      │
                    └─────────────────────────────────────────┘
                                    ▲
                                    │ (consumes)
                    ┌─────────────────────────────────────────┐
                    │ bed  (auth, lifecycle, services)        │
                    │     AuthService, MessageService,        │
                    │     BankService, FHS install            │
                    └─────────────────────────────────────────┘
                                    ▲
                                    │ (loads router)
                    ┌─────────────────────────────────────────┐
                    │ zoid6  (unified router)                 │
                    │     MessageRouter loads every enabled  │
                    │     module                              │
                    └─────────────────────────────────────────┘
                                    ▲
                    ┌─────────────────────────────────────────┐
                    │ casino / empyre / murdermotel / …       │
                    │     Per-game MessageRouter              │
                    └─────────────────────────────────────────┘
```

## 3. Python package layout

The package lives at `py/src/bbsengine6/`.

### 3.1 Top-level modules

| Module                       | Role                                               |
|------------------------------|----------------------------------------------------|
| `bed.py`                     | `bed` console script (thin shim that delegates to the bed package) |
| `blurb.py`                   | BBS blurb handler functions                        |
| `bottombar.py`               | Fragment-registry; per-package `registry_for(name)` plumbing |
| `common.py`                  | Logging setup, shared defaults                     |
| `conf.py`                    | `LOGGER_NAME = "bbsengine6"`                       |
| `database.py`                | PostgreSQL access — DSN, pool, contextvars role management |
| `editor.py`                  | Lightweight editor invoked from the daemon         |
| `engine.py`                  | (stub — kept for BC)                               |
| `folder.py`                  | ltree-backed folder hierarchy + visibility         |
| `form.py`                    | Tiny `FormItem` base class                         |
| `getdate.py`                 | Date parsing (python-dateutil)                     |
| `group.py`                   | Group management (legacy-ish)                      |
| `input.py`                   | Wrapper / shim around `io/input.py`                |
| `inputdate.py`               | Date input prompt                                  |
| `invite.py`                  | Generic invite-code DAL                            |
| `listbox.py`                 | Scrollable TUI listbox widget                      |
| `listboxcursor.py`           | Cursor helper for listbox                          |
| `md2tpl.py`                  | Markdown → Smarty `.tmpl` converter                |
| `menu.py`                    | TUI menu widget                                    |
| `message.py`                 | Unified pub/sub with channel persistence           |
| `module.py`                  | Module-registry / plugin loader                    |
| `password_hash.py`           | scrypt primary + SHA-256 legacy verify             |
| `pgrole.py`                  | Per-member PostgreSQL role provisioning            |
| `readfile.py`                | Read file into str (optional ANSI escape)          |
| `screen.py`                  | Shim → `bbsengine6.io.screen`                      |
| `sig.py`                     | Sig / folder management                            |
| `util.py`                    | Terminal, text, range parsing, input helpers       |

### 3.2 Sub-packages

| Sub-package                   | Role                                               |
|-------------------------------|----------------------------------------------------|
| `backend/`                    | `check*` routines that stage the database; `stage_zero` / `stage_one`; `lib`; wizard for spinning up a BBS DB |
| `bank/`                       | `account`, `bank`, `transaction`, `transfer`, plus `api/handler` (BankServiceHandler) |
| `channel/`                    | Channel WebSocket handlers                         |
| `console/`                    | Admin CLI: `createdatabase`, `member`, `memberapproval`, `showpgrole`, `session`, interactive menu |
| `ed/`                         | Terminal visual editor (`common/{buffer,fileops,keys,state,ui}.py`, `line/`, `visual/`) |
| `io/`                         | TUI primitives: `echo`, `getch`, `getstr`, `input`, `inputstring`, `inputchoice`, `inputboolean`, `inputinteger`, `terminal`, `screen`, `palette`, `keymap`, `common`, `const`, `lib`, `output`, `util` |
| `member/`                     | `lib`, `api/handler` — member subsystem            |
| `net/`                        | `address`, `frame_address`, `frame_types`, `packet`, `packet_types`, `packet_codec`, `crypto`, `transport`, `tcp`, `udp`, `socket`, `router`, `defaultrouter`, `integration`, `registry` |
| `password/`                   | Strategy pattern (`manager`, `storage`, `config`, `cipher`); ciphers `aes256gcm`, `plaintext`; storage `postgresql` |
| `services/`                   | `channel`, `invite`, `member` (server-side handlers) |
| `session/`                    | Generic `SessionManager` (consumed by bed)         |
| `sql/`                        | ~50 schema files (schema, views, enums, SECURITY DEFINER functions) |
| `startup/`                    | `lib`, `main`, `__main__`, `message_subscription`  |
| `examples/`                   | Demos + sample handlers (`message_demo.py`, `notify_handler.py`) |
| `tests/`                      | net-layer integration tests                        |

## 4. PHP web layer

### 4.1 Library (`php/`)

| File                  | Role                                          |
|-----------------------|-----------------------------------------------|
| `bootstrap.php`       | Sets the PHP `include_path`                   |
| `database.php`        | `bbsengine6\database\getDSN()`                |
| `engine.php`          | Global bootstrap (PEAR, Smarty, QuickForm2)   |
| `folder.php`          | `bbsengine6\folder` namespace                 |
| `blurb.php`           | Blurb handler functions                       |
| `libmember.php`       | `bbsengine6\libmember` helpers (checkflag, …) |
| `page.php`            | Page rendering helpers (permission-denied, markdown serve) |
| `serve-md.php`        | Serve .md files as plain text                 |
| `session.php`         | `bbsengine6\session` namespace                |
| `util.php`            | `bbsengine6\util\logentry`                    |
| `InputDate.php` `InputDateTime.php` `InputEmail.php` `InputUrl.php` | HTML_QuickForm2 `<input>` elements |
| `Form/`               | HTML_QuickForm2 clone + Captcha/{hCaptcha,Recaptcha,Turnstile,None,Factory} + DataSource/{Array,PdoDataSource} + Renderer/ArrayRenderer + Rule/{Callback,Equals,NonEmpty,Regex,Required,Rule,RuleRegistry} |

### 4.2 Entry points (`engine/`)

| File             | Role                                          |
|------------------|-----------------------------------------------|
| `router.php`     | Handler-registry router (`ROUTER_NEXT` / `ROUTER_STOP`) |
| `login.php`      | Member authentication                         |
| `logout.php`     | Member logout (destroys session)              |
| `join.php`       | Member registration                           |
| `direct.php` `simple.php` `standalone.php` `test.php` `test2.php` `serve-md.php` | Smaller entry points / smoke probes |

### 4.3 Smarty plugins (`smarty/`)

Functions: `apidocs`, `fa`, `repo`, `teos`. Modifiers: `ago`,
`datestamp`, `filesize`, `fromnow`, `linkurl`, `markdown`,
`parsedown`, `summarize`, `wpprop`.

### 4.4 Skin (`skin/`)

SCSS partials: `actions`, `animate`, `blurb`, `breadcrumbs`,
`clock`, `errormessage`, `form`, `lists`, `maturecontentwarning`,
`notify`, `pagefooter`, `pageheader`, `pagelinks`, `pagerinfo`,
`poweredby`, `redirectpage`, `tooltip`, `topbar`, `youarehere`,
plus `_bbsengine6mixins`, `_bbsengine6vars`, `_mixins`, `_vars`.

Templates: `actions`, `blurb-block`, `breadcrumbs`,
`cookienotice`, `errormessage`, `form`, `form-element`, `login`,
`nav`, `notify`, `pagefooter`, `pageheader`, `pagelinks`,
`page-markdown`, `page-markdown-sections`, `pagerinfo`,
`page-text`, `redirectpage`, `sig-detail`, `siglist`, `sigs`,
`sig-terse`, `socrates_post`, `topbar`, `topbar-cart`,
`topbar-choices`, `topbar-content`, `topbar-credits`,
`topbar-digitalclockflashingcolon`, `topbar-greetings`,
`topbar-join`, `topbar-loginlogout`, `topbar-middle`,
`topbar-sitedebug`, `youarehere`.

### 4.5 JavaScript (`js/`)

- `bbsengine6.js` — singleton (AJAX, CSRF, sanitization, interval
  management).
- `jquery.smoothState.js` — vendored page-transition framework.
- `initsmoothstate.js`, `inittinymce.js`, `checkcurrentmemberid.js`,
  `clock.js`, `redirectpage.js`, `topbar.js` + `topbar-{credits,
  greetings, join, loginlogout, nav}.js`.

## 5. SQL schema

`py/src/bbsengine6/sql/` holds the canonical schema. Highlights:

- `bbsengine6.sql` — schema, roles, extensions, GRANTs.
- `member.sql` — member table + supporting views / functions.
- `message.sql` — message + recipient + views.
- `channel.sql` — channel pub/sub.
- `bank.sql` — bank ledger.
- `createrol.sql`, `createschema.sql`, `extensions.sql`,
  `grants.sql` — DDL helpers (SECURITY DEFINER).
- `log.sql` — audit log.
- `ltree.sql` — ltree extension glue for folders.
- `manage_*_priv.sql` — privilege-management functions.
- `map_*.sql` — member-flag maps (`map_member_flag.sql` is the
  canonical example).
- `memberinet.sql`, `migrate_notify_to_message.sql` —
  notify→message migration glue.
- `getflags.sql`, `getsubblurbs.sql` — read helpers.
- A handful of `*_view.sql` files mirror tables for read paths.

`handbook/migrations/` carries per-feature migration scripts.

## 6. Handbook cross-reference

`handbook/` is the user-facing manual. Per-topic:

| Topic                                 | Handbook file                                       |
|---------------------------------------|-----------------------------------------------------|
| Quick start                           | `handbook/QUICKSTART.md`                            |
| Database setup                        | `handbook/SETUP.md`                                 |
| Production deployment                 | `handbook/PRODUCTION_DEPLOYMENT.md`                 |
| Security model                        | `handbook/SECURITY.md`                              |
| Apache integration                    | `handbook/APACHE_INTEGRATION.md` / `APACHE_QUICK_COMPARISON.md` / `APACHE_UWSGI_SETUP.md` |
| Runtime conversion (zoidweb4 → 6)     | `handbook/RUNTIME_CONVERSION.md`                    |
| PHP SPL autoload                      | `handbook/BBSENGINE6_PHP_SPL.md`                    |
| Router guide                          | `handbook/ROUTER.md`                                |
| JSON handling                         | `handbook/JSON_HANDLING_GUIDE.md`                   |
| Network layer guide                   | `handbook/NET_LAYER_GUIDE.md`                       |
| WebSocket realtime plan               | `handbook/WEBSOCKET_REALTIME_PLAN.md`               |
| Web-server realtime plan              | `handbook/WEBSERVER_REALTIME_PLAN.md`               |
| Notify migration (historical)         | `handbook/README_NOTIFY.md` + `NOTIFY_*.md`         |
| Per-module design specs               | `handbook/specs/*.md`                               |
| Per-module manual pages               | `handbook/{database,listbox,module,util,blurb_demo,…}.md` |

`handbook/specs/` (the design specs) holds the canonical reference
for each subsystem:

| Spec                                  | Subsystem                                         |
|---------------------------------------|---------------------------------------------------|
| `architecture.md`                     | System-wide architecture                           |
| `decisions.md`                        | Architectural Decision Records                     |
| `flows.md`                            | End-to-end message / request flows                |
| `dependencies.md`                     | Cross-package dependency map                      |
| `index.md`                            | Spec index                                         |
| `modules.md`                          | Module-registry contract                          |
| `module.md`                           | `module.py` contract                              |
| `member.md`                           | `member` subsystem (recipient validation, groups) |
| `database.md`                         | Database / contextvars / role plumbing            |
| `listbox.md`                          | TUI listbox widget contract                       |
| `md2tpl.md`                           | Markdown → Smarty template converter             |
| `blurb.md` `BLURB_SPEC.md` `FOLDER_SPEC.md` | Content / folder management                |
| `bottombar.md`                        | Per-package fragment registry                     |
| `console.md` `console/*.md`           | Admin CLI                                          |
| `BBSENGINE6_NOTIFYD_*.md` (10 files)  | **HISTORICAL** — notify subsystem (deleted)       |
| `NET_LAYER_SPEC.md`                   | Network layer                                      |
| `BESTPRACTICE.md`                     | Best practices                                     |

## 7. Phase 0-5 hardening summary

`ROBUSTNESS_REVIEW.md` records the 2026 Phase 0-5 audit in detail.
Headline counts (per the audit):

| Phase | Focus                                  | Findings |
|-------|----------------------------------------|----------|
| 0     | Unblock the test suite (schema, conftest, broken tests) | 4 |
| 1     | Fix Python runtime crashes             | 7 |
| 2     | Python security hardening              | 9 |
| 3     | PHP web layer hardening                | 14 |
| 4     | Python I/O / UI hardening              | 7 |
| 5     | Regression test infrastructure         | 2 |
|       | **Total**                              | **43**   |

The audit also adds Phase 5 regression tests (`py/tests/test_*.py`)
that pin every fix so future regressions are caught at PR time.

In addition to the Phase 0-5 audit, the recent work includes:

- The `notify → message` subsystem migration
  (`TODO-message-migration.md`, commit `a689c89`). The `notify`
  messaging subsystem was deleted; only three functions survive
  (`member.moniker_exists`, `member.group_exists`,
  `member.get_group_members`). See
  `CHANGELOG_NOTIFY_MESSAGING.md` for the historical changelog (now
  marked HISTORICAL — most of it is stale; only the surviving
  functions remain relevant).
- The `member.py` → `member/` package refactor (commit `ca3d680`).
- The generic `SessionManager` extraction into `session/`
  (commit `e281806`).
- The `bottombar` FragmentRegistry introduction (commits `d9ac821`,
  `e2b6e38`, `c2a6c02`).
- The per-package `registry_for(name)` plumbing (commit `d9ac821`).

## 8. Test layout

### 8.1 Python (`py/tests/`)

~50 pytest modules cover the engine. Highlights:

- `test_database_create.py`, `test_checkfunctions.py`,
  `test_manage_schema_priv.py`, `test_member_verify_found.py`,
  `test_member_update_with_flags.py` — DB plumbing.
- `test_message_*.py` (channel, lib, local_cache, phase1_gaps) —
  message subsystem regression.
- `test_router_send_notification.py`,
  `test_transport_send_to_remote.py` — net layer.
- `test_packet_bounds.py`, `test_packet_codec.py` — packet decoder
  hardening (Phase 2).
- `test_safe_path_containment.py` — `util.get_safe_path` (Phase 2).
- `test_password_hash_scrypt.py` — scrypt migration (Phase 2).
- `test_module_runcallback_no_eval.py` — `module.runcallback`
  (Phase 2).
- `test_echo_raw_lock.py`, `test_inputstring_filter_kwarg.py`,
  `test_inputdate_fallback.py`,
  `test_listbox_key_end_math.py`,
  `test_bottombar_truncate.py` — I/O / UI hardening (Phase 4).
- `test_startup_subpackage.py`,
  `test_startup_message_subscription.py`,
  `test_startup_message_subscription_module.py`,
  `test_startup_zoid6_missing.py` — startup refactor regressions.
- `test_net_frames/` — TCP/UDP/WebSocket integration tests.
- `test_indent.py`, `test_pluralize.py`, `test_template.py`,
  `test_tmpl.py`, `test_screen.py`, `test_terminal_title.py`,
  `test_inputchoice_key_f2.py`, `test_inputstring_enhancements.py`,
  `test_inputstring_key_f1.py`, `test_key_events.py`,
  `test_level_fail.py`, `test_module_package_kwarg.py`,
  `test_invite.py`, `test_group.py`,
  `test_check_notifications_args_pool.py`,
  `test_console_editflags.py`,
  `test_console_member_add_edit.py`, `test_channel_announce_only.py`,
  `test_folder_create.py`, `test_md2tpl.py`,
  `test_buildrec.py`, `test_ed.py`, `test_ed_integration.py`,
  `test_ed_line.py` — utility / widget coverage.

### 8.2 Top-level Python (`tests/`)

- `unit/test_range.py` — pure unit smoke.
- `integration/test_stage_one_checkengine.py` — stage-0/stage-1
  self-checks.
- `test_member_transactions.py` — single Python test.

### 8.3 PHP (`tests/`)

Phase 3 regression tests (created 2026-08-02):

- `test_autoExecute_safe_where.php`
- `test_csrf_protection.php`
- `test_libmember_checkflag_scalar.php`
- `test_linkurl_modes.php`
- `test_redact_secrets.php`
- `test_session_namespace_fix.php`
- `test_session_undefined_constants.php`
- `test_session_validate_format.php`
- `test_smarty_systemdsn_fixes.php`

## 9. Authoritative file index

| Path                                       | Role                                  |
|--------------------------------------------|---------------------------------------|
| `py/src/bbsengine6/__init__.py`            | Package init / module-registry re-exports |
| `py/src/bbsengine6/_version.py`            | Auto-stamped version                  |
| `py/src/bbsengine6/database.py`            | PostgreSQL pool, DSN, contextvars     |
| `py/src/bbsengine6/module.py`              | Module registry / plugin loader       |
| `py/src/bbsengine6/message.py`             | Pub/sub + channel persistence         |
| `py/src/bbsengine6/net/transport.py`       | WebSocket + TCP + UDP transport       |
| `py/src/bbsengine6/net/packet.py`          | Packet encoder / decoder              |
| `py/src/bbsengine6/net/router.py`          | Router (per-connection state)         |
| `py/src/bbsengine6/net/registry.py`        | Service registry                      |
| `py/src/bbsengine6/bank/api/handler.py`    | BankServiceHandler                    |
| `py/src/bbsengine6/member/api/handler.py`  | MemberServiceHandler                  |
| `py/src/bbsengine6/channel/api/handler.py` | ChannelServiceHandler                 |
| `py/src/bbsengine6/session/lib.py`        | Generic SessionManager                |
| `py/src/bbsengine6/startup/main.py`       | DB bring-up                           |
| `py/src/bbsengine6/password_hash.py`      | scrypt + SHA-256                      |
| `py/src/bbsengine6/sql/`                  | ~50 schema files                      |
| `py/pyproject.toml`                        | Python manifest (console_script `bed`) |
| `php/engine.php`                           | PHP global bootstrap                  |
| `php/session.php`                          | `bbsengine6\session` namespace        |
| `php/database.php`                         | DSN helper                            |
| `php/util.php`                             | `logentry()`                          |
| `php/Form/`                                | HTML_QuickForm2 clone                 |
| `engine/router.php`                        | Handler-registry router               |
| `engine/login.php`                         | Member login                          |
| `engine/logout.php`                        | Member logout                         |
| `smarty/`                                  | ~13 Smarty plugins                    |
| `skin/`                                    | SCSS + Smarty templates               |
| `js/bbsengine6.js`                         | Browser singleton                     |
| `js/jquery.smoothState.js`                 | Vendored page-transition framework    |
| `handbook/QUICKSTART.md`                   | Quick start                           |
| `handbook/SETUP.md`                        | DB setup                              |
| `handbook/PRODUCTION_DEPLOYMENT.md`        | Production deploy                     |
| `handbook/specs/`                          | Per-module design specs               |
| `ROBUSTNESS_REVIEW.md`                     | Phase 0-5 audit                       |
| `router.md` `NET_LAYER.md` `FEATURES_NET_LAYER.md` | Net-layer deep dives        |
| `module_registration.md`                   | Module-registry contract              |
| `listbox_feature_multicolumn.md`           | Listbox multi-column spec             |
| `composer.json`                            | PHP deps (`erusev/parsedown-extra`)   |
| `Makefile`                                 | Root build orchestrator               |

## 10. Out of scope

- **Authentication wire-protocol** — bed's `AuthService`.
- **Daemon lifecycle** — bed.
- **Per-game logic** — each game repo.
- **The notify messaging subsystem** — deleted; see
  `CHANGELOG_NOTIFY_MESSAGING.md` (HISTORICAL) for the changelog.
  The three surviving functions are in
  `py/src/bbsengine6/member/lib.py`.
- **The `BBSENGINE6_NOTIFYD_*.md` specs** — 10 files in
  `handbook/specs/` marked SUPERSEDED. They are kept for
  archaeology; do not link to them from new docs.
- **PHP framework refactor** — `php/zoid6.php` and the
  zoid6-vintage monoliths are frozen; new PHP code should follow
  the SPL autoload pattern documented in
  `handbook/BBSENGINE6_PHP_SPL.md`.
