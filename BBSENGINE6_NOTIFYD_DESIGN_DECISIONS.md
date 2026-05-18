# bbsengine6 notifyd - Design Decisions

Status: NOT YET IMPLEMENTED
Last Updated: 2026-05-18 13:43:46

---

## Design Decisions & Rationale

### 1. Threading Model

**Decision**: Use threading.Thread for background polling, not asyncio

**Rationale**:
- Match bbsengine6's existing `getch()` pattern (threading-based)
- Simpler error handling and debugging
- No need for async/await complexity
- Easy integration with synchronous psycopg3 API
- Familiar to bbsengine6 developers

**Alternatives Considered**:
- asyncio: Would require async database driver, harder to debug
- Multiprocessing: Overkill for I/O-bound task, harder to coordinate

---

### 2. Custom Event Hooks

**Decision**: Create separate EventBus, don't reuse io.KeyEventSystem

**Rationale**:
- io.KeyEventSystem designed for keyboard input events only
- Separate system for application events (login, game events)
- Optional integration with io.KeyEventSystem possible
- Cleaner separation of concerns
- More flexible event firing

**Alternatives Considered**:
- Reuse io.KeyEventSystem: Would conflate keyboard and app events
- No event system: Would require manual integration points everywhere

---

### 3. Credential Storage Strategy

**Decision**: Hybrid strategy - Try env → keyring → prompt

**Rationale**:
- Env vars for CI/CD and testing
- Keyring for secure persistent storage
- Prompt as last resort for interactive setup
- Flexible per-deployment configuration
- No hardcoded secrets in codebase

**Alternatives Considered**:
- Only env vars: Not suitable for production servers
- Only keyring: Requires additional setup, fails in CI
- Only prompt: Not suitable for non-interactive services

---

### 4. Configuration Format

**Decision**: JSON with environment variable substitution

**Rationale**:
- Familiar format, human-readable
- Native Python support (json module)
- Environment variable substitution for secrets
- Easy to parse and validate
- Compatible with systemd EnvironmentFile=
- Not as verbose as YAML

**Alternatives Considered**:
- YAML: More readable but requires additional dependency
- TOML: Good but less familiarity
- Python code: Security risk if not careful
- Flat files: Too limited for complex config

---

### 5. State Storage

**Decision**: PostgreSQL with bbsengine6's existing pool

**Rationale**:
- No additional database setup required
- Leverage existing psycopg3 pool infrastructure
- Data durability and ACID properties
- Easy integration with bbsengine6's notify tables
- Single source of truth for state

**Alternatives Considered**:
- SQLite: Would require separate file, less suitable for multi-process
- Redis: Additional dependency, not suitable for IMAP state tracking
- In-memory: Lost on daemon restart, no durability

---

### 6. Systemd Integration

**Decision**: Type=simple service with manual PID management

**Rationale**:
- Simple daemon (not Type=notify)
- Easy to reason about lifecycle
- Graceful shutdown via SIGTERM
- Standard logging via journalctl
- Compatible with existing bbsengine6 deployment

**Alternatives Considered**:
- Type=notify: More complex, requires systemd-notify protocol
- Type=forking: Would require double-fork, not needed
- Manual script: Would lose service management benefits

---

### 7. Daemon vs getch() Model for BBS

**Decision**: Recommend getch() integration for BBS deployments

**Rationale**:
- **BBS-friendly**: Fits terminal paradigm perfectly
- **No daemon overhead**: No persistent background process
- **Native isolation**: Per-member queues already in bbsengine6.notify
- **Event-driven**: Perfect for application events
- **Simple deployment**: Just configuration, no systemd needed
- **Minimal resource usage**: No persistent threads

**Daemon Model**:
- Better for continuous 24/7 monitoring
- Better for non-BBS applications
- More resource intensive

---

### 8. IMAP RFC822 Parsing

**Decision**: Use email.parser module for RFC822 parsing

**Rationale**:
- Standard Python library, no external dependencies
- Handles complex email formats
- Proper encoding handling
- Supports multipart emails
- Mature and well-tested

---

### 9. Error Handling Philosophy

**Decision**: Graceful degradation - individual failures don't crash daemon

**Rationale**:
- One IMAP server failure doesn't crash daemon
- One event handler exception doesn't affect others
- Notifications sent even if history recording fails
- Logging for debugging without stopping service
- Improved reliability for production

**Implementation**:
- Try/except around each server poll
- Try/except around event handlers
- Fallback if storage unavailable
- Comprehensive logging of all errors

---

### 10. Testing Strategy

**Decision**: Comprehensive unit tests with mocking

**Rationale**:
- Mock IMAP servers (don't depend on real Gmail/SMTP)
- Mock system keyring (don't depend on user keyring)
- Mock bbsengine6.notify (don't depend on notification module)
- Test database isolation
- Fast test execution
- No external service dependencies

**Coverage**:
- >85% overall code coverage
- >95% for critical modules
- Tests for all error paths

---

## Trade-offs Made

| Decision | Gain | Trade-off |
|----------|------|-----------|
| Threading vs asyncio | Simplicity | Slight latency in polling |
| JSON config | Familiarity | Less expressive than code |
| PostgreSQL state | Durability, ACID | Additional database dependency |
| Graceful degradation | Reliability | Missing notifications not retried |
| getch() model for BBS | Minimal overhead | No true background monitoring |

---

## Future Considerations

### Potential Improvements

1. **Event Filtering**: Allow per-member event filtering
2. **Template Enhancements**: More sophisticated template language
3. **Webhook Integration**: Fire webhooks instead of just notify
4. **OAuth2 Support**: For Gmail and other OAuth providers
5. **Rate Limiting**: Per-recipient notification limits
6. **Notification Scheduling**: Defer notifications to business hours
7. **Multi-Instance**: Run separate daemons per configuration

---

For architecture overview, see [BBSENGINE6_NOTIFYD_ARCHITECTURE.md](BBSENGINE6_NOTIFYD_ARCHITECTURE.md).

For component specifications, see [BBSENGINE6_NOTIFYD_COMPONENTS.md](BBSENGINE6_NOTIFYD_COMPONENTS.md).
