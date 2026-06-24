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

### Phase 1F: Notify → message_delivery Rename

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
