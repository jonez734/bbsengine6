# notify_message_demo Specification

## Overview

`notify_message_demo.py` is an interactive two-user messaging demonstration that showcases bbsengine6's notification system with real-time message sending, receiving, and F2-based message viewing.

## Features

### Core Functionality

- **Message Sending**: Type `@<recipient> <message>` to send messages to other users
- **Message Receiving**: Messages appear in recipient's queue (demo mode) or database (persistent mode)
- **F2 Key - View Messages**: Press F2 to display all unread messages
- **Message Status**: Tracks sent/received message counts
- **Template Support**: Customizable message templates with variable substitution
- **Echo Commands**: Optional echo command processing in messages
- **Input Validation**: ASCII-only input validation (printable 0x20-0x7E)

### Demo Modes

#### Demo Mode (Default)
- In-memory message queues using thread-safe deques
- Messages shared across instances within same process
- Max 100 messages per queue
- No persistence - messages lost on exit
- Fastest for testing and development

#### Database Mode
- Persistent storage in PostgreSQL (`engine.__notify` and `engine.__notify_recipient`)
- Survives process restarts
- Supports read status tracking
- Suitable for production use

### F2 Key Feature

#### What F2 Does
- **Display unread messages**: Shows all messages sent to the current user that haven't been read yet
- **Mark as read**: Automatically marks displayed messages as read (demo mode: removes from queue)
- **Show summary**: Displays message count before listing messages
- **Preserve input**: User can continue editing their message after pressing F2

#### Message Display Format
```
--- N unread message(s) ---

[RECEIVED] sender_name: rendered_message
[RECEIVED] sender_name: another_message
```

#### F2 Behavior by Scenario
1. **No messages**: Shows "--- No unread messages ---"
2. **New messages**: Shows count and lists all messages
3. **After viewing**: Second F2 press shows "No unread messages" (all marked as read)
4. **During input**: Displays messages then returns to editing mode

## Architecture

### Class Hierarchy

```
AsciiValidator
├── is_valid_char()      - Single character validation
├── is_valid_string()    - String validation
└── validate_or_raise()  - Validation with exception

TemplateEngine
├── DEFAULT_TEMPLATE = "{sender}: {message}"
├── render()             - Apply template with variables
├── validate_template()  - Check template syntax
├── get_required_variables() - Extract {variable} names
└── safe_substitute()    - Substitute variables safely

EchoProcessor
├── is_echo_command()    - Detect echo commands
└── process_echo()       - Execute echo safely

DemoConfig (dataclass)
├── moniker              - Username (required)
├── template             - Message template (default: "{sender}: {message}")
├── max_messages         - Max queue size (default: 50)
├── check_timeout        - Status check interval (default: 2.0s)
├── urgency              - Message urgency level (default: "ROUTINE")
├── enable_echo_commands - Allow echo processing (default: True)
├── rate_limit           - Max msgs/hour (default: 100)
└── clear_prompt_on_timeout - Clear prompt on idle (default: False)

MessageHandler
├── send_message()       - Send to recipient
├── receive_messages()   - Get unread messages
├── get_stats()          - Get send/receive counts
├── get_history()        - Get message history
└── Demo queues:
    ├── _demo_queues     - Class-level in-memory queues
    └── _queues_lock     - Thread safety lock

NotifyMessageDemo
├── __init__()           - Initialize with config
├── run_interactive()    - Main interactive loop
├── _process_input()     - Parse and execute commands
├── _check_and_display_messages() - F2 handler
├── _get_unread_count()  - Count unread messages
└── _show_stats()        - Display message statistics
```

### F2 Implementation Details

#### Handler Chain
1. **User presses F2** in inputstring
2. **inputstring calls `handle_f2(buffer, curpos, scroll_offset, max_width)`**
3. **`handle_f2()` calls `self._check_and_display_messages()`**
4. **`_check_and_display_messages()` calls `handler.receive_messages()`**
5. **Messages displayed via `echo()` output**
6. **Handler returns buffer unchanged** - user continues editing

#### Key Registration
In `inputstring.py`:
```python
function_key_handlers={
    "KEY_F2": handle_f2,  # Maps F2 key to handler
}
```

#### Status Display
- **Status bar** shows "F2: Messages (n)" where n = unread count
- Updates before each `inputstring()` call via `update_status_display()`

## Commands

### Message Sending
```
@<recipient> <message>
```
Example: `@alice Hello Alice, how are you?`

### Special Commands
- `?` - Show help
- `q` or `quit` - Exit demo
- `stats` - Show message statistics
- `F2` - View unread messages (key press)

### Echo Commands (if enabled)
```
echo <text>     - Execute and output text
!echo <text>    - Alternative syntax
```

## Configuration

### Environment Variables
- `NOTIFY_MESSAGE_DEMO_DATABASENAME` - Database name for persistent mode

### Command Line Arguments
```bash
python notify_message_demo.py --user alice [--databasename zoid6test]
```

### DemoConfig Parameters
```python
config = DemoConfig(
    moniker="alice",                          # Username
    template="{sender}: {message}",           # Message template
    max_messages=50,                          # Queue size
    check_timeout=2.0,                        # Status check interval
    urgency="ROUTINE",                        # Default urgency
    enable_echo_commands=True,                # Allow echo
    rate_limit=100,                           # Messages per hour
    clear_prompt_on_timeout=False             # UI behavior
)
```

## Data Models

### Message Structure (receive_messages)
```python
{
    "direction": "in",                  # "in" or "out"
    "timestamp": datetime,              # Message creation time
    "sender": "alice",                  # Sender moniker
    "message": "alice: Hello Bob",      # Rendered message (with template)
}
```

### Statistics
```python
{
    "sent": 5,          # Messages sent by this user
    "received": 3,      # Messages received by this user
    "errors": 0         # Send/receive errors
}
```

## Threading

- **Thread-safe**: All message operations use locks
- **Demo queue lock**: Protects `_demo_queues` class variable
- **Per-instance lock**: Protects stats and history in MessageHandler
- **Safe concurrent access**: Multiple threads can send/receive simultaneously

## Testing

### Test Suites

1. **test_notify_message_f2_demo.py** (7 tests)
   - Mock/in-memory demo mode tests
   - F2 functionality with demo queues
   - Message persistence across instances

2. **test_notify_message_f2_demo_integration.py** (11 tests)
   - Database integration tests
   - Real PostgreSQL persistence
   - F2 with database backend

3. **test_notify_message_f2_demo_keypresses.py** (11 tests)
   - Keypress simulation tests
   - F2 key behavior
   - Message sending and receiving flow

### Running Tests
```bash
# All F2 tests
pytest tests/test_notify_message_f2_demo*.py -v

# Specific test suite
pytest tests/test_notify_message_f2_demo.py -v

# Single test
pytest tests/test_notify_message_f2_demo.py::TestNotifyMessageF2Demo::test_alice_sends_message_bob_presses_f2 -v
```

## Error Handling

### Input Validation
- **ASCII validation**: Only printable ASCII (0x20-0x7E) allowed
- **Length limits**: Messages max 500 chars, usernames max 50 chars
- **Template validation**: Template syntax checked on config creation

### Graceful Degradation
- **Invalid recipient**: Error logged, message skipped
- **Database errors**: Falls back to demo mode
- **Missing template variables**: Empty string substituted

## Performance Characteristics

### Demo Mode
- **Memory**: ~100 messages per queue × number of users
- **Latency**: <1ms message send/receive
- **Thread contention**: Minimal (lock held briefly)

### Database Mode
- **Latency**: 10-50ms per operation (database round-trip)
- **Scalability**: Limited by database connection pool
- **Persistence**: All messages saved to disk

## Security Considerations

- **Input validation**: ASCII-only prevents injection attacks
- **Template safety**: No code execution in templates
- **SQL injection**: Parameterized queries in database operations
- **Thread safety**: Atomic operations protect concurrent access

## Future Enhancements

- [ ] Message encryption at rest
- [ ] Message expiration (TTL)
- [ ] Read receipts with timestamps
- [ ] Message reactions/emoji
- [ ] Search/filter messages
- [ ] Message history export
- [ ] Integration with other notification types

## References

- `notify.py` - Core notification system
- `inputstring.py` - Interactive input with function key support
- `database.py` - Database connection management
- `screen.py` - Terminal control
