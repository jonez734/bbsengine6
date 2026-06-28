[x] upgrade bbsengine.org to use bootstrap.php (to fix Smarty.class.php include error) - DONE
   - Problem: engine.php:14 requires Smarty.class.php directly but can't find it
   - Solution: Add `require_once("/srv/www/bbsengine6/php/bootstrap.php");` at top of each PHP file
   - Files updated in www/org/php/: index.php, login.php, logout.php, register.php, post.php, page.php, archive.php, download.php, dir.php, handbook.php, handbook-index.php, handbook-chapter.php, about.php, testform.php, phpinfo.php, bbsenginedotorg.php, gencaptchaimage.php
   - Files updated in engine/: join.php, login.php, logout.php, router.php
   - Also updated: php/session.php, php/page.php, smarty/*.php, www/org/smarty/*.php
   - Note: No Composer changes - use existing bootstrap.php

[x] sync www/org/smarty/modifier.markdown.php with smarty/modifier.markdown.php - DONE

[ ] logout hook -- some code in murdermotel gets run when the user logs out (including eof) (@since 20221015)
[x] port to PDO from PEAR::MDB2 @since 20230402
[x] php8
[x] io.echo(): unknown tokens (anything in curly braces) are silently dropped. make a way to display them unchanged (@since 20240107)
[ ] Fix /handbook/6/ 500 internal server error - add default mode=index when no mode is specified in handbook.php (@since 20250623)
[ ] SETBOTTOMBAR packet type (12) - server-to-client UI update for bottom bar (e.g., casino module can update client status bar) (@since 20250621)

## Python Issues

- [x] Fix psycopg-pool 3.3.0 incompatibility

## Unified Pub/Sub Channel System

**Status:** Phases 1A-1E, Integration complete

Add a channel subscription system to `bbsengine6/net/transport.py` that all games can use for real-time messaging.

### Channel Naming Convention
```
casino:table:{moniker}        # e.g., casino:table:blackjack-1
empyre:island:{id}            # e.g., empyre:island:5
empyre:ship:{id}              # e.g., empyre:ship:3
murdermotel:room:{id}         # e.g., murdermotel:room:entrance
member:{moniker}              # e.g., member:alice - personal channel for direct messages
system:shout                  # global chat (all connected users)
system:announcements         # sysop broadcasts only (reserved)
```

**Relationship with notify system:**
- Message system replaces and absorbs notify (persistence, groups, rate limiting, blocking)
- The old notify system becomes delivery mechanisms (email daemon, SMS) that subscribe to message channels

---

## Implementation Phases

### Phase 1A: Core Channel System ✓ DONE

Basic pub/sub without persistence.

**transport.py additions:**
```python
class ChannelManager:
    def __init__(self):
        self._channels: Dict[str, Set[int]] = {}  # channel -> set of session_ids
        self._callbacks: Dict[str, List[Callable]] = {}  # channel -> callbacks for bots
    
    def subscribe(self, session_id: int, channel: str) -> None
    def unsubscribe(self, session_id: int, channel: str) -> None
    def register_callback(self, channel: str, callback: Callable) -> None  # for bots
    def get_subscribers(self, channel: str) -> Set[int]
    def unsubscribe_all(self, session_id: int) -> None  # cleanup on disconnect
    
    async def publish(self, channel: str, message: Dict) -> None:
        # Send to all WebSocket subscribers
        # Also invoke registered callbacks
```

**Message types:**
- `subscribe_channel` - subscribe session to a channel
- `unsubscribe_channel` - unsubscribe from a channel
- `get_subscriptions` - list current subscriptions

**Keep existing `broadcast()` and path-based messaging for backward compatibility.**

**Tests:** 13 passed (test_message_channel.py)

---

### Phase 1B: Persistence ✓ DONE

Add database storage for messages, delivered to offline users on connect.

**Database table:**
- `engine.__message` - main message table (sql/message.sql)
- `engine.__message_recipient` - per-recipient delivery tracking

**DAL functions (bbsengine6/message.py):**
- `store_message()` - store message with recipients
- `get_pending_messages()` - retrieve pending messages
- `mark_delivered()` - mark as delivered
- `mark_read()` - mark as read
- `get_unread_count()` - count unread
- `deliver_pending_on_connect()` - deliver pending on auth

**Features:**
- Messages stored in DB when published
- On connect, deliver pending messages to user
- Delivery tracking (datedelivered)
- Read tracking (dateread)

**Tests:** 33 passed (test_message_persistence.py)

---

### Phase 1C: Groups, Blocking, Rate Limiting ✓ DONE

Add notify-like features directly into message system.

**Database tables (sql/message_groups.sql):**
- `engine.__message_group` - distribution lists
- `engine.__message_group_member` - group membership
- `engine.__message_block` - sender blocks
- `engine.__message_type` - message types with rate limits
- `engine.__message_rate_limit` - rate limit tracking

**DAL functions (bbsengine6/message.py):**
- Groups: `create_message_group()`, `add_to_message_group()`, `get_message_group_members()`, `get_user_groups()`
- Blocking: `block_sender()`, `unblock_sender()`, `is_blocked()`
- Rate limiting: `check_rate_limit()`, `record_message_sent()`, `get_message_type_rate_limit()`

**Features:**
- Groups: @everyone and custom groups
- Blocking: recipient can block senders
- Rate limiting: per-sender, per-message-type, per-hour limits

**Tests:** 33 passed (test_message_persistence.py)

---

### Phase 1D: Multi-Channel Delivery ✓ DONE

Add delivery mechanisms that subscribe to message channels.

**Delivery handlers (message_delivery.py):**
- `DeliveryManager` - coordinates handlers
- `InMemoryQueueHandler` - delivers to connected users via WebSocket
- `EmailDeliveryHandler` - sends via SMTP (optional)
- `SMSDeliveryHandler` - sends via SMS gateway (optional)

**F2/Client integration:**
- `io/getch.py:_check_notifications()` - uses message system, falls back to notify
- `io/screen.py:get_notification_status()` - uses message system, falls back to notify
- F2 key shows pending message count in bottombar
- Pending messages delivered on auth via `deliver_pending_on_connect()`

**Tests:** 33 passed (test_message_persistence.py)

---

### Phase 1E: Templating ✓ DONE

Add variable substitution in messages.

**Features:**
- `{variable}` and `$variable` substitution in messages
- Template storage in message table (template, template_vars columns)
- `render_template()` - render template with variables
- `render_message_content()` - render with optional template
- `parse_variables_from_content()` - extract variables from content
- `validate_template()` - validate template syntax
- Built-in variables: year, month, day, date, time, timestamp

**Tests:** 33 passed (test_message_persistence.py)
- Phase 1E: Templating - Create new test file `test_message_templating.py` (~52 tests)

---

### Phase 1F: Notify → message_delivery Rename ✓ DONE

Rename the notify module to message_delivery, keeping notify as alias during transition.

**Changes:**
- Package: `bbsengine6/notify/` → `bbsengine6/message_delivery/`
- Module imports: `from bbsengine6.notify import` → `from bbsengine6.message_delivery import`
- SQL tables: Rename to `__message_delivery*` (reuse existing `__message*` tables for data)
- SQL views: Rename views
- Config vars: `notify.*` → `message_delivery.*` in echo.py
- External deps: Update casino, mistermcfeely imports
- Backward compat: Keep `notify` as alias during transition

**Tests needed:**
- Verify backward compat: `from bbsengine6 import notify` still works
- Verify new import: `from bbsengine6 import message_delivery` works
- Verify both point to same implementation
- All existing `test_notify*.py` tests (18 files) continue to pass
- All existing `test_message*.py` tests (4 files) continue to pass

---

### Phase 1G: Postoffice Service (IMAP Polling) ✓ bed.json DONE

Add postoffice service to BED (via casino) that polls IMAP servers for new email and notifies users.

**bed.json** (casino package data):
```json
{
  "postoffice": {
    "enabled": false,
    "poll_interval": 30,
    "mailboxes": []
  },
  "debug": false
}
```

**Config loading (casino/config.py):**
- `load_config()` with priority: overrides → config file → bed.json defaults
- Environment variables: CASINO_DEBUG, CASINO_POSTOFFICE_ENABLED, etc.
- `get_postoffice_config()` helper function

**Message routing:**
- Channel: `postoffice:check_mail`
- Notification: Uses `message.send()` with sender, subject, ~500 char preview

**Service implementation:**
- Mode A: Background asyncio task polls IMAP on interval (if `enabled: true`)
- Mode B: Handles `check_mail` message type for manual requests

**Tests needed:**

| Test File | What it tests |
|-----------|---------------|
| `test_postoffice_service.py` | Service class, handle_message() |
| `test_postoffice_imap_polling.py` | IMAP connection, polling, new email detection |
| `test_postoffice_background_task.py` | Background polling task starts/stops |
| `test_postoffice_manual_check.py` | Manual check via message type |
| `test_postoffice_notification.py` | Notification sent with correct content |
| `test_postoffice_config.py` | Config loading (3 priority levels) |
| `test_postoffice_channel.py` | Sends to `postoffice:check_mail` channel |

**Key test scenarios:**

1. **Background polling (Mode A):**
   - Service starts, creates asyncio task
   - Polls IMAP on interval
   - Detects new email, sends notification
   - Service stops, task cancels

2. **Manual check (Mode B):**
   - Client sends `check_mail` message
   - Service polls IMAP
   - Returns results to client

3. **Config priority:**
   - Env var overrides bed.json
   - Config file overrides bed.json defaults

4. **Notification content:**
   - Sender extracted correctly
   - Subject extracted correctly
   - Body preview (~500 chars)

---

### Integration (Games) ✓ DONE

1. Add channel subscription message handlers in `api/handler.py`
2. On `join_table`: auto-subscribe to `casino:table:{moniker}`
3. On `watch_table`: also subscribe to same channel (unifies logic)
4. Replace `server.broadcast(message, table_moniker)` with `server.publish(channel, message)`

**Benefits:**
- Single unified system for all real-time messaging across all games
- Players automatically get updates (no separate watch concept needed for players)
- System events (password changes, announcements) can use same infrastructure
- Bots can register callbacks to receive channel messages

### Implementation (bbsengine6)

Add to `transport.py`:

```python
class ChannelManager:
    def __init__(self):
        self._channels: Dict[str, Set[int]] = {}  # channel -> set of session_ids
        self._callbacks: Dict[str, List[Callable]] = {}  # channel -> callbacks for bots
    
    def subscribe(self, session_id: int, channel: str) -> None
    def unsubscribe(self, session_id: int, channel: str) -> None
    def register_callback(self, channel: str, callback: Callable) -> None  # for bots
    def get_subscribers(self, channel: str) -> Set[int]
    def unsubscribe_all(self, session_id: int) -> None  # cleanup on disconnect
    
    async def publish(self, channel: str, message: Dict) -> None:
        # Send to all WebSocket subscribers
        # Also invoke registered callbacks
```

Add message types to handler:
- `subscribe_channel` - subscribe session to a channel
- `unsubscribe_channel` - unsubscribe from a channel
- `get_subscriptions` - list current subscriptions

Keep existing `broadcast()` and path-based messaging for backward compatibility.

### Integration (casino)

1. Add channel subscription message handlers in `api/handler.py`
2. On `join_table`: auto-subscribe to `casino:table:{moniker}`
3. On `watch_table`: also subscribe to same channel (unifies logic)
4. Replace `server.broadcast(message, table_moniker)` with `server.publish(channel, message)`

### Replace Notify System

When message system is complete, it replaces notify entirely:

**Client changes (bbsengine6/io/getch.py):**
- Replace `notify.count(moniker)` with message count query
- Replace `notify.get_queue(moniker)` with message queue query
- Replace notification display with message display
- Update `get_notification_status()` to use message tables

**Database:**
- Migrate existing `engine.__notify` data to `engine.__message` if needed
- Or keep notify tables as read-only archive, new messages go to message tables

**What notify module becomes:**
- Deprecated (read-only for historical data)
- Or removed after migration

**Client integration points:**
- `bbsengine6/io/getch.py:_check_notifications()` - poll for messages
- `bbsengine6/io/getch.py:_show_pending_notifications()` - display messages
- `bbsengine6/io/screen.py:get_notification_status()` - bottombar status

### Benefits
- Single unified system for all real-time messaging across all games
- Players automatically get updates (no separate watch concept needed for players)
- System events (password changes, announcements) can use same infrastructure
- Bots can register callbacks to receive channel messages

### Member-to-Member Messaging

Use `member:{moniker}` channel for direct messaging:

```
member:{moniker}  →  Each user subscribes to their own channel on connect
```

- To message alice: publish to `member:alice`
- Only alice receives it (if subscribed)
- If alice is offline, message goes to any registered callbacks (bots) or is dropped

External programs can send messages by publishing to a member's channel.

### Database Startup Updates (Future)

For chat persistence (if implemented in bbsengine6, shared across games), add SQL files in `bbsengine6/sql/`:
- `chat_message.sql` - table definition with grants
- `chat_channel.sql` - channel metadata and ACL with grants
- `chat_message_view.sql` - view with local timestamps with grants

Update `bbsengine6/startup.py`:
- Add schema creation for `chat` (if not exists)
- Add each class to the import list in dependency order
- Add grants for each class

Each SQL file contains table/view definition + grants in the same file (follows `notify.sql` pattern).

### Tests

Add comprehensive tests for all message system features:

**Channel subscription tests:**
- `test_subscribe_to_channel` - session subscribes to channel
- `test_unsubscribe_from_channel` - session unsubscribes from channel
- `test_subscribe_multiple_sessions` - multiple sessions on same channel
- `test_unsubscribe_all_on_disconnect` - cleanup on session disconnect
- `test_publish_to_channel` - message published to all subscribers
- `test_publish_empty_channel` - no subscribers, no error

**Callback tests (for bots):**
- `test_register_callback` - bot registers callback for channel
- `test_callback_invoked_on_publish` - callback receives published messages
- `test_multiple_callbacks_per_channel` - multiple bots on same channel

**Message types tests:**
- `test_subscribe_channel_message` - subscribe_channel message type
- `test_unsubscribe_channel_message` - unsubscribe_channel message type
- `test_get_subscriptions_message` - get_subscriptions message type

**Member channel tests:**
- `test_member_channel_subscribe` - subscribe to own member:moniker channel
- `test_direct_message_via_member_channel` - publish to member:channel delivers to that member

**Integration tests:**
- `test_message_publish_with_notify_integration` - message system delivers to connected users

---

### Tests

Add comprehensive tests for all message system features:

**Phase 1A tests (Core Channel System) ✓ DONE:**
- `test_subscribe_to_channel` - session subscribes to channel
- `test_unsubscribe_from_channel` - session unsubscribes from channel
- `test_subscribe_multiple_sessions` - multiple sessions on same channel
- `test_unsubscribe_all_on_disconnect` - cleanup on session disconnect
- `test_publish_to_channel` - message published to all subscribers
- `test_publish_empty_channel` - no subscribers, no error
- `test_register_callback` - bot registers callback for channel
- `test_callback_invoked_on_publish` - callback receives published messages
- `test_multiple_callbacks_per_channel` - multiple bots on same channel
- `test_subscribe_channel_message` - subscribe_channel message type
- `test_unsubscribe_channel_message` - unsubscribe_channel message type
- `test_get_subscriptions_message` - get_subscriptions message type
- `test_member_channel_subscribe` - subscribe to own member:moniker channel
- `test_direct_message_via_member_channel` - publish to member:channel delivers to that member

**Phase 1B tests (Persistence):**
- `test_message_persistence` - messages stored in DB, delivered to offline users (SKIPPED - requires table)
- `test_message_delivery_tracking` - automatic delivery tracking on connect (SKIPPED)
- `test_message_read_receipt` - client acknowledges receipt (SKIPPED)

**Phase 1C tests (Groups, Blocking, Rate Limiting):**
- `test_message_groups` - @everyone and custom groups
- `test_message_rate_limiting` - per-sender, per-channel rate limits
- `test_message_blocking` - sender blocked by recipient
- `test_message_urgency` - priority levels (ROUTINE, IMPORTANT, URGENT, CRITICAL)

**Phase 1D tests (Multi-Channel Delivery):**
- `test_message_multi_channel` - email, SMS delivery via subscribed handlers

**Phase 1E tests (Templating):**
- `test_message_templating` - variable substitution in messages

---

## Future Phases (Beyond 1G)

Potential enhancements for the message system:

**Phase 2A: Message Threads/Conversations**
- Group messages into conversations/threads
- `engine.__message_thread` table
- Reply-to, parent message tracking

**Phase 2B: Rich Media**
- File attachments, images
- `engine.__message_attachment` table
- Storage backend integration

**Phase 2C: Message Editing**
- Edit after sending
- Version history
- "Edited" indicator

**Phase 2D: Reactions**
- Emoji reactions to messages
- Like, thumbs up, etc.

**Phase 2E: Full-Text Search**
- Search across all messages
- PostgreSQL full-text search
- Search API

**Phase 2F: Moderation**
- Report messages
- Admin delete with reason
- Message flagging

**Phase 2G: Message Scheduling**
- Send later / scheduled messages
- `engine.__message_scheduled` table
- Cron job to send

**Phase 2H: Analytics**
- Message counts per user/channel
- Activity dashboards
- Popular channels

---

## MemberServices for BED

Create MemberServices for the BBS Engine Daemon (BED), leveraging bbsengine6's member system for profile management, membership tiers, and referral tracking.

### Implementation Tasks

**bbsengine6:**
- [x] Update bbsengine6/sql/memberview.sql - add tier column from attrs->>'tier'
- [x] Update bbsengine6/startup.py to add: member.sql, refcode.sql (register existing tables/views)
- [x] Create bbsengine6/services/member.py - MemberService class:
  - get_profile(moniker) → Dict (from engine.member view)
  - update_profile(moniker, attrs) → Dict (via member.setattrs)
  - get_tier(moniker) → str (from engine.member.tier)
  - set_tier(moniker, tier) → bool (via member.setattrs)
  - get_referral_code(moniker) → str (from engine.__member.refcode)
  - get_referrals(moniker) → List[Dict] (from engine.__member.parentmoniker)
  - use_referral_code(moniker, code) → Dict (via engine.map_refcode_use)

**casino:**
- [x] Add MemberServiceHandler to casino/api/handler.py
- [x] Register service in MessageRouter.register_all() with message types: member_profile, member_update, member_tier, member_referral_code, member_referrals
- [x] Create comprehensive tests in casino/tests/test_member_services.py

### Test Classes

- [x] TestMemberServicesDAL - Integration tests with real database (zoid6test)
- [x] TestMemberServicesBED - WebSocket tests via BED with mocked services
- [x] TestMemberServicesMocked - Unit tests with mocked DAL

### Database Schema (Existing + View Update)

- engine.__member - member table (attrs JSONB, refcode, parentmoniker)
- engine.member - view with all member columns + computed fields + tier
- engine.__refcode - referral codes
- engine.map_refcode_use - referral usage tracking

---

### Fix FK Column Types and Remove Unused Tables

- [ ] Fix `engine.__actionlog.moniker` - change from `text` to `citext` with FK constraint (actively used in zoid6 PHP)
- [ ] Fix `engine.map_sigop_sigpath.createdbymoniker` - change from `bigint` to `citext` with FK constraint
- [ ] Fix `engine.map_sigop_sigpath.approvedbymoniker` - change from `bigint` to `citext` with FK constraint
- [ ] Remove `engine.__blocklist` table - unused code, no references found

---

## GPG Key Support for Message Signing

Add columns to support GPG keys for signing messages.

- [ ] Add `gpg_public_key` column to `engine.__member` table
  - [ ] Store ASCII-armored GPG public key
  - [ ] Add index for efficient lookups
- [ ] Add `gpg_keyid` column to `engine.__member` table
  - [ ] Store short key ID for quick reference
- [ ] Add `gpg_fingerprint` column to `engine.__member` table
  - [ ] Store full 40-character fingerprint
- [ ] Create SQL migration file: `bbsengine6/sql/gpg_keys.sql`
  - [ ] Add columns with proper grants
- [ ] Create view: `engine.member` includes gpg columns
- [ ] Create DAL functions in `bbsengine6/member.py`:
  - [ ] `set_gpg_key(args, moniker, public_key)` - store GPG key
  - [ ] `get_gpg_key(args, moniker)` - retrieve GPG key
  - [ ] `delete_gpg_key(args, moniker)` - remove GPG key
  - [ ] `verify_gpg_key(args, moniker, signature, data)` - verify signed message
- [ ] Add message signing to message system:
  - [ ] Sign messages with member's GPG key when sending
  - [ ] Verify GPG signatures on received messages
  - [ ] Store signature with message record
- [ ] Handle GPG key passphrases/authentication:
  - [ ] Add `gpg_key_password` column to `engine.__session` table (temporary, session-scoped)
  - [ ] Create DAL function to store decrypted private key in session
  - [ ] Implement secure passphrase entry via WebSocket (not stored in DB)
  - [ ] Session-scoped key decryption (key only available during active session)
  - [ ] Clear passphrase from memory after use
  - [ ] Add `unlock_gpg_key` message type for WebSocket clients
  - [ ] Add `gpg_key_locked` response flag to indicate key needs unlock

---

## Package Data Helper (importlib.files style)

- [x] Add `bbsengine6.module.files(module_ref) -> pathlib.Path` function
  - Returns pathlib.Path to module's directory (like importlib.files)
  - Uses existing `module.get()` to resolve module
  - Location: bbsengine6/py/src/bbsengine6/module.py
  
- [x] Add `bbsengine6.module.folder(module_ref, name: str) -> pathlib.Path | None` function
  - Returns pathlib.Path to module's subdirectory, or None if missing
  - Generic: works with any subdirectory name (data, tpl, sql, etc.)
  - Example: module.folder('bed', 'data') -> Path or None

- [ ] Add tests for module.files() and module.folder()
  - Test with bbsengine6 built-in module
  - Test with external module (bed)
  - Test folder() returns None for missing directories

---

## Modular Architecture (See zoid6/TODO.md)

### Remove common.logentry

The thread-safe version in `bbsengine6/util.py` is the canonical one. The duplicate in `common.py` should be removed.

- Delete `logentry()` from `bbsengine6/common.py`
- No external usage found in casino, empyre, murdermotel, asimov, or zoid6

### Create bank subpackage

Create `bbsengine6/bank/api/handler.py` for the modular architecture.

See zoid6/TODO.md for full context.

---

## Phase 4: Generic Invite Code System

**Plan (2026-06-24):**

Build a generic invite code system in `bbsengine6` that all modules (casino, empyre, murdermotel, member) can use to gate access to resources (tables, islands, rooms, etc.) via short alphanumeric codes.

### Files to create

1. **`bbsengine6/py/src/bbsengine6/sql/invite.sql`** — schema + view
2. **`bbsengine6/py/src/bbsengine6/invite.py`** — DAL functions (functional style, mirrors `session.py`)
3. **`bbsengine6/py/src/bbsengine6/services/invite.py`** — `InviteService` class (class style, mirrors `services/channel.py`)
4. **`bbsengine6/py/tests/test_invite.py`** — tests

### Files to update

5. **`bbsengine6/py/src/bbsengine6/sql/bbsengine6.sql`** — add `\i invite.sql` to include chain (after `session.sql`)
6. **`bbsengine6/py/tests/conftest.py`** — add `"invite.sql"` to `_get_notify_sql_files()` list

### Schema (`invite.sql`)

**Table `engine.__invite`:**
- `id bigserial primary key`
- `module text not null` — `'casino'`, `'empyre'`, `'murdermotel'`, `'member'`, etc.
- `resourceid text not null`
- `code text not null`
- `createdbymoniker citext` → `engine.__member(moniker)` `on update cascade on delete set null`
- `datecreated timestamptz`
- `dateexpires timestamptz`
- `dateused timestamptz` — set when code is redeemed
- `usedbymoniker citext` → `engine.__member(moniker)` `on update cascade on delete set null`
- `revoked timestamptz` — set when code is revoked (nullable; non-null = revoked)
- `casinotablemoniker citext` → `casino.__table(moniker)` `on update cascade on delete cascade`
  (populated only when `module='casino'`; allows FK cleanup when a table is deleted)
- Unique index on `(module, resourceid, code)` to prevent duplicates
- Partial unique index `WHERE revoked IS NULL AND dateused IS NULL` to prevent duplicate active codes per resource

**View `engine.invite`:**
Mirrors `session.sql:25-35` pattern:
- Exposes `*epoch` (integer seconds) and `*local` (current user's timezone) for `datecreated`, `dateexpires`, `dateused`, `revoked`
- Joined via `left outer join engine.__member as currentmember on (loginid = CURRENT_USER)`

**Grants:**
- `grant select, insert, update, delete on engine.__invite to web, term, sysop;`
- `grant select on engine.invite to web, term, sysop;`

### DAL (`bbsengine6/invite.py`)

Functional style with `_work(conn)` + `kwargs.pop("conn")` pattern (matches `session.py`):

- `create_invite(args, module, resourceid, createdbymoniker, dateexpires=None, code=None, **kwargs) -> Dict`
  - If `code` is None, generate `secrets.token_urlsafe(6)` (8 chars, URL-safe, hard to guess)
  - Returns `{success, message, id, code, datecreated, dateexpires}` or `{success: False, message: ...}`
- `get_invites(args, module, resourceid, include_revoked=False, include_used=False, **kwargs) -> List[Dict]`
  - Defaults to filtering out revoked and used invites
  - Ordered by `datecreated desc`
- `validate_invite(args, module, resourceid, code, **kwargs) -> Optional[Dict]`
  - Returns invite dict if valid (not used, not revoked, not expired)
  - Returns None otherwise
- `mark_used(args, invite_id, usedbymoniker, **kwargs) -> bool`
  - Sets `dateused=now()`, `usedbymoniker=...`
  - Returns False if already used or revoked (idempotent guard)
- `revoke_invite(args, invite_id, **kwargs) -> bool`
  - Sets `revoked=now()` (soft delete via flag, per design decision)
  - Returns False if already revoked, used, or not found

Uses `database.query()` for safe identifier/value composition.

### Service (`bbsengine6/services/invite.py`)

`InviteService` class:
- `__init__(self, args)`
- Wraps DAL methods in `{success, message, ...}` envelopes (matches `services/channel.py:75-79`)
- Message-type constants:
  - `MESSAGE_INVITE_CREATE = "invite_create"`
  - `MESSAGE_INVITE_LIST = "invite_list"`
  - `MESSAGE_INVITE_REVOKE = "invite_revoke"`
  - `MESSAGE_INVITE_VALIDATE = "invite_validate"`
  - `MESSAGE_INVITE_USE = "invite_use"`

### Tests (`test_invite.py`)

Test classes (function-scoped, with `test_args` + `test_pool` fixtures; autouse rollback from conftest provides data isolation):
- `TestCreateInvite` — default random code, explicit code, with expiry, duplicate detection
- `TestGetInvites` — by module+resourceid, ordering, default filters out used/revoked, opt-in flags
- `TestValidateInvite` — valid, wrong code, used, revoked, expired, wrong module
- `TestMarkUsed` — success, idempotent on already-used, rejected on revoked
- `TestRevokeInvite` — success, idempotent on already-revoked, on missing id
- `TestInviteService` — checks return envelope shape, message-type constants
- `TestCasinoFk` — invite FKs to `casino.__table`; deleting the table cascades

### Out of scope (separate task)

- Removing `casino.__table_invite`
- Updating casino to use `bbsengine6.invite` module
- Implementing `create_invite` / `list_invites` / `revoke_invite` message handlers in casino router
- Module-specific invite validation logic (per-module)

### Implementation tasks

- [ ] Create `bbsengine6/sql/invite.sql` - shared invite code table:
  ```sql
  CREATE TABLE engine.__invite (
      id bigserial primary key,
      module text not null,  -- 'casino', 'empyre', 'murdermotel', etc.
      resourceid text not null,  -- tableid, islandid, roomid, etc.
      code text not null,
      createdbymoniker citext constraint fk_invite_createdby references engine.__member(moniker) on update cascade on delete set null,
      datecreated timestamptz,
      dateused timestamptz,
      dateexpires timestamptz,
      -- Module-specific FKs for referential integrity:
      constraint fk_invite_casino foreign key (resourceid) references casino.__table(moniker) on delete cascade
  );
  -- Add similar FKs as modules are added:
  -- constraint fk_invite_empyre foreign key (resourceid) references empyre.__island(id) on delete cascade
  ```
- [ ] Create `engine.invite` view with local timezone conversion
- [ ] Create `bbsengine6/invite.py` - DAL functions:
  - [ ] `create_invite(args, module, resourceid, createdbymoniker, dateexpires)` → returns code
  - [ ] `get_invites(args, module, resourceid)` → list of codes
  - [ ] `revoke_invite(args, invite_id)` → bool
  - [ ] `validate_invite(args, module, resourceid, code)` → returns invite record or None
  - [ ] `mark_used(args, invite_id)` → bool

---

## Phase 5: Logging

### Enhanced logentry() Function
- [x] Add key-value parameters to `bbsengine6.util.logentry()`:
  - [x] `module: str = ""`
  - [x] `action: str = ""`
  - [x] `moniker: str = ""`
  - [x] `loginid: str = ""`
  - [x] `ip_address: str = ""`
  - [x] `fingerprint: str = ""`
  - [x] `table: str = ""`
  - [x] `**kwargs` for additional fields
- [x] Build formatted string: `[module] action key=value key=value message`
- [x] Keep backward compatibility (no new params = original behavior)
- [x] Update bank/bank.py `log_event()` to use new util.logentry()

### Log Format Standard
**Format:** `[module] action key=value key=value free_text_at_end`

- [x] Key-value pairs go at the start (e.g., `moniker=john amount=100`)
- [x] Free text goes at the end (no `reason=` prefix)
- [x] Use underscores for multi-word fields (e.g., `loginid`, `accountid`)

### Module log_event() Cleanup
- [x] `bbsengine6/bank/bank.py:11` - remove `log_event()` definition
- [x] `bbsengine6/bank/bank.py:67` - refactor `add_funds_failed` (add_funds method)
- [x] `bbsengine6/bank/bank.py:87` - refactor `add_funds` success
- [x] `bbsengine6/bank/bank.py:113` - refactor `remove_funds_failed` (amount check)
- [x] `bbsengine6/bank/bank.py:118` - refactor `remove_funds_failed` (account not found)
- [x] `bbsengine6/bank/bank.py:122` - refactor `remove_funds_failed` (insufficient funds)
- [x] `bbsengine6/bank/bank.py:141` - refactor `remove_funds` success
- [x] `bbsengine6/bank/bank.py:166` - refactor `transfer` success (transfer_request)
- [x] `bbsengine6/bank/bank.py:175` - refactor `transfer` failure
- [x] `bbsengine6/bank/bank.py:191` - refactor `approve_transfer` success
- [x] `bbsengine6/bank/bank.py:201` - refactor `approve_transfer` failure
- [x] `bbsengine6/bank/bank.py:216` - refactor `reject_transfer` success
- [x] `bbsengine6/bank/bank.py:223` - refactor `reject_transfer` failure
- [x] Verify no external imports of `bbsengine6.bank.log_event` (confirmed: 0)
- [x] Run bank tests to verify refactor (25 passed)

### Phase 5 Complete
- [x] `bbsengine6.util.logentry()` enhanced with key-value params (module, action, moniker, loginid, ip_address, fingerprint, table, **kwargs)
- [x] Format: `[module] action key=value key=value free_text`
- [x] Backward compatibility preserved
- [x] `bbsengine6/bank/bank.py` refactored: `log_event()` removed, all 12 call sites use `logentry()` directly
- [x] All other modules (casino, empyre, mistermcfeely, murdermotel, bed, zoid6, asimov, asb) verified clean of `log_event`/`log_entry` definitions
- [x] `mistermcfeely` keeps `log_entry_fn` callback DI pattern (intentional, different from `log_event` wrapper)
- [x] Full test suite: 1091 passed, 18 pre-existing failures (verified unrelated to logging changes), 13 skipped

---

## Phase 6: Channel Access Control

### Invite-Only Channels
- [ ] Add `invite_only` flag to channel creation
- [ ] Add invite code validation for joining invite-only channels
- [ ] Use generic `engine.__invite` system for channel invites
- [ ] Only invited users can subscribe to invite-only channels
- [ ] Channel owner can manage invites

### Moderated Channels
- [ ] Add `moderated` flag to channel creation
- [ ] Add `moderators` list to channel (monikers)
- [ ] Add `member_moderation` config (boolean):
  - true: members' messages require approval
  - false: members can post freely (default)
- [ ] Add `non_member_moderation` config (boolean):
  - true: non-members' messages require approval
  - false: non-members can post freely (default)
- [ ] Add both fields to channel schema
- [ ] Implement moderation logic based on sender's membership status
- [ ] Add message types: `approve_message`, `reject_message`
- [ ] Moderators receive notification of pending messages

### Private Channels
- [ ] Add `private` flag to channel creation
- [ ] Private channels don't appear in `get_subscriptions` list
- [ ] Users must know exact channel name to join
- [ ] Only invited/approved users can subscribe
- [ ] Sysops see private channels in list (with indicator)

### Announce-Only Channels
- [ ] Add `announce_only` flag to channel creation
- [ ] Add `announcers` list to channel (monikers who can post)
- [ ] Only announcers can send messages to the channel
- [ ] Anyone can subscribe and read (viewers)
- [ ] Sysops are always announcers by default

## Phase 7: Move `bank` package to `services/bank/` and split into focused services

### 7.0 Decisions
- Approach: **move + split** `BankService` into `AccountService`, `TransactionService`, `TransferService` (matches the single-domain shape of the other `services/*` modules)
- Keep a **temporary shim** at `bbsengine6.bank` (and at the empyre/casino/mistermcfeely import paths they use) re-exporting the new services, so cross-repo consumers keep working
- Add **back-compat re-exports** in `services/__init__.py`

### 7.1 Relocate the package
- [ ] `git mv bbsengine6/py/src/bbsengine6/bank/ bbsengine6/py/src/bbsengine6/services/bank/`
  - [ ] `__init__.py`
  - [ ] `account.py`
  - [ ] `bank.py`
  - [ ] `transaction.py`
  - [ ] `transfer.py`
  - [ ] `api/__init__.py`
  - [ ] `api/handler.py`
- [ ] Remove leftover `bbsengine6/py/src/bbsengine6/bank/__pycache__/`

### 7.2 Split `BankService` into focused services
- [ ] `services/bank/account.py` — promote `Account` class to `AccountService`; keep DAL-style methods (`get`, `get_or_create`, `update`, `get_balance`)
- [ ] `services/bank/transaction.py` — promote `Transaction` class to `TransactionService`; keep `get_history` and the underlying `INSERT` helper
- [ ] `services/bank/transfer.py` — promote `Transfer` class to `TransferService`; keep `create`, `approve`, `reject`, `get_pending`
- [ ] Move `BankService.add_funds` / `remove_funds` / `get_balance` / `get_history` / `get_pending_transfers` / `transfer` / `approve_transfer` / `reject_transfer` onto the appropriate service:
  - `AccountService`: `get_balance`, `add_funds`, `remove_funds`
  - `TransactionService`: `get_history`
  - `TransferService`: `transfer`, `approve_transfer`, `reject_transfer`, `get_pending`
- [ ] Delete the umbrella `services/bank/bank.py` once methods are relocated
- [ ] Update `services/bank/__init__.py` to re-export the three services and drop `BankService`

### 7.2.1 Implement `AccountService` and `LedgerService`

#### Decisions
- `get_balance` lives on `AccountService` (not the umbrella)
- Balance UPDATE SQL uses `balance = balance ± %s` with `RETURNING balance` to avoid lost-update races
- `logentry(..., module="bank")` preserved across the move
- `add_funds` / `remove_funds` move out of the umbrella into a new `LedgerService` that owns the `bank.__transaction` INSERT

#### New / changed files
- [ ] `services/bank/account.py` — rename class `Account` → `AccountService`; preserve `get`, `get_or_create`, `get_by_id`, `update`; add `get_balance(moniker) -> int` (returns `account["balance"]` or `0`)
- [ ] `services/bank/ledger.py` (new) — `LedgerService` class:
  - [ ] Constants: `MESSAGE_LEDGER_CREDIT = "ledger_credit"`, `MESSAGE_LEDGER_DEBIT = "ledger_debit"` (matches `InviteService` pattern)
  - [ ] `__init__(args)` holds `self.accounts = AccountService(args)`
  - [ ] `add_funds(moniker, amount, transaction_type="credit", description="", member_moniker="") -> dict`:
    - [ ] Validate `amount > 0`; on failure, `logentry(..., action="add_funds_failed")` with `module="bank"`, return `{success: False, message: "Amount must be positive"}`
    - [ ] Single `database.connect` block:
      - [ ] `UPDATE bank.__account SET balance = balance + %s WHERE moniker = %s RETURNING id, balance`
      - [ ] `INSERT INTO bank.__transaction (accountid, amount, transactiontype, description, membermoniker) VALUES (%s, %s, %s, %s, %s)` using the returned `id`
    - [ ] On success, `logentry(..., action="add_funds", module="bank", ...)` and return `{success: True, message, new_balance}`
  - [ ] `remove_funds(moniker, amount, transaction_type="debit", description="", member_moniker="") -> dict`:
    - [ ] Validate `amount > 0`; return failure envelope
    - [ ] `self.accounts.get(moniker)`; return "Account not found" with `action="remove_funds_failed"` if missing
    - [ ] If `account["balance"] < amount`, return "Insufficient funds. Balance: …" with `action="remove_funds_failed"`, `level=WARNING`
    - [ ] Single `database.connect` block:
      - [ ] `UPDATE bank.__account SET balance = balance - %s WHERE moniker = %s RETURNING id, balance`
      - [ ] `INSERT INTO bank.__transaction (...)` with the returned `id`
    - [ ] On success, `logentry(..., action="remove_funds", module="bank", ...)` and return `{success, message, new_balance}`
- [ ] `services/bank/__init__.py` — `from .account import AccountService; from .ledger import LedgerService; __all__ = ["AccountService", "LedgerService"]`
- [ ] `services/bank/api/handler.py`:
  - [ ] Top-of-file import: `from bbsengine6.bank import BankService` → `from bbsengine6.services.bank import AccountService, LedgerService`
  - [ ] Constructor: `self.bank_service = BankService(args)` → `self.accounts = AccountService(args); self.ledger = LedgerService(args)`
  - [ ] `_handle_balance`: `self.bank_service.get_balance(moniker)` → `self.accounts.get_balance(moniker)`; `self.bank_service.account.get(moniker)` → `self.accounts.get(moniker)`
  - [ ] `_handle_add`: `self.bank_service.add_funds(...)` → `self.ledger.add_funds(...)`
  - [ ] `_handle_remove`: `self.bank_service.remove_funds(...)` → `self.ledger.remove_funds(...)`
  - [ ] Leave `_handle_history`, `_handle_pending`, `_handle_transfer_*`, `_handle_list_all` unchanged (handled in later 7.x subphases)
  - [ ] SQL reference `cur.execute("SELECT * FROM bank.__account …")` (line 259) unchanged — schema namespace is independent of the Python path

#### Shim (in-tree only)
- [ ] `bbsengine6/bank/__init__.py` — temporary re-export:
  ```python
  # Deprecated shim — use bbsengine6.services.bank instead.
  from bbsengine6.services.bank import AccountService as Account
  __all__ = ["Account"]
  ```
  (`LedgerService` is new, no alias needed. `Transaction` / `Transfer` aliases land when those services are promoted.)

#### Tests
- [ ] `bbsengine6/py/tests/test_bank.py`:
  - [ ] Update import to `from bbsengine6.services.bank import AccountService, LedgerService` (keep `Transaction` / `Transfer` lines for later subphases)
  - [ ] Rewrite call sites currently written as `bank.account.get_or_create(...)` → `account_service.get_or_create(...)`
  - [ ] Add minimal coverage for `LedgerService.add_funds` / `remove_funds` if not already present: happy path, `amount <= 0`, missing account, insufficient funds
- [ ] `bbsengine6/py/tests/conftest.py` — unchanged (only references `bank.sql` schema)

#### Verify
- [ ] `rg -n "bbsengine6\.bank" bbsengine6/` returns only the shim file
- [ ] `rg -n "BankService" bbsengine6/ empyre/ casino/ mistermcfeely/` returns no matches
- [ ] `rg -n "bank\.account\." bbsengine6/` returns no matches
- [ ] `pytest bbsengine6/py/tests/test_bank.py` passes
- [ ] WebSocket smoke: `bank_balance` → `bank_add(10)` → `bank_balance` reflects +10
- [ ] WebSocket smoke: `bank_remove` over current balance returns `Insufficient funds` and writes nothing to `bank.__account` or `bank.__transaction`
- [ ] WebSocket smoke: `bank_add` with `amount <= 0` returns failure envelope, no DB writes
- [ ] Logs show `module="bank"` preserved in `logentry` calls

#### Out of scope (later 7.x subphases)
- Promoting `Transaction` → `TransactionService` (owns `bank.__transaction` writes for transfers)
- Promoting `Transfer` → `TransferService` and updating the transfer/approve/reject/pending handlers
- Deleting `services/bank/bank.py`
- DeprecationWarning on the shim, cross-repo migration, shim deletion (Phase 7.8)

### 7.3 Update internal imports
- [ ] `services/bank/api/handler.py:3` — `from bbsengine6.bank import BankService` → `from bbsengine6.services.bank import AccountService, TransactionService, TransferService`
- [ ] `services/bank/api/handler.py:53` — `self.bank_service = BankService(args)` → `self.account = AccountService(args)`, `self.transaction = TransactionService(args)`, `self.transfer = TransferService(args)`; update each handler method to call the right service
- [ ] `services/bank/api/handler.py:259` — `cur.execute("SELECT * FROM bank.__account …")` (SQL, **unchanged**)
- [ ] In-file relative imports — adjust one extra level (`from ..util import logentry` → `from ...util import logentry`)
- [ ] Leave SQL references (`bank.__account`, `bank.__transaction`, `bank.__transfer`) untouched — schema namespace is independent of the Python package path
- [ ] Leave `startup.py` lines 56–61 (`("bank.__account", "bank.sql")` …) untouched

### 7.4 Update in-tree consumers (`bbsengine6/`)
- [ ] `bbsengine6/py/src/bbsengine6/member.py:9` — keep the `bank` import working via the shim (see 7.6) or switch to `from .services.bank import AccountService, TransferService` and update lines 287, 313
- [ ] `bbsengine6/py/src/bbsengine6/console/member.py:543` — same
- [ ] `bbsengine6/py/tests/test_bank.py:11` — update import to `from bbsengine6.services.bank import AccountService, TransactionService, TransferService` and rewrite call sites (currently `bank.account.get_or_create`, `bank.transfer(…)`) against the new service names

### 7.5 Update cross-repo consumers
- [ ] `empyre/` — point `empyre.bank` import (and the `bank.BankService(...)` calls) at the new path
  - [ ] `empyre/src/empyre/lib.py` (lines 17, 26, 237)
  - [ ] `empyre/src/empyre/sysopoptions.py:58`
  - [ ] `empyre/src/empyre/yearlyreport.py:162`
  - [ ] `empyre/src/empyre/combat/joust.py:75`
  - [ ] `empyre/src/empyre/quests/zircon.py:148`
  - [ ] `empyre/src/empyre/quests/raidpiratecamp.py:20`
  - [ ] `empyre/src/empyre/town/lucifersden.py:59`
  - [ ] `empyre/src/empyre/town/naturaldisasterbank.py:32`
  - [ ] `empyre/src/empyre/api/handler.py:120, 578`
  - [ ] `empyre/src/tests/test_bank_integration.py`
  - [ ] `empyre/src/tests/test_town_naturaldisasterbank.py` (lines 76, 94)
- [ ] `casino/src/casino/services/bank.py:8` — `from bbsengine6.bank import BankService as BankModule` → `from bbsengine6.services.bank import AccountService as BankModule` (or whichever subset it actually uses) and update downstream call sites
- [ ] `mistermcfeely/src/postoffice/api/handler.py:100, 363` — switch from `bank.BankService(...)` to the focused service(s)

### 7.6 Back-compat shim (temporary)
- [ ] Replace `bbsengine6/py/src/bbsengine6/bank/__init__.py` with a thin re-export:
  ```python
  # Deprecated shim — use bbsengine6.services.bank instead.
  from bbsengine6.services.bank import (
      AccountService as Account,
      TransactionService as Transaction,
      TransferService as Transfer,
  )
  __all__ = ["Account", "Transaction", "Transfer"]
  ```
  - Note: `BankService` is **not** re-exported here, since 7.2 deletes it; the shim only covers the three DAL classes. Code that called `bank.BankService(...)` must switch to the focused service(s) — surface this in the commit message.
- [ ] Add re-export to `bbsengine6/py/src/bbsengine6/services/__init__.py`:
  ```python
  from .bank import AccountService, TransactionService, TransferService  # noqa: F401
  ```
- [ ] Add a `DeprecationWarning` on import in the shim once call sites are migrated (deferred to 7.8)

### 7.7 Verify
- [ ] `rg -n "bbsengine6\.bank" bbsengine6/` returns only the shim file
- [ ] `rg -n "BankService" bbsengine6/ empyre/ casino/ mistermcfeely/` returns no matches (umbrella is gone)
- [ ] `rg -n "bank\.account\.|bank\.transfer\(|bank\.transaction\." bbsengine6/ empyre/ casino/ mistermcfeely/` returns no matches
- [ ] `pytest bbsengine6/py/tests/test_bank.py` passes
- [ ] Run project linter / typecheck
- [ ] WebSocket smoke test for all bank message types: `bank_balance`, `bank_add`, `bank_remove`, `bank_transfer_request`, `bank_transfer_approve`, `bank_transfer_reject`, `bank_pending`, `bank_history`, `bank_list_all`

### 7.8 Cleanup (follow-up, separate commit)
- [ ] Delete `bbsengine6/py/src/bbsengine6/bank/` shim
- [ ] Update any remaining direct imports of `bbsengine6.bank` to `bbsengine6.services.bank`
- [ ] Remove the `services/__init__.py` re-exports if no longer needed

### 7.9 Per-member accounts for casino hand flow (cross-repo)

Cross-reference. The full task list lives in
`casino/TODO.md` "Rework: route per-hand money through the bank".
bbsengine6 owns one decision: whether per-member accounts are
added to the existing `bbsengine6.bank` package or a new
`bank.__member_account` table is created.

- [ ] **Schema decision (bbsengine6-owned).** Per-member
  accounts in `bbsengine6.bank` (extend the existing package)
  vs a new `bank.__member_account` table (parallel structure).
  Document the decision in `bbsengine6/bank/` once made;
  cross-reference from `casino/TODO.md` "Rework" tasks.
- [ ] **Migration script.** Backfill existing
  `engine.__member.credits` values into the chosen bank
  structure. Reconcile against any `bank.__account` rows
  already mapped to members.
- [ ] **Transactional `LedgerService.credit` / `debit`.**
  Extend the Phase 7.2.1 `LedgerService` so each credit/debit
  is atomic across the `bank.__account` UPDATE and the
  `bank.__transaction` INSERT. Required for the casino's
  "one transaction per hand" requirement.

## 8. Security Review: AuthService and PlayerService

**Status:** Planning
**Mode:** Read-only review. No code changes; no refactor sketches. Build phase is separate.

**Decisions:**
- Output: one report per class file (4 reports) + 1 cross-project consolidation addendum
- Lens: security only (credential handling, secrets, session lifecycle, channel subscription, error responses). No DRY/code-quality findings.
- Test gaps: list missing test cases by name only. No test bodies drafted.
- Non-goals: no refactor proposal, no code changes, no deep dive into underlying credential validators (verifyMemberFound, checkpassword, etc.), no commentary on zoid6 TODO for future empyre PlayerService.
- Cross-project AuthService duplication: noted in each per-class report (security-relevant differences only); full delta in consolidation addendum.

### 8.1 Report: `casino.PlayerService`
- [ ] Read `casino/src/casino/services/player.py` (70 lines)
- [ ] Read constructor / instantiation sites
- [ ] Read associated test files to map current security-relevant coverage
- [ ] Draft report: Scope, Findings (severity-tagged), Test gaps (names only), Cross-project note
- [ ] Write report to output location

### 8.2 Report: `casino.AuthService`
- [ ] Read `casino/src/casino/api/handler.py:101-171` (`AuthService` class)
- [ ] Read `MessageRouter` instantiation site (`handler.py:1175`)
- [ ] Read associated test files: `casino/src/casino/tests/test_api.py`, `test_channel_integration.py`, `test_player_observer.py`, `test_player_stats.py`, `test_player_stats_integration.py`
- [ ] Draft report: Scope, Findings, Test gaps, Cross-project note (compare to mistermcfeely + empyre AuthService)
- [ ] Write report to output location

### 8.3 Report: `mistermcfeely.AuthService`
- [ ] Read `mistermcfeely/src/postoffice/api/handler.py:58-126` (`AuthService` class)
- [ ] Read `MessageRouter` instantiation site (`handler.py:486`)
- [ ] Read associated test files: `mistermcfeely/tests/test_email_auth_integration.py`, `test_password_integration.py`, `test_audit_log.py`
- [ ] Draft report: Scope, Findings, Test gaps, Cross-project note
- [ ] Write report to output location

### 8.4 Report: `empyre.AuthService`
- [ ] Read `empyre/src/empyre/api/handler.py:69-148` (`AuthService` class)
- [ ] Read `MessageRouter` instantiation site (`handler.py:701`)
- [ ] Read associated test file: `empyre/src/tests/test_api_handler.py`
- [ ] Draft report: Scope, Findings, Test gaps, Cross-project note
- [ ] Write report to output location

### 8.5 Cross-`AuthService` Consolidation Addendum
- [ ] Compare the three `AuthService` implementations on security-relevant axes only:
  - [ ] Credential helper differences (timing-attack surface, error semantics)
  - [ ] Session registration differences (authz boundary location)
  - [ ] Channel-subscription differences (who can subscribe, race conditions)
  - [ ] Logging/audit differences (failure visibility)
  - [ ] Response payload differences (what leaks to client post-auth)
- [ ] No refactor proposal. Observations only.

### 8.6 Severity Categories (used in all 4 reports)
- [ ] `blocker` — must fix
- [ ] `major` — should fix
- [ ] `minor` — nice to fix
- [ ] `nit` — style/clarity

### 8.7 Test Gap Categories (security-relevant only, names only)
- [ ] Bad-password paths
- [ ] Unknown-moniker paths
- [ ] DB-error paths
- [ ] Double-auth / re-auth
- [ ] Disconnect-during-auth
- [ ] Channel-subscribe authz (cross-moniker)
- [ ] Logging-on-failure (audit trail)
- [ ] Constant-time password comparison (where testable)

### 8.8 Follow-up (separate, post-review)
- [ ] Code changes and refactor (deferred — will be planned after this review lands)

---

## `bbsengine6.io` sink infrastructure for thin-client BED conversion

### Context and scope

The thin-client BED conversion (planned across `empyre/TODO.md`,
`bed/TODO.md`, and the per-game cross-references) needs a way to
intercept every `bbsengine6.io` primitive call (`echo`, `inputchoice`,
`inputstring`, `inputboolean`, `inputinteger`, `inputchar`, `inputdate`,
`inputfilename`, `inputpassword`, `screen.setbottombar`,
`screen.register_bottombar_fragment`,
`screen.unregister_bottombar_fragment`) and dispatch it to a per-connection
`BEDSink` that builds BED wire envelopes, instead of writing to stdout
or reading from a TTY.

The interception mechanism must be:
- **Asyncio-native** (per-task isolation via `contextvars.ContextVar`).
- **100% backward-compatible** (door mode with no sink installed is
  byte-for-byte identical to today).
- **Opt-in per connection** (the BED process installs a `BEDSink` at
  `WebSocketServer.on_connect` time; door-mode processes never install
  one).
- **Reusable across all games** (empyre, casino, murdermotel,
  mistermcfeely, zoid6, plus any future BED-hosted game).

The work is split into six phases. Backward compat is verified at
every phase boundary by running the door-mode test corpus against the
refactored code and asserting byte-for-byte equality of the rendered
output.

### Door-mode test corpus (Phase 0a pre-flight)

The door-mode test corpus is the set of `bbsengine6/tests/` files
that exercise the `io` and `screen` modules in door-mode (no
`WebSocketServer`, no BED). For each phase boundary, the corpus is
run; any failure means the phase is not complete.

Corpus files (read from `bbsengine6/py/tests/`):
- `test_inputchoice_key_f2.py` — inputchoice F2 (cross-references the
  `key_f2` work in `bed/TODO.md`).
- `test_inputstring_enhancements.py` — inputstring.
- `test_inputstring_key_f1.py` — inputstring F1.
- `test_key_events.py` — keystroke handling.
- `test_screen.py` — screen module.
- `test_more_prompt.py` — more-prompt.
- `test_terminal_title.py` — terminal.
- `test_template.py`, `test_tmpl.py` — template/MCI tokens.
- `test_md2tpl.py` — md → tpl.
- `test_interactive_harness.py` — interactive.
- `test_ed.py`, `test_ed_line.py`, `test_ed_integration.py` — editor.
- `test_indent.py` — indent.
- `test_buildrec.py` — buildrec.
- `test_bank.py` — bank.
- `test_bed_router_loading.py` — BED router loading (cross-references
  the `MessageRouter` work in Phase 5 below).
- `test_packet_codec.py` — packet codec.
- `test_pluralize.py` — pluralize.

The new `bbsengine6/tests/test_io_backward_compat.py` will run this
corpus at every phase boundary and assert byte-for-byte equality of
the rendered output for a fixed battery of inputs (plain text, MCI
tokens, `{var:foo}` references, ANSI escapes).

### Pre-flight grep: `io.echo` return-value usage (Phase 0a pre-flight)

Pre-flight grep result: **zero matches** for any of:
- `result = io.echo(`
- `return io.echo(`
- `if io.echo(`
- `assert io.echo(`
- `yield io.echo(`
- `, io.echo(`

The 6,665 `io.echo(...)` call sites across the monorepo are all bare
calls (the return value is discarded). This means Phase 3 (changing
`echo()` to return `str`) is safe — no existing caller will be
surprised by the new return type.

### Phase 0 — Sink infrastructure (no behavior change)

- [ ] Add `bbsengine6/io/sink.py` with:
  - `class Sink(Protocol)`: structural-typed protocol with one method
    per primitive (`echo`, `inputchoice`, `inputstring`, `inputboolean`,
    `inputinteger`, `inputchar`, `inputdate`, `inputfilename`,
    `inputpassword`, `screen_setbottombar`,
    `screen_register_bottombar_fragment`,
    `screen_unregister_bottombar_fragment`).
  - `class DefaultSink`: implements the protocol by delegating to the
    current `bbsengine6.io` private `_impl` functions.
  - `class IOSinkError(Exception)`: raised when a sink is missing a
    primitive.
  - Module-level `_active_sink: ContextVar[Optional[Sink]] =
    ContextVar("bbsengine6_io_sink", default=None)`.
  - `def set_io_sink(sink: Sink) -> Token`,
    `def reset_io_sink(token: Token) -> None`,
    `def get_active_sink() -> Optional[Sink]`,
    `def require_active_sink() -> Sink`.
- [ ] Refactor each `bbsengine6.io` primitive into:
  - `def _impl_xxx(...)`: the current code path, unchanged.
  - `def xxx(...)`: the public function. If
    `_active_sink.get()` returns a non-`None` sink, dispatch to
    `sink.xxx(...)`. Otherwise call `_impl_xxx(...)`.
- [ ] Apply to: `echo`, `inputchoice`, `inputstring`, `inputboolean`,
  `inputinteger`, `inputchar`, `inputdate`, `inputfilename`,
  `inputpassword`, `screen.setbottombar`,
  `screen.register_bottombar_fragment`,
  `screen.unregister_bottombar_fragment`.
- [ ] **Backward compat check**: all existing tests in
  `bbsengine6/tests/` pass with zero changes. The default sink is
  `None`, so the public functions take the `_impl` path, which is the
  current code. `test_io_backward_compat.py` runs the door-mode
  corpus and asserts byte-for-byte equality.
- [ ] Add `bbsengine6/tests/test_io_sink.py`:
  - `test_no_sink_uses_default`: no sink installed → `echo("hello")`
    takes the `_impl` path.
  - `test_set_io_sink_dispatches`: install a recording sink, call
    `echo("hello")`, assert the sink received the call.
  - `test_reset_io_sink_restores_default`: install a sink, reset,
    call `echo("hello")`, assert default behavior.
  - `test_nested_sinks`: install sink A, install sink B (returns a
    token), reset B, assert A is active; reset A, assert default.
  - `test_asyncio_task_isolation`: in two concurrent asyncio tasks,
    install different sinks; each task sees its own sink (contextvar
    semantics).
  - `test_sink_missing_primitive_raises`: sink doesn't implement
    `inputchoice`; `io.inputchoice(...)` raises `IOSinkError`.

### Phase 1 — `echo_render()` public function (mod 2)

- [ ] Add `bbsengine6/io/echo_render.py` with:
  - `def echo_render(text: str, **kwargs) -> str`: pure function, no
    I/O. Applies MCI token substitution (`{f6}`, `{labelcolor}`,
    `{var:foo}`) and returns the rendered string. The kwargs are the
    same as `echo()` today (`end`, `flush`, `fg`, `bg`, `bold`, etc.).
  - This is the **single source of truth** for "what would the door
    have rendered?".
  - No contextvar lookup, no sink dispatch — purely a string
    transformation.
- [ ] Refactor `bbsengine6.io.echo` to call `echo_render(text, **kwargs)`
  internally, then dispatch to the sink (or default `_impl_echo`) for
  the actual I/O.
- [ ] **Backward compat check**: existing tests pass with zero
  changes. The rendered string for any input is byte-for-byte
  identical to the pre-refactor output. `test_io_backward_compat.py`
  passes.
- [ ] Add `bbsengine6/tests/test_echo_render.py`:
  - `test_echo_render_no_io`: `echo_render("hello {f6}world")` returns
    the MCI-substituted string with no stdout output.
  - `test_echo_render_matches_echo`: for a battery of inputs (plain
    text, MCI tokens, `{var:foo}` references, ANSI escapes),
    `echo_render(text)` returns the same string the original
    `echo(text)` would have written to the terminal.
  - `test_echo_render_kwargs`: `end=""`, `flush=True`, `fg=`, `bg=`,
    `bold=` kwargs are all honored.
  - `test_echo_render_pure`: same input always returns same output
    (deterministic, no global state mutation).

### Phase 2 — `mci.parse` / `mci.render` public functions (mod 3)

- [ ] Add `bbsengine6/io/mci.py` with:
  - `class MCITokenKind(Enum)`: `text`, `color`, `var_ref`,
    `palette_ref`, `mci_code`, `ansi_escape`.
  - `class MCIToken`: dataclass with `kind: MCITokenKind`,
    `value: str`, and (for `var_ref`) `name: str`.
  - `def parse(text: str) -> List[MCIToken]`: tokenizes the input.
  - `def render(tokens: List[MCIToken], palette: Dict[str, str]) -> str`:
    renders tokens back to a string using the given palette (which
    maps `{var:foo}` names to color codes).
- [ ] Refactor `echo_render` to use `mci.parse` + `mci.render`
  internally (no behavior change, just structure).
- [ ] Add a "Future: discriminated union" note in this section: if a
  real need shows up (e.g. type-safe rendering, pattern matching on
  token kind), the `MCIToken` dataclass can be replaced with a
  `Union[MCIText, MCIColor, ...]`. v1 uses the dataclass for
  simplicity and minimum invasive-ness.
- [ ] **Backward compat check**: existing tests pass with zero
  changes. `test_io_backward_compat.py` passes.
- [ ] Add `bbsengine6/tests/test_mci.py`:
  - `test_parse_plain_text`: `"hello world"` →
    `[MCIToken(kind="text", value="hello world")]`.
  - `test_parse_mci_code`: `"{f6}"` →
    `[MCIToken(kind="mci_code", value="f6")]`.
  - `test_parse_var_ref`: `"{var:promptcolor}"` →
    `[MCIToken(kind="var_ref", name="promptcolor")]`.
  - `test_parse_mixed`: `"Hello {f6}World {var:foo}"` → mixed list of
    text, mci_code, var_ref.
  - `test_render_roundtrip`:
    `render(parse(text), default_palette) == text` for a battery of
    inputs.
  - `test_render_unknown_var`: `"{var:nonexistent}"` renders as a
    literal `"{var:nonexistent}"` (preserves the original string on
    lookup failure, matching door-mode behavior).
  - `test_parse_ansi_escape`: `"\x1b[31m"` →
    `MCIToken(kind="ansi_escape", value="\x1b[31m")`.

### Phase 3 — `echo()` returns the rendered string (mod 1)

- [ ] Change `bbsengine6.io.echo` signature:
  `def echo(text, **kwargs) -> str`. Returns the rendered string.
- [ ] The default behavior (no sink) calls
  `_impl_echo(rendered, **kwargs)` which writes to stdout/screen
  and returns the rendered string.
- [ ] The sink-based behavior calls `sink.echo(rendered, **kwargs)`
  and returns whatever the sink returns.
- [ ] **Backward compat check**: every existing caller of `echo(...)`
  that doesn't use the return value is unaffected. The pre-flight
  grep (Phase 0a) found zero return-value usages, so no caller
  fixes are needed. `test_io_backward_compat.py` passes.
- [ ] Add `bbsengine6/tests/test_echo_return.py`:
  - `test_echo_returns_rendered_string`: `echo("hello")` returns
    `"hello"`.
  - `test_echo_returns_mci_rendered`: `echo("{f6}hello")` returns the
    MCI-substituted string.
  - `test_echo_sink_return_propagates`: a sink that returns
    `"sink-override"` → `echo("hello")` returns `"sink-override"`.

### Phase 4 — Sink-based variants for the other primitives

- [ ] `inputchoice(prompt, options, default="", **kwargs) -> str | None`:
  if a sink is set, dispatch to `sink.inputchoice(...)`. Otherwise
  call `_impl_inputchoice(...)`.
- [ ] Same for `inputstring`, `inputboolean`, `inputinteger`,
  `inputchar`, `inputdate`, `inputfilename`, `inputpassword`.
- [ ] Same for `screen.setbottombar`,
  `screen.register_bottombar_fragment`,
  `screen.unregister_bottombar_fragment`.
- [ ] **Backward compat check**: door-mode callers see zero behavior
  change. `test_io_backward_compat.py` passes.
- [ ] Add `bbsengine6/tests/test_io_sink_per_primitive.py`: one test
  per primitive, asserting the sink is called when set, the default
  is called when not set, and the return value propagates correctly.

### Phase 5 — `MessageRouter` + `MessageRouterMixin` + `WebSocketServer.on_connect_hook`

This is the integration point that ties the sink infrastructure
(Phases 0–4) to the BED wire format. The `MessageRouter` is the
per-process message dispatcher (one per BED daemon, loaded via
`--router`). The `BEDSink` (defined in `bed/TODO.md`) is a
per-connection adapter that uses the `MessageRouter`'s session API to
manage per-connection state and pending-request futures.

- [ ] Add `MessageRouter` and `MessageRouterMixin` to
  `bbsengine6/net/router.py` (extended, alongside the existing
  `InternetRouter`). The new class sits next to the existing
  `InternetRouter`; both coexist.
  - `class MessageRouter`: per-process message dispatcher. Owns
    per-session state. Methods:
    - `__init__(self, args)`: stores `args`, initializes
      `self.sessions: Dict[int, Dict[str, Any]]` and
      `self.pending_requests: Dict[int, Dict[int, asyncio.Future]]`.
    - `get_session(self, websocket) -> Dict[str, Any]`: returns the
      per-session state dict, creating it if needed.
    - `get_pending_request(self, websocket, request_id: int) ->
      asyncio.Future`: returns the future for a pending IO request,
      creating it if needed.
    - `resolve_pending_request(self, websocket, request_id: int,
      value: Any) -> None`: resolves a pending request's future
      with the given value. No-op (with logentry debug) on late
      replies.
    - `cleanup_session(self, websocket) -> None`: drops all
      per-session state when a WebSocket disconnects.
    - `next_request_id(self, websocket) -> int`: allocates the next
      monotonic `request_id` for a session.
  - `class MessageRouterMixin`: a mixin that adds the same API to
    any class. Per-game routers (`DefaultRouter`,
    `empyre.api.handler.MessageRouter`, etc.) inherit from this
    mixin to gain the API without changing their existing class
    hierarchy. Less invasive than a new base class.
- [ ] Add `WebSocketServer.__init__` parameter
  `on_connect_hook: Optional[Callable[[WebSocket, MessageRouter],
  Awaitable[None]]] = None`. Default `None` = no hook.
- [ ] Modify `WebSocketServer.start` so the inline `on_connect`
  delegates the message loop to the hook when one is registered:
  ```python
  async def on_connect(websocket):
      # ... existing handshake logic ...
      if self._on_connect_hook is not None:
          await self._on_connect_hook(websocket, self.router)
          return
      # Existing message loop (backward compat with no hook)
      async for raw_message in websocket:
          # ... existing dispatch logic ...
  ```
  The hook signature is `async def on_connect_hook(websocket,
  router)`. The `router` is the per-process `MessageRouter` (passed
  in by the `WebSocketServer`).
- [ ] Add `MessageRouterMixin` to
  `bbsengine6.net.defaultrouter.DefaultRouter` (one-line change to
  its class declaration). The `DefaultRouter` gains
  `get_session` / `get_pending_request` / `resolve_pending_request` /
  `cleanup_session` / `next_request_id` via the mixin.
- [ ] **Backward compat check**: the `on_connect_hook` is optional;
  if not provided, the server behaves exactly as before. The
  `MessageRouterMixin` is additive; existing per-game routers that
  don't adopt it still work (they just don't have the session API).
  The `MessageRouter` and `MessageRouterMixin` are additive additions
  to `bbsengine6/net/router.py`; the existing `InternetRouter` is
  unchanged. `test_io_backward_compat.py` passes.
- [ ] Add `bbsengine6/tests/test_message_router_mixin.py`:
  `get_session`, `get_pending_request`, `resolve_pending_request`,
  `cleanup_session`, `next_request_id` work as expected on a class
  that inherits from the mixin.
- [ ] Add `bbsengine6/tests/test_web_socket_server_on_connect_hook.py`:
  hook called after handshake, with `router` argument; hook owns
  the message loop; hook raises → connection closed; no hook →
  backward-compat behavior.
- [ ] Add `bbsengine6/tests/test_message_router_session_api.py`:
  `MessageRouter` (not the mixin) has the same API; the
  `get_session` and `get_pending_request` methods are
  per-connection (keyed by `id(websocket)`); `cleanup_session`
  drops all state.

### Adoption (cross-project)

The new `MessageRouter` / `MessageRouterMixin` / sink infrastructure
is consumed by:

- **`bed`** (`bed/TODO.md`): the `BEDSink` (per-connection adapter)
  holds a reference to the per-process `MessageRouter` and uses
  `get_session` / `get_pending_request` / `next_request_id` to
  build BED envelopes and await replies. The `BEDSink` is installed
  via the `WebSocketServer.on_connect_hook` (option e: the hook
  owns the message loop).
- **`empyre`** (`empyre/TODO.md`): `empyre.api.handler.MessageRouter`
  adds `MessageRouterMixin` to its class declaration (one-line
  change). The empyre per-game router gains the session API.
- **`casino`** (`casino/TODO.md`): cross-reference note (no code
  change required; the casino `MessageRouter` can opt into the
  mixin later if needed).
- **`murdermotel`**, **`mistermcfeely`**, **`zoid6`**: cross-reference
  notes (no code change required for v1).

### Implementation order

1. bbsengine6 Phase 0 (sink infrastructure + sink tests).
2. bbsengine6 Phase 1 (`echo_render` + tests).
3. bbsengine6 Phase 2 (`mci.parse` / `mci.render` + tests).
4. bbsengine6 Phase 3 (`echo` returns str + tests).
5. bbsengine6 Phase 4 (sink-based variants for other primitives +
   tests).
6. bbsengine6 Phase 5 (`MessageRouter` + mixin +
   `WebSocketServer.on_connect_hook` + tests).
7. `bed` Phase 0/1/3/4 (see `bed/TODO.md` "BED `Sink` integration
   with `bbsengine6.io`" section).
8. Game-repo cross-references in `empyre`, `casino`, `murdermotel`,
   `mistermcfeely`, `zoid6` (see each repo's `TODO.md`).

At every step (1–6), `test_io_backward_compat.py` runs the door-mode
corpus and asserts byte-for-byte equality of the rendered output. If
any test fails, the step is not complete.
