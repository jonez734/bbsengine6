# bbsengine6 notifyd - Deployment & Multi-User Guide

Status: NOT YET IMPLEMENTED
Last Updated: 2026-05-18 13:43:46

---

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- bbsengine6 installed and configured
- Linux with systemd

### Step 1: Install Dependencies

```bash
cd /home/opencode/data/work/bbsengine6/py
source /home/opencode/.venv/bin/activate
pip install -e .
```

### Step 2: Create Configuration

```bash
mkdir -p ~/.bbsengine6/notifyd

# Copy example config
cp /home/opencode/data/work/bbsengine6/py/src/bbsengine6/notifyd/examples/minimal.json \
   ~/.bbsengine6/notifyd/config.json

# Edit for your IMAP servers
vim ~/.bbsengine6/notifyd/config.json
```

### Step 3: Set Credentials

**Using Environment Variables**:
```bash
export GMAIL_PASSWORD="your-app-password"
export CORPORATE_PASSWORD="your-password"
```

**Using Keyring**:
```bash
python -c "import keyring; keyring.set_password('notifyd', 'Gmail:user@gmail.com', 'password')"
```

### Step 4: Test Configuration

```bash
python -m bbsengine6.notifyd test-imap
python -m bbsengine6.notifyd test-notify
```

### Step 5: Install Systemd Service

```bash
sudo cp /home/opencode/data/work/bbsengine6/py/src/bbsengine6/notifyd/notifyd.service \
       /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable notifyd
sudo systemctl start notifyd
```

---

## Deployment Models

### Model 1: Daemon-Based Deployment

Continuous background daemon monitoring IMAP servers.

**When to Use**:
- Need continuous 24/7 email monitoring
- Desktop email notification scenario
- Non-BBS applications

**Setup**:
```bash
systemctl start notifyd
systemctl enable notifyd  # Auto-start on boot
```

**Monitoring**:
```bash
journalctl -u notifyd -f
```

### Model 2: getch() Integration (Recommended for BBS)

Integrate with bbsengine6's existing `getch()` notification system.

**When to Use**: (RECOMMENDED)
- BBS with users at terminal
- Event-based notifications
- Minimal resource usage desired
- Per-member isolation needed

**Setup**:
1. Fire events from bbsengine6 code
2. getch() checks notifications automatically
3. No daemon needed

**Code**:
```python
import bbsengine6.notifyd as notifyd

notifyd.fire_event("user-login", {
    "moniker": "john",
    "timestamp": datetime.now().isoformat()
})
```

### Model 3: Scheduled IMAP Polling

Use cron or systemd timer for periodic polling.

**When to Use**:
- Want email monitoring without daemon
- Acceptable 5-10 minute latency
- Low resource usage priority

**Cron Setup**:
```bash
# /etc/cron.d/notifyd-poll
*/5 * * * * bbsengine6 /usr/bin/python3 -m bbsengine6.notifyd poll-imap
```

**Systemd Timer**:
```ini
# /etc/systemd/system/notifyd-poll.timer
[Unit]
Description=NotifyD IMAP Polling
After=network.target postgresql.service

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

---

## Multi-User Considerations

### Single Daemon Instance

notifyd runs as a single system daemon (`bbsengine6` user), not per-application-user.

### Multiple IMAP Accounts

One daemon can monitor multiple email accounts:

```json
{
  "imap": {
    "servers": [
      {
        "name": "AdminEmail",
        "host": "imap.gmail.com",
        "username": "admin@company.com",
        "recipients": ["admin_team"]
      },
      {
        "name": "SupportEmail",
        "host": "imap.company.com",
        "username": "support@company.com",
        "recipients": ["support_team"]
      }
    ]
  }
}
```

### Per-Member Notifications

Use getch() integration for native per-member isolation:

```python
from bbsengine6.member import _threadlocal
import bbsengine6.notifyd as notifyd

def on_event(event_type, data):
    moniker = getattr(_threadlocal, "moniker", None)
    if moniker:
        notifyd.fire_event(event_type, {
            **data,
            "moniker": moniker  # Include member context
        })
```

### Multi-Member BBS Architecture

**For pure multi-member BBS systems, use getch() integration**:
- Built-in per-member notification queues
- Thread-local member identity from `_threadlocal.moniker`
- No daemon overhead
- Native isolation

See [BBSENGINE6_NOTIFYD_ARCHITECTURE.md](BBSENGINE6_NOTIFYD_ARCHITECTURE.md#model-2-getch-integration-recommended-for-bbs) for details.

---

## Troubleshooting

### Daemon Won't Start

Check logs:
```bash
sudo journalctl -u notifyd -n 50
```

Common issues:
- Missing config file
- Invalid JSON
- Database connection failed
- Permission denied

### IMAP Connection Failures

Test connections:
```bash
python -m bbsengine6.notifyd test-imap
```

Common issues:
- Wrong server/port
- Invalid credentials
- SSL certificate problems
- Firewall blocking

### Notifications Not Sending

Test notifications:
```bash
python -m bbsengine6.notifyd test-notify
```

Common issues:
- bbsengine6.notify not configured
- Database not initialized
- Invalid template name

### High Resource Usage

Check for stuck processes:
```bash
ps aux | grep notifyd
```

Review logs for errors:
```bash
journalctl -u notifyd --since "1 hour ago"
```

---

## Performance Optimization

### IMAP Polling

- Increase `poll_interval` if emails are not time-sensitive
- Default 30s - adjust based on needs
- Each server polled in separate thread

### Database

- notifyd uses bbsengine6's existing pool
- No additional database tuning needed
- Monitor `notifyd_history` table size
- Clean up old records periodically:
  ```sql
  DELETE FROM notifyd_history 
  WHERE sent_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
  ```

### Memory

Typical usage: ~50MB per daemon instance

---

## Recommended BBS Deployment

For bbsengine6 BBS systems, use:

1. **getch() Integration Model** (no daemon)
   - Fire events with `notifyd.fire_event()`
   - No separate daemon process
   - Per-member isolation built-in
   - Minimal resource overhead

2. **Optional: Scheduled Polling**
   - Cron job polls IMAP every 5-10 minutes
   - Results added to notification queue
   - Users see during next getch()

3. **Configuration Only**
   - Single config file per system
   - No systemd service needed
   - Simple deployment

This model minimizes complexity while maintaining full notification functionality.

---

For configuration options, see [BBSENGINE6_NOTIFYD_CONFIGURATION.md](BBSENGINE6_NOTIFYD_CONFIGURATION.md).

For architecture details, see [BBSENGINE6_NOTIFYD_ARCHITECTURE.md](BBSENGINE6_NOTIFYD_ARCHITECTURE.md).
