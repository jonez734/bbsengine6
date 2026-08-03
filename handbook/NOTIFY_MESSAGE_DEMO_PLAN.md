# Notify Message Demo - Implementation Plan

> **STATUS (2026-07-22): SUPERSEDED.** The notify_message_demo
> (`bbsengine6/examples/notify_message_demo.py`) was deleted
> along with the rest of the notify package in Phase 7 of
> `TODO-message-migration.md`. This plan is preserved for
> historical reference only. The final state of the demo is
> captured in `NOTIFY_MESSAGE_DEMO_FINAL_SUMMARY.md` (also
> now historical).

## Overview

A multi-user interactive message system demo built on top of bbsengine6's notify system. Users can run separate instances in different terminals and exchange messages using templates with variable substitution.

## Architecture

### Core Components

#### 1. **Message Handler** (`MessageHandler` class)
- Manages user context (moniker, notification queue)
- Receives and processes incoming notifications
- Validates ASCII content
- Renders templates with variables
- Thread-safe queue management

#### 2. **Template System** (`TemplateEngine` class)
- Echo template: `"{sender}: {message}"` (default)
- Custom templates with named variables
- Per-user custom templates (alice_template, bob_template)
- Safe variable substitution
- Variable validation (printable ASCII only)

#### 3. **ASCII Validator** (`AsciiValidator` class)
- Validates all user input (printable ASCII)
- Validates template variables
- Ensures command safety
- Rejects control characters, non-ASCII

#### 4. **Demo Runner** (`NotifyMessageDemo` class)
- Two concurrent user threads (alice, bob)
- Shared notification infrastructure
- Interactive prompt system
- Graceful shutdown (ESC or ctrl+c)
- Message history and statistics

#### 5. **Configuration** (`DemoConfig` dataclass)
- User monikers
- Templates (default + custom)
- Timeouts
- Message limits
- Urgency levels

## Features

### Basic Messaging
- User A sends message → User B receives notification
- User B replies → User A receives notification
- Bidirectional communication with no special sync needed

### Templates
```python
# Echo template (default)
"{sender}: {message}"

# Custom templates per-user
alice_template = "Alice says: {message}"
bob_template = "[BOB] {message}"

# With timestamp
"{timestamp} - {sender}: {message}"

# With emoji (printable ASCII only, no control chars)
">> {sender}: {message}"
```

### Echo Commands
- Available in message input
- Format: `echo <args>` or `!echo <args>`
- Executes shell echo command safely
- Output inserted into message
- Examples:
  - `echo "Hello"` → sends message "Hello"
  - `!echo $(date)` → sends timestamp message
  - `echo {date}` → template variable expansion

### Input Validation
- Only printable ASCII allowed (0x20-0x7E)
- No control characters, escape sequences, or non-ASCII
- Templates validated before use
- Variables checked for ASCII compliance

### Multi-Terminal Support
- Start alice in Terminal 1: `python notify_message_demo.py --user alice`
- Start bob in Terminal 2: `python notify_message_demo.py --user bob`
- Messages flow through shared notify queue
- Each user has independent notification queue

## Implementation Details

### File Structure
```
bbsengine6/py/src/bbsengine6/examples/
├── notify_message_demo.py          # Main demo module (450+ lines)
└── tests/
    └── test_notify_message_demo.py # Comprehensive tests (500+ lines)
```

### Class Hierarchy

```
NotifyMessageDemo (main runner)
├── MessageHandler (per-user)
│   ├── AsciiValidator
│   ├── TemplateEngine
│   └── NotificationQueue
└── DemoConfig (configuration)
```

### Thread Safety
- Thread-local storage for user context
- Lock-protected access to:
  - Message queue
  - Message history
  - Statistics counters
- Atomic operations for round counting
- Event-based shutdown signaling

### Notification Flow
```
User A Input
    ↓
ASCII Validation
    ↓
Echo Command Processing (optional)
    ↓
Template Rendering
    ↓
Create Notification (sender=A, recipient=B)
    ↓
Engine Notify Queue
    ↓
User B's Notification Queue (UserNotificationQueue)
    ↓
User B Reads & Renders
    ↓
Display on Console
```

## Test Coverage

### Unit Tests (150+ lines)
- **AsciiValidator**: Valid/invalid ASCII, edge cases
- **TemplateEngine**: Template rendering, variable substitution, escaping
- **Echo Processing**: Command parsing, execution, output capture
- **Input Validation**: Boundary conditions, special characters

### Integration Tests (150+ lines)
- **Two-way messaging**: A→B→A communication
- **Template variants**: Different templates per user
- **Echo commands**: Command execution in templates
- **Rate limiting**: Hit notify system limits
- **Blocking**: User blocking behavior
- **Concurrent access**: Thread safety

### Behavior Tests (150+ lines)
- **Happy path**: Normal message exchange
- **Error recovery**: Invalid input handling
- **Edge cases**: Empty messages, max length, special chars
- **Shutdown**: Clean exit scenarios

### Performance Tests (50+ lines)
- Message throughput
- Template rendering speed
- Queue access latency
- Memory usage under load

## Usage Examples

### Basic Two-User Demo
```bash
# Terminal 1
python notify_message_demo.py --user alice

# Terminal 2
python notify_message_demo.py --user bob
```

### Custom Templates
```bash
# Terminal 1 - Alice with custom template
python notify_message_demo.py --user alice \
  --template "Alice: {message}"

# Terminal 2 - Bob with different template
python notify_message_demo.py --user bob \
  --template "[BOB RECEIVED] {message}"
```

### With Echo Commands
```
alice@prompt> echo "Hello Bob"
# Sends message: "Hello Bob"

bob@prompt> echo "I'm at $(date +%H:%M)"
# Sends message with current time

alice@prompt> !echo "Test message"
# Alternative ! prefix syntax
```

### Mixed Communication
```
alice@prompt> Hello Bob!
bob@prompt> Hi Alice! Just got your message
alice@prompt> echo "Great to hear from you"
bob@prompt> reply with custom template
alice@prompt> quit
```

## Configuration Options

### Command-line Arguments
```python
--user MONIKER           # Username (alice, bob, etc)
--template TEMPLATE      # Custom message template
--max-messages N         # Max messages per session (default: 50)
--timeout SECONDS        # Notification check timeout (default: 2.0)
--urgency LEVEL          # Notification urgency (default: ROUTINE)
--no-echo-commands       # Disable echo command processing
--rate-limit RATE        # Max messages/hour (default: 100)
```

### Template Variables
- `{sender}` - Sending user's moniker
- `{message}` - The message content
- `{timestamp}` - ISO format timestamp
- `{sequence}` - Message sequence number
- Custom variables from echo output

## Security & Validation

### Input Validation Layers
1. **ASCII Check**: Only printable ASCII (0x20-0x7E)
2. **Length Check**: Max 500 chars per message
3. **Template Check**: Valid variable syntax
4. **Command Check**: Only echo allowed, args validated
5. **Database Check**: Moniker exists, rate limit OK

### Protection Against
- Control character injection
- Terminal escape sequences
- Command injection (echo args only)
- SQL injection (via notify system)
- Buffer overflow (size limits)
- Rate limit attacks (notify system)

## Key Design Decisions

1. **Single Echo Command**: Keep it simple, only echo allowed
   - Safe to execute (no pipes, redirects, etc)
   - Clear security boundary
   - Easy to test

2. **Printable ASCII Only**: No UTF-8, emojis, or control chars
   - Works on all terminals
   - Simple validation logic
   - Clear security model

3. **Template Variables**: Safe string substitution only
   - No eval() or code execution
   - No format string attacks
   - Explicit variable list

4. **Per-User Templates**: Different rendering per user
   - More flexible demo
   - Shows template system capabilities
   - Easier to follow different user perspectives

5. **Thread-Local Context**: No shared state confusion
   - Each user has own validation context
   - No race conditions
   - Clear ownership

## Performance Considerations

- Template rendering: O(1) per message
- ASCII validation: O(n) where n = message length
- Queue operations: O(1) deque operations
- Memory: ~1KB per queued message
- CPU: Minimal, I/O bound on user input

## Error Handling

```python
Handled Scenarios:
├── Invalid moniker → User not found
├── Template syntax error → Show error, request retry
├── ASCII validation fail → Reject character, show hint
├── Rate limit exceeded → Notify, wait, retry
├── Notification queue full → Drop oldest, log warning
├── User blocked → Silently drop (standard behavior)
├── Invalid echo command → Show error, request retry
├── Database error → Graceful error message, close
└── Shutdown (ESC/ctrl+c) → Clean exit, show stats
```

## Future Extensions

1. **More Command Types**: Besides echo (cat, date, etc)
2. **File Attachment**: Send small text files
3. **Message Encryption**: Optional user privacy
4. **Persistent History**: Save to database
5. **Web UI**: Browser-based variant
6. **More Templates**: Pre-built template library
7. **User Groups**: Send to multiple users
8. **Analytics**: Message statistics, graphs

## Success Criteria

- [x] Two users can exchange messages in separate terminals
- [x] Templates work with variable substitution
- [x] Echo commands execute safely
- [x] ASCII validation prevents injection attacks
- [x] Custom per-user templates work
- [x] Comprehensive test coverage (400+ lines)
- [x] Code passes linting (ruff format + check)
- [x] Clear documentation and examples
- [x] Graceful error handling
- [x] Thread-safe operations
