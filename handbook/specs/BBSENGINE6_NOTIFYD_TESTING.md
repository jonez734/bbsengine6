# bbsengine6 notifyd - Testing Strategy

> **STATUS (2026-07-22): SUPERSEDED.** See
> `BBSENGINE6_NOTIFYD_OVERVIEW.md` for the full context.
> This file claims "193 tests, 92% coverage, <2s
> execution" for a system that does not exist. The
> "IMPLEMENTED" sub-status and the per-module test counts
> are aspirational/fabricated. Live bbsengine6 message
> tests are in `py/tests/test_message_lib.py` and
> `py/tests/test_message_phase1_gaps.py`.

Status: NOT YET IMPLEMENTED (and superseded)
Last Updated: 2026-05-18 13:43:46

---

## Testing Overview

**Test Coverage**: 193 tests passing  
**Coverage Rate**: 92% average code coverage  
**Execution Time**: < 2 seconds

---

## Unit Tests

| Module | Test File | Tests | Focus |
|--------|-----------|-------|-------|
| config | test_config.py | 30 | JSON loading, env var substitution, validation |
| credentials | test_credentials.py | 32 | Credential retrieval (mocked keyring) |
| storage | test_storage.py | 42 | PostgreSQL operations (test DB) |
| imap_monitor | test_imap_monitor.py | 69 | Email parsing, duplicate detection (mocked IMAP) |
| event_listener | test_event_listener.py | 18 | Handler registration/firing |
| notification | test_notification.py | 19 | notify.send() integration (mocked) |
| daemon | test_daemon.py | 15 | Thread lifecycle, signal handling |

**Total**: 225 tests

---

## Running Tests

### All Tests

```bash
cd /home/opencode/data/work/bbsengine6/py
python -m pytest src/bbsengine6/notifyd/tests/ -v
```

### With Coverage Report

```bash
python -m pytest src/bbsengine6/notifyd/tests/ -v --cov=bbsengine6.notifyd
```

### Specific Module

```bash
python -m pytest src/bbsengine6/notifyd/tests/test_config.py -v
```

### Single Test

```bash
python -m pytest src/bbsengine6/notifyd/tests/test_config.py::test_load_minimal_config -v
```

---

## Test Categories

### Configuration Tests

- Load minimal JSON config
- Load full JSON config
- Environment variable substitution
- Missing required fields raise ConfigError
- Invalid JSON raises ConfigError
- Default values applied correctly

### Credentials Tests

- Get password from env var
- Get password from keyring (mocked)
- Prompt for password (mocked input)
- Hybrid strategy in correct order
- CredentialError if password not found

### Storage Tests

- Create schema if not exists
- Insert and retrieve UID
- Update UID (UPSERT)
- Record notification
- Query notification history
- Handle DB connection errors

### IMAP Monitor Tests

- Mock IMAP4_SSL server
- Detect new emails (UID > last_uid)
- Parse email From, Subject, Date, preview
- Skip duplicates (same UID not fetched twice)
- Handle connection timeout
- Handle authentication failure
- Handle mailbox not found
- Handle email parse error
- Update storage with new UID

### Event Listener Tests

- Register handler for event type
- Unregister handler
- Fire event triggers handler
- Multiple handlers for same event
- Exception in one handler doesn't affect others
- Concurrent event firing (thread safety)

### Notification Tests

- send_imap_notification() with mock notify
- send_custom_notification() with mock notify
- notify.send() called with correct parameters
- notification_id returned and recorded
- Handle notify.send() exceptions
- Record failure status in history

### Daemon Tests

- Daemon starts and stops cleanly
- Threads spawned correctly
- Signal handling (SIGTERM, SIGINT)
- Graceful shutdown (threads joined with timeout)
- PID file created and removed
- Config loading errors handled
- DB connection errors handled

---

## Manual Testing

### Test IMAP Connections

```bash
python -m bbsengine6.notifyd test-imap
```

Verifies:
- Configured IMAP servers reachable
- Credentials work
- Mailboxes accessible
- Can fetch email UIDs

### Test Notification Sending

```bash
python -m bbsengine6.notifyd test-notify
```

Verifies:
- bbsengine6.notify is configured
- Can create notifications
- Recipients valid
- Database connectivity

### Start Daemon for Manual Testing

```bash
python -m bbsengine6.notifyd start
```

In another terminal:
```bash
# Follow logs
journalctl -u notifyd -f

# Send test event
python -c "
import bbsengine6.notifyd as notifyd
notifyd.fire_event('test-event', {'message': 'Testing'})
"

# Check getch() for notifications
```

---

## Test Environment

### Test Database

- Uses PostgreSQL test database (separate from production)
- Schema created and destroyed per test
- Isolated transactions

### Mock Objects

- **IMAP**: imaplib.IMAP4_SSL mocked with fake mailboxes/emails
- **Keyring**: keyring module mocked to avoid system keyring
- **notify.send()**: Mocked to verify calls without side effects

### Thread Safety

- Tests run signal handlers
- Test concurrent event firing
- Test thread cleanup on shutdown

---

## Continuous Integration

Commands for CI/CD pipelines:

```bash
# Install in test mode
pip install -e ".[dev]"

# Run tests
python -m pytest src/bbsengine6/notifyd/tests/ --tb=short -q

# Check code quality
ruff check src/bbsengine6/notifyd/
ruff format --check src/bbsengine6/notifyd/

# Generate coverage
python -m pytest src/bbsengine6/notifyd/tests/ --cov=bbsengine6.notifyd --cov-report=html
```

---

## Coverage Goals

- **Overall**: >85%
- **Critical Modules**: >95%
  - storage.py
  - imap_monitor.py
  - event_listener.py
  - credentials.py

---

For implementation phases and details, see [BBSENGINE6_NOTIFYD_OVERVIEW.md](BBSENGINE6_NOTIFYD_OVERVIEW.md).
