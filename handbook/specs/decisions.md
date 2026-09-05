# bbsengine6 Architectural Decision Records

> Status: canonical. Last updated 2026-09-04.
> Each ADR records the decision, the rationale, the alternatives
> considered, and the outcome. The rationale paragraphs are
> authoritative; the surrounding background and source links have
> been pruned.

## Contents

1. [Layered Architecture](#decision-1-layered-architecture)
2. [Module / Plugin System](#decision-2-module--plugin-system)
3. [Terminal-First Design](#decision-3-terminal-first-design)
4. [Multi-Language Stack](#decision-4-multi-language-stack)
5. [PostgreSQL](#decision-5-postgresql)
6. [Separation of Web Layer](#decision-6-separation-of-web-layer)
7. [No Circular Dependencies](#decision-7-no-circular-dependencies)
8. [Rich Terminal UI](#decision-8-rich-terminal-ui)
9. [Explicit Cascade Ordering for Primary Key Changes](#decision-9-explicit-cascade-ordering-for-primary-key-changes)
10. [Per-Op `access(args, op, **kwargs)` Policy Modules](#decision-10-per-op-accessargs-op-kwargs-policy-modules)
11. [Layered `bbsengine6.message` Package](#decision-11-layered-bbsengine6message-package)
12. [`startup.main` as the Canonical Bootstrap Entry Point](#decision-12-startupmain-as-the-canonical-bootstrap-entry-point)
13. [Dedicated `zoid6` Owner Role for SECURITY DEFINER Helpers](#decision-13-dedicated-zoid6-owner-role-for-security-definer-helpers)
14. [Single-Source-of-Truth bcrypt in `bbsengine6.password`](#decision-14-single-source-of-truth-bcrypt-in-bbsengine6password)
15. [`notify` Subsystem Deletion](#decision-15-notify-subsystem-deletion)

---

## Decision 1: Layered Architecture

### Decision

bbsengine6 is organised as four layers:

1. **Data** — `database.py` + `py/src/bbsengine6/sql/`.
2. **Business Logic** — `session/`, `member/`, `bank/`, `channel/`,
   `message/`, `auth/`, `services/`, `invite.py`, `pgrole.py`,
   `password.py`, `password_cipher/`, `blurb.py`, `folder.py`,
   `util.py`, `bottombar.py`, `menu_next/`, `editor.py`,
   `screen.py`.
3. **Presentation** — `io/`, `menu.py`, `listbox.py`, `form.py`,
   `editor.py` / `ed/`, `input.py` + the PHP web layer
   (`engine/`, `php/`, `smarty/`, `skin/`, `js/`).
4. **Module System** — `module.py` + every registered module.

### Rationale

Separation of concerns lets each layer be tested without dragging
in the next. The data layer is swappable behind `database.getpool`;
business logic is shared by terminal and web clients; presentation
layers can be added without touching the layer below. The module
system overlays all three so a new feature can compose anything it
needs.

The concrete layering — which packages sit in which layer — is
documented in [`architecture.md`](./architecture.md#1-layered-architecture).

### Alternatives considered

- **Monolith.** Single huge module with prompts, queries, and
  rendering interleaved. Rejected: hard to test, hard to reuse,
  can't add a web layer without forking the data path.
- **Microservices.** Auth / messaging / session each in a separate
  process. Rejected: overkill for a single BBS, network overhead,
  service discovery, complex deploy.

### Outcome

Layered architecture. See [`architecture.md`](./architecture.md).

---

## Decision 2: Module / Plugin System

### Decision

`bbsengine6.module` is the runtime-loadable plugin loader. Every
registered module exposes `init`, `access`, `buildargs`, `main`,
discovered via `importlib.import_module`. Per-op authorization is
delegated to a package-specific `access(args, op, **kwargs)` (see
[Decision 10](#decision-10-per-op-accessargs-op-kwargs-policy-modules)).

### Rationale

Plugins add features without touching the core. `init` runs once
per load; `access` is the policy hook; `buildargs` parses CLI flags;
`main` runs the feature. The loader wraps everything in
`runcallback` so exceptions surface as a clean `False`/traceback
rather than a process crash.

The `MenuOption` registry in `bbsengine6.menu_next` is the modern
way for game submodules to register options against a shared
menu — see the consumer pattern in `casino/SPEC.md` §3 and the
description in [`./module.md`](./module.md).

### Alternatives considered

- **Monolithic features.** Keep every feature in core. Rejected:
  large, hard-to-test, can't remove or opt out.
- **Separate pip packages.** Each feature ships as its own
  distribution. Rejected: no unified interface, no built-in access
  control, hard to discover.

### Outcome

`module.run` + the four-function contract. New modules can be
added without modifying the loader.

---

## Decision 3: Terminal-First Design

### Decision

The primary user interface is the terminal. The Python TUI is
rich (colors, widgets, keyboard navigation); the web layer
(`engine/`, `php/`, `smarty/`, `skin/`, `js/`) is a secondary
read/write surface over the same database.

### Rationale

bbsengine.org is a bulletin board system; the BBS heritage is
text-first. Terminal clients work over SSH, render instantly,
and don't require a browser or JavaScript. The web layer reuses
the same database, so the two clients stay in lock-step without
a unifying web framework.

### Alternatives considered

- **Web-first.** Flask / Django with full HTML + JS. Rejected:
  adds web-framework complexity and breaks the BBS aesthetic.
- **Desktop GUI (Qt / GTK).** Rejected: requires X11 / Wayland,
  complex build, no SSH access.

### Outcome

Terminal-first, web-secondary. The web layer is documented in
[`../../SPEC.md`](../../SPEC.md#4-php-web-layer).

---

## Decision 4: Multi-Language Stack

### Decision

Python owns the terminal, the business logic, and the WebSocket
daemon (`bed.py` + `net/`). PHP owns the web request handlers.
JavaScript owns client-side interactivity in the browser.

### Rationale

Each language is chosen for what it does best. Python handles
system complexity and the TUI. PHP is mature web hosting and
matches the existing site deployment. JavaScript is the browser
standard. Splitting along these lines avoids either dragging a
web framework into the terminal or rebuilding the TUI for the
web.

### Alternatives considered

- **All Python.** Flask/Django for the web. Rejected: web
  framework weight; terminal would still need its own stack.
- **All PHP.** Rejected: terminal libraries are weaker; PHP is
  not a good fit for system plumbing.
- **Python + Node split.** Rejected: massive overkill, service
  orchestration, complex deploy.

### Outcome

Multi-language stack with the boundaries in
[`architecture.md` §3](./architecture.md#3-domain-organization).

---

## Decision 5: PostgreSQL

### Decision

PostgreSQL 12+ is the primary database. The schema lives at
`py/src/bbsengine6/sql/`. JSONB, ltree, UUID-ossp, and roles are
load-bearing features.

### Rationale

PostgreSQL gives ACID, JSONB for flexible per-row state (`flags`,
`attrs`, `__session.data`), ltree for the folder hierarchy
(`py/src/bbsengine6/sql/ltree.sql`), UUID-ossp for session
identifiers, and a real role system that lets the engine run
each request under a member-scoped role. The five
SECURITY DEFINER helpers (`manage_schema_priv`,
`manage_database_priv`, `manage_role_privs`,
`manage_secondary_role`, `get_role_privs`) are owned by the
dedicated unprivileged `zoid6` role — see
[Decision 13](#decision-13-dedicated-zoid6-owner-role-for-security-definer-helpers).

### Alternatives considered

- **MySQL / MariaDB.** Rejected: weaker JSONB, no ltree.
- **SQLite.** Rejected: no concurrent writers, no role system.
- **NoSQL (MongoDB).** Rejected: structured data wants relational
  integrity.

### Outcome

PostgreSQL. See [`../../SPEC.md`](../../SPEC.md#5-sql-schema) for the
schema inventory.

---

## Decision 6: Separation of Web Layer

### Decision

The PHP web layer and the Python engine read/write the same
PostgreSQL database. They do not call each other over the wire
for ordinary request handling; integration points (real-time
push, login auditing) go through `bed`.

### Rationale

The two layers stay independent — neither has to know about the
other's runtime. Both can be deployed standalone. Real-time
push (Phase 11) and login flow (post-2026-08-23) share bed as
the broker: PHP authenticates locally with
`bbsengine6\\password\\libpassword`, Python authenticates
locally with `bbsengine6.password`, and bed's `AuthService`
issues the bearer tokens used by the WS layer.

### Alternatives considered

- **Thin PHP over Python REST API.** Rejected: PHP becomes a
  marshaling layer with full HTTP overhead per request.
- **Unified ORM across PHP and Python.** Rejected: language
  mismatch, would need middleware.

### Outcome

Independent layers, shared database. Bed is the integration
broker for real-time and authentication.

---

## Decision 7: No Circular Dependencies

### Decision

The package dependency graph is a strict DAG. Lower layers never
import upward. `module.py` is the cross-layer loader; loaded
modules may not import back into `module.py`. `util.py` has no
upward imports; it's a shared leaf.

### Rationale

Cycles break Python's import system, make tests brittle, and
hide what depends on what. A DAG lets every layer be reasoned
about and replaced in isolation.

### Alternatives considered

- **Allow cycles and rely on `importlib` caching.** Rejected:
  illusion of safety; refactoring becomes terrifying.
- **Everyone imports everyone.** Rejected: defeats the purpose
  of layering.

### Outcome

No cycles. Enforced by convention and code review; see
[`dependencies.md`](./dependencies.md) for the matrix.

---

## Decision 8: Rich Terminal UI

### Decision

The TUI uses ANSI colors (16, 256, 24-bit RGB), interactive
widgets (`menu`, `listbox`, `form`, `editor`), and keyboard
navigation. The widget set lives in `bbsengine6.io` and the
top-level `menu.py` / `listbox.py` / `form.py` / `editor.py` /
`ed/` modules.

### Rationale

Rich UI is faster and more pleasant than line-mode prompts; the
BBS audience expects it; modern terminals support it natively;
the implementation cost is contained inside `io/`.

### Alternatives considered

- **Plain text only.** Rejected: feels 1980s, slower navigation.
- **Full GUI (Qt / GTK).** Rejected: defeats BBS aesthetic,
  requires desktop, no SSH access.

### Outcome

Rich terminal UI. Phase 4 hardening (see
[`../../ROBUSTNESS_REVIEW.md`](../../ROBUSTNESS_REVIEW.md))
pinned DSR-based input waits, `_input_dirty`, the `filter` kwarg,
listbox math, and bottombar padding.

---

## Decision 9: Explicit Cascade Ordering for Primary Key Changes

### Decision

When changing a primary key value (e.g. member moniker),
`database.update` runs an explicit cascade in this order:

1. UPDATE dependent rows to the new key.
2. UPDATE the parent table with `updatepk=True`.
3. PostgreSQL `ON UPDATE CASCADE` handles any remaining dependents.
4. Commit — the whole operation is one transaction.

### Rationale

`ON UPDATE CASCADE` fires after the parent row changes, so the
parent UPDATE alone would violate the FK. Pre-emptively rewriting
dependents first lets the cascade succeed. The single transaction
keeps the system consistent under any failure.

### Alternatives considered

- **Rely on `CASCADE` alone.** Rejected: the FK violation fires
  before CASCADE runs.
- **`SET CONSTRAINTS ALL DEFERRED`.** Rejected: complex
  transaction management, easy to leave constraints disabled
  on failure.
- **Surrogate key only.** Rejected: breaking schema change.

### Outcome

Explicit cascade ordering. See `member.lib.update` for the
implementation pattern.

---

## Decision 10: Per-Op `access(args, op, **kwargs)` Policy Modules

### Decision

Authorization for a domain operation lives in a package-local
`access(args, op, **kwargs)` function. The wire-protocol handler
in `bed` decodes tokens / parses envelopes *before* calling
`access`; `access` only inspects decoded state and the domain
arguments.

### Rationale

The wire envelope (HMAC, expiry, instance match) is bound to the
transport; the policy is bound to the domain. Mixing the two
couples every policy module to bed's HMAC scheme and forces
test fixtures to mint valid tokens. Decoupling means `auth.access`
can be unit-tested with plain dicts; `bed/api/auth.py` owns the
HMAC plumbing.

### Per-op policy modules

| Module | Ops |
|--------|-----|
| `bbsengine6.auth.access` | `login`, `reconnect`, `refresh`, `revoke`. |
| `bbsengine6.bank.access` | `transfer`, `deposit`, `withdraw`, `read`. |
| `bbsengine6.message.access` | `subscribe`, `unsubscribe`, `list_pending`. |
| `bbsengine6.module.check` | `op="run"` at module-load time. |

The shared shape is documented in [`auth-bank.md`](./auth-bank.md).

### Alternatives considered

- **Single global `access` table.** Rejected: turns every
  authorization decision into a SQL lookup, hides per-op
  semantics.
- **Bed validates everything; Python packages trust blindly.**
  Rejected: pushes all policy into the wire layer; CLI
  consumers can't reuse it.

### Outcome

Per-op `access()` per package. Bed owns the wire envelope; the
package owns the policy.

---

## Decision 11: Layered `bbsengine6.message` Package

### Decision

`bbsengine6.message` is split into four layers — **Service**,
**DAL**, **State**, **Domain** — mirroring `casino`'s four-layer
architecture (see `casino/SPEC.md` §3).

| Layer | Module(s) |
|-------|-----------|
| Service | `bbsengine6.message.service`, `bbsengine6.message.lib` |
| DAL | `bbsengine6.message.dal.messages`, `…recipients`, `…groups`, `…blocking`, `…ratelimit`, `…types`, `…_pool` |
| State | `bbsengine6.message.cache` |
| Domain | `bbsengine6.message.templates`, `bbsengine6.message.access` (in `__init__.py`) |

The DAL never imports `psycopg` directly; all DB plumbing goes
through `bbsengine6.database`. Async DAL is not yet provided —
the current implementation is fully sync.

### Rationale

Before the split, `bbsengine6.message.lib` was 1850 lines
mixing policy, I/O, rendering, and DB plumbing. Per-table DAL
modules give the service layer a clean composition surface;
the cache module is intentionally *not* under `dal/` because
it has no DB I/O. Templates and access sit at the package root
because they're not DAL.

### Alternatives considered

- **Single 1850-line `message.py`.** Rejected: untestable,
  no layering, no per-table ownership.
- **Microservice over REST.** Rejected: per the rest of
  bbsengine6's layering decisions.

### Outcome

Layered package, documented in
[`../../SPEC.md`](../../SPEC.md#11-layered-package-layout) and the
message subsystem's own docs.

---

## Decision 12: `startup.main` as the Canonical Bootstrap Entry Point

### Decision

DB bring-up runs through `bbsengine6.startup.main`, which loops
`("stage_zero", "stage_one", "engine", "bank")` via
`startup.lib.runmodule` → `console.lib.runmodule(package="bbsengine6.startup")`
→ `module.run(...)`. The thin console-script shim is
`py/src/bbsengine6/bed.py`.

`bbsengine6.backend` owns the actual `check*`, `stage_zero`,
`stage_one`, `engine`, `bank` modules. `console/` and
`startup/` carry four-line shims that re-export
`init`, `access`, `buildargs`, `main` from the canonical home.

### Rationale

`console/` previously held admin UI; `startup/` held engine-init
plumbing. The two directories had drifted into byte-identical
duplicates with a broken four-stage orchestrator. Folding the
init plumbing into `backend/` makes the canonical home
unambiguous; the thin shims preserve existing import paths.

`console.lib.runmodule` gained a `package=` kwarg (default
`"bbsengine6.console"`) so the same dispatcher serves both
call sites. At the end of a successful boot,
`startup.main._maybe_subscribe_to_bed` opens a `BedConnection`
and subscribes to bed's message pushes (failure is non-fatal —
`io.getch` falls back to DB polling).

### Alternatives considered

- **Keep the duplicates, fix the orchestrator in place.**
  Rejected: keeps two copies of every check.
- **Inline backend into startup, drop console shims.**
  Rejected: breaks `console.check*` import paths.

### Outcome

Canonical home at `bbsengine6.backend/`. The change list is in
the Phase 0 / backend-refactor commit history (the
`TODO_BACKEND.md` working notes were retired as part of the
2026-09-04 doc consolidation).

---

## Decision 13: Dedicated `zoid6` Owner Role for SECURITY DEFINER Helpers

### Decision

The five privilege-management helpers — `manage_schema_priv`,
`manage_database_priv`, `manage_role_privs`,
`manage_secondary_role`, `get_role_privs` — are `SECURITY
DEFINER` functions owned by a dedicated unprivileged PostgreSQL
role `zoid6`
(`NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN INHERIT`).
`backend.checkzoid6role` creates the role; `backend.checkzoid6owner`
runs `ALTER FUNCTION ... OWNER TO zoid6` against the five
helpers if ownership has drifted. The `engine` schema is
`AUTHORIZATION zoid6` so `manage_schema_priv` can `GRANT USAGE`.

`database.verify_function_owner` checks the five helpers against
a hard-coded allow-list `("zoid6", "postgres")`. The `postgres`
entry is a one-release transition aid; it will be dropped in
the next release (see [`../../TODO_zoid6_role.md`](../../TODO_zoid6_role.md)).

### Rationale

The bootstrap principal (typically a login superuser like `jam`
or `opencode`) should not own runtime helpers. A NOSUPERUSER
owner is the smallest possible privilege that can still run
`ALTER FUNCTION ... OWNER TO` on the five helpers and `GRANT
USAGE` on `engine`. The allow-list converts a
non-deterministic ownership tuple into a fixed two-element
list.

Because `manage_schema_priv` is NOSUPERUSER-owned, every
`schema.sql` it grants on must itself be owned by `zoid6`. The
`engine` schema is handled in-repo via `backend.checkengine`;
other BBS submodules ship a `<module>.startup.check<module>`
mirror invoked from the submodule's startup `main` between
extension install and the schema.sql import. `casino.startup.checkcasino`
is the canonical example.

### Alternatives considered

- **Bootstrap principal owns the helpers.** Rejected: keeps
  superuser ownership in the runtime path.
- **Hard-coded `postgres` owner.** Rejected: makes the
  allow-list non-deterministic; environment drift = silent
  outage.

### Outcome

Dedicated `zoid6` owner role. See [`../../SPEC.md`](../../SPEC.md#5-sql-schema)
for the full pattern.

---

## Decision 14: Single-Source-of-Truth bcrypt in `bbsengine6.password`

### Decision

`bbsengine6.password` is the single source of truth for bcrypt
hashing on the Python side (mirrors PHP's
`bbsengine6\\password` namespace). The legacy
`bbsengine6.password_cipher` package keeps the `bbsengine6.password`
namespace free for bcrypt; `bbsengine6.password_cipher` is the
AES-256-GCM reversible encryption strategy for IMAP/SMTP secrets.

`bbsengine6.member.checkpassword` verifies locally
(`crypt(plaintext, stored)` with a passlib bcrypt fallback) and
rewrites legacy `$1$` MD5-crypt hashes to fresh `$2b$06$` on the
first successful login. PHP `bbsengine6\\password\\libpassword`
mirrors the same cost factor and emits `$2y$`. The
`chk_member_password_bcrypt` CHECK constraint
(`^\$2[abxy]$`, length 60) accepts both prefixes.

### Rationale

Before the change, the two sides were asymmetric: Python produced
new hashes locally (`bbsengine6.util._BCRYPT_ROUNDS = 6`) but
still round-tripped verify through PostgreSQL `crypt()`. PHP
round-tripped both directions. Round-tripping verify makes every
login hit PG twice and turns a `pgcrypto` upgrade into a
potential auth outage. After the rewrite, both sides produce and
verify locally; PG only stores and audits.

### Alternatives considered

- **PG-side round-trip on both languages.** Rejected: doubles
  PG load per login; cross-version pgcrypto drift is a risk.
- **Two different cost factors.** Rejected: complicates
  cross-language auth tests.

### Outcome

Single source of truth on each side. See
[`../../CHANGELOG.md`](../../CHANGELOG.md) entries "php: local
bcrypt hashing, no PostgreSQL crypt() round-trip" and
"py: member.checkpassword — local verify + opportunistic rehash".

---

## Decision 15: `notify` Subsystem Deletion

### Decision

The `notify` messaging subsystem was deleted in 2026 (commit
`a689c89`). Only three functions survive — `member.moniker_exists`,
`member.group_exists`, `member.get_group_members` — now in
`py/src/bbsengine6/member/lib.py`. The historical changelog
(`CHANGELOG_NOTIFY_MESSAGING.md`) was deleted as part of the
2026-09-04 doc consolidation; the surviving functions are
documented in [`./member.md`](./member.md) §"Moniker and group
validation (notify-era, retained)".

The replacement is the layered `bbsengine6.message` package
documented in [Decision 11](#decision-11-layered-bbsengine6message-package).

### Rationale

`notify` mixed wire-protocol, policy, and DB I/O in one place
and did not survive the Phase 0-5 hardening (see
[`../../ROBUSTNESS_REVIEW.md`](../../ROBUSTNESS_REVIEW.md) Phase 0.4
"Stale root tests that couldn't pass"). The `notify → message`
migration produced a layered package with a clean DAL,
replaced every call site, and pinned regression tests at every
layer.

### Alternatives considered

- **Keep `notify`, fix the tests.** Rejected: the architectural
  problems (mixing layers, no DAL boundary) remain.
- **Rename `notify` in place.** Rejected: rename-without-restructure
  hides the layering change.

### Outcome

Deleted; replaced by `bbsengine6.message`. The `BBSENGINE6_NOTIFYD_*.md`
specs are HISTORICAL — kept for archaeology, do not link to them
from new docs (see [`../../SPEC.md`](../../SPEC.md#10-out-of-scope)).

---

## Summary

| # | Decision | Choice |
|---|----------|--------|
| 1 | Architecture | Layered (data / business / presentation / module system) |
| 2 | Extensibility | Module / plugin system |
| 3 | Primary interface | Terminal (web secondary) |
| 4 | Languages | Python + PHP + JavaScript |
| 5 | Database | PostgreSQL 12+ |
| 6 | Web layer | Separate, shared database, bed as integration broker |
| 7 | Dependencies | No cycles |
| 8 | TUI | Rich widgets + keyboard navigation |
| 9 | PK changes | Explicit cascade ordering |
| 10 | Authorization | Per-op `access(args, op, **kwargs)` per package |
| 11 | Message package | Layered Service / DAL / State / Domain |
| 12 | Bootstrap entry | `bbsengine6.startup.main` |
| 13 | SECURITY DEFINER ownership | Dedicated `zoid6` role |
| 14 | Password hashing | Local verify + opportunistic rehash on each side |
| 15 | `notify` subsystem | Deleted; replaced by `bbsengine6.message` |

---

*Architectural Decision Records for bbsengine6.*
