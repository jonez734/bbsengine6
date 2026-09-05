# bbsengine6 Architecture

> Status: canonical. Last updated 2026-09-04.
> See [`../../SPEC.md`](../../SPEC.md) for the canonical package map and
> [`decisions.md`](./decisions.md) for the architectural decision records.

## Contents

1. [Layered Architecture](#1-layered-architecture)
2. [Package Tree](#2-package-tree)
3. [Domain Organization](#3-domain-organization)
4. [Cross-Layer Data Flow](#4-cross-layer-data-flow)
5. [Module System](#5-module-system)
6. [Visual Diagrams](#6-visual-diagrams)
7. [Cross-Cutting Concerns](#7-cross-cutting-concerns)

---

## 1. Layered Architecture

bbsengine6 is a **four-layer** system. The layering is the rationale
behind Decision 1 in [`decisions.md`](./decisions.md#decision-1-layered-architecture);
this file documents the layers themselves and where each package
lives in the source tree.

```
┌────────────────────────────────────────────────────────────┐
│  Presentation                                              │
│    io/, menu/, listbox.py, form.py, editor.py / ed/,       │
│    input.py, plus the PHP web layer (engine/, smarty/,     │
│    skin/, js/)                                            │
├────────────────────────────────────────────────────────────┤
│  Module System (cross-layer)                               │
│    module.py + every registered module                     │
├────────────────────────────────────────────────────────────┤
│  Business Logic                                            │
│    session/, member/, bank/, channel/, message/,           │
│    auth/, services/, blurb.py, folder.py, util.py,         │
│    invite.py, pgrole.py, password.py, password_cipher/,    │
│    editor.py, screen.py                                    │
├────────────────────────────────────────────────────────────┤
│  Data                                                      │
│    database.py, py/src/bbsengine6/sql/ (~50 schema files)  │
└────────────────────────────────────────────────────────────┘
```

The layer boundaries are enforced by the dependency direction:
lower layers never import upward. See [`dependencies.md`](./dependencies.md)
for the full matrix.

### 1.1 Data Layer

`bbsengine6.database` owns the PostgreSQL connection pool, DSN
construction, contextvars-based role management, and the SQL
helpers consumed by every higher layer. All SQL files in
`py/src/bbsengine6/sql/` are loaded through this module.

| Function | Purpose |
|----------|---------|
| `getpool(args, **kwargs)` | Return the shared `psycopg_pool.ConnectionPool`. |
| `connect(args, **kwargs)` | Build a one-shot connection (used by the `postgres` maintenance pool). |
| `query(sql, *params, **kwargs)` | Parameterised SELECT, returns `list[dict]`. |
| `insert(args, table, items, **kwargs)` | INSERT, returns new PK. |
| `update(args, table, pk, items, **kwargs)` | UPDATE by PK, supports explicit cascade for PK renames. |
| `delete(args, table, pk, **kwargs)` | DELETE by PK. |
| `upsert(args, table, items, **kwargs)` | INSERT … ON CONFLICT. |
| `transaction(conn, **kwargs)` | Context manager wrapper. |
| `execute(cur, query, *params)` | Low-level execute. |
| `executemany(cur, op, seq)` | Batch execute. |
| `getoid(args, typ, cur=None)` | Resolve a PostgreSQL custom type OID. |
| `convert_for_jsonb(v, *, wrap=True)` | Coerce Python values for JSONB columns. |
| `mogrifysql(cur, query, params)` | Render an SQL statement for debugging. |
| `parse_dsn(dsn)` / `make_dsn(args, **kwargs)` | DSN round-trip. |
| `set_current_role(role)` / `get_current_role()` | Contextvars role plumbing (consumed by `manage_role_privs.sql`). |
| `commit(args, conn=None, **kwargs)` / `rollback(args, conn=None, **kwargs)` | Transaction control. |
| `createrol(args, name, **kwargs)` / `rolexists(args, rolname)` | Role bootstrap helpers. |
| `schemaexists`, `tableexists`, `classexists`, `typeexists` | Idempotent DDL preflight. |

### 1.2 Business Logic Layer

Packages and modules grouped by responsibility:

| Package / Module | Role |
|------------------|------|
| `bbsengine6.session` | `SessionManager` (generic, in-memory WS session map) + DB-backed `start/read/write/garbagecollect` (consumed by CLI/web). `setcurrentsessionid` / `getcurrentsessionid` thread-local storage. |
| `bbsengine6.member` | `member.lib` (member CRUD, `checkpassword`, `setpassword`, `audit_password_hash`), `member.api.handler` (`MemberServiceHandler` invoked by bed). |
| `bbsengine6.bank` | `Account`, `Transaction`, `Transfer`, `BankService`, `bank.access`, `bank.api.handler` (`BankServiceHandler`). |
| `bbsengine6.channel` | Channel WebSocket plumbing; `channel.api.handler` (`ChannelServiceHandler`). |
| `bbsengine6.message` | Unified pub/sub with channel persistence. See [§2.4](#24-bbsengine6message-layered-package) for the layered layout. |
| `bbsengine6.auth` | `auth.access(args, op, **kwargs)` policy for bed's auth/reconnect/refresh/revoke ops. The bed handler decodes the HMAC token; `access` only inspects the decoded claims. |
| `bbsengine6.services` | Server-side handlers: `channel`, `invite`, `member`. |
| `bbsengine6.invite` | Generic invite-code DAL on `engine.__invite`. |
| `bbsengine6.pgrole` | Per-member PostgreSQL role provisioning (`ensure_login_role`, `sync_groups`). |
| `bbsengine6.password` | bcrypt single source of truth; mirrors PHP `bbsengine6\\password`. |
| `bbsengine6.password_cipher` | AES-256-GCM reversible encryption (ciphers `aes256gcm`, `plaintext`; storage `postgresql`). |
| `bbsengine6.blurb` | BBS blurb handler functions (legacy, retained for the PHP namespace). |
| `bbsengine6.folder` | ltree-backed folder hierarchy + visibility. |
| `bbsengine6.editor` | Lightweight editor invoked from the daemon (legacy path). |
| `bbsengine6.screen` | Shim to `bbsengine6.io.screen`. |
| `bbsengine6.util` | Terminal, text, range parsing, input helpers, `logentry`, `encryptpassword`. |
| `bbsengine6.menu` | Bordered terminal `Menu`/`Item` UI (legacy, kept). |
| `bbsengine6.menu_next` | New `MenuOption` dataclass + `register_menu_options` / `visible_options` registry. |
| `bbsengine6.bottombar` | Per-package `registry_for(name)` fragment registry consumed by `io.getch`. |
| `bbsengine6.common` | Logging setup, shared defaults. |
| `bbsengine6.conf` | `LOGGER_NAME = "bbsengine6"`. |

### 1.3 Presentation Layer

| Module / Package | Role |
|------------------|------|
| `bbsengine6.io` | TUI primitives (`echo`, `getch`, `getstr`, `input`, `inputstring`, `inputchoice`, `inputboolean`, `inputinteger`, `terminal`, `screen`, `palette`, `keymap`, `common`, `const`, `lib`, `output`, `util`). |
| `bbsengine6.listbox`, `listboxcursor` | Paginated TUI listbox. |
| `bbsengine6.form` | `FormItem` base class. |
| `bbsengine6.input`, `inputdate`, `getdate` | Date / datetime / email input wrappers. |
| `bbsengine6.ed` | Terminal visual editor: `common/{buffer,fileops,keys,state,ui}.py`, `line/`, `visual/`. |
| `bbsengine6.engine` | Stub (kept for BC). |
| PHP layer | `php/` (library), `engine/` (entry points), `smarty/` (plugins), `skin/` (SCSS + templates), `js/` (browser singleton + page-transition framework). See [`../../SPEC.md`](../../SPEC.md#4-php-web-layer). |

### 1.4 Module System

`bbsengine6.module` is the cross-layer plugin loader. It registers
modules, validates their `init`/`access`/`buildargs`/`main`
functions, runs them, and surfaces the result through
`runcallback`. See [§5](#5-module-system) for the contract.

---

## 2. Package Tree

The Python package lives at `py/src/bbsengine6/`. The list below is
verified against `ls py/src/bbsengine6/`.

### 2.1 Top-level modules

| Module | Role |
|--------|------|
| `__init__.py` | Module-registry re-exports (`register_module`, `get_module`, `MenuOption`, …). |
| `bed.py` | `bed` console script shim; delegates to the `bed` package. |
| `blurb.py` | BBS blurb handler functions. |
| `bottombar.py` | Fragment registry; `registry_for(name)` plumbing. |
| `common.py` | Logging setup, shared defaults. |
| `conf.py` | `LOGGER_NAME = "bbsengine6"`. |
| `database.py` | PostgreSQL pool, DSN, contextvars role management. |
| `editor.py` | Lightweight editor (legacy). |
| `engine.py` | Stub (kept for BC). |
| `folder.py` | ltree-backed folder hierarchy + visibility. |
| `form.py` | `FormItem` base class. |
| `getdate.py` | Date parsing (`python-dateutil`). |
| `input.py` / `inputdate.py` | Wrapper around `io.input`. |
| `invite.py` | Generic invite-code DAL on `engine.__invite`. |
| `listbox.py` / `listboxcursor.py` | Paginated TUI listbox widget. |
| `md2tpl.py` | Markdown → Smarty `.tmpl` converter. |
| `menu.py` | Legacy bordered TUI menu (`Menu` / `Item`). |
| `message.py` | Unified pub/sub with channel persistence. |
| `module.py` | Module-registry / plugin loader. |
| `password.py` | bcrypt (single source of truth); mirrors PHP `bbsengine6\\password`. |
| `pgrole.py` | Per-member PostgreSQL role provisioning. |
| `readfile.py` | Read file into `str` (optional ANSI escape). |
| `screen.py` | Shim → `bbsengine6.io.screen`. |
| `sig.py` | Sig / folder management (legacy alias). |
| `util.py` | Terminal, text, range parsing, input helpers. |

### 2.2 Sub-packages

| Sub-package | Role |
|-------------|------|
| `auth/` | `auth.access(args, op, **kwargs)` policy consumed by bed's `AuthService`. |
| `backend/` | `check*` routines that stage the database; `stage_zero` / `stage_one`; `lib`; wizard for spinning up a BBS DB. `checkpasswordformat` lands the `chk_member_password_bcrypt` CHECK constraint on every bootstrap. (The canonical home was created by the Phase 0 backend refactor; the old `TODO_BACKEND.md` was deleted as part of the 2026-09-04 consolidation.) |
| `bank/` | `account`, `bank`, `transaction`, `transfer`, plus `api/handler` (`BankServiceHandler`). |
| `channel/` | Channel WebSocket plumbing; `api/handler` (`ChannelServiceHandler`). |
| `console/` | Admin CLI: `createdatabase`, `member`, `memberapproval`, `showpgrole`, `session`, interactive menu. Console `check*` modules are thin shims over `backend/`. |
| `ed/` | Terminal visual editor (`common/{buffer,fileops,keys,state,ui}.py`, `line/`, `visual/`). |
| `io/` | TUI primitives — full module list in [§1.3](#13-presentation-layer). |
| `member/` | `lib`, `api/handler` — member subsystem. |
| `message/` | Layered pub/sub. See [§2.4](#24-bbsengine6message-layered-package). |
| `menu_next/` | New `MenuOption` registry (`MenuOption`, `register_menu_options`, `registered_options`, `visible_options`). |
| `net/` | `address`, `frame_address`, `frame_types`, `packet`, `packet_types`, `packet_codec`, `crypto`, `transport`, `tcp`, `udp`, `socket`, `router`, `defaultrouter`, `integration`, `registry`. |
| `password_cipher/` | AES-256-GCM strategy pattern (`manager`, `storage`, `config`, `cipher`); ciphers `aes256gcm`, `plaintext`; storage `postgresql`. |
| `services/` | `channel`, `invite`, `member` (server-side handlers). |
| `session/` | Generic `SessionManager` (consumed by bed); DB-backed session lifecycle. |
| `sql/` | ~50 schema files. Helpers are `SECURITY DEFINER` and owned by the dedicated `zoid6` role — see [`../../SPEC.md`](../../SPEC.md#5-sql-schema). |
| `startup/` | DB bring-up: `lib`, `main`, `__main__`, `message_subscription`. The `check*` modules here are thin shims over `backend/`. |
| `tests/` | Net-layer integration tests (`test_net_frames/`, plus `test_database_create.py`, `test_message_*.py`, `test_router_send_notification.py`, …). |
| `examples/` | Demos + sample handlers (`message_demo.py`, `notify_handler.py`). |

### 2.3 Cross-package entry point

`bbsengine6.startup.main` is the canonical bootstrap entry point
(see [decisions.md §12](./decisions.md#decision-12-startupmain-as-the-canonical-bootstrap-entry-point)). `startup.main`
loops through `("stage_zero", "stage_one", "engine", "bank")` via
`startup.lib.runmodule`, which delegates to `console.lib.runmodule`
with `package="bbsengine6.startup"`. `console.lib.runmodule` carries a
`package=` kwarg (default `"bbsengine6.console"`) so the same
mechanism serves both call sites. At the end of a successful boot,
`startup.main._maybe_subscribe_to_bed` opens a `BedConnection` and
subscribes to bed's message pushes (failure is non-fatal — `io.getch`
falls back to DB polling).

The thin console-script shim lives at `py/src/bbsengine6/bed.py`
and constructs a `BED` daemon from
`bbsengine6.net.WebSocketServer` + `bbsengine6.net.DefaultRouter`.

### 2.4 `bbsengine6.message` layered package

Added in Phase 11 (see [`../../TODO-message-migration.md`](../../TODO-message-migration.md)
and [`../../SPEC.md`](../../SPEC.md#11-layered-package-layout)):

| Layer | Module | Role |
|-------|--------|------|
| **Service** | `bbsengine6.message.service` | Business orchestration: enable/disable gate, rate-limit gating, blocking filter, recipient expansion, legacy `send` shim. |
| | `bbsengine6.message.lib` | Public re-export surface + `Message` / `MessageUrgency` dataclasses + DB helpers (`_make_args`, `_resolve_db`, `_coerce_urgency`). |
| **DAL** | `bbsengine6.message.dal.messages` | `engine.__message`, `engine.__message_recipient` I/O. |
| | `bbsengine6.message.dal.recipients` | `engine.__message_group_member` expansion. |
| | `bbsengine6.message.dal.groups` | `engine.__message_group[_member]` I/O. |
| | `bbsengine6.message.dal.blocking` | `engine.__message_block` I/O. |
| | `bbsengine6.message.dal.ratelimit` | `engine.__message_rate_limit`, `engine.__message_type` reads. |
| | `bbsengine6.message.dal.types` | `engine.__message_type` writes. |
| | `bbsengine6.message.dal._pool` | CONN_POOL_PATTERN helper + schema probes. |
| **State** | `bbsengine6.message.cache` | In-memory local unread counter (no DB). |
| **Domain** | `bbsengine6.message.templates` | `{var}` / `$var` template rendering. |
| | `bbsengine6.message.access` (in `__init__.py`) | Per-op authorization (subscribe / unsubscribe / list_pending). |

The DAL never imports `psycopg` directly; all DB plumbing goes
through `bbsengine6.database`. Async DAL is not yet provided — the
current implementation is fully sync via
`bbsengine6.database.getpool` / `pool.connection()`. See
[`../../SPEC.md`](../../SPEC.md#11-layered-package-layout).

---

## 3. Domain Organization

bbsengine6 can also be viewed as a collection of feature domains.
This section lists which packages participate in each domain; the
"depends on" column points at the layer they live in.

### 3.1 Session domain

- `bbsengine6.session` — `SessionManager` (in-memory WS map) +
  DB-backed `start/read/write/garbagecollect` lifecycle.
- `bbsengine6.database` — persistence.
- `bbsengine6.member` — member identity bound to a session.
- `bbsengine6.io` — logging.

Session record shape (DB row):

```python
{
  "id": UUID,
  "expiry": datetime,
  "lastactivity": datetime,
  "data": dict,            # JSONB column
  "ipaddress": str,
  "useragent": str,
  "moniker": str,
  "datecreated": datetime,
  "dateupdated": datetime,
}
```

### 3.2 Member domain

- `bbsengine6.member` — `member.lib` (CRUD, password verify, audit),
  `member.api.handler`.
- `bbsengine6.pgrole` — `ensure_login_role`, `sync_groups`.
- `bbsengine6.invite` — invite-code gating.
- `bbsengine6.password` — bcrypt single source of truth.
- `bbsengine6.password_cipher` — AES-256-GCM for IMAP/SMTP secrets.
- `bbsengine6.util` — `encryptpassword`, range/format helpers.

Member record shape:

```python
{
  "id": int,
  "loginid": str,
  "moniker": str,
  "email": str,
  "password": "$2b$06$...",     # bcrypt, CHECK constraint enforced
  "credits": int,
  "flags": dict,                # JSONB
  "attrs": dict,                # JSONB
  "ui": list[str],              # ARRAY of interface types
  "approved": bool,             # gates messageview reads
  "datecreated": datetime,
  "dateupdated": datetime,
  "lastlogin": datetime,
}
```

### 3.3 Message domain

The message domain has its own layered package — see
[§2.4](#24-bbsengine6message-layered-package). Briefly:

- `bbsengine6.message.service` — orchestration (`store_message`,
  `store_message_with_checks`, `send` legacy shim, `enable/disable`).
- `bbsengine6.message.dal.*` — Postgres I/O, one module per table family.
- `bbsengine6.message.cache` — local in-memory unread counter.
- `bbsengine6.message.templates` — pure rendering helpers.
- `bbsengine6.message.access` — per-op authorization.
- `bbsengine6.blurb` — legacy blurb surface kept for the PHP namespace.
- `bbsengine6.startup.message_subscription` — bed push subscription.

### 3.4 Bank domain

- `bbsengine6.bank` — `Account`, `Transaction`, `Transfer`,
  `BankService`.
- `bbsengine6.bank.access` — per-op policy (mirrors `auth.access`).
- `bbsengine6.bank.api.handler` — `BankServiceHandler` invoked by
  bed over the wire.

### 3.5 Channel domain

- `bbsengine6.channel` — channel WebSocket plumbing.
- `bbsengine6.services.channel` — server-side handler.
- `bbsengine6.net.transport` — TCP/UDP/WebSocket transport shared
  with `bed`.

### 3.6 Module / plugin domain

- `bbsengine6.module` — module-registry / plugin loader.
- `bbsengine6.menu_next` — `MenuOption` registry consumed by
  every game submodule (see `casino/SPEC.md` §3 for the consumer
  pattern).

### 3.7 Terminal I/O domain

- `bbsengine6.io` — TUI primitives.
- `bbsengine6.menu` / `menu_next` — menu widgets.
- `bbsengine6.listbox` / `listboxcursor` — paginated lists.
- `bbsengine6.form` — `FormItem`.
- `bbsengine6.input`, `inputdate`, `getdate` — input wrappers.
- `bbsengine6.ed` — terminal visual editor.
- `bbsengine6.bottombar` — per-package fragment registry.

### 3.8 Web domain

- `engine/*.php` — request entry points (`router.php`, `login.php`,
  `logout.php`, `join.php`, `direct.php`, `simple.php`,
  `standalone.php`, `test.php`, `test2.php`, `serve-md.php`).
- `php/` — library (`engine.php`, `database.php`, `session.php`,
  `libmember.php`, `blurb.php`, `page.php`, `util.php`, the
  `bbsengine6\\password` namespace, the `Form/` clone).
- `smarty/` — ~13 plugins (functions `apidocs`, `fa`, `repo`,
  `teos`; modifiers `ago`, `datestamp`, `filesize`, `fromnow`,
  `linkurl`, `markdown`, `parsedown`, `summarize`, `wpprop`).
- `skin/` — SCSS partials + Smarty templates.
- `js/` — `bbsengine6.js` singleton, vendored `jquery.smoothState.js`,
  per-widget init scripts.

### 3.9 Console / admin domain

- `bbsengine6.console` — admin CLI menu, `createdatabase`,
  `member`, `memberapproval`, `showpgrole`, `session`.
- `bbsengine6.backend` — DB staging wizard and the `check*`
  routines (`stage_zero`, `stage_one`, `engine`, `bank`,
  `checkroles`, `checkextensions`, `checkdatabase`,
  `checksuperuser`, `checkfunctions`, `checkclasses`, `checkflag`,
  `checkbank`, `checkloginid`, `checkwebserverrole`,
  `checkpasswordformat`, `checkzoid6role`, `checkzoid6owner`,
  `checkengine`).

---

## 4. Cross-Layer Data Flow

### 4.1 User login (terminal)

```
Terminal I/O (io.getch + io.inputstring)
   │ user enters moniker/password
   ▼
bbsengine6.member.checkpassword(args, loginid, password)
   │ SELECT password FROM engine.member WHERE loginid = ?
   │ verify locally (bcrypt $2[abxy]$); opportunistic rehash for legacy $1$
   ▼
bbsengine6.session.setcurrentsessionid(new_id)   # thread-local
bbsengine6.member.setthreadlocal_moniker(moniker)
   │
   ▼
io.echo("Welcome, …") + render menu
```

The corresponding web path is `engine/login.php` →
`bbsengine6\\password\\libpassword.verify_password` → DB UPDATE of
`lastlogin`. The `bbsengine6\\password` namespace mirrors Python's
`bbsengine6.password` (see [`../../CHANGELOG.md`](../../CHANGELOG.md)
"php: local bcrypt hashing, no PostgreSQL crypt() round-trip").

### 4.2 Message posting (terminal)

```
menu / listbox
   │ recipient selected
   ▼
editor / form
   │ subject + body captured
   ▼
bbsengine6.message.service.store_message_with_checks(...)
   │ rate-limit gating, blocking filter, recipient expansion
   ▼
bbsengine6.message.dal.messages.insert(...)
   │ INSERT INTO engine.__message / engine.__message_recipient
   ▼
bbsengine6.message.cache.incr_unread(recipient_moniker)
   │
   ▼
io.echo("Message posted!")
```

### 4.3 Web request

```
Browser → Apache → engine/router.php
   │ load Smarty plugin cache
   ▼
engine/login.php / engine/logout.php / page.php
   │ PHP namespace bbsengine6\\… resolves via SPL autoload
   │   (php/bootstrap.php sets include_path; class autoloader handles bbsengine6\\*)
   ▼
PHP database helper OR Python handler via WS (bed)
   │
   ▼
Smarty render + JS bundle (bbsengine6.js)
   │
   ▼
Browser
```

See [`../../SPEC.md`](../../SPEC.md#4-php-web-layer) for the PHP file
inventory.

---

## 5. Module System

### 5.1 Module contract

Every registered module exposes four entry points:

```python
def init(args, **kwargs) -> bool: ...
def access(args, op: str, **kwargs) -> bool: ...
def buildargs(args, **kwargs) -> argparse.Namespace | None: ...
def main(args, **kwargs) -> Any: ...
```

Modules are Python packages discovered via `importlib.import_module`
with the full module name. There is no fixed `bbsengine6/modules/`
directory — user plugins are typically installed in a separate
package (e.g. `mygame/`) on `PYTHONPATH`.

### 5.2 Loading flow

```
module.run(args, modulename, **kwargs)
  │
  ├─ check(modulename, op, **kwargs)
  │    ├─ importlib.reload() if args.debug is True
  │    ├─ importlib.import_module(modulename)
  │    ├─ Verify init(), access(), buildargs(), main() exist + callable
  │    ├─ _check_params() + inspect.signature() to validate signatures
  │    └─ m.access(args, op, **kwargs) — return False if not True
  │
  ├─ runcallback("modulename.init", **kwargs)
  │
  ├─ [if --help/-h in argv]
  │    ├─ runcallback("modulename.buildargs") → parser
  │    ├─ parser.print_help()
  │    └─ return True
  │
  ├─ runcallback("modulename.buildargs", **kwargs) → parser
  │    └─ parser.parse_args() (whitespace-stripped argv)
  │
  └─ runcallback("modulename.main", **kwargs)
       └─ Return result to caller
```

`validate_function()` is a standalone utility (uses
`get_type_hints()`) and is **not** part of the `check()` / `run()`
flow. Those use `_check_params()` + `inspect.signature()` instead.

### 5.3 Access policy modules

Several packages carry their own `access(args, op, **kwargs)`:

| Package | Recognised ops |
|---------|----------------|
| `bbsengine6.auth.access` | `login`, `reconnect`, `refresh`, `revoke`. The bed handler decodes the HMAC token and stuffs claims under `message["claims"]`; `access` only inspects decoded claims. |
| `bbsengine6.bank.access` | Domain verbs over a `BankServiceHandler` envelope. |
| `bbsengine6.message.access` | `subscribe`, `unsubscribe`, `list_pending`. |

These all follow the same shape: the per-op rules read
`session` (the live state) and `message` (the wire-shaped payload)
but never the raw token / secret. See
[`auth-bank.md`](./auth-bank.md) for the full pattern.

### 5.4 Module file structure

```
mymodule/
├── __init__.py          # init, access, buildargs, main
├── submodule1.py
├── submodule2.py
└── data/
    └── resource.sql
```

---

## 6. Visual Diagrams

### 6.1 System architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Web Browser / WebSocket client               │
└──────────┬────────────────────────────┬─────────────────────┘
           │ HTTP                       │ WS
           ▼                            ▼
┌──────────────────────────────────────────────────────────────┐
│  Apache + mod_php  ──►  php/  ──►  Smarty  ──►  skin/       │
│       ▲                                                       │
│       └────►  net/WebSocketServer  ◄────  bed AuthService      │
│                    ▲                                            │
│                    │     ┌────────────────────────────────┐     │
│              io/  │     │  bbsengine6 Python packages  │     │
│                    │     │  module, message, bank,      │     │
│                    ▼     │  member, channel, session,    │     │
│               database   │  auth, services, invite,      │     │
│                    ▲     │  pgrole, password_cipher,     │     │
│                    │     │  menu_next, bottombar, util   │     │
│                    │     └─────────────┬──────────────────┘     │
│                    │                   ▼                        │
│                    │     ┌────────────────────────────────┐     │
│                    └────►│  PostgreSQL (engine.* schema) │     │
│                          └────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 Layer dependencies

```
Layer 4: MODULE SYSTEM (module.py)
  │ Uses everything below
  │
Layer 3: PRESENTATION
  ├─ TUI:   io/, menu.py, listbox.py, form.py, editor.py, ed/, input.py
  └─ Web:   engine/, php/, smarty/, skin/, js/
  │ Depends on Layers 1-2
  │
Layer 2: BUSINESS LOGIC
  ├─ session/, member/, bank/, channel/, message/, auth/
  ├─ services/, invite.py, pgrole.py, password.py, password_cipher/
  ├─ blurb.py, folder.py, util.py, bottombar.py, menu_next/
  │ Depends on Layer 1
  │
Layer 1: DATA
  └─ database.py → psycopg / psycopg_pool → PostgreSQL
```

### 6.3 Request flow (terminal)

```
User Input
   │
   ▼
io.getch / io.inputstring
   │
   ▼
Presentation widget (menu / listbox / form / editor)
   │
   ▼
module.run(modulename)
   ├─ check(modulename, op)
   ├─ load / validate / init / access / buildargs
   └─ main(args)
        │
        ▼
Business logic (member / session / bank / message / …)
        │
        ▼
bbsengine6.database → psycopg → PostgreSQL
        │
        ▼
Back up through the layers
        │
        ▼
io.echo / io.screen
        │
        ▼
User's terminal
```

### 6.4 Request flow (web)

```
Browser HTTP / WS
   │
   ▼
Apache + mod_php / net.WebSocketServer
   │
   ▼
engine/router.php (PHP)            net.DefaultRouter (Python)
   │                                       │
   ▼                                       ▼
engine.php / login.php / …          bed.AuthService / bed.MessageService
   │                                       │
   ▼                                       ▼
PHP namespaces (bbsengine6\\password,   bbsengine6.auth.access
bbsengine6\\session, …)                bbsengine6.message.service
   │                                       │
   ▼                                       ▼
bbsengine6.database (shared)  ◄─────────────┘
   │
   ▼
PostgreSQL
```

---

## 7. Cross-Cutting Concerns

**Logging.** All layers write through `bbsengine6.util.logentry`,
which uses `conf.LOGGER_NAME = "bbsengine6"`. `io.echo(..., level="debug")`
suppresses output above the configured threshold.

**Error handling.** The module system catches and surfaces errors via
`runcallback`. The DAL/service layers raise; `bbsengine6.database`
raises `psycopg.Error`. The TUI layer prints a traceback via
`io.echo_traceback`.

**Access control.** Member flags are read via `member.lib.getflags`.
Per-op policy lives in `auth.access`, `bank.access`, and
`message.access`; the wire envelope is checked in the bed handler
*before* the access policy runs.

**State management.** Session id and moniker live in `threading.local`
inside `session.lib` and `member.lib`. JSONB columns
(`engine.member.flags`, `engine.member.attrs`, `engine.__session.data`)
hold flexible per-row state.

**Concurrency.** The data layer uses `psycopg_pool.ConnectionPool`
(default max 20). The DAL goes through `bbsengine6.database.getpool`
so every consumer shares the same pool.

---

*Architecture for bbsengine6.*
