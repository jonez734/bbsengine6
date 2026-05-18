# NotifyD - IMAP/Event Notification Daemon for bbsengine6

A robust daemon that monitors email servers and application events, routing all notifications through the `bbsengine6.notify` infrastructure. Supports IMAP monitoring with RFC822 parsing, configurable event listeners, and persistent notification history.

## Features

- **IMAP Email Monitoring**: Monitor multiple mailboxes across multiple servers
- **Event System**: Fire custom events from bbsengine6 code that trigger notifications
- **Flexible Credentials**: Three-tier credential lookup (env vars → keyring → prompt)
- **Notification Integration**: Routes all notifications through `bbsengine6.notify`
- **Audit Trail**: Records all notification attempts to PostgreSQL
- **Thread-Safe**: Asynchronous event handling and IMAP polling
- **Graceful Degradation**: Individual server failures don't crash the daemon
- **RFC822 Parsing**: Handles complex email formats with proper encoding handling

## Installation

### 1. Install Dependencies

```bash
cd /home/opencode/data/work/bbsengine6/py
source /home/opencode/.venv/bin/activate
pip install -e .
```

### 2. Create Configuration File

Copy one of the example configs:

```bash
# Minimal config (recommended for getting started)
cp src/bbsengine6/notifyd/examples/minimal.json /etc/bbsengine6/notifyd.json

# Or full config with all options
cp src/bbsengine6/notifyd/examples/full.json /etc/bbsengine6/notifyd.json
```

Edit the config file and add your IMAP servers and notification settings.

### 3. Set Environment Variables

For credentials, use environment variables with the pattern `${VARIABLE_NAME}`:

```bash
# In ~/.bashrc or ~/.profile
export GMAIL_PASSWORD="your-gmail-password"
export SUPPORT_EMAIL_PASSWORD="support-email-password"

# Or set in systemd service file
```

Alternatively, use the OS keyring:

```bash
# Store credentials in system keyring
python -c "import keyring; keyring.set_password('notifyd', 'Gmail:user@gmail.com', 'your-password')"
```

### 4. Create Notification Templates

Copy the example templates:

```bash
# Templates should be in templates/ directory in same location as config
cp src/bbsengine6/notifyd/templates/* /etc/bbsengine6/notifyd/templates/
```

Or create custom templates in the templates directory.

### 5. Initialize Database Schema

The daemon automatically creates the schema on first run, but you can manually run:

```bash
cd /home/opencode/data/work/bbsengine6/py
python -m bbsengine6.notifyd init-db
```

## Configuration

### Configuration File Format

See `examples/config.commented.json` for all available options with detailed explanations.

**Minimal example** (`examples/minimal.json`):
- Single Gmail server
- INBOX monitoring only
- Basic user-login event

**Full example** (`examples/full.json`):
- Multiple email servers
- Multiple mailboxes per server
- Multiple event listeners
- All configuration options

### IMAP Server Configuration

```json
{
  "imap_servers": [
    {
      "name": "Gmail",
      "host": "imap.gmail.com",
      "port": 993,
      "ssl": true,
      "username": "user@gmail.com",
      "password": "${GMAIL_PASSWORD}",
      "mailboxes": ["INBOX"],
      "poll_interval": 60,
      "timeout": 30
    }
  ]
}
```

**Fields**:
- `name`: Server identifier (used for logging)
- `host`: IMAP server hostname
- `port`: IMAP port (993 for SSL, 143 for plain)
- `ssl`: Use SSL/TLS (recommended: true)
- `username`: Email account username
- `password`: Password (see credential options below)
- `mailboxes`: List of mailboxes to monitor (case-sensitive)
- `poll_interval`: Check for new emails every N seconds
- `timeout`: Connection timeout in seconds

### Credential Options

Three-tier fallback for passwords:

1. **Environment Variables** - Fastest, no interaction:
   ```json
   "password": "${GMAIL_PASSWORD}"
   ```
   Will look for `GMAIL_PASSWORD` env var

2. **OS Keyring** - Secure, interactive setup once:
   ```json
   "password": "keyring.get_password('notifyd', 'Gmail:user@gmail.com')"
   ```
   Set up with:
   ```bash
   python -c "import keyring; keyring.set_password('notifyd', 'Gmail:user@gmail.com', 'password')"
   ```

3. **User Prompt** - Fallback if neither above works:
   ```json
   "password": "prompt"
   ```
   Will interactively ask for password

### Event Listener Configuration

```json
{
  "event_listeners": {
    "user-login": {
      "recipients": ["admin@example.com", "security@example.com"],
      "template": "user-login.tmpl",
      "urgency": "high"
    }
  }
}
```

**Fields**:
- `recipients`: List of email addresses to notify
- `template`: Template file to use (in templates/ directory)
- `urgency`: Level - "low", "medium", "high", "critical"

### Notification Templates

Template files use `{variable_name}` syntax:

```
Email from {sender}

{subject}

{body}

---
From: {sender}
Subject: {subject}
Date: {date}
```

**Available variables** (depend on notification type):

IMAP emails:
- `{sender}` - Email sender
- `{subject}` - Email subject
- `{body}` - Email body (first 500 chars)
- `{date}` - Email date

Events (custom):
- Any variables passed to `fire_event()` in code

## Usage

### Starting the Daemon

```bash
# Start in foreground (for debugging)
python -m bbsengine6.notifyd start

# Start as systemd service
sudo systemctl start notifyd
sudo systemctl enable notifyd  # Auto-start on boot
```

### CLI Commands

```bash
# Check daemon status
python -m bbsengine6.notifyd status

# Test IMAP connections
python -m bbsengine6.notifyd test-imap

# Test notification sending
python -m bbsengine6.notifyd test-notify

# Stop daemon
python -m bbsengine6.notifyd stop

# View configuration
python -m bbsengine6.notifyd config
```

### Firing Events from Code

```python
import bbsengine6.notifyd as notifyd
from datetime import datetime

# Fire an event
notifyd.fire_event("user-login", {
    "username": "john.doe",
    "ip_address": "192.168.1.100",
    "timestamp": datetime.now().isoformat(),
})
```

See `examples/integration_examples.md` for detailed integration examples.

### Systemd Service

Install the systemd service file:

```bash
sudo cp src/bbsengine6/notifyd/notifyd.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start notifyd
sudo systemctl status notifyd
```

View logs:

```bash
sudo journalctl -u notifyd -f
```

## Architecture

### Components

- **config.py** - JSON configuration loading with env var substitution
- **credentials.py** - Hybrid credential retrieval (env → keyring → prompt)
- **imap_monitor.py** - IMAP polling with RFC822 email parsing
- **hooks.py** - Thread-safe event bus for async event handling
- **event_listener.py** - Config-driven event handler registration
- **notification.py** - Notification dispatcher with bbsengine6.notify integration
- **storage.py** - PostgreSQL state tracking (UID tracking, history)
- **daemon.py** - Daemon lifecycle management with signal handling
- **cli.py** - Command-line interface

### Data Flow

```
IMAP Server
    ↓
imap_monitor.poll() → [RFC822 email]
    ↓
notification.send_imap_notification()
    ↓
bbsengine6.notify.notify()
    ↓
User Notification

Application Code
    ↓
notifyd.fire_event()
    ↓
event_listener → notification.send_custom_notification()
    ↓
bbsengine6.notify.notify()
    ↓
User Notification
```

### Thread Model

- **Main thread**: Config loading, signal handling
- **IMAP poller thread**: Monitors email servers (non-daemon)
- **Event bus thread pool**: Async event handler execution
- **Graceful shutdown**: SIGTERM/SIGINT → stop threads → exit

## Testing

### Run Tests

```bash
cd /home/opencode/data/work/bbsengine6/py
python -m pytest src/bbsengine6/notifyd/tests/ -v

# With coverage
python -m pytest src/bbsengine6/notifyd/tests/ -v --cov=bbsengine6.notifyd
```

### Test Results

- **193 tests passing** (1 skipped)
- **92% average coverage**
- 100% coverage on: imap_monitor, storage, event_listener, credentials

### Manual Testing

```bash
# Test IMAP connections
python -m bbsengine6.notifyd test-imap

# Test notification sending
python -m bbsengine6.notifyd test-notify

# Start daemon and monitor
python -m bbsengine6.notifyd start
# In another terminal:
tail -f /var/log/bbsengine6/notifyd.log
```

## Troubleshooting

### Daemon Won't Start

Check the configuration file:

```bash
python -m bbsengine6.notifyd config
```

Common issues:
- Missing config file at `/etc/bbsengine6/notifyd.json`
- Invalid JSON syntax
- Missing required fields (imap_servers, notification_settings)

### IMAP Connection Failures

Test connection to specific server:

```bash
python -m bbsengine6.notifyd test-imap
```

Common issues:
- Wrong host/port (use 993 for SSL, 143 for plain)
- Incorrect credentials (check env vars and keyring)
- SSL certificate issues (update ca-certificates)
- Firewall blocking IMAP port

### Notifications Not Sending

Check that bbsengine6.notify is properly configured:

```bash
python -m bbsengine6.notifyd test-notify
```

Common issues:
- bbsengine6.notify not installed
- Notification database not configured
- Event not registered in config

### Missing Email Body

Check that template file exists:

```bash
ls -la /etc/bbsengine6/notifyd/templates/
```

Common issues:
- Template file not found (check name and extension)
- Invalid variable names in template (check syntax)
- Email has no plain text body (HTML-only emails fallback to HTML)

### Database Errors

Check PostgreSQL connectivity:

```bash
python -c "import bbsengine6.database; print('Database OK')"
```

Common issues:
- PostgreSQL not running
- No bbsengine6 schema
- Incorrect connection string in bbsengine6 config

## Performance

### Email Polling

- Each server checked in parallel (separate threads)
- Configurable poll interval per server (default 60 seconds)
- State tracking in PostgreSQL (last UID) - only new emails checked
- Connection pooling for efficiency

### Notification Sending

- Events fire asynchronously (non-blocking)
- Multiple recipients batched in single API call
- Error recording with fallback if storage fails
- Graceful degradation on partial failures

### Resource Usage

- ~50MB memory per running daemon
- 1 thread per IMAP server + main thread
- 1 database connection per operation
- ~1 second per server poll (depends on email count)

## API Reference

### notifyd Module

```python
import bbsengine6.notifyd as notifyd

# Fire an event
notifyd.fire_event(event_name: str, variables: dict) -> None

# Get daemon status
status = notifyd.get_daemon_status() -> dict

# Get notification history
history = notifyd.get_notification_history(
    limit: int = 100,
    event_type: str = None,
    days: int = None
) -> list
```

### Configuration API

```python
from bbsengine6.notifyd.config import load_config

config = load_config("/etc/bbsengine6/notifyd.json")

# Access configuration
servers = config["imap_servers"]
listeners = config["event_listeners"]
settings = config["notification_settings"]
```

## Security Considerations

### Credentials

- Never commit passwords to version control
- Use environment variables for sensitive data
- Use OS keyring for persistent storage
- Prompt as last resort (interactive only)

### Notifications

- Restrict recipient list to authorized users
- Log all notifications for audit trail
- Use HTTPS for all external API calls
- Validate template variables to prevent injection

### Database

- Run daemon with minimal database privileges
- Ensure PostgreSQL is properly secured
- Enable database audit logging
- Restrict notifyd.notification_log table access

### Systemd

- Run daemon as dedicated user (not root)
- Use PrivateTmp, NoNewPrivileges, ProtectSystem
- Limit file/directory access with RestrictAddressFamilies
- Set resource limits (CPUQuota, MemoryLimit)

## Examples

### Basic Setup (Gmail only)

Use `examples/minimal.json`:

```json
{
  "imap_servers": [{
    "name": "Gmail",
    "host": "imap.gmail.com",
    "port": 993,
    "ssl": true,
    "username": "user@gmail.com",
    "password": "${GMAIL_PASSWORD}",
    "mailboxes": ["INBOX"],
    "poll_interval": 60
  }],
  "event_listeners": {
    "user-login": {
      "recipients": ["admin@example.com"],
      "template": "user-login.tmpl",
      "urgency": "high"
    }
  },
  "notification_settings": {
    "enabled": true,
    "log_history": true
  }
}
```

### Enterprise Setup

Use `examples/full.json` with multiple servers, mailboxes, and event types.

### Custom Events

See `examples/integration_examples.md` for code examples.

## Contributing

Running tests:

```bash
cd /home/opencode/data/work/bbsengine6/py
python -m pytest src/bbsengine6/notifyd/tests/ -v
```

Code style:

```bash
ruff format src/bbsengine6/notifyd/
ruff check src/bbsengine6/notifyd/ --fix
```

## Multi-Member Scenarios

**For BBS multi-member support**: Use [getch() integration](GETCH_INTEGRATION.md) with [multi-member guide](GETCH_MULTI_USER.md) for:

- ✅ Native per-member notification isolation
- ✅ Thread-local member identity from `_threadlocal.moniker`
- ✅ Automatic notification filtering per member
- ✅ No daemon needed

**For daemon-based notifications**: See [MULTI_USER_GUIDE.md](MULTI_USER_GUIDE.md) for limitations and workaround patterns.

**Recommended**: Use getch() integration for multi-member BBS systems - it's inherently multi-member aware.

## Related Documentation

- [bbsengine6 Database](../database.py) - Connection pooling and queries
- [bbsengine6 Notify](../notify.py) - Notification infrastructure
- [NOTIFYD_SPEC.md](../../NOTIFYD_SPEC.md) - Full specification and design
- [NOTIFYD_IMPLEMENTATION_CHECKLIST.md](../../NOTIFYD_IMPLEMENTATION_CHECKLIST.md) - Implementation details
- [MULTI_USER_GUIDE.md](MULTI_USER_GUIDE.md) - Multi-user limitations and workarounds

## License

Part of bbsengine6 project.
