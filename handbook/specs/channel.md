# bbsengine6.channel — channel pub/sub + announce-only enforcement

> **Status:** canonical. The 9-phase rollout landed 2026-09-05 (see
> `bbsengine6/TODO_BBSENGINE6_CHANNEL.md` for the implementation plan
> and `bbsengine6/CHANGELOG.md` for the Phase 6 entry).
> **117 bbsengine6 + 5 casino tests passing** against
> `BBSENGINE6_CHANNEL_TEST_DBNAME=zoid6` (the
> `chk_member_moniker_format` migration needs the connecting role to
> own `engine.__member`; in production this is `sysop`, in dev
> sandboxes it may be `jam` or similar — see §9).

`bbsengine6.channel` is the in-process pub/sub fabric layered on top
of `bbsengine6.net.ChannelState` (the in-memory subscriber index) and
backed by `engine.__channel` / `engine.__channel_announcer` (the
persistent configuration). The four moving parts are:

- **`bbsengine6.net.channel_publish`** — the routing workhorse. When
  invoked with both `sender_moniker` and `args`, consults
  `ChannelService.can_publish` for announce-only enforcement before
  fanning out to WebSocket subscribers and in-process callbacks.
- **`bbsengine6.services.channel.ChannelService`** — persistent
  configuration (announce-only flag, explicit announcer lists) plus
  the mutation permission gate (`_require_authority`).
- **`bbsengine6.channel.api.handler`** — WebSocket surface: subscription
  verbs (`ChannelServiceHandler`) and admin verbs
  (`ChannelAdminHandler`). Auto-seed runs once at register time.
- **`bbsengine6.channel.naming`** — single source of truth for the
  `<app>:<kind>:<id>` naming convention.

The CLI surface is `con channel <verb>` in `bbsengine6.console.channel`.

## Contents

- [Architecture](#architecture)
- [Components](#components)
  - [`bbsengine6.services.channel` — `ChannelService`](#services)
  - [`bbsengine6.net` — channel primitives](#net-primitives)
  - [`bbsengine6.channel.naming` — naming helpers](#naming)
  - [`bbsengine6.channel.api.handler` — WS surface](#ws-surface)
- [SQL schema](#sql-schema)
- [Permission model](#permission-model)
- [Naming convention](#naming-convention)
- [Auto-seed algorithm](#auto-seed)
- [Namespacing convention](#namespacing)
- [Configuration](#configuration)
- [CLI surface — `con channel <verb>`](#cli)
- [WebSocket protocol](#ws-protocol)
- [Extension guide for new modules](#extension)
- [Operational notes](#ops)
- [Test coverage](#tests)
- [Migration history](#migration)
- [See also](#see-also)

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   Application (game package)                  │
│        (casino.api.handler._publish_to_table, etc.)         │
└────────────────────────┬─────────────────────────────────────┘
                         │
                  channel_publish(state, channel, msg,
                                  server=...,
                                  sender_moniker=...,
                                  args=...)
                         │
                         ▼
       ┌─────────────────────────────────────┐
       │  bbsengine6.net.channel_publish     │
       │  (transport.py:151)                │
       │  ┌─────────────────┐                │
       │  │ ChannelService  │  if sender +   │
       │  │  .can_publish   │  args present  │
       │  │   (services/    │                │
       │  │   channel.py)   │                │
       │  └─────────────────┘                │
       │  ┌─────────────────┐                │
       │  │ ChannelState    │  in-memory     │
       │  │ (transport.py   │  subscriber    │
       │  │  :40)           │  + callback    │
       │  └─────────────────┘                │
       └────────────────┬──────────────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
  ┌──────────────────┐    ┌──────────────────────┐
  │  WebSocket fan-  │    │  Callback fan-out    │
  │  out to subscribed│    │  for in-process bots │
  │  websockets       │    │                      │
  └──────────────────┘    └──────────────────────┘
```

The same `ChannelState` instance is shared by the `WebSocketServer`
(constructed in `bed.main.BED.start`) and the channel `MessageRouter`
(constructed via the `MessageRouterClass(..., channel_state=state)`
kwarg). Subscribers register through the WS verb path; publishers
fan out via the same map.

## Components

### `bbsengine6.services.channel` — `ChannelService`

`ChannelService(args)` is the persistent-configuration layer plus the
permission gate for mutators. Lives in
`bbsengine6/services/channel.py:21-358`.

| Method | Signature | Auth | Returns |
|---|---|---|---|
| `create_channel` | `(name, createdby, description=None, announce_only=False, announcers=None) -> Dict` | any | `{success, channel:{...}}` |
| `get_channel` | `(name) -> Optional[Dict]` | — | dict from `engine.channel` view or `None` |
| `list_channels` | `(limit=100, offset=0, announce_only=None) -> List[Dict]` | — | list, ordered by name |
| `set_announce_only` | `(name, announce_only, by_moniker) -> Dict` | sysop OR `createdby` | `{success, message}` |
| `add_announcer` | `(channel_name, moniker, addedby) -> Dict` | sysop OR `createdby` | `{success, message}` |
| `remove_announcer` | `(channel_name, moniker, actor_moniker) -> Dict` | sysop OR `createdby` | `{success, message}` |
| `can_publish` | `(channel_name, moniker, is_sysop=None) -> Dict` | — | `{allowed, reason}` |
| `_require_authority` | `(channel_name, by_moniker) -> Optional[Dict]` | helper | `None` on success or error dict |

`_require_authority` returns `None` on success. Callers use the
conventional pattern:

```python
verdict = self._require_authority(name, by_moniker)
if verdict is not None:
    return verdict
```

This keeps the permission denials on the same return-value path as
other failures (no exceptions).

`can_publish` is the predicate called by `channel_publish` when both
`sender_moniker` and `args` are supplied. See [Permission model](#permission-model).

See `bbsengine6/member/lib.py` for `member_module.issysop` and the
related member verification helpers.

### `bbsengine6.net` — channel primitives

The transport layer's channel primitives live in
`bbsengine6/net/transport.py:40-239`.

| Function / Class | Signature | Notes |
|---|---|---|
| `ChannelState` (class) | dataclass with `channels`, `callbacks`, `session_channels` | per-daemon; built by `bed.main.BED.start` |
| `channel_subscribe` | `(state, session_id, channel) -> None` | adds to both `channels[channel]` and `session_channels[session_id]` |
| `channel_unsubscribe` | `(state, session_id, channel) -> None` | symmetric removal |
| `channel_unsubscribe_all` | `(state, session_id) -> None` | disconnect cleanup |
| `channel_register_callback` | `(state, channel, callback) -> None` | for in-process bots |
| `channel_unregister_callback` | `(state, channel, callback) -> None` | |
| `channel_unregister_all_callbacks` | `(state) -> None` | |
| `channel_get_subscribers` | `(state, channel) -> Set[int]` | |
| `channel_get_session_channels` | `(state, session_id) -> Set[str]` | |
| `channel_publish` | `async (state, channel, message, server=None, sender_moniker=None, args=None) -> None` | the routing workhorse |

`channel_publish` body, in order:

1. **Permission check.** If both `sender_moniker` and `args` are
   present, call `ChannelService.can_publish`. On verdict
   `allowed=False`, log a warning and return (drop the publish).
2. **WebSocket fan-out.** Iterate `server._clients`; for each
   websocket subscribed to this channel (matched by either
   `_bbsengine6_session_id` or `id(websocket)`), send the JSON-encoded
   message. Failed sends remove the dead socket from
   `server._clients` and explicitly close it to release the FD.
3. **Callback fan-out.** For each registered in-process callback,
   invoke it (await if coroutine). Callback exceptions are logged at
   `ERROR` but do not abort the publish.

The previous implementation routed via `server.broadcast(path=...)`,
which only reached clients connected to that path; clients on the
canonical `default` path were silently dropped. The current
implementation matches either identity (transport-allocated or
Python-id) to avoid this footgun.

See `handbook/specs/net-layer.md` for the `WebSocketServer` and the
path-based fan-out context.

### `bbsengine6.channel.naming` — naming helpers

Lives in `bbsengine6/channel/naming.py`.

| Helper | Returns | Use |
|---|---|---|
| `table_channel(app, moniker)` | `<app>:table:<moniker>` | per-table pub/sub |
| `member_channel(moniker)` | `member:<moniker>` | per-member inbox (reserved) |
| `global_channel(app)` | `<app>:global` | per-app announcements |
| `announcement_channel()` | `system:announcements` | reserved |
| `shout_channel()` | `system:shout` | reserved |
| `parse_channel(name)` | `(app, kind, id)` | round-trip; non-namespaced → `("", "", name)` |

Inline `f"myapp:table:{moniker}"` is fragile: a future rename is a
grep-and-replace across every module. Use these helpers so a
renaming change is a one-line edit.

### `bbsengine6.channel.api.handler` — WS surface

Lives in `bbsengine6/channel/api/handler.py:1-500`.

Top-level helpers:

| Symbol | Role |
|---|---|
| `_resolve_channel_config(config)` | dual-shape read (flat `bed.json` / nested `zoid6.json`) |
| `_ensure_daemon_member(args, moniker)` | lazy namespaced daemon member creation |
| `_auto_seed_channels(args, channel_cfg)` | idempotent seed step at register time |

Classes:

- **`BaseService`** — accepts `channel_state` kwarg; the channel router
  pattern is for any service that needs to publish through the
  shared state.
- **`ChannelServiceHandler`** — the subscription verbs
  (`subscribe_channel`, `unsubscribe_channel`, `get_subscriptions`).
- **`ChannelAdminHandler`** — the admin verbs (`channel_create`,
  `channel_list`, `channel_get`, `channel_set_announce_only`,
  `channel_add_announcer`, `channel_remove_announcer`). Registered
  conditionally on `channel_cfg.admin_handler.enabled`.
- **`MessageRouter`** — the constructor takes `channel_state=`,
  `server=`, and `config=`. `register_all(server)` registers the
  service handler, conditionally registers the admin handler, and
  runs `_auto_seed_channels`.

The router's `register_all` is gated on `channel_cfg.enabled`
(default `True`); operators disable channel services entirely by
setting that flag without touching code.

## SQL schema

`bbsengine6/sql/channel.sql`. Loaded by
`bbsengine6.backend.checkchannel` as part of `stage_one`; idempotent
on existing DBs (skipped via `classexists`).

```sql
create table engine.__channel (
    "id"            bigserial unique not null primary key,
    "name"          text not null unique,         -- pub/sub topic
    "description"   text,
    "announce_only" boolean not null default false,
    "createdby"     citext constraint fk_channel_createdby
                      references engine.__member(moniker)
                      on update cascade on delete set null,
    "datecreated"   timestamptz default now(),
    "datemodified"  timestamptz default now()
);

create table engine.__channel_announcer (
    "id"         bigserial unique not null primary key,
    "channel_id" bigint not null constraint fk_channel_announcer_channel
                   references engine.__channel(id)
                   on update cascade on delete cascade,
    "moniker"    citext not null constraint fk_channel_announcer_moniker
                   references engine.__member(moniker)
                   on update cascade on delete cascade,
    "addedby"    citext constraint fk_channel_announcer_addedby
                   references engine.__member(moniker)
                   on update cascade on delete set null,
    "dateadded"  timestamptz default now(),
    unique(channel_id, moniker)
);

create or replace view engine.channel as
    select c.id, c.name, c.description, c.announce_only,
           c.createdby, c.datecreated, c.datemodified,
           coalesce(
             (select array_agg(a.moniker order by a.moniker)
              from engine.__channel_announcer a
              where a.channel_id = c.id),
             '{}'::citext[]
           ) as announcers
    from engine.__channel c;

create index idx_engine_channel_name
    on engine.__channel(name);
create index idx_engine_channel_announce_only
    on engine.__channel(announce_only)
    where announce_only = true;
create index idx_engine_channel_announcer_channel
    on engine.__channel_announcer(channel_id);
create index idx_engine_channel_announcer_moniker
    on engine.__channel_announcer(moniker);

grant all on engine.__channel              to web, sysop, term;
grant all on engine.__channel_id_seq        to web, sysop, term;
grant all on engine.__channel_announcer     to web, sysop, term;
grant all on engine.__channel_announcer_id_seq to web, sysop, term;
grant select on engine.channel             to web, term, sysop, member;
```

The `engine.channel` view aggregates the announcer list per channel
into a `citext[]` for convenient single-row reads. `list_channels`
and `get_channel` query through the view.

The `chk_member_moniker_format` constraint on `engine.__member` is
extended by `bbsengine6.sql.checkmember_moniker_format` to allow
namespaced monikers (`^[a-zA-Z0-9_]+(?::[a-zA-Z0-9_]+)?$`). Loaded
every startup via `bbsengine6.backend.checkmember_moniker_format`;
the DO block is a no-op on already-migrated DBs.

## Permission model

The publish-side gate (`can_publish`):

```
publish(channel, sender)
  │
  ├── if sender_moniker is None → ALLOW (bypass; for system publishes)
  │
  ├── channel exists?
  │     └── NO → DENY ("Channel not found")
  │
  ├── announce_only?
  │     └── NO → ALLOW (open channel)
  │
  └── YES (announce-only)
        ├── is_sysop?       → ALLOW ("Sysop")
        ├── is_announcer?    → ALLOW ("Announcer")
        └── else            → DENY ("Channel is announce-only; sender is not an announcer")
```

The mutator-side gate (`_require_authority`):

| Mutator | Authority |
|---|---|
| `set_announce_only` | sysop OR `createdby` |
| `add_announcer` | sysop OR `createdby` (target member must also exist) |
| `remove_announcer` | sysop OR `createdby` (new `actor_moniker` parameter — breaking change vs. legacy) |
| `create_channel` | any authenticated caller (sysop-only enforcement not currently applied — future-work item) |

Read-side (subscription) is open to any authenticated member; there
is no read-side permission model. Channels are not encrypted and are
visible to anyone who subscribes.

The sysop check uses `bbsengine6.member.lib.issysop`; see
`handbook/specs/member.md`.

## Naming convention

Channels follow `<app>:<kind>:<id>`:

| Pattern | Example | Used for |
|---|---|---|
| `<app>:table:<moniker>` | `casino:table:blackjack-1` | per-table game state |
| `<app>:global` | `casino:global` | per-app announcements |
| `member:<moniker>` | `member:alice` | per-member inbox (reserved) |
| `system:announcements` | (literal) | sysop-only broadcasts |
| `system:shout` | (literal) | global chat (reserved) |

Cross-app conventions:

- Casino uses `casino:table:<moniker>` and `casino:global`.
- empyre uses `empyre:island:<id>` (anomaly: app prefix + kind suffix
  differ from the `<app>:table:` pattern; the namespacing helper
  `table_channel(app, moniker)` produces `<app>:table:<moniker>` so
  empyre needs to either keep its custom format or migrate). The
  naming helpers document the canonical shape; modules with
  non-conforming names should note the deviation in their own README.
- murdermotel uses `murdermotel:room:<id>`.
- zoo: (TODO when onboarded).

`parse_channel(name)` round-trips the helpers, returning
`(app, kind, id)`. Non-namespaced names yield `("", "", name)` so
callers can decide how to handle them.

## Auto-seed

`_auto_seed_channels(args, channel_cfg)` runs at `register_all` time
and is **best-effort**: every failure mode logs a warning and
skips. The daemon never fails to start because of a seed miss.

Sequence:

```
MessageRouter.register_all(server)
  │
  ├── gate on channel_cfg.enabled
  │
  ├── register ChannelServiceHandler verbs
  │
  ├── if channel_cfg.admin_handler.enabled:
  │       register ChannelAdminHandler verbs
  │
  └── _auto_seed_channels(args, channel_cfg)
        for entry in channel_cfg.auto_seed:
          validate entry.shape (dict, name, createdby)
          call _ensure_daemon_member(args, entry.createdby)
              if not is_namespaced_moniker → warn + skip
              if moniker_exists(args, moniker) → return moniker
              else:
                  try register_module_member(args, moniker)
                  except → warn + skip
          if daemon_member ready:
              call ChannelService.create_channel(...)
              if "already exists" → no-op (idempotent re-run)
              else if not success → warn + skip
```

The namespaced daemon member (e.g. `zoid6:casino`) is created via
`register_module_member` which bypasses the standard reservation
check by requiring namespaced-lowercase-shape. See
[Namespacing convention](#namespacing).

## Namespacing convention

Four layers of defense prevent human/machine moniker collisions:

1. **SQL regex.** `chk_member_moniker_format` allows
   `^[a-zA-Z0-9_]+(?::[a-zA-Z0-9_]+)?$` (was
   `^[a-zA-Z0-9_]+$` before the migration).
2. **Python validation.** `_validate_moniker_shape` rejects BOTH
   reserved flat names AND namespaced monikers from the standard
   `libmember.insert` path.
3. **Bypass path.** `register_module_member` accepts only
   namespaced-lowercase-shape; bypass is structural, not trust-based.
4. **Reserved list.** `RESERVED_MONIKERS = {"sysop", "term", "web",
   "bed"}` — only shipped PG role names. bbsengine6 does not reserve
   module-specific names; downstream installs that need additional
   reservations fork this constant or add their own gating layer.

| Layer | Fires when |
|---|---|
| SQL regex | Any `INSERT` / `UPDATE` on `engine.__member` |
| `_validate_moniker_shape` | Standard registration path (`console member add` → `libmember.insert`) |
| `register_module_member` | Module bootstrap code only (e.g. `channel.api.handler._auto_seed_channels`) |
| `RESERVED_MONIKERS` | Rejects flat-form names matching shipped roles |

The migration owner caveat: the `chk_member_moniker_format` ALTER
requires the connecting role to own `engine.__member`. In
production this is `sysop` (per the GRANT chain in
`sql/grants.sql` / `sql/member.sql` / `sql/channel.sql`). In dev
sandboxes the connecting role (e.g. `opencode`) may not own the
table; in that case the migration can't apply. This is a sandbox
limitation, not a code issue.

See `handbook/specs/member.md` and
`bbsengine6/EXTENDING_CHANNELS.md` for the namespacing extension
contract.

## Configuration

### `bed.json` — top-level `channel` block

```jsonc
{
  "channel": {
    "enabled": true,
    "modulepath": "bbsengine6.channel.api.handler",
    "description": "Channel service (pub/sub messaging, channel subscriptions, announce-only enforcement)",
    "admin_handler_enabled": true,
    "auto_seed": [
      {
        "name": "casino:global",
        "createdby": "zoid6:casino",
        "announce_only": false,
        "description": "Casino-wide announcement channel (open publishing)"
      },
      {
        "name": "system:announcements",
        "createdby": "zoid6:casino",
        "announce_only": true,
        "announcers": ["sysop"],
        "description": "System-wide announcements (sysop/announcer-only publishing)"
      }
    ]
  }
}
```

### `zoid6.json` — nested `services.channel` block

```jsonc
{
  "services": {
    "channel": {
      "enabled": true,
      "modulepath": "bbsengine6.channel.api.handler",
      "description": "Channel service (pub/sub messaging, channels)",
      "admin_handler": {
        "enabled": true,
        "verbs": [
          "channel_create",
          "channel_list",
          "channel_get",
          "channel_set_announce_only",
          "channel_add_announcer",
          "channel_remove_announcer"
        ]
      }
    }
  }
}
```

### Dual-shape read

`_resolve_channel_config` accepts either shape; flat (bed.json)
wins when both are present (defensive against accidental
duplication). This means the same code path works for both
deployment topologies.

### Auto-seed ownership caveat

`register_module_member` writes a row to `engine.__member`. The
connecting role must own the table. In production this is `sysop`
(granted via `channel.sql` lines 62-66). In the dev sandbox, the
connecting role (`opencode`) does not own `engine.__member`
(owned by `jam`), so the auto-seed path returns `None` and the
operator sees a `W: channel auto-seed: failed to create daemon
member 'zoid6:casino'; skipping channel seed. Check DB
permissions.` line. This is expected sandbox behavior; in
production it should never fire.

## CLI surface — `con channel <verb>`

The CLI is registered as a subcommand of the `con` console. Each
verb emits JSON to stdout and exits non-zero on failure so shell
scripts can detect via `$?`.

| Verb | Args | Behavior |
|---|---|---|
| `create <name>` | `--description, --announce-only, --announcer (repeatable), --moniker` | Calls `ChannelService.create_channel` with `--moniker` as `createdby` |
| `list` | `--limit, --offset, --announce-only {yes,no,any}` | Defaults: limit=100, offset=0, announce-only=any |
| `get <name>` | — | Returns the channel dict from `engine.channel` view |
| `set-announce-only <name> <value>` | value in `{true,1,yes,on}` (case-insensitive) | Calls `ChannelService.set_announce_only(name, value, by_moniker=moniker)` |
| `add-announcer <name> <moniker>` | `--moniker` is actor; second positional is target | Calls `ChannelService.add_announcer(name, target, addedby=moniker)` |
| `remove-announcer <name> <moniker>` | `--moniker` is actor; second positional is target | Calls `ChannelService.remove_announcer(name, target, actor_moniker=moniker)` |

Output envelope (success): `{"success": true, ...}`. Failure:
`{"success": false, "message": "..."}` with optional
`"code": "not_found"` / `"code": "not_authenticated"`.

The verb catalog mirrors the WS-side `ChannelAdminHandler` verbs.

Cross-ref `handbook/specs/console.md` for `con` dispatch conventions.

## WebSocket protocol

### Subscription verbs

| Verb | Direction | Request fields | Response |
|---|---|---|---|
| `subscribe_channel` | C→S | `channel: str` | `{type: "subscribed", channel, message}` |
| `unsubscribe_channel` | C→S | `channel: str` | `{type: "unsubscribed", channel, message}` |
| `get_subscriptions` | C→S | — | `{type: "subscriptions", channels: [...]}` |

### Admin verbs

| Verb | Direction | Request fields | Response |
|---|---|---|---|
| `channel_create` | C→S | `name, description?, announce_only?, announcers?` | `{type: "channel_create_result", success, channel?}` |
| `channel_list` | C→S | `limit?, offset?, announce_only?` | `{type: "channel_list_result", channels: [...], limit, offset}` |
| `channel_get` | C→S | `name` | `{type: "channel_get_result", channel}` or error |
| `channel_set_announce_only` | C→S | `name, value: bool` | `{type: "channel_set_announce_only_result", success, message?}` |
| `channel_add_announcer` | C→S | `name, moniker` | `{type: "channel_add_announcer_result", success, message?}` |
| `channel_remove_announcer` | C→S | `name, moniker` | `{type: "channel_remove_announcer_result", success, message?}` |

### Error envelope

```
{
  "type": "error",
  "code": "<one of not_authenticated | invalid_request | not_found | unknown_verb>",
  "message": "<optional human-readable detail>"
}
```

### Authentication

Every verb (subscription or admin) requires an authenticated
session. The actor moniker is resolved from
`MessageRouter.sessions.get_moniker(session_id)`. Admin
mutators delegate to `ChannelService._require_authority(channel_name,
actor_moniker)` for the sysop-or-creator check.

### Disconnection cleanup

When a WebSocket disconnects, `bed.main.BED.start`'s registered
router hooks fire:

```
WebSocketServer → router.unregister_session(session_id)
  └─ channel_unsubscribe_all(state, session_id)
  └─ sessions.unregister_session(session_id)
```

The session id is the transport-allocated `_bbsengine6_session_id`
when available, or `id(websocket)` as a fallback for unit tests
that pass mock websockets.

Cross-ref `handbook/specs/net-layer.md` (WebSocket transport) and
`handbook/specs/member.md` (session management).

## Extension guide for new modules

Five-step onboarding for any module that wants to publish or
subscribe to channels:

1. **Accept a shared `channel_state`.** Mirror
   `bed.main.BED.start`'s contract:

   ```python
   class MessageRouter:
       def __init__(self, args, *, channel_state=None, server=None, config=None, **kwargs):
           self.args = args
           self.channel_state = channel_state or ChannelState()
           self.server = server
           self.config = config or {}
   ```

2. **Plumb `sender_moniker` through `channel_publish`.** Use the
   `channel_publish(state, channel, message, server=...,
   sender_moniker=..., args=...)` signature directly. Without
   `sender_moniker`, the announce-only check is bypassed (which
   is correct for system-internal publishes but wrong for
   user-driven publishes).

3. **Use namespaced daemon members for service identities.** A
   module that needs a daemon identity (for auto-seeded channels
   whose `createdby` must be a real `engine.__member` row) uses
   `register_module_member(args, "<your-module>:<purpose>")`.

4. **Add entries to `bed.json` channel.auto_seed.** The
   `MessageRouter` runs the auto-seed step at register time. The
   `createdby` should be namespaced per your module.

5. **Read per-module config from `args.config_file`.** zoid6's
   `MessageRouter._register_module` forwards `config=module_config`
   to sub-router constructors. Routers read their `services.<module>`
   sub-config from it.

Also: use `bbsengine6.channel.naming.table_channel(app, moniker)` and
friends instead of inline `f"myapp:table:{moniker}"` literals. Single
source of truth.

bbsengine6 does not need to change to onboard a new module — the
existing primitives in `bbsengine6.net` and the namespacing
convention are designed to be reused. The `register_module_member`
bypass is the only path that accepts namespaced monikers, and it
requires the namespaced-lowercase-shape triple. Downstream
installations that need additional reservations fork
`RESERVED_MONIKERS` or add their own gating layer; bbsengine6
provides no config-driven extension hook.

Cross-ref `bbsengine6/EXTENDING_CHANNELS.md` for the full
onboarding walk-through.

## Operational notes

### Single `ChannelState` per daemon

`bed.main.BED.start` constructs one `ChannelState()` and passes it
to both `WebSocketServer(channel_state=state)` and
`MessageRouterClass(..., channel_state=state)`. Previously each
consumer built its own, leaving `server.publish()` reaching no
subscribers because the server's internal map was disconnected
from the router's. Now both see the same state.

The per-router `server._channel_state = self.channel_state`
boilerplate that `casino.api.handler.register_all` used to set is
deprecated — delete the line if you're upgrading an older router.

### Disconnection cleanup

`_session_id_for(websocket)` falls back to `id(websocket)` when the
websocket doesn't allow attribute assignment (mock websockets in
unit tests). Production websockets get the
`WebSocketServer`-allocated `_bbsengine6_session_id`.

### Channel publish failure semantics

Errors during WS send drop the dead websocket from `server._clients`
and explicitly close it to release the FD immediately rather than
waiting for garbage collection. The publish itself logs at
`WARN` but never raises.

Callback failures are logged at `ERROR` but do not abort the publish.
A single broken bot cannot affect a fan-out to other subscribers.

### Daemon startup is never blocked by auto-seed failures

Every layer of the auto-seed step has a warn-and-skip fallback. The
operator sees warning lines in the startup log but the daemon
starts anyway. This is intentional: a misconfigured `auto_seed`
entry is not a fatal error.

### Migration owner caveat

The `chk_member_moniker_format` migration runs `ALTER TABLE
engine.__member` which requires the connecting role to own the
table. In production this is `sysop` (per the GRANT chain in
`channel.sql` / `grants.sql`). In dev sandboxes where the
connecting role doesn't own the table, the migration can't apply.
The code path is correct; only the sandbox is limited.

To verify the migration in dev: log in as `jam` (or any table
owner) and run `python -m bbsengine6.startup` once. Subsequent
`opencode`-role startups will see the constraint already at the
namespaced pattern and skip.

## Test coverage

117 bbsengine6 + 5 casino tests passing against
`BBSENGINE6_CHANNEL_TEST_DBNAME=zoid6`.

| File | Tests | Coverage |
|---|---|---|
| `test_message_channel.py` | 33 | ChannelState primitives, WS fan-out, callback fan-out |
| `test_channel_announce_only.py` | 25 | CRUD + permission gates + publish gating + new creator-allowed cases |
| `test_member_reserved.py` | 23 | Namespacing + reservation policy + bypass shape checks |
| `test_channel_config.py` | 11 | Dual-shape config read + bypass path + warn-and-skip |
| `test_cli_con.py` | 15 | `con channel` argparse routing + `ChannelAdminHandler` allowed_verbs |
| `test_channel_naming.py` | 10 | Each helper produces the documented format; `parse_channel` roundtrips |
| `casino/tests/test_channel_integration.py` | 5 | Casino disconnect-cleanup + message-type registration |
| **Total** | **122** | all pass |

Run the suite:

```sh
cd bbsengine6/py
BBSENGINE6_CHANNEL_TEST_DBNAME=zoid6 \
    python -m pytest \
        tests/test_message_channel.py \
        tests/test_channel_announce_only.py \
        tests/test_member_reserved.py \
        tests/test_channel_config.py \
        tests/test_cli_con.py \
        tests/test_channel_naming.py \
    -v
```

`test_channel_announce_only.py` defaulted its DB to `zoid6test`;
the `BBSENGINE6_CHANNEL_TEST_DBNAME` env override lets the same
suite run against `zoid6` (which exists in the dev sandbox) or any
other target DB.

## Migration history

The 9-phase rollout (2026-09-05):

- **Phase 1.5** — `bbsengine6.backend.checkchannel` (stage_one
  bootstrap), `bbsengine6.member.lib.RESERVED_MONIKERS` /
  `is_namespaced_moniker` / `register_module_member`,
  `engine.__channel` + `engine.__channel_announcer` schema,
  `bed.json` `channel` block with `auto_seed`, `zoid6.json`
  `services.channel.admin_handler`.
- **Phase 1** — `bed.main.BED.start` constructs one `ChannelState()`
  per daemon and threads it to `WebSocketServer` and
  `MessageRouterClass`. Per-router `server._channel_state = ...`
  boilerplate removed.
- **Phase 5** — `ChannelService._require_authority` gates
  `set_announce_only` / `add_announcer` / `remove_announcer`. New
  `actor_moniker` parameter on `remove_announcer` (breaking change).
- **Phase 3** — `bbsengine6.net.defaultrouter.DefaultRouter`
  registers `bbsengine6.channel.api.handler.MessageRouter` in
  `register_all`, so any deployment using the default router
  exposes `subscribe_channel` / `unsubscribe_channel` /
  `get_subscriptions`.
- **Phase 2** — `casino.api.handler.BaseService` gains
  `_publish_to_table` / `_publish_global` helpers. Five
  `server.publish` call sites in `casino.api.handler` and the
  yahtzee / tictactoe `_broadcast` helpers all routed through
  `channel_publish` with `sender_moniker` and `args` attached.
- **Phase 4** — `bbsengine6.channel.api.handler.ChannelAdminHandler`
  exposes the six `channel_*` admin verbs. Registered
  conditionally on `channel_cfg.admin_handler.enabled`.
- **Phase 6** — `bbsengine6.channel.naming` with
  `table_channel` / `member_channel` / `global_channel` /
  `announcement_channel` / `shout_channel` / `parse_channel`.
- **Phase 7** — `bbsengine6.console.channel` `con channel <verb>`
  CLI. `zoid6.api.handler._register_module` forwards
  `config=module_config` to sub-routers with TypeError fallback.
- **Phase 7.5** — `bbsengine6/EXTENDING_CHANNELS.md` 7-step onboarding
  guide.
- **Phase 8** — Test expansion from 33 → 117.

Two bug fixes landed alongside:

- `add_announcer` was calling `verifyMemberFound` without the
  required `pool=` kwarg (pre-existing failure on legacy test
  runs). Replaced with inline existence check on the same
  connection as the INSERT.
- `register_module_member`'s bypass path was tripping on three
  layers of defense (shape validation, pool requirement, default
  `primarykey="id"` on a table that has no `id` column). Now
  threads `_skip_shape_validation=True`, builds its own
  `database.connect` context when no caller pool/conn is given,
  and defaults to `primarykey="moniker"`.

Plus a startup fix: `chk_member_moniker_format` migration was
inlined in `member.sql`, but `checkclasses` only reloads that file
when `engine.__member` doesn't exist (which is never on existing
DBs). Extracted to a dedicated `checkmember_moniker_format.sql` +
`checkmember_moniker_format.py` module that runs every startup;
the inline block in `member.sql` was removed.

## See also

- [`handbook/specs/net-layer.md`](./net-layer.md) — WebSocket
  transport, the underlying `ChannelState` container lives here.
- [`handbook/specs/messaging.md`](./messaging.md) — orthogonal
  message subsystem, similar DAL pattern but independent storage.
- [`handbook/specs/member.md`](./member.md) — `issysop`,
  `verifyMemberFound`, session management, namespacing
  reservation.
- [`handbook/specs/console.md`](./console.md) — `con` CLI dispatch
  conventions.
- [`handbook/specs/database.md`](./database.md) —
  `database.connect` / `database.query` / `database.insert`
  helpers used throughout.
- [`handbook/specs/architecture.md`](./architecture.md) — package
  layering and cross-module dependencies.
- [`bbsengine6/EXTENDING_CHANNELS.md`](../../py/src/bbsengine6/EXTENDING_CHANNELS.md)
  — onboarding guide for new modules.
- [`bbsengine6/TODO_BBSENGINE6_CHANNEL.md`](../../TODO_BBSENGINE6_CHANNEL.md)
  — full implementation plan.
- [`bbsengine6/CHANGELOG.md`](../../CHANGELOG.md) — Phase 6 entry
  with per-commit history.
