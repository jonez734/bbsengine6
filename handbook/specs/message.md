# bbsengine6.message — messaging subsystem

> **Status:** canonical. Phase 11 (2026-09-01). Replaces the deleted
> `bbsengine6.notify` / `bbsengine6.message_delivery` packages
> (2026-07-22). See `bbsengine6/TODO-message-migration.md` for the
> full migration history.

The `bbsengine6.message` package is the single source of truth for
channel-based pub/sub with PostgreSQL persistence, rate limiting,
blocking, recipient groups, templating, and a per-member unread
counter. Consumers (bed, casino, empyre, the bottombar F2
notification, the message CLI) call into this package; the old
notify / message_delivery APIs are gone.

## Contents

- [Layered architecture](#layered-architecture)
- [Public API](#public-api)
- [DAL contract](#dal-contract)
- [Recipient resolution](#recipient-resolution)
- [Rate limiting and blocking](#rate-limiting-and-blocking)
- [Templates](#templates)
- [CLI](#cli)
- [Module API and `access()`](#module-api-and-access)
- [SQL surface](#sql-surface)
- [Migration history](#migration-history)

## Layered architecture

Phase 11 (2026-09-01) split the package into four layers that
mirror `casino`'s four-layer architecture (see `casino/SPEC.md` §3):

| Layer       | Module                                            | Role                                                                                          |
|-------------|---------------------------------------------------|-----------------------------------------------------------------------------------------------|
| **Service** | `bbsengine6.message.service`                      | Business orchestration. Enable/disable gate, rate-limit gating, blocking filter, recipient expansion, legacy `send` shim |
|             | `bbsengine6.message.lib`                          | Public re-export facade + `Message` dataclass, `MessageUrgency` enum, DB helpers              |
| **DAL**     | `bbsengine6.message.dal.messages`                 | `engine.__message`, `engine.__message_recipient` I/O                                          |
|             | `bbsengine6.message.dal.recipients`               | `engine.__message_group_member` expansion (`@group`, `@everyone`)                             |
|             | `bbsengine6.message.dal.groups`                   | `engine.__message_group[_member]` I/O                                                         |
|             | `bbsengine6.message.dal.blocking`                 | `engine.__message_block` I/O                                                                  |
|             | `bbsengine6.message.dal.ratelimit`                | `engine.__message_rate_limit`, `engine.__message_type` reads                                  |
|             | `bbsengine6.message.dal.types`                    | `engine.__message_type` writes                                                                |
|             | `bbsengine6.message.dal._pool`                    | CONN_POOL_PATTERN helper + `information_schema.tables` probe                                  |
| **State**   | `bbsengine6.message.cache`                        | In-memory local unread counter (no DB)                                                        |
| **Domain**  | `bbsengine6.message.templates`                    | `{var}` / `$var` template rendering                                                           |
|             | `bbsengine6.message.access` (in `__init__.py`)    | Per-op authorization (`subscribe` / `unsubscribe` / `list_pending`)                           |

The DAL never imports `psycopg` directly; all DB plumbing goes
through `bbsengine6.database`. Services call DAL methods; DAL
executes queries; the engine layer never makes direct database
calls. The local unread cache in `cache.py` is not a DAL module
because it has no DB I/O — it sits at the package root so the DAL
contract stays "talks to Postgres only".

## Public API

The full public surface is re-exported from
`bbsengine6.message.lib` and wildcard-imported into
`bbsengine6.message.__init__`. `from bbsengine6.message import <name>`
resolves any name listed below.

### Dataclasses and enums

| Name              | Definition                              | Notes                                                          |
|-------------------|-----------------------------------------|----------------------------------------------------------------|
| `Message`         | `dataclass` (id, channel, sender_moniker, content, data, urgency, template, template_vars, datestamp) | `timestamp` and `recipients` are derived properties            |
| `MessageUrgency`  | `Enum(ROUTINE, IMPORTANT, URGENT, CRITICAL)` | Coerced to str via `_coerce_urgency` at the service boundary   |

### Persistence and delivery

| Function                              | Signature                                                                                                          | Notes                                                                                       |
|---------------------------------------|--------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| `send`                                | `send(notification_type, recipients, template, template_vars=None, sender_moniker=None, data=None, urgency=None, should_persist=True, args=None, **kwargs) -> int` | Legacy `message_delivery.send` shim. Returns `engine.__message.id`, or `0` if disabled / rate-limited / no recipient survived expansion |
| `store_message`                       | `store_message(channel, sender_moniker, content, recipient_monikers=None, data=None, urgency="ROUTINE", template=None, template_vars=None, database=None) -> int` | Thin wrapper over `store_message_with_checks` returning the new message id                  |
| `store_message_with_checks`           | returns `dict{message_id, rate_limit_ok, recipients_stored, recipients_blocked, recipients_skipped}`                | The full-diagnostics variant used by `net/integration.py` and the bed `MessageRouter`        |
| `get_pending_messages`                | `get_pending_messages(moniker, limit=50, database=None) -> List[dict]`                                              | Datestamp-DESC, status IN (`pending`, `delivered`)                                          |
| `get_pending_messages_prioritized`    | `get_pending_messages_prioritized(moniker, limit=50, database=None) -> List[dict]`                                  | CRITICAL/URGENT/IMPORTANT/ROUTINE order then datestamp-DESC                                 |
| `deliver_pending_on_connect`          | `deliver_pending_on_connect(moniker, database=None) -> List[dict]`                                                  | Prioritized; calls `mark_delivered` on every row returned                                   |
| `mark_delivered`                      | `mark_delivered(message_id, moniker, database=None)`                                                               | UPDATE `engine.__message_recipient` SET status='delivered', datedelivered=now()             |
| `mark_read`                           | `mark_read(message_id, moniker, database=None)`                                                                    | UPDATE `engine.__message_recipient` SET status='read', dateread=now()                       |
| `expunge`                             | `expunge(message_id, sender_moniker, database=None) -> bool`                                                        | Sender-side hard delete; FK CASCADE removes recipient rows                                   |
| `get_queue`                           | `get_queue(moniker, database=None) -> List[dict]`                                                                  | Legacy notify-era API; thin wrapper around `get_pending_messages(..., limit=1000)`           |
| `get_urgent`                          | `get_urgent(moniker, limit=50, database=None) -> List[dict]`                                                        | `urgency IN ('URGENT', 'CRITICAL')`, ordered by urgency bucket then datestamp               |
| `get_unread_count`                    | `get_unread_count(moniker, database=None, *, args=None, pool=None, conn=None) -> int`                              | DB-side COUNT; returns `0` and logs a warning when `engine.__message_recipient` is missing  |

### Recipient resolution

| Function                  | Signature                                                                                        | Notes                                                                                                                              |
|---------------------------|--------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| `resolve_recipients`      | `resolve_recipients(recipients, database=None) -> List[str]`                                     | Expands `@group_name` and `@everyone` references; depth cap 10; dedups by first occurrence                                          |
| `member.group_exists`     | `bbsengine6.member.group_exists(args, group_name, **kwargs) -> bool|None`                       | Survives from the deleted notify package; validates format and queries `engine.__message_group`                                     |
| `member.get_group_members`| `bbsengine6.member.get_group_members(args, group_name, **kwargs) -> List[str]|None`             | Survives from the deleted notify package; recursive expansion with cycle detection                                                |

### Enable / disable and unread cache

| Function                      | Signature                                                | Notes                                                                       |
|-------------------------------|----------------------------------------------------------|-----------------------------------------------------------------------------|
| `is_enabled`                  | `() -> bool`                                             | Module-level boolean; defaults `True`                                       |
| `enable`                      | `() -> None`                                             | Set the module-level boolean to `True`                                      |
| `disable`                     | `() -> None`                                             | Set the module-level boolean to `False` (every service returns early/empty) |
| `get_local_unread_count`      | `(moniker) -> int`                                       | Process-local cache; `-1` means "never read"                                |
| `set_local_unread_count`      | `(moniker, count) -> None`                               | Write to the cache (clamped `>= 0`)                                         |
| `bump_local_unread_count`     | `(moniker, delta=1) -> None`                             | Atomic update                                                               |
| `clear_local_unread_cache`    | `() -> None`                                             | Reset the cache (used by tests)                                            |

### Groups and blocking

| Function                    | Signature                                                                                                  | Notes                                                              |
|-----------------------------|------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| `create_message_group`      | `create_message_group(name, createdby=None, description=None, database=None) -> int`                      | INSERT into `engine.__message_group`; returns new id               |
| `add_to_message_group`      | `add_to_message_group(group_id, member_moniker, addedby=None, database=None) -> bool`                     | Idempotent INSERT (ON CONFLICT DO NOTHING)                          |
| `remove_from_group`         | `remove_from_group(group_id, member_moniker, database=None) -> bool`                                      | DELETE; returns `True` if a row was removed                         |
| `get_message_group_members` | `get_message_group_members(group_id, database=None) -> List[str]`                                         | SELECT member_moniker rows                                          |
| `get_user_groups`           | `get_user_groups(moniker, database=None) -> List[dict]`                                                   | Groups the user belongs to                                          |
| `block_sender`              | `block_sender(blocker_moniker, blocked_moniker, database=None) -> bool`                                   | Idempotent INSERT into `engine.__message_block`                     |
| `unblock_sender`            | `unblock_sender(blocker_moniker, blocked_moniker, database=None) -> bool`                                 | DELETE                                                              |
| `is_blocked`                | `is_blocked(blocker_moniker, blocked_moniker, database=None) -> bool`                                    | `True` iff a row exists for the pair                                |
| `get_blocked`               | `get_blocked(moniker, database=None) -> List[str]`                                                       | Inverse of `is_blocked`: blocker monikers who have blocked `moniker`|

### Rate limiting

| Function                          | Signature                                                                                  | Notes                                                                                |
|-----------------------------------|--------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| `check_rate_limit`                | `check_rate_limit(sender_moniker, message_type, database=None) -> Tuple[bool, int]`         | Returns `(allowed, remaining)`; `0` per-hour limit means unlimited                    |
| `record_message_sent`             | `record_message_sent(sender_moniker, message_type, database=None) -> bool`                  | UPSERT into `engine.__message_rate_limit` for the current hour bucket                  |
| `set_rate_limit`                  | `set_rate_limit(type_name, limit, database=None) -> bool`                                  | Idempotent UPDATE-or-INSERT on `engine.__message_type.rate_limit_per_hour`            |
| `get_message_type_rate_limit`     | `get_message_type_rate_limit(message_type, database=None) -> int`                          | `0` if the type is not registered                                                    |

### Type registration (legacy shims)

| Function                  | Signature                                                                                                                                  | Notes                                                                                        |
|---------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| `register_type`           | `register_type(type_name, description="", rate_limit_per_hour=0, requires_approval=False, database=None) -> bool`                          | UPSERT into `engine.__message_type`                                                            |
| `register_type_compat`    | `register_type_compat(type_name, urgency=None, max_per_user_per_hour=0, persist_by_default=True, args=None, **kwargs) -> bool`             | Adapter that accepts the legacy `message_delivery.register_type` positional signature         |
| `get_types`               | `get_types(database=None) -> List[dict]`                                                                                                    | Every registered type, sorted by `type_name`                                                  |

### Templates

| Function                            | Signature                                                                | Notes                                                       |
|-------------------------------------|--------------------------------------------------------------------------|-------------------------------------------------------------|
| `render_template`                   | `render_template(template, variables) -> str`                            | `{var}` and `$var` substitution                             |
| `render_message_content`            | `render_message_content(content, template, template_vars) -> str`        | Picks `template`+`template_vars` when both are given         |
| `parse_variables_from_content`      | `parse_variables_from_content(content) -> List[str]`                     | Extracts every `{var}` / `$var` name used                    |
| `get_builtin_variables`             | `() -> Dict[str, Any]`                                                   | `year`, `month`, `day`, `hour`, `minute`, `timestamp`, `date`, `time` |
| `validate_template`                 | `validate_template(template) -> Tuple[bool, List[str]]`                  | Returns `(is_valid, errors)` for brace and `$var` mismatches |

## DAL contract

`bbsengine6.message.dal.*` is pure Postgres I/O. Modules never
import `psycopg`; every connection goes through `bbsengine6.database`
(via `_connect_ctx(args, pool)` in `dal/_pool.py`). The DAL also
provides a generic `table_exists(cur, schema, table)` helper that
runs a single `information_schema.tables` SELECT and never raises
— it returns `False` on any exception so a probe failure cannot
mask the caller's intent. This is what `get_unread_count` uses to
distinguish "zero unread" from "missing schema" when the
bootstrap hasn't run yet.

| Module            | Owns                                                                                                |
|-------------------|-----------------------------------------------------------------------------------------------------|
| `messages.py`     | `engine.__message`, `engine.__message_recipient` I/O                                                |
| `recipients.py`   | `engine.__member` (for `@everyone` expansion) and `engine.__message_group` (for `@group` lookups)   |
| `groups.py`       | `engine.__message_group`, `engine.__message_group_member` I/O                                       |
| `blocking.py`     | `engine.__message_block` I/O                                                                         |
| `ratelimit.py`    | `engine.__message_rate_limit` reads/writes; `engine.__message_type` reads                          |
| `types.py`        | `engine.__message_type` writes (`upsert`, `set_rate_limit`, `list_all`)                              |
| `_pool.py`        | `_connect_ctx(args, pool)` + `table_exists(cur, schema, table)`                                     |

Async DAL is not yet provided. The current implementation is fully
sync (via `bbsengine6.database.getpool` / `pool.connection()`); an
async counterpart under `bbsengine6.message.dal.aio/` would mirror
`casino/dal/aiosql/` once a consumer needs it.

## Recipient resolution

`resolve_recipients(recipients, database=None, sender_moniker=None,
source="member")` is the canonical recipient expansion path. It runs at the
service boundary (in `store_message_with_checks`) so callers can pass
`@group_name` or `@everyone` and get notify-style expansion transparently:

```
@everyone   -> SELECT moniker FROM engine.__member WHERE approved = TRUE
@group_name -> SELECT id FROM engine.__message_group WHERE name = ...
            -> SELECT member_moniker FROM engine.__message_group_member
               WHERE group_id = ...
alice       -> "alice"  (literal)
```

Expansion is recursive (depth cap 10) so nested groups work; the
`@everyone` token is case-insensitive (`@Everyone` works the same
as `@everyone`). The returned list preserves the first-seen order
with duplicates removed.

### Message source

Every message carries a `source` (the `engine.__message.source` column,
default `member`):

| Source | Meaning | Group rule |
|---|---|---|
| `member` | a logged-in sender (`sender_moniker` set) | unchanged: no source check |
| `operator` | CLI or no identity | unchanged: no source check |
| named, e.g. `casino.dealer:<table>`, `postoffice` | a system sender | may address only groups under a registered prefix; never `@everyone` |

A named source is registered in `engine.__message_source`
(`source`, `group_prefix`). A registration covers a group when the
group name equals the prefix or starts with `prefix:`, so prefix
`table` covers `table:jam`. An unregistered named source addresses
nothing. A refused group raises `PermissionError`, which
`store_message_with_checks` reports as `denied_reason`.

`store_message`, `store_message_with_checks`, and `send` accept
`source=`. Callers that do not pass it are tagged `member`.

Schema note: `sql/message.sql` and `sql/message_groups.sql` are the
source of truth. An existing installed database is not altered by
these files; the `source` column and `engine.__message_source` must be
created by hand (or the database recreated) on installs made before
this change.

The surviving `member.group_exists` and `member.get_group_members`
functions in `py/src/bbsengine6/member/lib.py` cover member
validation and recursive group expansion at the `bbsengine6.member`
package boundary. They are *not* a transport layer — they only
read `engine.__message_group` and `engine.__message_group_member`.
`resolve_recipients` is the message-system path; `member.get_group_members`
is the validation/lookup path. They share the same table family
but have different consumers.

## Rate limiting and blocking

Every `store_message_with_checks` call (and therefore every
`store_message` / `send`) runs through `_check_blocking_and_ratelimit`
in `bbsengine6.message.service`:

1. **Rate limit** — when `sender_moniker is not None`,
   `check_rate_limit(sender_moniker, channel, database=...)` is
   called. A `0` `rate_limit_per_hour` (or an unregistered type)
   means "unlimited" (`(True, 999)`). On deny the message is
   rejected before any DB writes and the result dict's
   `message_id` is `0`.
2. **Blocking** — for every recipient, `is_blocked(recipient,
   sender_moniker)` is consulted. Blocked pairs are skipped
   silently and accumulated into `recipients_blocked` /
   `recipients_skipped` in the diagnostics dict.
3. **Recording** — after a successful insert,
   `record_message_sent(sender_moniker, channel, ...)` bumps the
   current hour bucket's `engine.__message_rate_limit.message_count`.

`block_sender` / `unblock_sender` / `is_blocked` / `get_blocked`
are direct UIs onto `engine.__message_block` and are exposed for
caller-supplied blocks UI / CLI work.

## Templates

`bbsengine6.message.templates` is pure rendering (no I/O, no
policy). Two syntaxes are accepted in the same template:

- `{var_name}` — curly-brace substitution. Looks up
  `var_name` in the variables dict and substitutes `str(var_value)`.
- `$var_name` — dollar substitution. Same lookup, no braces.

`render_template(template, variables)` walks the variables dict
once and applies both substitutions to a single result string. The
dollar form is positional: `$varname` is replaced; `$ varname`
(with a space) is not. Unknown variables are not an error — they
simply do not match either pattern.

`validate_template(template)` returns `(is_valid, errors)` where
`errors` lists brace mismatches, dollar mismatches, and any
malformed `{` tokens (e.g. `{1foo}`).

`get_builtin_variables()` returns a fresh dict on every call with
the current wall-clock time:

| Key         | Value                            |
|-------------|----------------------------------|
| `year`      | `datetime.now().year`            |
| `month`     | `datetime.now().month`           |
| `day`       | `datetime.now().day`             |
| `hour`      | `datetime.now().hour`            |
| `minute`    | `datetime.now().minute`          |
| `timestamp` | `datetime.now().isoformat()`     |
| `date`      | `datetime.now().strftime("%Y-%m-%d")` |
| `time`      | `datetime.now().strftime("%H:%M:%S")` |

**Templates are rendered on the sending client, not by the daemon.**
The bed CLI renders `--template` with `--var k=v` before it sends
(`bed/src/bed/tools/message.py`, `_resolve_send_content`). The
shell's `message` command takes literal `--body` text. Either way
the daemon receives only rendered `content`, and the verb has no
`template` or `template_vars` fields. A message sent through bed or
the shell is stored with its rendered text, and its `template` and
`template_vars` columns are NULL. Only the operator CLI's `send`
and the library's `store_message` / `send` store a template name
and variables.

## CLI

`python -m bbsengine6.message` (or `python -m bbsengine6.message.cli`)
runs the operator CLI. The default program name is `bbsengine6-msg`.

| Subcommand         | Args                                                       | Mutating? |
|--------------------|------------------------------------------------------------|-----------|
| `list-types`       | —                                                          | no        |
| `pending`          | `moniker [--limit N]` (default 50)                         | no        |
| `unread`           | `moniker`                                                  | no        |
| `mark-read`        | `moniker --message-id N [--yes]`                           | yes       |
| `mark-delivered`   | `moniker --message-id N [--yes]`                           | yes       |
| `expunge`          | `--message-id N --sender MONIKER [--yes]`                  | yes       |
| `register-type`    | `type_name [--description TEXT] [--rate-limit N] [--requires-approval] [--yes]` | yes |
| `resolve`          | `--to TOKEN [--to TOKEN ...]`                              | no        |
| `send`             | `--to TOKEN [--to TOKEN ...] --type TYPE --body BODY [--sender MONIKER] [--urgency U] [--vars k=v] [--dry-run] [--yes]` | yes |

`--type` is required for `send`; there is no default channel.
`--urgency` takes `ROUTINE`, `IMPORTANT`, `URGENT`, or `CRITICAL`
(default `ROUTINE`). `--rate-limit` defaults to `0`, which means
unlimited.

`--yes` is required before a mutating subcommand writes. Without
it the command refuses and prints `… pass --yes`. `send --dry-run`
renders and resolves recipients without calling `send`, and does
not need `--yes`.

`send --to @everyone` is a privilege gate, not a confirmation:
the CLI calls `issysop` (`bbsengine6.backend.lib`) against the
connected DB role and refuses unless `current_user` is in the
`sysop` pg role. `--to` accepts comma-separated tokens
(`alice,bob`) and may be repeated.

`--database` overrides `$BBSENGINE6_DBNAME` (default `zoid6`).

### Client commands

These call the bed daemon and do not need database access. They
send with the signed-in member's token, so the sender is never
taken from the command line.

**Bed CLI** (`message`, installed from the `bed` package):

```
message send --account alice --to bob --content "hello from alice"
```

- The subcommand comes first. Common flags (`--account`,
  `--token-file`, `--moniker`) go after it, as in the example.
- `send` runs through the daemon by default. `--direct` stores
  through the local database instead.
- `--channel` defaults to `cli.message`. `--urgency` defaults to
  `ROUTINE`. `--to` may be repeated.
- The body is `--content TEXT`, or `--template` with `--var k=v`.
  A `--template` is rendered by this CLI before the send, so the
  daemon stores the rendered text only.

**Shell** (`message`, inside a `shell` session):

```
message --to bob --body "hello from alice"
```

- The shell sends on the `member:direct` channel with urgency
  `ROUTINE`. `--to` accepts comma-separated monikers, and may be
  repeated. `--urgency` may be given.

Note that the two clients default to different channels
(`cli.message` in the bed CLI, `member:direct` in the shell).

Each login has its own token file. `--account NAME` reads
`bed-NAME.token` beside the default token file; `--token-file`
overrides it. See bed's handbook for the token file rules.

## Module API and `access()`

`bbsengine6.message` is a first-class module under the bbsengine6
module registry. `bbsengine6.message.init(args)` registers
`bbsengine6.message` with `apis={"access": access}` so the
loader can resolve the per-op authorization policy via
`bbsengine6.get_module_api("bbsengine6.message", "access")`.

`access(args, op, /, **kwargs)` authorizes `op` for the given
session/message pair. Recognized op values:

| `op`            | Required `message` keys | Returns `True` when                                |
|-----------------|-------------------------|-----------------------------------------------------|
| `subscribe`     | `moniker`               | the target `moniker` is non-empty and session.is_sysop is True, or session.moniker equals the target |
| `unsubscribe`   | `moniker`               | (same as `subscribe`)                               |
| `list_pending`  | `moniker`               | (same as `subscribe`)                               |
| `send`          | `sender`                | the `sender` is non-empty and session.is_sysop is True, or session.moniker equals the sender |

`send` is self-only: a member may send only as themselves, and a
sysop may send as anyone. The sender is the `sender` field of the
message; bed takes the actual sender from the session token, so the
wire field is only checked against the session here.

A `session` of `None` (an unbound websocket) is always denied, and
so is any op not listed above.

At module-load time (`bbsengine6.module.check` calls with
`op="run"` and no `session` kwarg), `access` returns `True` for
everyone; the per-op rules only fire when the caller passes a
`session` kwarg. The function does NOT perform input validation
(moniker or sender present, non-empty); that's the caller's job,
sitting next to the wire-envelope shape checks.

### bed `message_send` verb

bed exposes sending over its WebSocket as the `message_send` wire
type, handled by `bed.api.message` (`_handle_send`). The request
carries `recipients`, `content`, and optionally `channel` (default
`member:direct`) and `urgency` (default `ROUTINE`; `IMPORTANT`,
`URGENT`, and `CRITICAL` are the other values). The reply is
`message_send_result`, with `message_id` on success.

The verb does not take a sender. It passes the SHA-256 digest of
the session token to `engine.bed_message_send`, which reads the
sender from the session row. It refuses an empty recipient list
(`missing_recipients`) and empty content (`missing_content`), and
returns `not_sent` when no recipient survives expansion or the rate
limit is reached. Groups (`@group`) and `@everyone` are expanded by
the SQL function; `@here` is refused.

The verb takes `content` only. It has no template fields; templates
are rendered by the client first (see [Templates](#templates)).

## SQL surface

The schema lives under `py/src/bbsengine6/sql/`:

| File                              | Purpose                                                                                  |
|-----------------------------------|------------------------------------------------------------------------------------------|
| `message.sql`                     | `engine.__message`, `engine.__message_recipient`, supporting indexes                     |
| `message_groups.sql`              | `engine.__message_group`, `engine.__message_group_member`                                 |
| `message_type.sql`                | `engine.__message_type`                                                                  |
| `message_rate_limit.sql`          | `engine.__message_rate_limit`                                                            |
| `message_block.sql`               | `engine.__message_block`                                                                 |
| `message_enum.sql`                | `urgency` enum (ROUTINE / IMPORTANT / URGENT / CRITICAL)                                 |
| `messageview.sql`                 | `engine.message`, `engine.message_unread`, `engine.message_urgent`, `engine.message_blocked` |
| `migrate_notify_to_message.sql`   | One-time migration of legacy notify tables (already-migrated clusters skip)               |

Bootstrap verification is performed by
`py/src/bbsengine6/backend/checkmessage.py`, which is called by
`backend.stage_one.main()` during `bbsengine6.startup`.

## Migration history

The full Phases 1-11 checklist is in
`bbsengine6/TODO-message-migration.md`. The short version:

- **Phase 1-2 (2026-07-22):** gap-fills (`remove_from_group`,
  `get_blocked`, `get_urgent`, `expunge`, `get_queue`, recipient
  expansion, `set_rate_limit`, `register_type`, `get_types`,
  `Message` dataclass, `MessageUrgency` enum) plus the four
  `engine.message*` views.
- **Phase 3 (2026-07-22):** all consumers (io/getch.py,
  io/echo.py, bottombar.py, member/lib.py, net/integration.py,
  net/transport.py) migrated off the deleted notify package.
- **Phase 4 (2026-07-22):** backend bootstrap updated
  (`checkmessage` is now the canonical message-system check).
- **Phase 5-6 (2026-07-22):** test infrastructure refreshed;
  `migrate_notify_to_message.sql` provided for opt-in data
  migration.
- **Phase 7 (2026-07-22):** `bbsengine6.notify` and
  `bbsengine6.message_delivery` packages deleted along with the
  SQL files, daemons, examples, and test files. Only
  `member.moniker_exists`, `member.group_exists`, and
  `member.get_group_members` survived.
- **Phase 8-9 (2026-08):** channel/sub system quality fixes
  (`store_message_with_checks` with blocking + rate limit,
  urgency-first delivery, real `send_to_remote`, etc.); router's
  last `notify.send()` call site routed through
  `message.store_message`.
- **Phase 10 (2026-08-04):** the `send(...)` and
  `register_type_compat(...)` shims landed so casino and other
  downstream game packages stay importable after Phase 7.
- **Phase 11 (2026-09-01):** layered package refactor. The
  package surface (`from bbsengine6.message import <name>`) is
  unchanged; the implementation moved to
  `bbsengine6.message.{service,dal.*,cache,templates,lib}`.

### Who may address a named group

A named group (`@name`) is addressable only by:

| Sender | May address `@name` |
|---|---|
| a `member` who belongs to the group | yes |
| a `member` who does not belong to the group | no (`PermissionError`) |
| a sysop (`issysop`) | yes, any group |
| an `operator` (CLI, no sender) | yes, any group |
| a named source (e.g. `casino.dealer:<table>`) | only groups under a prefix it is registered for |

`@everyone` keeps its own rule: a sysop (or a role listed in
`everyone_allowed_roles`) only, and never a named source.

The check runs in `resolve_recipients` before the group is expanded, so a
refused group raises `PermissionError` and nothing is stored. Membership is
read from `engine.__message_group_member` (`dal.groups.is_member`).

### Table message groups (casino)

Casino creates one group per table, named `table:<moniker>`. The group is
owned by casino (`casino/tablegroups.py`); bbsengine6 stores and expands it
like any other group. A table's bot dealer posts as the named source
`casino.dealer:<moniker>`, registered for the prefix `table:<moniker>`.

**Implemented here:** a named source may address only the group prefixes it is
registered for (see *Message source* above).

**Not yet implemented:** a rule that a member may send to `@table:<moniker>`
only while seated at that table. Today nothing in `resolve_recipients` checks
seating, so any sender can address a table group that the source rule allows.
Until the seated-only check lands, treat `table:` groups as readable by anyone
who can send, and do not rely on them for privacy.

### Live-database test isolation

Calls through `bbsengine6.message.service` (group creation, membership, the
source registry) open their own connections. A test that runs them inside a
rolled-back transaction on the DAL alone does not isolate them, and their
writes commit to the live database. `casino.tablegroups.reconcile` deletes
every `table:` group whose table is not in its `table_monikers` argument, so
calling it with a partial list against a live database removes real groups.
Run such checks against a database that holds no real data, or pass the full
list of existing tables.
