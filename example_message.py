#!/usr/bin/env python
"""
Simple standalone example of using the bbsengine6 message system.

This script demonstrates:
1. Sending messages with channels
2. Receiving pending messages (prioritized by urgency)
3. Using message groups (@group, @everyone)
4. Blocking senders
5. Marking messages as read

To run:
    cd /home/opencode/data/work/bbsengine6
    python example_message.py

The message system is the unified pub/sub + persistence layer that
replaced the legacy ``bbsengine6.notify`` package. Messages are
organized by ``channel`` (e.g. ``"casino:table:blackjack-1"``,
``"system:announcements"``) and stored in ``engine.__message`` with
per-recipient rows in ``engine.__message_recipient``. They support
urgency (ROUTINE/IMPORTANT/URGENT/CRITICAL), rate limiting, blocking,
and templating.
"""

from datetime import datetime, timezone
import sys

# Add py module to path
sys.path.insert(0, "py/src")

from bbsengine6 import message
from bbsengine6.message import (
    MessageUrgency,
    create_message_group,
    add_to_message_group,
    block_sender,
    is_blocked,
    get_unread_count,
)


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def example_basic_send() -> int:
    """Example 1: Basic message sending."""
    print_section("Example 1: Basic Message Sending")

    # Send a message on a channel
    print("1. Sending message on channel 'example.basic'...\n")
    msg_id = message.store_message(
        channel="example.basic",
        sender_moniker="alice",
        content="Hello {name}, welcome to {system}!",
        recipient_monikers=["jam"],
        template="Hello {name}, welcome to {system}!",
        template_vars={"name": "Jam", "system": "bbsengine6"},
        urgency=MessageUrgency.ROUTINE,
    )
    print(f"   ✓ Message stored (id={msg_id})\n")
    return msg_id


def example_urgency_levels() -> None:
    """Example 2: Different urgency levels surface CRITICAL first."""
    print_section("Example 2: Urgency Levels")

    urgencies = [
        (MessageUrgency.ROUTINE, "Regular update"),
        (MessageUrgency.IMPORTANT, "Important announcement"),
        (MessageUrgency.URGENT, "Urgent action needed"),
        (MessageUrgency.CRITICAL, "CRITICAL: Immediate action"),
    ]

    for urgency, body in urgencies:
        msg_id = message.store_message(
            channel="example.urgency",
            sender_moniker="system",
            content=body,
            recipient_monikers=["jam"],
            urgency=urgency,
        )
        print(f"  {urgency.value:10} -> stored id={msg_id}")

    print("\n   get_pending_messages_prioritized() will surface these in")
    print("   CRITICAL/URGENT/IMPORTANT/ROUTINE order, regardless of")
    print("   insertion order.\n")


def example_with_data() -> None:
    """Example 3: Messages with structured data (JSONB)."""
    print_section("Example 3: Structured Data")

    print("Sending message with structured data (game result)...\n")

    msg_id = message.store_message(
        channel="example.data",
        sender_moniker="blackjack",
        content="You earned {amount} {currency} in {game}!",
        recipient_monikers=["jam"],
        template="You earned {amount} {currency} in {game}!",
        template_vars={"amount": 1000, "currency": "credits", "game": "Blackjack"},
        urgency=MessageUrgency.IMPORTANT,
        data={
            "game_type": "blackjack",
            "amount": 1000,
            "currency": "credits",
            "transaction_id": "txn_abc123",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    print(f"   ✓ Stored id={msg_id}")
    print("   data column is JSONB; consumers can query it directly.\n")


def example_groups() -> None:
    """Example 4: Group-based messaging via @group_name expansion."""
    print_section("Example 4: Group Targeting")

    print("1. Creating message group '@guild:dragons'...\n")
    group_id = create_message_group(
        name="@guild:dragons",
        createdby="alice",
        description="The Dragons guild",
    )
    add_to_message_group(group_id, "alice")
    add_to_message_group(group_id, "bob")
    add_to_message_group(group_id, "jam")
    print(f"   ✓ Group created (id={group_id})\n")

    print("2. Sending message to group members via store_message()...\n")
    result = message.store_message_with_checks(
        channel="example.group",
        sender_moniker="alice",
        content="Guild announcement: meeting in 10 minutes!",
        recipient_monikers=["jam"],  # expansion is caller's responsibility
        urgency=MessageUrgency.IMPORTANT,
    )
    print(f"   ✓ Stored id={result['message_id']}")
    print(f"   Recipients stored: {result['recipients_stored']}")
    print(f"   Recipients blocked: {result['recipients_blocked']}\n")

    # To expand @group automatically, resolve it first:
    print(
        "   (For automatic @group expansion, use get_message_group_members\n"
        "    before calling store_message.)\n"
    )


def example_blocking() -> None:
    """Example 5: Sender blocking.

    Note: in the message system, blocking is per-(blocker, blocked)
    pair. ``block_sender('jam', 'alice')`` means jam won't receive
    messages sent by alice. is_blocked(recipient, sender) returns
    whether a specific message would be blocked.
    """
    print_section("Example 5: Sender Blocking")

    print("1. jam blocks alice...\n")
    block_sender("jam", "alice")
    print("   ✓ Block recorded\n")

    print("2. Checking blocking status...\n")
    is_alice_blocked = is_blocked("jam", "alice")
    print(f"   - messages from alice to jam blocked: {is_alice_blocked}")
    is_bob_blocked = is_blocked("jam", "bob")
    print(f"   - messages from bob to jam blocked: {is_bob_blocked}\n")


def example_retrieve_messages() -> None:
    """Example 6: Retrieving messages."""
    print_section("Example 6: Retrieving Messages")

    print("1. Sending test messages on 'example.retrieve'...\n")
    sent_ids: list[int] = []
    for i in range(3):
        msg_id = message.store_message(
            channel="example.retrieve",
            sender_moniker="alice",
            content=f"Test message {i + 1}",
            recipient_monikers=["jam"],
            urgency=MessageUrgency.ROUTINE,
        )
        sent_ids.append(msg_id)
    print(f"   ✓ Stored ids: {sent_ids}\n")

    print("2. Retrieving all pending+delivered for jam (prioritized)...\n")
    pending = message.get_pending_messages_prioritized("jam", limit=10)
    print(f"   Found {len(pending)} messages; first 3 of retrieve channel:")
    retrieved = [m for m in pending if m["channel"] == "example.retrieve"][:3]
    for m in retrieved:
        print(f"     - {m['content'][:50]} (id={m['id']}, urgency={m['urgency']})")
    print()

    print("3. Unread count via get_unread_count()...\n")
    unread = get_unread_count("jam")
    print(f"   jam has {unread} unread messages\n")

    if retrieved:
        print("4. Marking first as read...\n")
        message.mark_read(retrieved[0]["id"], "jam")
        print(f"   ✓ Marked id={retrieved[0]['id']} as read\n")


def example_complete_workflow() -> None:
    """Example 7: End-to-end workflow: send -> receive -> mark read."""
    print_section("Example 7: Complete Workflow")

    print("Step 1: alice sends a message to jam...\n")
    msg_id = message.store_message(
        channel="example.workflow",
        sender_moniker="alice",
        content="Check this out!",
        recipient_monikers=["jam"],
        urgency=MessageUrgency.IMPORTANT,
        data={"post_id": 12345, "shared_by": "alice"},
    )
    print(f"   ✓ Stored id={msg_id}\n")

    print("Step 2: jam retrieves pending messages on connect...\n")
    delivered = message.deliver_pending_on_connect("jam")
    print(f"   ✓ {len(delivered)} delivered\n")

    print("Step 3: jam marks the message as read...\n")
    message.mark_read(msg_id, "jam")
    print(f"   ✓ Marked id={msg_id} as read\n")

    print("Step 4: Verify unread count decreased...\n")
    new_count = get_unread_count("jam")
    print(f"   jam now has {new_count} unread messages\n")


def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  bbsengine6 Message System - Examples")
    print("=" * 60)

    try:
        example_basic_send()
        example_urgency_levels()
        example_with_data()
        example_groups()
        example_blocking()
        example_retrieve_messages()
        example_complete_workflow()

        print("\n" + "=" * 60)
        print("  ✓ All examples completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Review the examples above")
        print("  2. Check TODO-message-migration.md for the migration plan")
        print("  3. Run: pytest tests/test_message_lib.py -v")
        print("  4. See py/src/bbsengine6/examples/ for more patterns")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   Make sure the database is running and initialized")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
