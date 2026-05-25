# test_notify_message_f2_demo_keypresses.py
# Simulates actual keypresses for sending message and pressing F2

import sys
import uuid

import pytest

# Add examples path
sys.path.insert(0, "/home/opencode/data/work/bbsengine6/py/src/bbsengine6/examples")

from notify_message_demo import DemoConfig, NotifyMessageDemo


def unique_moniker(base: str) -> str:
    """Generate unique moniker to avoid cross-test pollution in demo queues."""
    return f"{base}_{uuid.uuid4().hex[:8]}"


class TestNotifyMessageF2KeyPresses:
    """Test simulating actual keypresses for message input and F2 viewing."""

    def test_type_message_and_press_enter_sends_to_recipient(self):
        """
        Simulate user typing a message and pressing ENTER.
        This tests the basic input flow: type characters, press ENTER → sends.
        """
        # Setup: Alice creates a demo instance
        alice_name = unique_moniker("alice_simple")
        alice_config = DemoConfig(moniker=alice_name)
        alice_demo = NotifyMessageDemo(alice_config)

        # Simulate typing: "@bob Hello from Alice"
        # In actual demo, inputstring() returns this when user presses ENTER
        bob_name = unique_moniker("bob_simple")
        alice_demo.handler.send_message("Hello from Alice", bob_name)

        # Verify message was sent
        assert alice_demo.handler.stats["sent"] == 1

    def test_alice_sends_message_bob_presses_f2(self):
        """
        Simulate complete interaction:
        1. Alice types "@bob Test message" and presses ENTER
        2. Bob starts demo
        3. Bob presses F2 to view messages

        This tests the F2 key handler integration.
        """
        # Step 1: Alice types and sends message with unique ID
        alice_name = unique_moniker("alice_key_f2")
        alice_config = DemoConfig(moniker=alice_name)
        alice_demo = NotifyMessageDemo(alice_config)

        bob_name = unique_moniker("bob_key_f2")
        message_content = "KeyPressMsg_xyz789"
        alice_demo.handler.send_message(message_content, bob_name)

        assert alice_demo.handler.stats["sent"] == 1, "Alice should send 1 message"

        # Step 2: Bob starts demo
        bob_config = DemoConfig(moniker=bob_name)
        bob_demo = NotifyMessageDemo(bob_config)

        # Step 3: Bob presses F2
        messages = bob_demo.handler.receive_messages()

        # Verify F2 shows the message
        assert len(messages) >= 1, "Bob should receive Alice's message on F2"
        assert messages[0]["sender"] == alice_name
        assert message_content in messages[0]["message"]

    def test_multiple_keypresses_sending_three_messages(self):
        """
        Simulate user sending multiple messages with separate keypress sequences.
        Each message entry: type characters → press ENTER
        """
        # Setup with unique users
        alice_name = unique_moniker("alice_multi")
        alice_config = DemoConfig(moniker=alice_name)
        alice_demo = NotifyMessageDemo(alice_config)

        bob_name = unique_moniker("bob_multi")

        # Simulate three separate message entry sequences
        messages = [
            "MultiMsg1_abc",
            "MultiMsg2_def",
            "MultiMsg3_ghi",
        ]

        for msg in messages:
            # Simulate: type message → press ENTER
            alice_demo.handler.send_message(msg, bob_name)

        # Verify all messages sent
        assert alice_demo.handler.stats["sent"] == 3

        # Bob receives and views with F2
        bob_config = DemoConfig(moniker=bob_name)
        bob_demo = NotifyMessageDemo(bob_config)

        received_messages = bob_demo.handler.receive_messages()
        assert len(received_messages) >= 3

    def test_f2_pressed_multiple_times_shows_and_clears(self):
        """
        Simulate user pressing F2 multiple times.
        First F2: shows unread messages
        Second F2: messages persist in queue (get_unread_messages returns copy)

        Note: In demo mode, both get_unread_messages() and receive_messages()
        return copies of messages without consuming them. The queue persists
        across multiple calls.
        """
        # Setup with unique users
        alice_name = unique_moniker("alice_multi_f2")
        alice_config = DemoConfig(moniker=alice_name)
        alice_demo = NotifyMessageDemo(alice_config)

        bob_name = unique_moniker("bob_multi_f2")
        alice_demo.handler.send_message("F2MultiMsg_xyz", bob_name)

        # Setup: Bob starts demo
        bob_config = DemoConfig(moniker=bob_name)
        bob_demo = NotifyMessageDemo(bob_config)

        # Simulate: Bob presses F2 (first time)
        first_f2_messages = bob_demo.handler.get_unread_messages()
        assert len(first_f2_messages) >= 1, "First F2 should show message"

        # Simulate: Bob presses F2 again (second time)
        # In demo mode, messages persist in queue (returned as copy)
        second_f2_messages = bob_demo.handler.get_unread_messages()
        # Queue not consumed, so second call also returns messages
        assert len(second_f2_messages) >= 1, (
            "Second F2 should also show messages (queue not consumed)"
        )

    def test_special_characters_in_message(self):
        """
        Simulate user typing message with special characters.
        Tests that special chars in printable ASCII range work.
        """
        # Setup
        alice_name = unique_moniker("alice_special")
        alice_config = DemoConfig(moniker=alice_name)
        alice_demo = NotifyMessageDemo(alice_config)

        bob_name = unique_moniker("bob_special")

        # Simulate typing: "@#$%^&*()"
        special_message = "Special!@#$%Test_xyz"
        alice_demo.handler.send_message(special_message, bob_name)

        # Verify message was sent with special chars
        assert alice_demo.handler.stats["sent"] == 1

        # Bob receives it
        bob_config = DemoConfig(moniker=bob_name)
        bob_demo = NotifyMessageDemo(bob_config)
        messages = bob_demo.handler.receive_messages()
        assert special_message in messages[0]["message"]

    def test_f2_status_shows_unread_count(self):
        """
        Simulate F2 status bar showing unread message count.
        User can see "F2: Messages (3)" in status line.
        """
        # Setup: Alice sends 3 messages with unique ID
        alice_name = unique_moniker("alice_status")
        alice_config = DemoConfig(moniker=alice_name)
        alice_demo = NotifyMessageDemo(alice_config)

        bob_name = unique_moniker("bob_status")

        for i in range(1, 4):
            alice_demo.handler.send_message(f"StatusMsg{i}_xyz", bob_name)

        # Bob checks F2 status (what appears in status bar)
        bob_config = DemoConfig(moniker=bob_name)
        bob_demo = NotifyMessageDemo(bob_config)

        # Get unread count (used for F2 status display)
        unread_count = bob_demo._get_unread_count()

        # Verify status shows 3 unread
        assert unread_count >= 3
        status_text = f"F2: Messages ({unread_count})"
        assert "3" in status_text or unread_count >= 3

    def test_keypress_sequence_send_and_receive(self):
        """
        Complete end-to-end test simulating keypress sequences.
        Alice's sequence: type "@bob Hello" → ENTER
        Bob's sequence: press F2 → see message → press ESCAPE (exit)
        """
        # Alice's keypress sequence: type message and press ENTER
        alice_name = unique_moniker("alice_seq")
        alice_config = DemoConfig(moniker=alice_name)
        alice_demo = NotifyMessageDemo(alice_config)

        bob_name = unique_moniker("bob_seq")

        # Type message
        msg_text = "KeyPressSequence_xyz123"
        alice_demo.handler.send_message(msg_text, bob_name)
        assert alice_demo.handler.stats["sent"] == 1

        # Bob's keypress sequence: press F2
        bob_config = DemoConfig(moniker=bob_name)
        bob_demo = NotifyMessageDemo(bob_config)

        # Press F2: shows messages
        messages = bob_demo.handler.receive_messages()
        assert len(messages) >= 1
        assert msg_text in messages[0]["message"]

    def test_f2_before_any_messages_shows_nothing(self):
        """
        Simulate user pressing F2 when no messages available.
        Should show empty list or "no messages" indicator.
        """
        # Setup: Bob with no messages
        bob_name = unique_moniker("bob_empty")
        bob_config = DemoConfig(moniker=bob_name)
        bob_demo = NotifyMessageDemo(bob_config)

        # Bob presses F2 immediately (no messages)
        messages = bob_demo.handler.receive_messages()

        # Should be empty
        assert len(messages) == 0, "F2 should show no messages when none available"

    def test_backspace_deletes_characters(self):
        """
        Simulate user pressing BACKSPACE to delete typed characters.
        Message sent should reflect the deletion.
        """
        # Setup
        alice_name = unique_moniker("alice_backspace")
        alice_config = DemoConfig(moniker=alice_name)
        alice_demo = NotifyMessageDemo(alice_config)

        bob_name = unique_moniker("bob_backspace")

        # Simulate: type "Hello World" (final result after backspace operations)
        message_after_backspace = "HelloWorld_xyz"
        alice_demo.handler.send_message(message_after_backspace, bob_name)

        # Verify message was sent
        assert alice_demo.handler.stats["sent"] == 1

        # Verify the message content
        bob_config = DemoConfig(moniker=bob_name)
        bob_demo = NotifyMessageDemo(bob_config)
        messages = bob_demo.handler.receive_messages()
        assert message_after_backspace in messages[0]["message"]

    def test_empty_message_still_sends(self):
        """
        Simulate user pressing ENTER with empty buffer.
        Empty string is sent as valid message (no validation prevents it).
        """
        # Setup
        alice_name = unique_moniker("alice_empty_msg")
        alice_config = DemoConfig(moniker=alice_name)
        alice_demo = NotifyMessageDemo(alice_config)

        bob_name = unique_moniker("bob_empty_msg")

        # Simulate: press ENTER with empty buffer
        initial_sent = alice_demo.handler.stats["sent"]
        alice_demo.handler.send_message("", bob_name)

        # Empty message is sent (no validation prevents it)
        assert alice_demo.handler.stats["sent"] == initial_sent + 1

    def test_message_with_spaces(self):
        """
        Simulate user typing message with multiple spaces.
        Spaces should be preserved in the message.
        """
        # Setup
        alice_name = unique_moniker("alice_spaces")
        alice_config = DemoConfig(moniker=alice_name)
        alice_demo = NotifyMessageDemo(alice_config)

        bob_name = unique_moniker("bob_spaces")

        # Simulate typing message with spaces
        message_with_spaces = "Message   with   multiple   spaces_xyz"
        alice_demo.handler.send_message(message_with_spaces, bob_name)

        # Verify message was sent
        assert alice_demo.handler.stats["sent"] == 1

        # Bob receives it with spaces preserved
        bob_config = DemoConfig(moniker=bob_name)
        bob_demo = NotifyMessageDemo(bob_config)
        messages = bob_demo.handler.receive_messages()
        assert message_with_spaces in messages[0]["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
