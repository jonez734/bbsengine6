# bbsengine6 Module Dependencies

> Status: canonical. Last updated 2026-09-04.
> Cross-package matrix only. Console-package sub-dependency maps
> live in [`./console.md`](./console.md); the net layer is
> documented in [`./net-layer.md`](./net-layer.md). The legacy
> `NET_LAYER_SPEC.md` was folded into the current spec set during
> the 2026-09-04 consolidation.

## Contents

1. [Cross-Package Matrix](#1-cross-package-matrix)
2. [Layer-to-Layer Edges](#2-layer-to-layer-edges)
3. [External Dependencies](#3-external-dependencies)
4. [Circular Dependencies](#4-circular-dependencies)
5. [Coupling Notes](#5-coupling-notes)

---

## 1. Cross-Package Matrix

`→` means "depends on". Entries are limited to direct imports
between `bbsengine6.*` packages / sub-packages.

### 1.1 Top-level → top-level

| Module | Imports |
|--------|---------|
| `bbsengine6.database` | psycopg, psycopg_pool, `bbsengine6.io` (logging) |
| `bbsengine6.session` | `bbsengine6.database`, `bbsengine6.member`, `bbsengine6.io` |
| `bbsengine6.member` | `bbsengine6.database`, `bbsengine6.pgrole`, `bbsengine6.password`, `bbsengine6.util`, `bbsengine6.io` |
| `bbsengine6.bank` | `bbsengine6.database`, `bbsengine6.util` |
| `bbsengine6.channel` | `bbsengine6.net` (transport), `bbsengine6.util` |
| `bbsengine6.message` | `bbsengine6.database`, `bbsengine6.io`, `bbsengine6.util` |
| `bbsengine6.auth` | (none — pure policy module) |
| `bbsengine6.services` | `bbsengine6.channel`, `bbsengine6.member`, `bbsengine6.bank`, `bbsengine6.util` |
| `bbsengine6.invite` | `bbsengine6.database`, `bbsengine6.io` |
| `bbsengine6.pgrole` | `bbsengine6.database`, `bbsengine6.util` |
| `bbsengine6.password` | (none — bcrypt single source of truth) |
| `bbsengine6.password_cipher` | (none — strategy pattern, no upward imports) |
| `bbsengine6.blurb` | `bbsengine6.database`, `bbsengine6.util` |
| `bbsengine6.folder` | `bbsengine6.database`, `bbsengine6.util` |
| `bbsengine6.menu` | `bbsengine6.util`, `bbsengine6.io`, `bbsengine6.database` |
| `bbsengine6.menu_next` | (none — pure registry dataclass) |
| `bbsengine6.bottombar` | `bbsengine6.module`, `bbsengine6.database`, `bbsengine6.io` |
| `bbsengine6.editor` | `bbsengine6.util`, `bbsengine6.screen`, `bbsengine6.io`, `bbsengine6.member` |
| `bbsengine6.screen` | `bbsengine6.io` (re-export shim) |
| `bbsengine6.util` | `bbsengine6.io` (logging), stdlib only |
| `bbsengine6.common` | stdlib (`logging`) only |
| `bbsengine6.conf` | stdlib (`os`) only |
| `bbsengine6.module` | `bbsengine6.database`, `bbsengine6.io`, stdlib (`importlib`) |
| `bbsengine6.bed` | `bbsengine6.io`, `bbsengine6.database`, `bbsengine6.net` |

### 1.2 Sub-package → sub-package

| Source | Imports |
|--------|---------|
| `bbsengine6.session.api` | `bbsengine6.session.lib` |
| `bbsengine6.member.api` | `bbsengine6.member.lib` |
| `bbsengine6.bank.api` | `bbsengine6.bank.*` (account / bank / transaction / transfer) |
| `bbsengine6.channel.api` | `bbsengine6.channel.lib` (handler shape) |
| `bbsengine6.message.service` | `bbsengine6.database`, `bbsengine6.io`, `bbsengine6.message.cache`, `bbsengine6.message.dal.*`, `bbsengine6.message.lib`, `bbsengine6.message.templates` |
| `bbsengine6.message.dal.*` | `bbsengine6.database` (every DAL module goes through `bbsengine6.database.getpool`); never `psycopg` directly |
| `bbsengine6.message.cache` | (none — in-memory state) |
| `bbsengine6.message.templates` | (none — pure rendering) |
| `bbsengine6.message.lib` | `bbsengine6.database`, internal re-exports |
| `bbsengine6.password_cipher.{manager,storage,cipher,config}` | stdlib only (strategy pattern) |
| `bbsengine6.io.*` | other `bbsengine6.io.*` modules only |
| `bbsengine6.ed.common` | `bbsengine6.io` (terminal primitives) |
| `bbsengine6.ed.line` | `bbsengine6.ed.common` |
| `bbsengine6.ed.visual` | `bbsengine6.ed.common` |
| `bbsengine6.backend.*` | `bbsengine6.database`, `bbsengine6.io`, `bbsengine6.util`, `bbsengine6.module` |
| `bbsengine6.console.*` | shims re-exporting `bbsengine6.backend.*` (see [console.md](./console.md)); non-shim modules (`createdatabase`, `member`, `memberapproval`, `showpgrole`, `session`, `main`) depend on `bbsengine6.database`, `bbsengine6.member`, `bbsengine6.session`, `bbsengine6.util` |
| `bbsengine6.startup.*` | shims re-exporting `bbsengine6.backend.*`; `startup.main` additionally imports `bbsengine6.io`, `bbsengine6.database`, `bbsengine6.util`, `bbsengine6.member`, `startup.message_subscription` |
| `bbsengine6.startup.message_subscription` | `bbsengine6.io`, optional `bed.client.connection` |
| `bbsengine6.net.*` | `bbsengine6.io`, stdlib (`asyncio`, `socket`, `ssl`) — full list in [`./net-layer.md`](./net-layer.md) |

### 1.3 Dependency graph (cross-package)

```
PostgreSQL
    ▲
    │
bbsengine6.database
    ▲           ▲           ▲           ▲           ▲
    │           │           │           │           │
session   member   bank     channel   message      auth
    ▲       │   ▲    ▲           ▲           ▲
    │       │   │    │           │           │
    └───┬───┘   │    │           │           │
        │       │    │           │           │
      io  ◄──── util  ◄───────────┴───────────┘
        ▲
        │
       module (cross-layer)
        ▲
        │
       bed
```

`auth` has no upward imports — it's a pure policy module invoked
by `bed` over decoded claims.

---

## 2. Layer-to-Layer Edges

### 2.1 Data → nothing

```
bbsengine6.database
  └─ external: psycopg, psycopg_pool
```

The data layer is the root of the DAG. No upward imports.

### 2.2 Business Logic → Data + Utilities

```
session/  ─┐
member/   ─┤
bank/     ─┼─→ database
channel/  ─┤
message/  ─┤   (message DAL talks only to database)
invite    ─┤
pgrole    ─┤
blurb     ─┤
folder    ─┘
```

`message.dal.*` follows the same rule but is broken out into
one module per `engine.__message*` table family. None of them
import `psycopg` directly — they all go through
`bbsengine6.database`.

### 2.3 Presentation → Business Logic + Data

```
menu.py  ─┐
listbox.py ─┤
form.py   ─┼─→ database
editor.py ─┤
ed/       ─┤
input.py  ─┘
   │
   └─→ util
   └─→ io.*
```

Widgets query `database` for paginated lists and use `util` for
formatting. `menu_next` is a separate, dependency-free
`MenuOption` registry.

### 2.4 Module System → Everything

```
bbsengine6.module
   ├─→ database (access control)
   ├─→ io.echo (error display)
   ├─→ imported modules (dynamic)
   └─→ util (helpers)
```

Modules loaded via `module.run` may import any business-logic
package; they must not import `module.py` itself.

### 2.5 I/O Subpackage → I/O Subpackage only

```
echo → terminal, palette, const, echovars
screen → terminal, const
getch → keymap
inputstring → getch, echo
inputinteger → inputstring, echo
inputboolean → getch, echo
inputchoice → getch, echo
terminal → stdlib (shutil, terminfo)
palette, keymap, const, echovars → no imports
```

The `io/` subpackage never reaches into business logic. Higher
levels (widgets, modules) reach into it.

### 2.6 Service / Handler Surface

```
bank/api/handler.py     (BankServiceHandler)   consumed by bed
member/api/handler.py   (MemberServiceHandler) consumed by bed
channel/api/handler.py  (ChannelServiceHandler) consumed by bed
services/invite.py                            consumed by bed
services/channel.py                           consumed by bed
services/member.py                            consumed by bed
```

These handlers are the wire surface. Each package exposes its
own `access(args, op, **kwargs)` for the policy; the handler
owns the wire envelope (HMAC decode, JSON parse, response
shape). See [decisions.md §10](./decisions.md#decision-10-per-op-accessargs-op-kwargs-policy-modules)
and [`auth-bank.md`](./auth-bank.md).

---

## 3. External Dependencies

### 3.1 Python (required)

```
psycopg >= 3.0                PostgreSQL driver
psycopg-pool                  Connection pooling
python-dateutil               (getdate.py)
```

### 3.2 Python (stdlib)

`os`, `sys`, `types`, `logging`, `argparse`, `uuid`, `datetime`,
`json`, `copy`, `pwd`, `time`, `re`, `hashlib`, `random`, `shutil`,
`importlib`, `pickle`, `subprocess`, `termios`, `tty`, `fcntl`,
`select`, `secrets`, `threading`, `contextvars`, `asyncio`,
`dataclasses`, `enum`, `itertools`, `abc`.

### 3.3 Python (optional)

```
wcwidth                      terminal width (io.terminal fallback)
bed.client.connection        only consumed by startup.message_subscription
```

### 3.4 PHP (required)

```
PHP >= 8.1
PDO + PDO PostgreSQL driver
Smarty >= 3.0
HTML_QuickForm2              (Form/ clone)
```

### 3.5 PHP (vendored)

`bbsengine6/php/` ships its own `bbsengine6\\password` namespace
(`libpassword.php`) and a `Form/` clone (QuickForm2 + Captcha
providers + DataSource + Rule registry + ArrayRenderer).

### 3.6 Browser

```
jQuery >= 3.0                DOM + AJAX
jquery.smoothState.js        vendored (handbook/js/)
bbsengine6.js                project singleton (handbook/js/)
```

### 3.7 PostgreSQL

```
PostgreSQL >= 12
ltree                        hierarchical folders
uuid-ossp                    session ids
pgcrypto                     (legacy; verify path removed in 2026-08)
```

---

## 4. Circular Dependencies

### Status: NONE

bbsengine6 has no circular dependencies. The rule is enforced
by review:

- The data layer is a leaf.
- `bbsengine6.util` is a leaf (only depends on `bbsengine6.io`
  for logging).
- `bbsengine6.io` is a leaf within itself.
- `bbsengine6.module` is the cross-layer loader; loaded modules
  do not import `bbsengine6.module` back.
- Per-package `access(args, op, **kwargs)` is pure (no upward
  imports in `auth`; the others are confined to their package).

### Adding a new module

When adding a new module or sub-package:

1. **Verify the dependency direction.** Lower layers must not
   import upward. New code in `bbsengine6.io` cannot import
   `bbsengine6.member`.
2. **Use the `bbsengine6.database` boundary.** New DAL modules
   under any sub-package go through `bbsengine6.database`;
   never `import psycopg` directly.
3. **Use the package-local `access(args, op, **kwargs)`.** New
   authorization policies live in the package that owns the
   domain verb, not in bed or in `module.py`.
4. **Extract if a cycle appears.** If two packages need each
   other, extract the shared code into a third leaf and have
   both depend on it.

---

## 5. Coupling Notes

### 5.1 Coupling levels

| Package | Coupling | Notes |
|---------|----------|-------|
| `bbsengine6.database` | low | only external libs + `io.echo` for logging |
| `bbsengine6.util` | low | stdlib + `io.echo` only |
| `bbsengine6.io` | low | intra-package only |
| `bbsengine6.auth` | none | pure policy module |
| `bbsengine6.menu_next` | none | pure registry dataclass |
| `bbsengine6.password` | none | bcrypt single source of truth |
| `bbsengine6.password_cipher` | none | strategy pattern |
| `bbsengine6.session` | medium | `database` + `member` + `io` |
| `bbsengine6.member` | medium | `database` + `pgrole` + `password` + `util` |
| `bbsengine6.bank` | medium | `database` + `util` |
| `bbsengine6.message` | medium | `database` + `io` + `util` + own sub-packages |
| `bbsengine6.module` | medium | `database` + `io` + `importlib` |

### 5.2 Reusability rank

1. `bbsengine6.database` — used by every higher layer.
2. `bbsengine6.util` — used by most business-logic modules.
3. `bbsengine6.io` — used by every TUI widget and module.
4. `bbsengine6.session` / `member` / `bank` / `channel` /
   `message` — used by bed and the daemons.
5. Widgets (`menu`, `listbox`, `form`, `editor`, `ed/`) —
   terminal-client specific.
6. `bbsengine6.bed` — entry point only.

### 5.3 Performance implications

`bbsengine6.database.getpool` returns the shared
`psycopg_pool.ConnectionPool` (default max 20). Every consumer
shares it. DAL modules use the same pool; the
`CONN_POOL_PATTERN` (`cur= / conn= / pool= / args=` priority)
is the standard way to accept a connection in helpers.

Caching:
- `bbsengine6.message.cache` — in-memory local unread counter.
- `bbsengine6.session.SessionManager` — in-memory WS session map.
- `bbsengine6.io.bottombar` — fragment registry cache.

There is no global cross-process cache; PostgreSQL is the
authoritative store.

---

*Module Dependencies for bbsengine6.*
