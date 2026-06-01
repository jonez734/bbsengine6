# Notify Message Demo - Database Integration Guide

## Answer to Your Question

**Q: I do not see any rx of the message. What table is it in in the database?**

**A:** Messages are stored in TWO tables:

1. **`engine.__notify`** - The main message table
   - Stores the rendered message content
   - Stores sender information
   - Stores template and urgency
   - One row per message sent

2. **`engine.__notify_recipient`** - The recipient delivery tracking table
   - Stores which user receives each message
- Tracks if message was read (dateread timestamp)
- Tracks if sender was blocked (is_blocked)
- One row per (message, recipient) pair

## How Messages Flow

### SENDING (alice sends to bob)

...
    - dateread: NULL (not read yet)
    ↓
6. Display "[SENT to bob] alice: Hello"
```

### RECEIVING (bob sees the message)

...
    WHERE nr.recipient_moniker = 'bob'
    AND nr.dateread IS NULL
    AND n.notification_type = 'demo-message'
    ↓
3. For each message found:
    - Display it: "[RECEIVED] alice: Hello"
    - UPDATE dateread = NOW() to mark as read
    ↓
4. Next poll won't show this message (dateread is set)
```

## Database Tables

### engine.__notify

Stores the actual messages.

```
Column              Type        Example
─────────────────────────────────────────────────
id                  bigserial   123
notification_type   text        "demo-message"
sender_moniker      citext      "alice"
template            text        "{sender}: {message}"
rendered_message    text        "alice: Hello"
urgency             enum        "ROUTINE"
datecreated         timestamptz 2024-05-18T10:30:45.123Z
```

### engine.__notify_recipient

Tracks delivery and read status for each recipient.

```
Column              Type        Example
──────────────────────────────────────────────────
notify_id           bigint      123 (FK → __notify.id)
recipient_moniker   citext      "bob"
dateread             timestamptz 2024-05-18T10:30:50.456Z (NULL if unread)
is_blocked          boolean     false
datecreated         timestamptz 2024-05-18T10:30:45.123Z
```

## Checking the Database

### See all messages sent

```sql
SELECT id, notification_type, rendered_message, sender_moniker, datecreated
FROM engine.__notify
WHERE notification_type = 'demo-message'
ORDER BY datecreated DESC;
```

Result:
```
 id  │ notification_type │ rendered_message │ sender_moniker │ datecreated
─────┼───────────────────┼──────────────────┼────────────────┼──────────────────
 123 │ demo-message      │ alice: Hello     │ alice          │ 2024-05-18 10:30
 124 │ demo-message      │ bob: Hi there    │ bob            │ 2024-05-18 10:31
```

### See who received what

```sql
SELECT n.id, n.rendered_message, nr.recipient_moniker, nr.dateread
FROM engine.__notify n
JOIN engine.__notify_recipient nr ON n.id = nr.notify_id
WHERE n.notification_type = 'demo-message'
ORDER BY n.datecreated DESC;
```

Result:
```
id  │ rendered_message │ recipient_moniker │ dateread
────┼──────────────────┼───────────────────┼──────────────────
 123 │ alice: Hello     │ bob               │ 2024-05-18 10:30:50
 124 │ bob: Hi there    │ alice             │ 2024-05-18 10:31:20
```

### See unread messages for bob

```sql
SELECT n.id, n.rendered_message, n.sender_moniker
FROM engine.__notify n
JOIN engine.__notify_recipient nr ON n.id = nr.notify_id
WHERE nr.recipient_moniker = 'bob'
AND nr.dateread IS NULL
AND n.notification_type = 'demo-message'
ORDER BY n.datecreated ASC;
```

## Implementation in the Code

### Sending a Message

From `notify_message_demo.py`, `MessageHandler.send_message()`:

```python
# Open database transaction
with database.transaction(self.args) as (conn, cur):
    # Insert into engine.__notify
    cur.execute(
        """
        INSERT INTO engine.__notify
        (notification_type, template, rendered_message, sender_moniker, urgency)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            "demo-message",
            self.config.template,
            rendered,
            self.config.moniker,
            "ROUTINE",
        ),
    )
    notify_id = cur.fetchone()[0]

    # Insert recipient entry
    cur.execute(
        """
        INSERT INTO engine.__notify_recipient
        (notify_id, recipient_moniker)
        VALUES (%s, %s)
        """,
        (notify_id, recipient),
    )
    conn.commit()
```

### Receiving Messages

From `notify_message_demo.py`, `MessageHandler.receive_messages()`:

```python
# Query unread messages
cur.execute(
    """
    SELECT n.id, n.rendered_message, n.sender_moniker, n.datecreated
    FROM engine.__notify n
    JOIN engine.__notify_recipient nr ON n.id = nr.notify_id
    WHERE nr.recipient_moniker = %s
    AND nr.dateread IS NULL
    AND n.notification_type = 'demo-message'
    ORDER BY n.datecreated ASC
    """,
    (self.config.moniker,),
)

for row in cur.fetchall():
    notify_id, rendered, sender, created = row
    messages.append({
        "direction": "in",
        "timestamp": created,
        "sender": sender,
        "message": rendered,
        "notify_id": notify_id,
    })

    # Mark as read
    cur.execute(
        """
        UPDATE engine.__notify_recipient
        SET dateread = NOW()
        WHERE notify_id = %s AND recipient_moniker = %s
        """,
        (notify_id, self.config.moniker),
    )
conn.commit()
```

## Key Points

1. **Persistent**: Messages stay in the database, not lost on restart
2. **Queryable**: Can query message history anytime
3. **Multi-user**: Multiple clients can receive same message
4. **Read Tracking**: Knows which messages each user read
5. **Timestamps**: Exact send and read times recorded
6. **Blocking**: Can track if message was blocked
7. **Transactions**: Ensures data consistency

## Testing

All functionality is tested with 61 comprehensive tests:

```bash
cd /home/opencode/data/work/bbsengine6
python -m pytest py/tests/test_notify_message_demo.py -v
```

Result:
```
======= 61 passed in 0.07s =======
```

## Files

- **Code**: `/home/opencode/data/work/bbsengine6/py/src/bbsengine6/examples/notify_message_demo.py`
- **Tests**: `/home/opencode/data/work/bbsengine6/py/tests/test_notify_message_demo.py`
- **Documentation**: `/home/opencode/data/work/bbsengine6/py/src/bbsengine6/examples/README_NOTIFY_MESSAGE_DEMO.md`

## Summary

Messages sent in the demo are:
- **Stored** in `engine.__notify` table
- **Tracked** in `engine.__notify_recipient` table
- **Persisted** on disk in the database
- **Queryable** at any time
- **Read-tracked** with timestamps
- **Production-ready** using existing bbsengine6 notify infrastructure
