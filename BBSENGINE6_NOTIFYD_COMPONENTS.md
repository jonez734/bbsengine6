# bbsengine6 notifyd - Component Specifications

Status: NOT YET IMPLEMENTED
Last Updated: 2026-05-18 13:43:46

---

## Core Components

### 1. Configuration System (`config.py`)

**ImapServer Dataclass**:
```python
@dataclass
class ImapServer:
    name: str                          # Unique identifier
    host: str                          # IMAP server hostname
    port: int = 993                    # IMAP port
    use_ssl: bool = True               # Use SSL/TLS
    username: str                      # IMAP login username
    password: str                      # Password from credentials module
    mailbox: str = "INBOX"             # Mailbox to monitor
    poll_interval: int = 30            # Seconds between polls
    notification_type: str = "imap.message"
    recipients: List[str] = field(default_factory=list)
    urgency: str = "ROUTINE"           # ROUTINE|IMPORTANT|URGENT|CRITICAL
    enabled: bool = True               # Whether active
    timeout: int = 10                  # Connection timeout
```

**NotifydConfig Dataclass**:
- `logging`: LoggingConfig
- `database`: DatabaseConfig
- `polling_interval`: Default 30s
- `credentials`: CredentialsConfig
- `imap`: List[ImapServer]
- `events`: EventsConfig
- `load()` classmethod: Load from JSON with env var substitution

### 2. Credentials Management (`credentials.py`)

**CredentialManager Class**:
- Constructor: `__init__(storage: str, keyring_service: str, prompt_on_missing: bool)`
- `get_password(server_name: str, username: str) -> str`
  - Hybrid strategy: env → keyring → prompt
  - Raises `CredentialError` if not found
- `store_password(server_name: str, username: str, password: str)`
  - Stores in keyring for future use

**Environment Variable Convention**:
- Config: `"password": "${GMAIL_PASSWORD}"`
- Maps to: `GMAIL_PASSWORD` environment variable
- Pattern: `${SERVER_NAME.upper().replace('-','_')}_PASSWORD`

### 3. Storage Layer (`storage.py`)

**NotificationStorage Class**:
- `get_last_uid(server: str, mailbox: str) -> int`
  - Returns last processed UID or 0
- `set_last_uid(server: str, mailbox: str, uid: int)`
  - UPSERT operation
- `record_notification(...)`
  - Records to notifyd_history table
- `get_notification_history(limit: int = 100) -> List[dict]`
  - Query recent notifications
- `_ensure_schema()`
  - Create tables if not exist

### 4. IMAP Monitor (`imap_monitor.py`)

**ImapMonitor Class**:
```python
class ImapMonitor:
    def poll(self):
        """Poll all enabled IMAP servers"""
    
    def _poll_server(self, server: ImapServer) -> bool:
        """Poll single IMAP server"""
    
    def _parse_email(self, raw_email_bytes: bytes) -> dict:
        """Parse RFC822 email message"""
```

**Features**:
- IMAP4_SSL connection with timeout
- Login, select mailbox, search, fetch
- RFC822 parsing (From, Subject, Date)
- Duplicate detection via UID tracking
- Per-server error handling (doesn't crash daemon)
- Calls dispatcher for each new email

### 5. Event Hooks (`hooks.py`)

**EventBus Class**:
```python
class EventBus:
    def on(self, event_type: str, handler: Callable[[dict], None]):
        """Register handler"""
    
    def off(self, event_type: str, handler: Callable):
        """Unregister handler"""
    
    def fire(self, event_type: str, data: dict):
        """Fire event (async, non-blocking)"""
    
    def get_handlers(self, event_type: str) -> List[Callable]:
        """Get registered handlers"""
```

**Module-Level Functions**:
- `fire_event(event_type: str, data: dict)`
- `register_event_handler(event_type: str, handler: Callable)`

**Thread Safety**: RLock protects handler registry

### 6. Event Listener (`event_listener.py`)

**EventListener Class**:
```python
class EventListener:
    def __init__(self, config: NotifydConfig, dispatcher: NotificationDispatcher):
        pass
    
    def register_handlers(self):
        """Register all configured handlers"""
    
    def _make_handler(self, event_type: str, handler_config: dict) -> Callable:
        """Create notification handler from config"""
```

**Features**:
- Reads event handlers from config
- Registers with EventBus
- Handler calls dispatcher.send_custom_notification()
- Optional io.KeyEventSystem integration

### 7. Notification Dispatcher (`notification.py`)

**NotificationDispatcher Class**:
```python
class NotificationDispatcher:
    def send_imap_notification(self,
                              recipient: str,
                              email_data: dict,
                              server: ImapServer) -> Optional[int]:
        """Send IMAP email notification"""
    
    def send_custom_notification(self,
                                event_type: str,
                                recipients: List[str],
                                template: str,
                                urgency: str,
                                template_vars: dict) -> Optional[int]:
        """Send custom event notification"""
```

**Features**:
- Calls `bbsengine6.notify.send()`
- Builds template variables
- Records to storage
- Error handling and logging
- Returns notification ID

### 8. Main Daemon (`daemon.py`)

**NotifyDaemon Class**:
```python
class NotifyDaemon:
    def __init__(self, config_path: Optional[str] = None):
        """Initialize daemon"""
    
    def start(self):
        """Start daemon and background threads"""
    
    def stop(self):
        """Stop gracefully"""
    
    def _monitor_loop(self):
        """IMAP polling background thread"""
```

**Features**:
- Config loading
- Thread spawning (IMAP Monitor, Event Listener)
- Signal handling (SIGTERM, SIGINT)
- PID file management
- Graceful shutdown

### 9. Command-Line Interface (`cli.py`)

**Entry Point**: `main()`

**Commands**:
- `start`: Start daemon
- `stop`: Stop daemon
- `status`: Check status
- `test-imap`: Test IMAP connections
- `test-notify`: Test notification sending

**Arguments**:
- `--config FILE`: Path to config.json
- `--pidfile PATH`: PID file location
- `--logfile PATH`: Log file location
- `--debug`: Enable debug logging

---

## Public API Exports

**`notifyd/__init__.py`**:
```python
from .hooks import EventBus, fire_event, register_event_handler
from .daemon import NotifyDaemon
from .config import NotifydConfig

__all__ = [
    "fire_event",
    "register_event_handler",
    "NotifyDaemon",
    "NotifydConfig"
]
```

### Usage Examples

**Firing Events**:
```python
import bbsengine6.notifyd as notifyd

notifyd.fire_event("user.login", {
    "moniker": "john",
    "timestamp": datetime.now().isoformat()
})
```

**Starting Daemon**:
```python
from bbsengine6.notifyd import NotifyDaemon

daemon = NotifyDaemon(config_path="/etc/bbsengine6/notifyd.json")
daemon.start()  # Runs until SIGTERM received
```

---

## Module Dependencies

| Module | Depends On |
|--------|-----------|
| config.py | (None) |
| credentials.py | config.py |
| storage.py | config.py |
| imap_monitor.py | config.py, credentials.py, storage.py |
| hooks.py | (None) |
| event_listener.py | config.py, hooks.py |
| notification.py | config.py, storage.py, bbsengine6.notify |
| daemon.py | All above |
| cli.py | daemon.py |

---

For database schema details, see [BBSENGINE6_NOTIFYD_DATABASE.md](BBSENGINE6_NOTIFYD_DATABASE.md).

For integration with bbsengine6, see [BBSENGINE6_NOTIFYD_INTEGRATION.md](BBSENGINE6_NOTIFYD_INTEGRATION.md).
