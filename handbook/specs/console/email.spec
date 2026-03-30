# Email Configuration Module (email.py)

## Overview

`email.py` manages system email configuration and settings. **Status: Incomplete** — Stub with design intent documented.

**File:** `bbsengine6/console/email.py`  
**Size:** 87 lines  
**Status:** Incomplete — add/edit/delete workflow not fully implemented

---

## Standard Module Interface (Declared)

```python
def init(args, **kwargs) -> bool
def access(args, op, **kwargs) -> bool
def buildargs(args, **kwargs) -> ArgumentParser | None
def main(args, **kwargs) -> bool
```

All functions are declared but minimally implemented.

---

## Current Implementation

### init()

```python
def init(args, **kwargs) -> bool:
    # Stub
```

### access()

```python
def access(args, op, **kwargs) -> bool:
    # Stub (probably requires SYSOP)
```

### buildargs()

```python
def buildargs(args, **kwargs) -> ArgumentParser | None:
    # Stub
```

### main()

```python
def main(args, **kwargs) -> bool:
    # Stub implementation
```

---

## Intended Design

### Purpose

Email module would provide sysop-level configuration for:
1. SMTP server settings (host, port, auth)
2. Email templates (member signup, password reset, notifications)
3. Email accounts and routing
4. Email logging and delivery status

### Proposed Menu Interface

```
Email Configuration
===================

[C]onfigure SMTP  - Set SMTP server settings
[T]emplates       - Manage email templates
[A]ccounts        - Email accounts and routing
[L]og             - View email delivery log
[T]est            - Send test email
[X]it             - Return to main menu
```

### Configuration Operations (Proposed)

#### SMTP Settings

Store system-wide SMTP configuration:

```python
{
    'smtp_host': 'mail.example.com',
    'smtp_port': 587,
    'smtp_user': 'noreply@example.com',
    'smtp_password': 'encrypted_password',
    'smtp_tls': True,
    'smtp_from_address': 'BBS <bbs@example.com>',
    'smtp_from_name': 'BBS Engine 6'
}
```

**Interactive Edit:**
```
SMTP Configuration
==================

SMTP Host: mail.example.com
SMTP Port: [587]
SMTP User: noreply@example.com
SMTP TLS: [Yes/No]
From Address: BBS <bbs@example.com>
From Name: BBS Engine 6

Test connection? (Y/n)
```

#### Email Templates

Manage template library for:
- New member welcome
- Email verification
- Password reset
- Account approved
- Notification emails
- System announcements

**Operations:**
- [N]ew template
- [E]dit template
- [D]elete template
- [P]review template

#### Email Accounts

Configure email accounts for specific purposes:

| Account | Purpose | From Address |
|---------|---------|--------------|
| noreply | System notifications | noreply@example.com |
| support | Support requests | support@example.com |
| billing | Billing notifications | billing@example.com |

### Database Storage (Proposed)

#### engine.email_config

System email configuration:

| Column | Type | Purpose |
|--------|------|---------|
| `configid` | varchar | Config key (smtp_host, smtp_port, etc.) |
| `value` | text | Config value |
| `encrypted` | boolean | Whether value is encrypted |

#### engine.email_template

Email templates:

| Column | Type | Purpose |
|--------|------|---------|
| `templateid` | serial | Primary key |
| `name` | varchar | Template name (e.g., "welcome") |
| `subject` | varchar | Email subject line |
| `body` | text | Email body (with placeholders like {name}, {link}) |
| `created` | timestamp | When template created |
| `modified` | timestamp | Last modification |

#### engine.email_account

Email accounts:

| Column | Type | Purpose |
|--------|------|---------|
| `accountid` | serial | Primary key |
| `name` | varchar | Account name (noreply, support, etc.) |
| `email` | varchar | Email address |
| `displayname` | varchar | Display name |
| `purpose` | varchar | Purpose (notifications, support, billing) |

#### engine.email_log

Email delivery log:

| Column | Type | Purpose |
|--------|------|---------|
| `logid` | serial | Primary key |
| `to_address` | varchar | Recipient email |
| `subject` | varchar | Email subject |
| `sent_date` | timestamp | When sent |
| `status` | varchar | SUCCESS, FAILED, BOUNCED |
| `error_message` | text | Failure reason if applicable |

---

## Integration Points

### Email Verification (Used by member.py)

```python
# In member.py when creating new member:
email.send_verification(member.email, member.moniker, verification_link)
```

### Password Reset (Planned)

```python
# In web app when user requests password reset:
email.send_password_reset(member.email, reset_link)
```

### Notifications (Planned integration with notify.py)

```python
# In notify.py when notification generated:
email.send_notification(member.email, notification_template, data)
```

### Account Approved (Used by memberapproval.py)

```python
# In memberapproval.py after approval:
email.send_approval(member.email, member.moniker)
```

---

## Implementation Approach

### Phase 1 (Current)

- Stub module exists
- Module discoverable
- No actual functionality

### Phase 2 (Proposed)

- SMTP configuration interface
- Basic email template editing
- Configuration storage
- Test SMTP connection

### Phase 3 (Proposed)

- Email logging and history
- Template preview
- Bulk email operations
- Email account management

### Phase 4 (Proposed)

- Integration with password reset
- Integration with member verification
- Integration with notification system
- Email delivery monitoring and retry

---

## Security Considerations

### Password Encryption

SMTP passwords should be:
- Stored encrypted in database
- Decrypted only in memory during send
- Never logged or displayed in plaintext

**Proposed:**
```python
encrypted_pw = crypto.encrypt(password, key)
database.update(
    table="engine.email_config",
    pk="configid",
    items={'value': encrypted_pw, 'encrypted': True}
)
```

### Access Control

Email configuration should be:
- Accessible only to sysop
- Audit logged for changes
- Requires confirmation for sensitive changes

### Rate Limiting

Prevent email spam:
- Per-address rate limit (e.g., 5 per hour)
- Global rate limit (e.g., 100 per hour)
- Bounce handling

---

## Error Handling

### Connection Errors

```python
try:
    smtp = smtplib.SMTP(smtp_host, smtp_port)
    smtp.starttls()
    smtp.login(smtp_user, smtp_password)
except smtplib.SMTPException as e:
    io.echo(f"SMTP Error: {e}", level="error")
    return False
```

### Template Errors

- Missing template → error
- Invalid placeholders → warning
- Template not found → error

### Database Errors

- Config update fails → rollback, return False
- Template save fails → rollback, return False
- Log write fails → non-fatal, continue

---

## Dependencies

**Proposed:**
- `smtplib` — SMTP client
- `email.mime` — MIME message creation
- `bbsengine6.database` — Configuration storage
- `bbsengine6.io` — User interface
- `bbsengine6.util` — Utility functions (encryption, templating)

**Current:**
- None (stub)

---

## Related Modules

- **member.py** — Uses email for verification
- **memberapproval.py** — Uses email for approval notification
- **notify.py** — Planned email delivery channel
- **web app** — Password reset, password change notifications

---

## Future Enhancements

### Advanced Features

- HTML email templates
- Email attachments
- Batch email send
- Email scheduling
- A/B testing templates
- Email analytics (open rate, click rate)

### Integration

- Webhook callbacks (bounce, delivery)
- Email alias mapping
- Reply-to address configuration
- List-unsubscribe support

### Compliance

- GDPR unsubscribe links
- CAN-SPAM compliance
- SPF/DKIM/DMARC configuration
- Archive and retention policies

