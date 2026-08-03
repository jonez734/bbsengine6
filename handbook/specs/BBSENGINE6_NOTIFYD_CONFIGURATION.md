# bbsengine6 notifyd - Configuration

> **STATUS (2026-07-22): SUPERSEDED.** See
> `BBSENGINE6_NOTIFYD_OVERVIEW.md` for the full context.
> The JSON schema documented here is for a never-built
> daemon that depended on the deleted `bbsengine6.notify`
> package. The actual bbsengine6 daemon
> (`py/src/bbsengine6/bed.py`) takes CLI args, not a JSON
> config file; the closest JSON config in the live
> codebase is `bed.json` (the external `bed` package
> config, see `TODO.md` "Phase 1G: Postoffice Service").

Status: NOT YET IMPLEMENTED (and superseded)
Last Updated: 2026-05-18 13:43:46

---

## Configuration File Format

### Location

`~/.bbsengine6/notifyd/config.json`

### Minimal Example

```json
{
  "logging": {"level": "INFO"},
  "database": {"use_bbsengine6_db": true},
  "credentials": {"storage": "hybrid"},
  "imap": {
    "servers": [
      {
        "name": "Gmail",
        "host": "imap.gmail.com",
        "username": "user@gmail.com",
        "password": "${IMAP_PASSWORD}",
        "recipients": ["player1"]
      }
    ]
  },
  "events": {"enable_custom_hooks": true, "handlers": {}}
}
```

### Full Example

```json
{
  "logging": {
    "level": "INFO",
    "file": "~/.bbsengine6/notifyd/notifyd.log"
  },
  "database": {
    "use_bbsengine6_db": true,
    "dbname": "bbsengine6",
    "user": "postgres"
  },
  "polling_interval": 30,
  "credentials": {
    "storage": "hybrid",
    "keyring_service": "notifyd",
    "prompt_on_missing": true
  },
  "imap": {
    "servers": [
      {
        "name": "Gmail",
        "host": "imap.gmail.com",
        "port": 993,
        "use_ssl": true,
        "username": "user@gmail.com",
        "password": "${IMAP_PASSWORD}",
        "mailbox": "INBOX",
        "poll_interval": 30,
        "notification_type": "imap.message",
        "recipients": ["player1", "player2"],
        "urgency": "ROUTINE",
        "enabled": true,
        "timeout": 10
      }
    ]
  },
  "events": {
    "enable_key_events": false,
    "enable_custom_hooks": true,
    "handlers": {
      "user.login": {
        "template": "user-login",
        "urgency": "ROUTINE",
        "send_to": ["@everyone"]
      },
      "user.logout": {
        "template": "user-logout",
        "urgency": "ROUTINE"
      },
      "game.event": {
        "template": "game-event",
        "urgency": "IMPORTANT"
      }
    }
  }
}
```

---

## Configuration Options

### Logging Configuration

```json
{
  "logging": {
    "level": "INFO|DEBUG|WARNING|ERROR|CRITICAL",
    "file": "optional-path-to-logfile"
  }
}
```

- `level`: Logging verbosity
- `file`: Optional file path (if omitted, logs to stdout)

### Database Configuration

```json
{
  "database": {
    "use_bbsengine6_db": true,
    "dbname": "bbsengine6",
    "user": "postgres",
    "host": "localhost",
    "port": 5432
  }
}
```

- `use_bbsengine6_db`: Use bbsengine6's existing connection pool (recommended: true)
- Others: Manual database configuration (only if use_bbsengine6_db is false)

### Credentials Configuration

```json
{
  "credentials": {
    "storage": "hybrid|env|keyring|prompt",
    "keyring_service": "notifyd",
    "prompt_on_missing": true
  }
}
```

**Storage Strategy**:
- `hybrid`: Try env → keyring → prompt (recommended)
- `env`: Only environment variables
- `keyring`: Only system keyring
- `prompt`: Only user prompt

### IMAP Server Configuration

```json
{
  "imap": {
    "servers": [
      {
        "name": "Gmail",
        "host": "imap.gmail.com",
        "port": 993,
        "use_ssl": true,
        "username": "user@gmail.com",
        "password": "${IMAP_PASSWORD}",
        "mailbox": "INBOX",
        "poll_interval": 30,
        "notification_type": "imap.message",
        "recipients": ["player1"],
        "urgency": "ROUTINE",
        "enabled": true,
        "timeout": 10
      }
    ]
  }
}
```

**Fields**:
- `name`: Server identifier (used for logging)
- `host`: IMAP server hostname
- `port`: IMAP port (993 for SSL, 143 for plain)
- `use_ssl`: Use SSL/TLS
- `username`: Email account username
- `password`: Password (see credential options)
- `mailbox`: Mailbox to monitor (case-sensitive)
- `poll_interval`: Check for new emails every N seconds
- `notification_type`: Type sent to bbsengine6.notify
- `recipients`: Who to notify
- `urgency`: ROUTINE|IMPORTANT|URGENT|CRITICAL
- `enabled`: Whether this server is active
- `timeout`: Connection timeout in seconds

### Event Handler Configuration

```json
{
  "events": {
    "enable_key_events": false,
    "enable_custom_hooks": true,
    "handlers": {
      "user.login": {
        "template": "user-login",
        "urgency": "ROUTINE",
        "send_to": ["@everyone"]
      }
    }
  }
}
```

**Fields**:
- `enable_key_events`: Listen to io.KeyEventSystem
- `enable_custom_hooks`: Listen to custom event hooks (recommended: true)
- `handlers`: Map of event name → configuration
  - `template`: Template name for notification
  - `urgency`: ROUTINE|IMPORTANT|URGENT|CRITICAL
  - `send_to`: Recipients list

---

## Credential Management

### Three-Tier Fallback

Credentials are retrieved in this order:

1. **Environment Variables**: `${SERVER_NAME_PASSWORD}` in config
   - Pattern: `${SERVER_NAME.upper().replace('-','_')}_PASSWORD`
   - Example: Gmail server → `${GMAIL_PASSWORD}`

2. **OS Keyring**: System keyring storage
   - Set with: `python -c "import keyring; keyring.set_password('notifyd', 'Gmail:user@gmail.com', 'password')"`

3. **User Prompt**: Interactive password entry
   - Only if above not available and `prompt_on_missing: true`

### Credential Examples

**Using Environment Variables**:
```bash
export GMAIL_PASSWORD="your-app-password"
export CORPORATE_PASSWORD="corp-email-password"
python -m bbsengine6.notifyd start
```

**Using Keyring**:
```bash
python -c "import keyring; keyring.set_password('notifyd', 'Gmail:user@gmail.com', 'your-password')"
python -m bbsengine6.notifyd start
```

**Using Prompt** (development only):
```bash
python -m bbsengine6.notifyd start
# Will prompt: "Password for Gmail: "
```

---

## Environment Variable Substitution

Config files support `${VARIABLE_NAME}` substitution:

```json
{
  "imap": {
    "servers": [
      {
        "password": "${GMAIL_PASSWORD}"
      }
    ]
  }
}
```

Will be replaced with the value of the `GMAIL_PASSWORD` environment variable.

---

## Configuration Loading

### Default Locations (in order)

1. CLI argument: `--config /path/to/config.json`
2. Environment variable: `NOTIFYD_CONFIG=/path/to/config.json`
3. Default paths:
   - `/etc/notifyd/config.json`
   - `~/.bbsengine6/notifyd/config.json`
   - `/etc/bbsengine6/notifyd.json`

### Validation

Configuration is validated on load:
- Required fields checked
- Port numbers validated
- Urgency levels checked
- Invalid config raises `ConfigError`

---

## Examples by Use Case

### Single Gmail Account

```json
{
  "logging": {"level": "INFO"},
  "database": {"use_bbsengine6_db": true},
  "credentials": {"storage": "hybrid"},
  "imap": {
    "servers": [{
      "name": "Gmail",
      "host": "imap.gmail.com",
      "username": "user@gmail.com",
      "password": "${GMAIL_PASSWORD}",
      "recipients": ["admin"]
    }]
  },
  "events": {
    "enable_custom_hooks": true,
    "handlers": {}
  }
}
```

### Multiple Email Servers

```json
{
  "imap": {
    "servers": [
      {
        "name": "Admin",
        "host": "imap.gmail.com",
        "username": "admin@company.com",
        "password": "${ADMIN_PASSWORD}",
        "recipients": ["admin_team"]
      },
      {
        "name": "Support",
        "host": "imap.company.com",
        "username": "support@company.com",
        "password": "${SUPPORT_PASSWORD}",
        "recipients": ["support_team"]
      },
      {
        "name": "Alerts",
        "host": "imap.alerts.com",
        "username": "alerts@company.com",
        "password": "${ALERTS_PASSWORD}",
        "recipients": ["ops_team"]
      }
    ]
  }
}
```

### Event-Only (No IMAP)

```json
{
  "imap": {"servers": []},
  "events": {
    "enable_custom_hooks": true,
    "handlers": {
      "user-login": {
        "template": "login.tmpl",
        "urgency": "ROUTINE",
        "send_to": ["security-team"]
      }
    }
  }
}
```

---

## Configuration Validation

Errors on load include:
- Missing required fields
- Invalid IMAP port
- Invalid urgency level
- Malformed JSON
- Missing referenced templates

---

See [BBSENGINE6_NOTIFYD_DEPLOYMENT.md](BBSENGINE6_NOTIFYD_DEPLOYMENT.md) for installation and setup instructions.
