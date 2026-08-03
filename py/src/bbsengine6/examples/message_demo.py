# examples/message_demo.py
# Interactive two-user message system demo using bbsengine6's
# bbsengine6.message module. Replaces the legacy notify_message_demo.py
# which used the deleted bbsengine6.notify package.

"""
Two-process chat demo: open two terminals, each running this script
with a different --moniker, and exchange messages on a shared channel.

This demo exercises the canonical patterns for the message system:
- Sending via store_message() on a shared channel
- Receiving via deliver_pending_on_connect() and get_pending_messages_prioritized()
- Per-moniker read state via mark_read()
- Local unread count cache for the bottombar

Unlike the legacy notify demo, the message system has no in-process
in-memory queue: messages are persisted to PostgreSQL immediately and
delivered when a session connects. This is the correct shape for a
multi-process system; the in-memory queue was a single-process artifact.
"""

import argparse
import sys
import threading
import time
from collections import deque
from datetime import datetime

sys.path.insert(0, "py/src")

from bbsengine6 import member
from bbsengine6.io.echo import echo, echo_traceback
from bbsengine6.io.inputstring import inputstring
from bbsengine6.io import screen, terminal
from bbsengine6.message import (
    MessageUrgency,
    deliver_pending_on_connect,
    get_pending_messages_prioritized,
    get_unread_count,
    mark_read,
    store_message,
)


def handle_character_input(key: str, buffer: str) -> str:
    """Process a single keystroke and return updated buffer.

    Used by tests for unit-testing the input loop. Mirrors
    inputstring's key handling for backspace, escape, and printable
    characters.
    """
    if key == "KEY_BACKSPACE":
        return buffer[:-1] if buffer else ""
    elif key == "KEY_ESC":
        return ""
    elif key.startswith("KEY_") or key in ("\x00", "\x03"):
        return buffer
    else:
        return buffer + key


def _resolve_member(moniker: str) -> int:
    """Look up member id; raise if unknown."""
    member_id = member.idfrommoniker(moniker, args=None)  # type: ignore[arg-type]
    if member_id is None:
        raise SystemExit(f"unknown moniker: {moniker}")
    return member_id


def send_message(
    sender: str,
    recipient: str,
    body: str,
    urgency: str = "ROUTINE",
) -> int:
    """Send a message on the direct channel between sender and recipient.

    Returns the message id, or 0 if rate-limited / disabled.
    """
    return store_message(
        channel=f"member:{recipient}",
        sender_moniker=sender,
        content=body,
        recipient_monikers=[recipient],
        urgency=urgency,
    )


def pop_messages(moniker: str) -> list:
    """Return and clear all pending messages for ``moniker``.

    Combines deliver_pending_on_connect() (DB-side delivery tracking)
    and get_pending_messages_prioritized() (urgency-first ordering).
    """
    deliver_pending_on_connect(moniker)
    return get_pending_messages_prioritized(moniker, limit=50)


class DemoState:
    """Holds per-session state for the demo.

    The legacy notify demo had an in-memory ``UserNotificationQueue``;
    the message system persists everything, so DemoState only caches
    the running session and the most recent N displayed messages for
    redraw.
    """

    def __init__(self, my_moniker: str, peer_moniker: str) -> None:
        self.my_moniker = my_moniker
        self.peer_moniker = peer_moniker
        self.display_buffer: deque = deque(maxlen=20)
        self.running = True

    def add_display(self, line: str) -> None:
        self.display_buffer.append(line)

    def render(self) -> None:
        screen.clear()
        echo(f"== chat with {self.peer_moniker} (you: {self.my_moniker}) ==")
        echo("=" * 60)
        for line in self.display_buffer:
            echo(line)
        unread = get_unread_count(self.my_moniker)
        echo("=" * 60)
        echo(f"({unread} unread) type a message and press Enter (Ctrl-C to quit):")
        sys.stdout.flush()


def poll_incoming(state: DemoState) -> None:
    """Background poller that pulls new messages and adds them to the buffer."""
    while state.running:
        try:
            msgs = pop_messages(state.my_moniker)
            for m in msgs:
                if m.get("channel") == f"member:{state.my_moniker}":
                    line = (
                        f"[{m.get('datestamp', '')}] "
                        f"{m.get('sender_moniker') or 'system'}: "
                        f"{m.get('content', '')}"
                    )
                    state.add_display(line)
                    mark_read(m["id"], state.my_moniker)
            time.sleep(0.5)
        except Exception as e:
            echo_traceback(f"poll_incoming error: {e}")


def run_demo(my_moniker: str, peer_moniker: str) -> None:
    """Main loop: poll incoming in a background thread, read input on main."""
    state = DemoState(my_moniker, peer_moniker)

    # Initial drain
    initial = pop_messages(my_moniker)
    for m in initial:
        if m.get("channel") == f"member:{my_moniker}":
            mark_read(m["id"], my_moniker)

    poller = threading.Thread(target=poll_incoming, args=(state,), daemon=True)
    poller.start()

    state.render()
    try:
        while state.running:
            line = inputstring("")
            if line is None:
                break
            line = line.strip()
            if not line:
                state.render()
                continue
            if line.startswith("/"):
                if line == "/quit":
                    break
                state.add_display(f"(unknown command: {line})")
                state.render()
                continue
            msg_id = send_message(
                sender=my_moniker,
                recipient=peer_moniker,
                body=line,
                urgency=MessageUrgency.ROUTINE.value,
            )
            ts = datetime.utcnow().strftime("%H:%M:%S")
            state.add_display(f"[{ts}] {my_moniker}: {line}  (id={msg_id})")
            state.render()
    except KeyboardInterrupt:
        pass
    finally:
        state.running = False
        terminal.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--moniker",
        required=True,
        help="Your member moniker (must already exist in the database)",
    )
    parser.add_argument(
        "--peer",
        required=True,
        help="The moniker you want to chat with",
    )
    args = parser.parse_args()

    try:
        _resolve_member(args.moniker)
        _resolve_member(args.peer)
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 2

    run_demo(args.moniker, args.peer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
