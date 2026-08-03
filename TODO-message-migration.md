# TODO: Migrate from notify to message.py

Replace the `bbsengine6.notify` / `bbsengine6.message_delivery` system with
`bbsengine6.message`. Both currently coexist with separate DB tables.

## Background

- `notify` (canonical: `message_delivery/lib.py`, 1518 lines) is the mature
  notification system with DB persistence, HMAC tamper protection, in-memory
  queues, TUI, daemon, and delivery handlers.
- `message.py` (815 lines) is the newer channel-based pub/sub system with its
  own DB tables (`__message*`), groups, blocking, rate limiting, and templating.
- `notify/__init__.py` re-exports everything from `message_delivery`.
- `getch.py` and `bottombar.py` already try `message.py` first, fall back to
  `notify`.
- `TODO.md:82-84`: "Message system replaces and absorbs notify (persistence,
  groups, rate limiting, blocking). The old notify system becomes delivery
  mechanisms (email daemon, SMS) that subscribe to message channels."

## Phase 1: Fill gaps in message.py

These notify features have no equivalent in message.py and must be added
before consumers can fully migrate. **STATUS: COMPLETE** (all 10 items
implemented 2026-07-22; see `py/tests/test_message_phase1_gaps.py`
for unit coverage of every new function).

- [x] **`remove_from_group(group_id, moniker, conn=)`** — remove a member
      from a message group. Implemented at `py/src/bbsengine6/message.py`
      after `add_to_message_group`. Returns `bool` (`True` if a row was
      removed). Honors `_message_enabled` flag.
- [x] **`get_blocked(moniker, conn=)`** — list who has blocked this sender.
      Implemented at `py/src/bbsengine6/message.py` after `is_blocked`.
      Returns `List[str]` of blocker monikers (the inverse of
      `is_blocked`: rows where `blocked_moniker = moniker`).
- [x] **`get_urgent(moniker, limit, conn=)`** — get URGENT/CRITICAL unread messages.
      Implemented at `py/src/bbsengine6/message.py` after
      `get_unread_count`. Returns the same dict shape as
      `get_pending_messages`; pre-filters on
      `urgency IN ('URGENT', 'CRITICAL')`; orders by urgency bucket
      (CRITICAL first) then datestamp.
- [x] **`expunge(message_id, sender_moniker, conn=)`** — sender-side hard
      delete of a message. Implemented at `py/src/bbsengine6/message.py`.
      `DELETE FROM engine.__message WHERE id = %s AND sender_moniker = %s`
      (the FK from `__message_recipient` is `on delete cascade`).
      Returns `bool` (`True` on actual deletion).
- [x] **`get_queue(moniker, conn=)`** — return pending messages for a user as
      a list of message-like objects (or dicts). Implemented as a thin
      wrapper around `get_pending_messages(..., limit=1000)`. The
      `io/getch.py:_show_pending_notifications` call site
      (line 555) now resolves correctly.
- [x] **`MessageUrgency`-like enum** — `class MessageUrgency(Enum)` with
      `ROUTINE`, `IMPORTANT`, `URGENT`, `CRITICAL` at
      `message.py:25`.
- [x] **`Message` dataclass** — at `message.py:33`, exposing `id`,
      `channel`, `sender_moniker`, `content`, `data`, `urgency`,
      `template`, `template_vars`, `datestamp`, plus derived
      `timestamp` (epoch seconds) and `recipients` properties.
- [x] **`@group` / `@everyone` recipient expansion** — new
      `resolve_recipients(recipients, conn=)` at `message.py`.
      `store_message` now invokes it on the inbound recipient list
      before the rate-limit / blocking checks, so callers can pass
      `@group_name` and `@everyone` and get the notify-style
      expansion transparently. `engine.__message_group` is used
      for named-group lookups; the depth cap (10) prevents
      infinite loops in malformed group chains.
- [x] **`set_rate_limit(type_name, limit, conn=)`** — runtime rate limit
      adjustment. UPSERT into `engine.__message_type`. Idempotent.
- [x] **`register_type(type_name, ..., conn=)` / `get_types(conn=)`** —
      runtime type registration / listing. `register_type` UPSERTs
      with full field set (`description`, `rate_limit_per_hour`,
      `requires_approval`); `get_types` returns a list of dicts
      sorted by `type_name`.

## Phase 2: Add SQL views for message tables

message.py has no SQL views. notify has 4 views that consumers may depend on.
**STATUS: COMPLETE**

- [x] Create `sql/messageview.sql` with views:
  - [x] `engine.message` — joins `__message` with `__message_recipient` and
        `__message_type`, exposing rendered content, urgency, status, and
        local-tz date columns (matching the `engine.notify` view pattern).
  - [x] `engine.message_unread` — filtered view for `status = 'pending'`.
  - [x] `engine.message_urgent` — filtered view for urgent/critical + unread.
  - [x] `engine.message_blocked` — view of blocked sender/recipient pairs.
- [x] Add views to `checkmessage.py` classlist.
- [x] Add `messageview.sql` to `conftest.py:_get_message_sql_files()` (or
      equivalent).
- [x] Create `sql/message_enum.sql` to install the urgency enum without
      requiring the notify system.

## Phase 3: Update consumers to use message.py exclusively

Remove the try-message/fall-back-to-notify pattern. **STATUS: COMPLETE**

- [x] **`io/getch.py:146-158`** — remove `from bbsengine6 import notify` and
      `_has_notify_module` flag. (Fixed 2026-07-22: the
      `_has_notify_module` references at lines 734 and 793
      were an orphaned dead branch — the variable was never
      defined after the Phase 7 notify deletion, so the
      notification bell/bottombar code was unreachable.
      Both call sites now use `check_notifications and moniker`
      directly.)
- [x] **`io/getch.py:467-487`** (`_check_notifications`) — remove notify
      fallback. Use `message.get_unread_count()` only.
- [x] **`io/getch.py:549-586`** (`_show_pending_notifications`) — replace
      `notify.get_queue()` + `Notification` dataclass iteration with
      message.py equivalent (dicts or new dataclass).
- [x] **`io/getch.py:538-546`** (`_get_urgency_color`) — replace
      `NotificationUrgency` enum import with message.py urgency mapping.
- [x] **`bottombar.py:71-78`** — remove `from bbsengine6 import notify`
      fallback. Use `message.get_unread_count()` only.
- [x] **`member/lib.py:209-222`** (`notifycount`) — change
      `notify.count(moniker)` to `message.get_unread_count(moniker)`.
- [x] **`member/lib.py:1239-1378`** — migrate `engine.__notify_group` SQL
      references to `__message_group` / `__message_group_member`.
- [x] **`net/integration.py:17-203`** (`NotifyIntegration`) — replace
      `self.notify_module.send(...)` with `message.store_message(...)`.
- [x] **`net/transport.py:163-207`** (`send_to_remote`) — update
      `{"type": "notify"}` payload to use message.py fields.
- [x] **`net/transport.py:348-373`** (`handle_notification`) — update
      incoming handler to match new payload format.
- [x] **`io/echo.py:124-129`** — added `message.*color` echo variables
      alongside existing `notify.*color` (kept for backward compat).

## Phase 4: Update backend bootstrap

- [x] **`backend/checkmessage.py`** — add messageview.sql views to classlist.
      Update enum source to message_enum.sql.
- [x] **`backend/checknotify.py`** — kept for backward compat. Notify
      classes are still loadable but not called by stage_one.
- [x] **`backend/stage_one.py`** — verified `checkmessage` is in the module
      loop (no change needed).
- [x] **`backend/backend.spec`** — TODO: update docs (pending).

## Phase 5: Update test infrastructure

- [x] **`tests/conftest.py`** — added `_get_message_sql_files()` helper,
      `schema_init` now loads message tables. `_get_notify_sql_files()` is
      retained for tests that need the legacy schema.
- [ ] **Migrate or rewrite notify test files** — the following 17+ test files
      import from `bbsengine6.notify` and test against `__notify*` tables.
      These will be removed in Phase 7 (notify package deletion):
  - [ ] `test_notify.py` → drop in Phase 7
  - [ ] `test_notify_lib.py` → drop in Phase 7
  - [ ] `test_notify_mac.py` → drop in Phase 7 (HMAC is not in message.py)
  - [ ] `test_notify_mark_read.py` → drop in Phase 7
  - [ ] `test_notify_send_receive.py` → drop in Phase 7
  - [ ] `test_notify_integration.py` → drop in Phase 7
  - [ ] `test_notify_first_load_api.py` → drop in Phase 7
  - [ ] `test_notify_tui.py` → drop in Phase 7 (no TUI in message.py)
  - [ ] `test_notify_daemon.py` → drop in Phase 7
  - [ ] `test_notify_schema_columns.py` → drop in Phase 7
  - [ ] `test_notify_message_demo*.py` → drop in Phase 7
  - [ ] `test_notify_message_f2_*.py` → drop in Phase 7
- [x] **Existing message.py tests remain** — `test_message_lib.py`,
      `test_message_persistence.py`, `test_message_delivery.py`,
      `test_message_channel.py` are the source of truth going forward.

**Note:** The notify test files were deleted in Phase 7 along with the
notify package. Only `test_message_lib.py`, `test_message_channel.py`
remain from the message-side tests, and these are the source of truth.

## Phase 6: Data migration (optional)

- [x] Decide: keep notify tables as read-only archive (faster path; no
      production data loss). `migrate_notify_to_message.sql` provided
      for opt-in migration.
- [x] If migrating: write a migration script that maps notify columns to
      message columns (`notification_type` → `channel`, `rendered_message` →
      `content`, recipient status mapping, etc.) — see
      `sql/migrate_notify_to_message.sql`.

## Phase 7: Remove notify package

- [x] Delete `bbsengine6/notify/` package (all files).
- [x] Delete `bbsengine6/message_delivery/` package (all files).
- [x] Delete `bbsengine6/message_delivery_handlers.py` (delivery handlers
      not yet ported; removed along with package).
- [x] Delete notify SQL files: `notify.sql`, `notify_recipient.sql`,
      `notify_type.sql`, `notify_block.sql`, `notify_group.sql`,
      `notify_rate_limit.sql`, `notifyview.sql`, `notifyd.sql`.
- [x] Delete `backend/checknotify.py` and `backend/checknotifyd.py`.
- [x] Delete notify daemon: `notify/daemon/` and `message_delivery/daemon/`.
- [x] Delete notify examples: `example_notify.py`,
      `example_notify_with_input.py`, `examples/notify_message_demo.py`,
      `examples/ping_pong_demo.py`, `examples/test_ping_pong_demo.py`,
      `examples/README_PING_PONG.md`.
- [x] Delete `py/src/testnotify.py`.
- [x] Update `backend/lib.py` to remove `checknotify`/`checknotifyd` helpers.
- [x] Update `backend/backend.spec` to remove `checknotify`/`checknotifyd`
      entries; `checkmessage` now documented as the canonical bootstrap.
- [x] Update `TODO-notify.md` to mark migration complete (added
      "SUPERSEDED" banner; the underlying tables are gone).
- [x] Update `TODO.md:347-363` ("Replace Notify System") to mark
      complete (added "COMPLETE" banner; each line annotated DONE).
- [x] Delete notify test files: `test_notify*.py`, `test_group_recipient_resolution.py`,
      `test_console_checknotifyd.py`, `test_message_delivery.py`,
      `test_message_persistence.py`, `test_net_integration.py`.

## Not in scope

- **HMAC tamper protection** — notify feature not in message.py. If needed
  later, add as a separate concern (e.g. signed column on `__message`).
- **IMAP daemon** (`notify/daemon/`) — separate subsystem, not part of this
  migration. Decide its fate independently.
- **TUI** (`notify/tui.py`, `notify/main.py`) — if a message TUI is needed,
  write it against message.py from scratch.
- **`bed` involvement** — `bed` is a WebSocket daemon with no terminal. It
  does not touch notifications today. The migration is a data-layer swap in
  `getch.py` / `bottombar.py` / `member/lib.py`. `bed` stays untouched.

## Phase 8: Channel/Sub system fixes

Status: COMPLETE.

These were issues found by reviewing the channel/sub system after the
notify→message migration. They are documented here so future readers
see the rationale.

- [x] **Shared ChannelState** — `WebSocketServer` previously created
      its own internal `ChannelState`; the `ChannelServiceHandler` had
      a separate one. As a result, `server.publish(...)` saw zero
      subscribers. `WebSocketServer.__init__` now accepts
      `channel_state=...` and `register_router(router)` so BED can
      share a single state between server and router. Files:
      `net/transport.py`, `bed.py`, `channel/api/handler.py`,
      `casino/empyre/mistermcfeely/api/handler.py`.

- [x] **Stable session id** — handlers used `id(websocket)` which can
      be reused after GC. `SessionManager.alloc_session_id()` returns
      monotonic ids from `itertools.count`; the server stashes
      `_bbsengine6_session_id` on the websocket. Handlers read it via
      `getattr(websocket, "_bbsengine6_session_id", id(websocket))`
      for backward compat with mock-websocket unit tests.

- [x] **Wire blocking + rate limit into `store_message()`** —
      `is_blocked()` and `check_rate_limit()` were defined but not
      called by `store_message()`. New `store_message_with_checks()`
      returns per-recipient diagnostics. Legacy `store_message()`
      still returns an int for backward compat. `integration.py`
      updated to use the rich version.

- [x] **Callback deregistration** — `channel_register_callback()`
      appended to a list with no way to remove. Added
      `channel_unregister_callback()` and
      `channel_unregister_all_callbacks()`. Registration is now
      idempotent (dedup by identity).

- [x] **Urgency-first delivery** — `get_pending_messages()` ordered
      by datestamp only, so a CRITICAL message could be delivered
      after a ROUTINE one. Added
      `get_pending_messages_prioritized()` with a CASE expression
      over urgency. `deliver_pending_on_connect` uses the prioritized
      variant.

- [x] **`send_to_remote` real-network fix** — the function was a
      stub: it built a payload, `await asyncio.sleep(0)`, and
      returned `True` without opening a connection. Implemented the
      real `websockets.connect()` call with timeout, ack read, and
      proper error handling. 7 unit tests in
      `tests/test_transport_send_to_remote.py`.

- [x] **`send_with_internet` parameter rename** — first parameter
      was `notification_type` (legacy notify name). Renamed to
      `channel` to match `NotifyIntegration.send()` and the rest of
      the system. No external callers (only docs).

- [x] **`list_channels()` pagination** — added `limit`, `offset`,
      and `announce_only` filter args. Default limit 100.

- [x] **Cleanup** — deleted dead `pytest.mark.skip` markers and
      stub test classes in `tests/test_message_channel.py`. Added
      legacy header comments to `sql/subscribe.sql` and
      `sql/getsubblurbs.sql`.

## Phase 9: Migration close-out

Status: COMPLETE.

The migration plan in `TODO-message-migration.md` (Phases 1-7) plus
the channel/sub quality work (Phase 8) left three open items. All
addressed:

- [x] **Fix `InternetRouter.send_notification`** — the only remaining
      runtime call to the deleted `bbsengine6.notify` package
      (`net/router.py:67-73`). Now routes through
      `message.store_message`, mapping the legacy `priority` field
      to the message urgency enum (`low`/`normal` → ROUTINE,
      `high` → IMPORTANT, `urgent` → URGENT, `critical` → CRITICAL)
      and using `subject` as the channel (defaulting to
      `system:direct`). 8 unit tests in
      `tests/test_router_send_notification.py` cover the routing,
      priority mapping, per-recipient failure isolation, and a
      regression test that the legacy notify module is never called.

- [x] **Mark `TODO-notify.md` as superseded** — added a banner
      noting the work item is moot (Phase 7 deleted the underlying
      tables and the `bbsengine6/notify/` package).

- [x] **Mark `TODO.md:347-363` ("Replace Notify System") complete** —
      added a "COMPLETE" banner; each line annotated as DONE.

- [x] **Drop dead `notify.*` and `message_delivery.*` color keys**
      from `io/echo.py`. Both namespaces are gone (notify and
      message_delivery packages deleted). The canonical `message.*`
      keys remain.

## Dependencies

- Phase 1 must complete before Phase 3 (consumers need the new API).
- Phase 2 must complete before Phase 3 (views may be referenced).
- Phase 4 can run in parallel with Phase 3.
- Phase 5 should run after Phase 3 (tests validate the new consumer code).
- Phase 6 is independent and optional.
- Phase 7 is last.
- Phase 8 (channel/sub quality) is independent of the migration phases.
- Phase 9 (close-out) depends on Phases 1-8 being complete.
- Phase 8 is independent and addresses channel/sub system quality.
