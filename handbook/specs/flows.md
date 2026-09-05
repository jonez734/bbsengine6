# bbsengine6 End-to-End Flows

> Status: canonical. Last updated 2026-09-04.
> Trigger for every Python flow is `bbsengine6.startup.main` (see
> [decisions.md §12](./decisions.md#decision-12-startupmain-as-the-canonical-bootstrap-entry-point)
> for the bring-up sequence). The notify subsystem is gone; see
> [decisions.md §15](./decisions.md#decision-15-notify-subsystem-deletion).

## Contents

1. [High-Level Workflows](#1-high-level-workflows)
2. [Detailed Sequences](#2-detailed-sequences)
3. [State Transformations](#3-state-transformations)
4. [Data Structures at Each Layer](#4-data-structures-at-each-layer)
5. [Error Handling](#5-error-handling)

---

## 1. High-Level Workflows

### 1.1 Bootstrap

**Trigger.** `python -m bbsengine6.startup` (or the
`py/src/bbsengine6/bed.py` console-script entry point).

**Steps.**
1. `startup.lib.buildargs` parses argv.
2. `startup.main.main` opens the admin pool against the `postgres`
   maintenance DB and runs `stage_zero` (creates the target DB
   if missing).
3. `startup.main.main` selects the stage-one pool (caller-supplied
   if it points at the right dbname, otherwise a fresh target pool).
4. The loop runs `stage_one`, `engine`, `bank` via
   `startup.lib.runmodule(...)` →
   `console.lib.runmodule(..., package="bbsengine6.startup")` →
   `module.run(...)`. Each stage reads its `check*` siblings from
   `bbsengine6.backend`.
5. On failure: `conn.rollback()`, return `False`. On success:
   `conn.commit()`, return `True`.
6. `startup.main._maybe_subscribe_to_bed` opens a `BedConnection`
   and subscribes the current moniker to bed's message pushes.
   Failure is non-fatal — `io.getch` falls back to DB polling.

**Outcome.** `engine` schema + roles are present, the `bank` and
`message` tables exist, and (optionally) the local session is
subscribed to bed's push stream.

**Affected systems.**
- `bbsengine6.backend.*` (`stage_zero`, `stage_one`, `engine`,
  `bank`, the `check*` siblings).
- `bbsengine6.startup.{lib,main,message_subscription}`.
- `bbsengine6.console.lib.runmodule` (with `package=` kwarg).
- `bbsengine6.database` (admin pool + stage-one pool).
- PostgreSQL `engine` schema + roles.
- `bed.client.connection` (optional).

### 1.2 Login (terminal)

**Steps.**
1. The TUI displays a login prompt.
2. The user enters `moniker` and `password`.
3. `bbsengine6.member.checkpassword(args, loginid, password)` runs:
   one `SELECT password FROM engine.member WHERE loginid = ?`,
   verifies locally with `crypt(plaintext, stored)` (passlib
   bcrypt fallback). On success against a legacy `$1$` MD5-crypt
   hash, `bbsengine6.member.rehashpassword` rewrites the column to
   a fresh `$2b$06$`.
4. `bbsengine6.member.setthreadlocal_moniker(moniker)` binds the
   identity for the rest of the request.
5. `bbsengine6.session.setcurrentsessionid(uuid)` starts a DB-backed
   session row (`INSERT INTO engine.__session ...`).
6. `bbsengine6.pgrole.sync_groups(args, loginid)` reconciles the
   member's `m_<moniker>` PostgreSQL role group memberships.

**Outcome.** Active session, monotonic `bbsengine6.session.SessionManager`
allocation, fresh `__session` row, `lastlogin` updated.

**Affected systems.**
- `bbsengine6.io.{getch,inputstring,echo}`.
- `bbsengine6.member.lib.{checkpassword,rehashpassword,setthreadlocal_moniker}`.
- `bbsengine6.password` (bcrypt).
- `bbsengine6.session.lib` + `bbsengine6.session.SessionManager`.
- `bbsengine6.pgrole.sync_groups`.
- PostgreSQL `engine.member`, `engine.__session`,
  `engine.pgrole`.

### 1.3 Login (web)

**Trigger.** `POST /login.php` (or `engine/login.php`).

**Steps.**
1. `engine/login.php` reads the form payload.
2. `bbsengine6\libmember\checkpassword` (or the new
   `bbsengine6\\password\\libpassword.verify_password`) verifies
   locally against the bcrypt hash stored in `engine.member.password`.
3. On success, `engine.session` namespace sets the PHP session
   cookie (`PHPSESSID`) and writes an `engine.__session` row.
4. On a legacy `$1$` hash, `rehashpassword` rewrites the column.
5. PHP redirects to the post-login page; the page template is
   rendered by Smarty against `engine.member` flags.

**Outcome.** Authenticated PHP session, fresh `__session` row.

### 1.4 Authenticate on WebSocket (bed)

**Steps.**
1. Client opens a WebSocket to `bed`.
2. Client sends `{"type": "login", "moniker": "...", "password": "..."}`.
3. `bed/api/auth.py` runs the credential check (mirrors
   `bbsengine6.password`).
4. `bed/api/auth.py` decodes the HMAC, stuffs claims under
   `message["claims"]`, and calls `bbsengine6.auth.access(args,
   op="login", session=…, message=…)`. Op is `login` — always
   returns True (the credential provider decided).
5. `bed` issues a bearer token and registers a session in
   `bbsengine6.session.SessionManager` via `alloc_session_id` +
   `register_session`.

For subsequent ops:
- `reconnect`: `auth.access` requires either an unbound websocket
  or matching moniker.
- `refresh`: `auth.access` requires the same `session_id` claim
  as the live websocket.
- `revoke`: `auth.access` accepts any signature-valid token.

See [decisions.md §10](./decisions.md#decision-10-per-op-accessargs-op-kwargs-policy-modules)
and [`auth-bank.md`](./auth-bank.md).

### 1.5 Message flow (Phase 11 layered)

**Steps.**
1. Sender calls `bbsengine6.message.service.store_message_with_checks(...)`.
2. `service` runs the enable/disable gate (`is_enabled()`).
3. `service` resolves the database via `_resolve_db` (env → kwarg →
   args), normalises urgency via `_coerce_urgency`, and expands
   recipients via `bbsengine6.message.dal.recipients.resolve_recipients`.
4. `service` runs `_check_blocking_and_ratelimit`:
   - `dal.ratelimit.check_rate_limit` consumes the sender's quota
     against `engine.__message_rate_limit`.
   - For each recipient, `dal.blocking.is_blocked` checks
     `engine.__message_block`.
5. `service` calls `dal.messages.insert` against
   `engine.__message` + `engine.__message_recipient`.
6. `service` updates `bbsengine6.message.cache` (in-memory unread
   counter).
7. If bed is reachable, `bbsengine6.startup.message_subscription`
   (registered on the receiver's behalf at startup) fans the
   unread bump out via `bed`.

**Outcome.** `engine.__message` row + per-recipient rows;
`bbsengine6.message.cache` updated; bed pushes the unread bump.

**Affected systems.**
- `bbsengine6.message.{service,lib,cache,templates}`.
- `bbsengine6.message.dal.{messages,recipients,blocking,ratelimit}`.
- `bbsengine6.database.getpool`.
- `bbsengine6.startup.message_subscription`.
- `bed.MessageService`.
- PostgreSQL `engine.__message`, `engine.__message_recipient`,
  `engine.__message_block`, `engine.__message_rate_limit`,
  `engine.__message_group[_member]`.

### 1.6 Bank transfer

**Steps.**
1. Sender calls `BankService.transfer(args, from_account, to_account,
   amount)`.
2. `bbsengine6.bank.api.handler._handle_bank_transfer_request`:
   - Maps wire message `bank_transfer_request` → domain op
     `transfer` via `OP_MAP`.
   - Builds a `SessionState` adapter from `bbsengine6.session.SessionManager`.
   - Calls `bbsengine6.bank.access(args, op="transfer",
     session=…, message=…)`. Policy decides whether the live
     session owns the source account.
   - Calls `BankService.transfer` (TOCTOU-safe: SELECT … FOR UPDATE
     on both account rows, debit + credit + INSERT into
     `engine.__transaction` in one transaction).
   - Returns the JSON-safe row dict.

**Outcome.** Debited + credited accounts; new `engine.__transaction`
row; both account rows locked and committed atomically.

### 1.7 Module / menu execution

**Steps.**
1. Menu (or CLI) invokes `module.run(args, modulename, **kwargs)`.
2. `module.check` verifies the module exposes
   `init`/`access`/`buildargs`/`main` and that
   `modulename.access(args, op="run", …)` returns True.
3. `module.runcallback("modulename.init", …)` runs one-time setup.
4. If `--help` / `-h` is in argv: `module.runcallback("modulename.buildargs")`
   builds the parser, prints help, returns True.
5. `module.runcallback("modulename.buildargs", …)` parses argv.
6. `module.runcallback("modulename.main", …)` runs the feature and
   returns the result.
7. The menu (`bbsengine6.menu` or `bbsengine6.menu_next`) renders
   the next state via `bbsengine6.io.{echo,screen}`.

**Outcome.** Feature executed, result surfaced through the
widget, ready for the next user action.

### 1.8 Navigation / menu flow

**Steps.**
1. `bbsengine6.menu.Menu.display` (or `menu_next.registered_options` /
   `visible_options`) renders available items.
2. `io.getch` reads the next keystroke.
3. `menu.Menu.handle` updates the cursor; the new frame is rendered
   via `io.echo` + `io.screen.setcursor`.
4. On ENTER, `menu.Menu.run` returns the selected `Item`. The
   `requires` predicate is evaluated; if it fails, the menu is
   re-displayed with a warning.
5. The resolved module is dispatched via `module.run`.

**Outcome.** Module dispatched, result threaded back to the menu
loop.

### 1.9 Web request

**Steps.**
1. Browser sends HTTP request to Apache.
2. Apache routes to a `engine/*.php` entry point.
3. `php/engine.php` boots Smarty, PEAR Log, QuickForm2.
4. The entry-point PHP loads the page (`engine/page.php` helpers,
   `bbsengine6\\session`, `bbsengine6\\database`, `bbsengine6\\password`).
5. Smarty renders the page with data from `bbsengine6.libmember`.
6. JS bundle (`js/bbsengine6.js` + per-widget init scripts) ships
   in the HTML; jQuery + smoothState take over the DOM.
7. Browser executes client-side logic; AJAX calls go back to
   `engine/*.php`.

**Outcome.** HTML + JS rendered; user interacts.

---

## 2. Detailed Sequences

### 2.1 Bootstrap (`bbsengine6.startup.main`)

```
OPERATOR                        startup.main                 backend                  console.lib        module.run       database
  │                                  │                          │                        │                  │                │
  │ python -m bbsengine6.startup     │                          │                        │                  │                │
  ├─────────────────────────────────>│                          │                        │                  │                │
  │                                  ├─ buildargs / parse argv  │                        │                  │                │
  │                                  │                          │                        │                  │                │
  │                                  ├─ admin pool against     │                        │                  │                │
  │                                  │  'postgres'              │                        │                  │                │
  │                                  ├─────────────────────────────  database.getpool    ───────────────────>│                │
  │                                  │                          │                        │                  │                │
  │                                  ├─ stage_zero ────────────>│                        │                  │                │
  │                                  │  via runmodule ─────────>│                        │                  │                │
  │                                  │                          ├────────────────────────>  module.run ───>  │
  │                                  │                          │  backend.stage_zero     │                  │  CREATE DATABASE│
  │                                  │                          │<────────────────────────────────────────────────│
  │                                  │                          │                        │                  │                │
  │                                  ├─ select stage-one pool   │                        │                  │                │
  │                                  ├─ stage_one ─────────────>│                        │                  │                │
  │                                  ├─────────────────────────────  ...                  ───────────────────>│                │
  │                                  ├─ engine ────────────────>│                        │                  │  schema.sql     │
  │                                  ├─────────────────────────────  ...                  ───────────────────>│  (engine.auth.z│
  │                                  │                          │                        │                  │   oid6)         │
  │                                  ├─ bank ──────────────────>│                        │                  │  bank.sql       │
  │                                  │                          │                        │                  │                │
  │                                  ├─ commit / rollback       │                        │                  │                │
  │                                  ├─────────────────────────────  conn.commit()       ───────────────────>│                │
  │                                  │                          │                        │                  │                │
  │                                  ├─ _maybe_subscribe_to_bed│                        │                  │                │
  │                                  ├─ (optional) BedConnection.subscribe  ───────────────────────────────────────>  bed (WS) │
  │                                  │                          │                        │                  │                │
  │<────────────── ready ───────────│                          │                        │                  │                │
```

**State after bootstrap.** `engine` schema owned by `zoid6`;
helper functions owned by `zoid6`; `engine.member`,
`engine.__session`, `engine.__message*`, `engine.__bank_*` populated
by their respective schema files; (optional) bed push subscription
active for the current session.

### 2.2 WebSocket login (`bed` + `bbsengine6.auth.access`)

```
CLIENT                          bed/api/auth.py            bbsengine6.auth.access    bbsengine6.password       bbsengine6.session
  │                                  │                            │                            │                          │
  │ {"type":"login",                 │                            │                            │                          │
  │  "moniker":"alice",              │                            │                            │                          │
  │  "password":"…"}                 │                            │                            │                          │
  ├─────────────────────────────────>│                            │                            │                          │
  │                                  │                            │                            │                          │
  │                                  ├─ credential check ─────────────────────────────────────────>│                          │
  │                                  │   SELECT password FROM     │                            │  crypt() verify          │
  │                                  │   engine.member WHERE      │                            │  (passlib bcrypt fallback│
  │                                  │   loginid = ?              │                            │   on healthy $2[abxy]$) │
  │                                  │<──────────────────────────────────────────────────────────│                          │
  │                                  │                            │                            │                          │
  │                                  ├─ mint HMAC token          │                            │                          │
  │                                  │                            │                            │                          │
  │                                  ├─ access(args, op="login", │                            │                          │
  │                                  │           session=None,    │                            │                          │
  │                                  │           message=…)        │                            │                          │
  │                                  ├───────────────────────────>│                            │                          │
  │                                  │                            ├─ op=="login" → True       │                          │
  │                                  │<───────────────────────────│                            │                          │
  │                                  │                            │                            │                          │
  │                                  ├─ alloc_session_id() ───────────────────────────────────────────────────────────>  │
  │                                  ├─ register_session(         │                            │                          │
  │                                  │     id, moniker, is_sysop)│                            │                          │
  │                                  ├──────────────────────────────────────────────────────────────────────────────────>  │
  │                                  │                            │                            │                          │
  │ {"type":"login_ok",              │                            │                            │                          │
  │  "token":"…"}                    │                            │                            │                          │
  │<─────────────────────────────────│                            │                            │                          │
```

**State after WS login.** `SessionManager._sessions` has one entry;
bearer token issued; client holds the token for subsequent messages.

### 2.3 Message send (Phase 11 layered)

```
SENDER                     message.service      message.dal.ratelimit   message.dal.blocking   message.dal.recipients   message.dal.messages    database                message.cache
  │                             │                       │                       │                       │                       │                       │                       │
  │ store_message_with_checks   │                       │                       │                       │                       │                       │                       │
  ├────────────────────────────>│                       │                       │                       │                       │                       │                       │
  │                             ├─ is_enabled() → True  │                       │                       │                       │                       │                       │
  │                             ├─ _resolve_db          │                       │                       │                       │                       │                       │
  │                             ├─ _coerce_urgency      │                       │                       │                       │                       │                       │
  │                             ├─ resolve_recipients ────────────────────────────────────────────────────────────────────>│                       │                       │
  │                             │                       │                       │                       │  expand groups         │                       │                       │
  │                             │<────────────────────────────────────────────────────────────────────────────────────────  │                       │                       │
  │                             │                       │                       │                       │                       │                       │                       │
  │                             ├─ check_rate_limit ───>│                       │                       │                       │                       │                       │
  │                             │                       ├─ SELECT … FROM engine.__message_rate_limit                                │                       │                       │
  │                             │                       ├───────────────────────  database.getpool / pool.connection ────────────────────────────>│                       │
  │                             │                       │<─ rows ───────────────────────────────────────────────────────────────────│                       │
  │                             │<─ allowed, remaining ─│                       │                       │                       │                       │                       │
  │                             │                       │                       │                       │                       │                       │                       │
  │                             ├─ for each recipient:  │                       │                       │                       │                       │                       │
  │                             │   is_blocked ───────────────────────────────────────────>│                       │                       │                       │
  │                             │<────────────────────────── blocked? ────────────│                       │                       │                       │
  │                             │                       │                       │                       │                       │                       │                       │
  │                             ├─ insert ────────────────────────────────────────────────────────────────────────────────────────────────────>│                       │
  │                             │                       │                       │                       │                       ├─ INSERT engine.__message / engine.__message_recipient  ───────>│
  │                             │<──────────────────────────────────────────────── message_id ──────────────────────────────────────────────────────────────────────│
  │                             │                       │                       │                       │                       │                       │                       │
  │                             ├─ cache.incr_unread ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────>│
  │                             │<──────────────────────────────────────────── ok ──────────────────────────────────────────────────────────────────────────────────────────│
  │                             │                       │                       │                       │                       │                       │                       │
  │<── {message_id, …} ────────│                       │                       │                       │                       │                       │                       │
```

**State after send.** `engine.__message` row + per-recipient rows;
`message.cache` bumped for each recipient; (if bed is reachable)
push events fired to each recipient.

### 2.4 Module execution

```
CALLER                      module                database        io.echo                  MODULE
  │                          │                       │              │                       │
  │ module.run(args, "x")    │                       │              │                       │
  ├─────────────────────────>│                       │              │                       │
  │                          ├─ check("x","run")     │              │                       │
  │                          ├─ importlib.reload() (if debug)      │                       │
  │                          ├─ importlib.import_module("x")       │                       │
  │                          ├─ verify init/access/buildargs/main callable                │
  │                          ├─ inspect.signature check             │                       │
  │                          ├─ x.access(args, op="run", **kw)      │                       │
  │                          ├─────────────────────>│ (access data)│                       │
  │                          │<─ access allowed ───│              │                       │
  │                          ├─ runcallback("x.init")              │                       │
  │                          ├───────────────────────────────────────────────────────────────────>  init(args)
  │                          │<──────────────────────────────────────────────────────────────────  ok
  │                          ├─ if --help in argv:                  │                       │
  │                          │   buildargs → parser.print_help     │                       │
  │                          │   return True                        │                       │
  │                          ├─ runcallback("x.buildargs")         │                       │
  │                          ├───────────────────────────────────────────────────────────────────>  buildargs(args)
  │                          │<────────────────────────────────────  parser
  │                          ├─ parser.parse_args()                 │                       │
  │                          ├─ runcallback("x.main", args)        │                       │
  │                          ├───────────────────────────────────────────────────────────────────>  main(args)
  │                          │<────────────────────────────────────  result
  │                          │   try/except wraps: on error →      │                       │
  │                          │     io.echo_traceback(e)             │                       │
  │<─ result ───────────────│                       │              │                       │
```

**Key points.**
- Access is checked before import; import is checked before run.
- `_check_params` + `inspect.signature` validate signatures
  (the standalone `validate_function` is *not* part of this flow).
- Errors are caught and rendered via `io.echo_traceback`; the
  loader returns `None` or an error sentinel so the menu can
  display gracefully.

### 2.5 Navigation

```
USER                  io.getch                menu.Menu             module                  MODULE
  │                     │                       │                    │                       │
  │ arrow key           │                       │                    │                       │
  ├────────────────────>│                       │                    │                       │
  │                     ├─ read key ──> key code│                    │                       │
  │                     │                       ├─ handle(key)       │                       │
  │                     │                       ├─ update cursor     │                       │
  │                     │                       ├─ io.screen.setcursor(row, col)
  │                     │                       ├─ io.echo(frame)    │                       │
  │                     │                       │                    │                       │
  │ ENTER               │                       │                    │                       │
  ├────────────────────>│                       │                    │                       │
  │                     ├─ key code ───────────>│                    │                       │
  │                     │                       ├─ selected = current│                       │
  │                     │                       ├─ if item.requires:│                       │
  │                     │                       │   eval predicate   │                       │
  │                     │                       ├─ module.run(args,  │                       │
  │                     │                       │   item.module)     │                       │
  │                     │                       ├───────────────────>│                       │
  │                     │                       │                    ├─ …                    │
  │                     │                       │<────────────────────  result                │
  │                     │                       ├─ io.echo(result)   │                       │
```

**Outcome.** Selected feature ran; menu loop resumes.

---

## 3. State Transformations

### 3.1 Before login

```
Session (thread-local):
  currentsessionid = None
  currentmoniker = None

SessionManager:
  _sessions = {}   # in-memory WS map
  _id_counter: not started

Database:
  engine.__session: empty (or expired rows only)
  engine.member:   lastlogin NULL for current user
```

### 3.2 After login

```
Session (thread-local):
  currentsessionid = <uuid>
  currentmoniker = "alice"

SessionManager:
  _sessions[<id>] = {"moniker": "alice", "is_sysop": False}

Database:
  engine.__session: new row with session uuid
  engine.member: lastlogin = now()
  engine.pgrole: m_alice login role granted group memberships
```

### 3.3 During message send

```
Database (single transaction):
  engine.__message:               new row
  engine.__message_recipient:     new row per recipient (after rate-limit + block + expansion)

Cache:
  message.cache[recipient] += 1   (in-memory)
```

### 3.4 After module execution

```
Module state:
  current_module = "menu_next.<registrar>"
  menu cursor at the resolved option

User:
  sees next prompt / output frame
```

---

## 4. Data Structures at Each Layer

### 4.1 Data Layer (PostgreSQL)

**Session (`engine.__session`):**

```sql
CREATE TABLE engine.__session (
  id            UUID PRIMARY KEY,
  expiry        TIMESTAMP NOT NULL,
  lastactivity  TIMESTAMP,
  data          JSONB,
  ipaddress     INET,
  useragent     TEXT,
  datecreated   TIMESTAMP DEFAULT NOW(),
  dateupdated   TIMESTAMP DEFAULT NOW(),
  moniker       VARCHAR(32)
);
```

**Member (`engine.member`):**

```sql
CREATE TABLE engine.member (
  id            SERIAL PRIMARY KEY,
  loginid       VARCHAR(32) UNIQUE,
  moniker       VARCHAR(32),
  email         VARCHAR(254),
  password      VARCHAR(255),                 -- bcrypt $2[abxy]$06$…
  credits       INT DEFAULT 100,
  flags         JSONB DEFAULT '{}',
  attrs         JSONB DEFAULT '{}',
  ui            TEXT[],                       -- ARRAY of interface types
  approved      BOOLEAN NOT NULL DEFAULT FALSE,
  datecreated   TIMESTAMP DEFAULT NOW(),
  dateupdated   TIMESTAMP,
  lastlogin     TIMESTAMP,
  CONSTRAINT chk_member_password_bcrypt
    CHECK (password ~ '^\$2[abxy]\$' AND length(password) = 60)
);
```

**Message (`engine.__message` + `engine.__message_recipient`):**

```sql
CREATE TABLE engine.__message (
  id           SERIAL PRIMARY KEY,
  sender_moniker VARCHAR(32),
  channel      VARCHAR(64) NOT NULL,
  urgency      VARCHAR(16) NOT NULL DEFAULT 'ROUTINE',
  content      TEXT,
  data         JSONB DEFAULT '{}',
  created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE engine.__message_recipient (
  message_id   INT NOT NULL REFERENCES engine.__message(id) ON DELETE CASCADE,
  recipient_moniker VARCHAR(32) NOT NULL,
  read_at      TIMESTAMP,
  PRIMARY KEY (message_id, recipient_moniker)
);
```

The full schema inventory is in
[`../SPEC.md`](../SPEC.md#5-sql-schema).

### 4.2 Business Logic (Python dicts)

**Session row** (mirrors `engine.__session`):

```python
{
  "id": UUID,
  "expiry": datetime,
  "lastactivity": datetime,
  "data": {"preferences": {"colormode": "ansi", "width": 80}},
  "ipaddress": "192.168.1.1",
  "useragent": "Terminal v1.0",
  "moniker": "alice",
  "datecreated": datetime,
  "dateupdated": datetime,
}
```

**Member row**:

```python
{
  "id": 123,
  "loginid": "alice",
  "moniker": "alice",
  "email": "alice@example.com",
  "password": "$2b$06$...",
  "credits": 500,
  "flags": {"admin": False, "moderator": False, "verified": True},
  "attrs": {"signature": "Alice", "bio": "..."},
  "ui": ["term", "web"],
  "approved": True,
  "datecreated": datetime,
  "dateupdated": datetime,
  "lastlogin": datetime,
}
```

**Message (`bbsengine6.message.Message`)**:

```python
{
  "id": 12345,
  "sender_moniker": "alice",
  "channel": "casino.dealer",
  "urgency": "ROUTINE",
  "content": "Welcome back.",
  "data": {"template": "greet", "vars": {"first_name": "Alice"}},
  "recipients": ["bob", "carol"],
  "created_at": datetime,
}
```

### 4.3 Presentation (terminal)

**Menu frame:**

```
╔══════════════════════════════════════╗
║          BBSENGINE MAIN MENU         ║
╠══════════════════════════════════════╣
║ ☐ Read Messages                      ║
║ ☒ Post Message                       ║
║ ☐ Edit Profile                       ║
║ ☐ Logout                             ║
╠══════════════════════════════════════╣
║ [ENTER] Select  [ESC] Quit  [?] Help ║
╚══════════════════════════════════════╝
```

**Listbox frame:**

```
Message List (Page 1 of 5)
  1. alice - Need feedback on design    | 2026-09-01 10:15
  2. bob   - Project status update      | 2026-09-02 14:22
  3. carol - Upcoming meeting           | 2026-09-03 15:30

[UP/DOWN] Navigate  [PAGEUP/DOWN] Page  [ENTER] Select  [ESC] Exit
```

### 4.4 Presentation (web JSON)

```json
{
  "success": true,
  "data": {
    "messages": [
      {"id": 456, "from": "alice", "subject": "Feedback", "date": "2026-09-01T10:15:00", "read": false}
    ]
  },
  "timestamp": "2026-09-04T18:50:00"
}
```

---

## 5. Error Handling

### 5.1 Database error

```
SQL Query Execution
  │
  ├─ psycopg.Error
  │   ├─ logentry via bbsengine6.util.logentry
  │   ├─ io.echo(error, level="error")
  │   └─ return None / False / []
  │
  └─ Connection Timeout
      ├─ reconnect via pool
      └─ retry once
```

### 5.2 Auth error

```
bed/api/auth.py
  │
  ├─ credential check fails
  │   ├─ log entry
  │   └─ return {"type": "login_fail", "reason": "invalid_credentials"}
  │
  ├─ HMAC decode fails
  │   ├─ log entry
  │   └─ return {"type": "envelope_error", "reason": "bad_signature"}
  │
  └─ bbsengine6.auth.access returns False
      └─ return {"type": "forbidden", "op": "<op>"}
```

### 5.3 Module execution error

```
module.run(modulename)
  │
  ├─ module.check fails
  │   └─ io.echo("Access denied"); return False
  │
  ├─ module.load fails
  │   └─ io.echo("Module not found"); return False
  │
  ├─ signature check fails
  │   └─ io.echo("Invalid module API"); return False
  │
  ├─ module.main raises Exception
  │   ├─ runcallback catches
  │   ├─ io.echo_traceback(exception)
  │   └─ return None / error sentinel
  │
  └─ return result
```

### 5.4 Message subsystem errors

```
bbsengine6.message.service.store_message_with_checks
  │
  ├─ is_enabled() == False → empty diagnostics, message_id=0
  │
  ├─ rate limit exceeded → diagnostics.rate_limit_ok=False, no insert
  │
  ├─ recipient blocked → diagnostics.recipients_blocked.append(...)
  │
  ├─ psycopg.Error → bubbles up; caller logs and surfaces via io.echo
  │
  └─ success → message_id, diagnostics
```

### 5.5 Bootstrap errors

```
bbsengine6.startup.main
  │
  ├─ stage fails → conn.rollback(); return False
  │
  ├─ bed unreachable → io.echo(level="debug") "bed unreachable;
  │   using DB-polling fallback"
  │
  └─ all stages ok → conn.commit(); return True
```

---

*Data Flow Specification for bbsengine6.*
