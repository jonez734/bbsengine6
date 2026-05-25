== bbsengine6 notify subsystem tui ==

- [x] read bbsengine6/py/src/bbsengine6/notify/*.py and *.md
- [x] read bbsengine6/py/src/bbsengine6/examples/notify_message_demo
- [x] read NOTIFY_MESSAGE_DEMO_SPEC
- [x] build the code and make it run when I do `python -m bbsengine6.notify`
- [x] optimize and consolidate as needed
- [x] do a comprehensive review of the code for robustness and security
- [ ] make a comprehensive set of integrated tests-- access via api instead of direct database calls
- [x] be sure all features in every demo are merged
- [x] be sure to activate venv!
- [x] build/update __main__ patterned after murdermotel/src/murdermotel/__main__.py and murdermotel/src/murdermotel/__main__.py
  * try/except/finally
  * handle KeyboardInterupt, EOFError
  * finally resets screen
- [x] update specs and docs
- [x] calling the module tui.py is run, just make sure I can run it with the
  python -m from above.

== Architecture ==

- `bbsengine6.notify` (python -m bbsengine6.notify): Notification TUI
  Entry: notify/__main__.py → notify/main.py
  TUI: notify/tui.py (run_until_quit)
  Daemon: notify/daemon/ (IMAP + event notification daemon)
    CLI: python -m bbsengine6.notify.daemon {start,stop,status}
- `bbsengine6.notify.daemon`: IMAP/Event notification daemon
  Entry: notify/daemon/__main__.py → notify/daemon/cli.py

== Key Files ==

- notify/__init__.py - public API
- notify/lib.py - core notification API (send, get_notifications, mark_read, expunge, etc.)
- notify/tui.py - notification list TUI (run_until_quit = actual TUI loop)
- notify/demo.py - demo mode messaging (shared with notify_message_demo.py)
- notify/main.py - TUI entry point (buildargs, init, access, main)
- notify/__main__.py - module entry for python -m bbsengine6.notify
- notify/daemon/ - IMAP monitoring + event notification daemon
  - __init__.py, cli.py, daemon.py, config.py, storage.py
  - imap_monitor.py, event_listener.py, hooks.py, notification.py, credentials.py
  - __main__.py - module entry for python -m bbsengine6.notify.daemon
- examples/notify_message_demo.py - uses notify/demo.py for shared demo logic

== Security Model ==

Authorization:
- `expunge(notification_id, current_moniker)`: Only the sender may delete their notification. Ownership verified via SELECT before DELETE.
- `mark_read(notification_id, current_moniker)`: Only the recipient may mark their own notifications as read.
- `mark_delivered(notification_id, current_moniker)`: Only the recipient may mark their own notifications as delivered.

Privacy:
- `@everyone` recipient expansion falls back to `engine.__member` (all registered members), not `engine.__session` (active sessions). Active session data is not exposed via notification expansion.

Rate limiting (deny by default):
- Unregistered notification types: denied (returns False) — prevents abuse of unknown types
- Registered types: enforced per-user per-hour limits
- Exceptions in rate limit check: denied (returns False) — fail-safe behavior

Output sanitization:
- `EchoProcessor.process_echo()` sanitizes subprocess output: strips non-printable ASCII, caps at 500 chars
