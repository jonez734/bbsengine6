# bbsengine6 notifyd - Dependencies

Status: NOT YET IMPLEMENTED
Last Updated: 2026-05-18 13:43:46

---

## Python Dependencies

Add to `bbsengine6/py/pyproject.toml` in the `dependencies` section:

| Package | Version | Purpose |
|---------|---------|---------|
| `imapclient` | `>=2.3.0` | High-level IMAP client library |
| `keyring` | `>=24.0.0` | Secure credential storage |
| `psycopg` | `>=3.1.0` | PostgreSQL driver (already exists in bbsengine6) |
| `psycopg-pool` | `>=3.1.0` | Connection pooling (already exists in bbsengine6) |

**Already Provided by bbsengine6**:
- `psycopg[binary]` - PostgreSQL driver
- `psycopg-pool` - Connection pool management

---

## System Dependencies

### Required

- **Python**: 3.9, 3.10, 3.11, or 3.12 (bbsengine6's requirement)
- **PostgreSQL**: 12 or later (existing bbsengine6 database)
- **Linux with systemd**: For daemon management

### Optional

- **Python keyring backend**: For secure credential storage
  - Debian/Ubuntu: `python3-keyring`
  - Fedora: `python3-keyring`
  - macOS: Built-in Keychain support

---

## External Services

### Required

- **PostgreSQL Database**: Stores IMAP state and notification history
  - Must be accessible from notifyd daemon
  - Existing bbsengine6 database reused
  - No additional setup needed

### Optional

- **IMAP Servers**: For email monitoring
  - Any standard IMAP server (Gmail, Outlook, etc.)
  - IMAP over SSL (port 993) recommended
  - Credentials needed (password or app-specific password)

---

## Development Dependencies

For development and testing, add to `pyproject.toml` `[dev]` extras:

```python
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1.0",
]
```

Install for development:
```bash
pip install -e ".[dev]"
```

---

## Installation Commands

### Install notifyd with Dependencies

```bash
cd /home/opencode/data/work/bbsengine6/py
pip install -e .
```

This installs bbsengine6 with notifyd and all dependencies.

### Install Just Development Tools

```bash
pip install -e ".[dev]"
```

---

## Dependency Details

### imapclient

High-level IMAP client library for Python.

**Why Used**:
- Simplifies IMAP protocol handling
- Better error handling than imaplib
- RFC822 email parsing
- Connection timeout support

**Alternatives**:
- imaplib (stdlib): Lower-level, more verbose
- IMAPClient: Same as imapclient (different name)

### keyring

Cross-platform Python library for accessing system keyring.

**Why Used**:
- Secure credential storage without hardcoding
- Fallback to environment variables or prompts
- No dependency on external password managers

**Alternatives**:
- Environment variables only: Less secure
- Hardcoding: Major security risk
- External password managers: More complex setup

### psycopg

Modern PostgreSQL driver for Python with async support.

**Why Used**:
- Excellent performance
- Connection pooling built-in
- Type safety and error handling
- Already used by bbsengine6

**Note**: Already required by bbsengine6, no additional installation needed.

---

## Compatibility

### Python Versions

- ✅ Python 3.9
- ✅ Python 3.10
- ✅ Python 3.11
- ✅ Python 3.12

### Operating Systems

- ✅ Linux (required for systemd)
- ⚠️ macOS (systemd not available, use manual daemon or cron)
- ❌ Windows (systemd not available, would need alternative daemon manager)

---

## Version Constraints

### Why Minimum Versions

- **imapclient >= 2.3.0**: Supports modern IMAP features and error handling
- **keyring >= 24.0.0**: Better cross-platform support
- **psycopg >= 3.1.0**: Connection pool support, async features
- **Python >= 3.9**: Type hints, modern language features

---

## Upgrade Path

### Upgrading imapclient

```bash
pip install --upgrade imapclient
```

No API changes expected in minor versions.

### Upgrading keyring

```bash
pip install --upgrade keyring
```

Backward compatible with notifyd.

### Upgrading psycopg

```bash
pip install --upgrade psycopg
```

psycopg 3.x is a major version rewrite from 2.x, but bbsengine6 uses 3.x API.

---

## Troubleshooting Dependencies

### ImportError: No module named 'imapclient'

```bash
pip install imapclient>=2.3.0
```

### ImportError: No module named 'keyring'

```bash
pip install keyring>=24.0.0
```

### ImportError: No module named 'psycopg'

Already installed by bbsengine6, verify:
```bash
pip list | grep psycopg
```

### IMAP Connection Issues

May indicate:
- imapclient too old
- IMAP server incompatibility
- Network issues

Update and test:
```bash
python -m bbsengine6.notifyd test-imap
```

---

## Security Considerations

### Credential Storage

- Never hardcode IMAP passwords
- Use environment variables for CI/CD
- Use system keyring for servers
- Use prompts for interactive setup

### IMAP Security

- Always use SSL (port 993)
- Verify SSL certificates
- Use app-specific passwords when available (Gmail, Outlook)
- Never reuse production passwords in testing

### Database Security

- Use bbsengine6's existing database configuration
- Ensure PostgreSQL access is restricted
- notifyd should connect as read-write user
- Audit logs in notifyd_history table

---

For installation instructions, see [BBSENGINE6_NOTIFYD_DEPLOYMENT.md](BBSENGINE6_NOTIFYD_DEPLOYMENT.md).

For configuration details, see [BBSENGINE6_NOTIFYD_CONFIGURATION.md](BBSENGINE6_NOTIFYD_CONFIGURATION.md).
