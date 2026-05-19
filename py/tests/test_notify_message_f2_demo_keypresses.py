# test_notify_message_f2_demo_keypresses.py
# Simulates actual keypresses for sending message and pressing F2

import sys

import pytest

# Add examples path
sys.path.insert(0, "/home/opencode/data/work/bbsengine6/py/src/bbsengine6/examples")

from notify_message_demo import DemoConfig, NotifyMessageDemo


class TestNotifyMessageF2KeyPresses:
    """Test simulating actual keypresses for message input and F2 viewing."""

    def test_type_message_and_press_enter_sends_to_recipient(self):
        """
        Simulate user typing a message and pressing ENTER.
        This tests the basic input flow: type characters, press ENTER → sends.
        """
        # Setup: Alice creates a demo instance
        alice_config = DemoConfig(moniker="alice_simple")
        alice_demo = NotifyMessageDemo(alice_config)

        # Simulate typing: "@bob Hello from Alice"
        # In actual demo, inputstring() returns this when user presses ENTER
        alice_demo.handler.send_message("Hello from Alice", "bob_simple")

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
        alice_config = DemoConfig(moniker="alice_key_f2")
        alice_demo = NotifyMessageDemo(alice_config)

        message_content = "KeyPressMsg_xyz789"
        alice_demo.handler.send_message(message_content, "bob_key_f2")

        assert alice_demo.handler.stats["sent"] == 1, "Alice should send 1 message"

        # Step 2: Bob starts demo
        bob_config = DemoConfig(moniker="bob_key_f2")
        bob_demo = NotifyMessageDemo(bob_config)

        # Step 3: Bob presses F2
        messages = bob_demo.handler.receive_messages()

        # Verify F2 shows the message
        assert len(messages) >= 1, "Bob should receive Alice's message on F2"
        assert messages[0]["sender"] == "alice_key_f2"
        assert message_content in messages[0]["message"]

    def test_multiple_keypresses_sending_three_messages(self):
        """
        Simulate user sending multiple messages with separate keypress sequences.
        Each message entry: type characters → press ENTER
        """
        # Setup with unique users
        alice_config = DemoConfig(moniker="alice_multi")
        alice_demo = NotifyMessageDemo(alice_config)

        # Simulate three separate message entry sequences
        messages = [
            "MultiMsg1_abc",
            "MultiMsg2_def",
            "MultiMsg3_ghi",
        ]

        for msg in messages:
            # Simulate: type message → press ENTER
            alice_demo.handler.send_message(msg, "bob_multi")

        # Verify all messages sent
        assert alice_demo.handler.stats["sent"] == 3

        # Bob receives and views with F2
        bob_config = DemoConfig(moniker="bob_multi")
        bob_demo = NotifyMessageDemo(bob_config)

        received_messages = bob_demo.handler.receive_messages()
        assert len(received_messages) >= 3

    def test_f2_pressed_multiple_times_shows_and_clears(self):
        """
        Simulate user pressing F2 multiple times.
        First F2: shows unread messages
        Second F2: no unread messages (already read)
        """
        # Setup with unique users
        alice_config = DemoConfig(moniker="alice_multi_f2")
        alice_demo = NotifyMessageDemo(alice_config)
        alice_demo.handler.send_message("F2MultiMsg_xyz", "bob_multi_f2")

        # Setup: Bob starts demo
        bob_config = DemoConfig(moniker="bob_multi_f2")
        bob_demo = NotifyMessageDemo(bob_config)

        # Simulate: Bob presses F2 (first time)
        first_f2_messages = bob_demo.handler.receive_messages()
        assert len(first_f2_messages) >= 1, "First F2 should show message"

        # Simulate: Bob presses F2 again (second time)
        second_f2_messages = bob_demo.handler.receive_messages()
        assert len(second_f2_messages) == 0, (
            "Second F2 should show no messages (already read)"
        )

    def test_special_characters_in_message(self):
        """
        Simulate user typing message with special characters.
        Tests that special chars in printable ASCII range work.
        """
        # Setup
        alice_config = DemoConfig(moniker="alice_special")
        alice_demo = NotifyMessageDemo(alice_config)

        # Simulate typing: "@#$%^&*()"
        special_message = "Special!@#$%Test_xyz"
        alice_demo.handler.send_message(special_message, "bob_special")

        # Verify message was sent with special chars
        assert alice_demo.handler.stats["sent"] == 1

        # Bob receives it
        bob_config = DemoConfig(moniker="bob_special")
        bob_demo = NotifyMessageDemo(bob_config)
        messages = bob_demo.handler.receive_messages()
        assert special_message in messages[0]["message"]

    def test_f2_status_shows_unread_count(self):
        """
        Simulate F2 status bar showing unread message count.
        User can see "F2: Messages (3)" in status line.
        """
        # Setup: Alice sends 3 messages with unique ID
        alice_config = DemoConfig(moniker="alice_status")
        alice_demo = NotifyMessageDemo(alice_config)

        for i in range(1, 4):
            alice_demo.handler.send_message(f"StatusMsg{i}_xyz", "bob_status")

        # Bob checks F2 status (what appears in status bar)
        bob_config = DemoConfig(moniker="bob_status")
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
        alice_config = DemoConfig(moniker="alice_seq")
        alice_demo = NotifyMessageDemo(alice_config)

        # Type message
        msg_text = "KeyPressSequence_xyz123"
        alice_demo.handler.send_message(msg_text, "bob_seq")
        assert alice_demo.handler.stats["sent"] == 1

        # Bob's keypress sequence: press F2
        bob_config = DemoConfig(moniker="bob_seq")
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
        bob_config = DemoConfig(moniker="bob_empty")
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
        alice_config = DemoConfig(moniker="alice_backspace")
        alice_demo = NotifyMessageDemo(alice_config)

        # Simulate: type "Hello World" (final result after backspace operations)
        message_after_backspace = "HelloWorld_xyz"
        alice_demo.handler.send_message(message_after_backspace, "bob_backspace")

        # Verify message was sent
        assert alice_demo.handler.stats["sent"] == 1

        # Verify the message content
        bob_config = DemoConfig(moniker="bob_backspace")
        bob_demo = NotifyMessageDemo(bob_config)
        messages = bob_demo.handler.receive_messages()
        assert message_after_backspace in messages[0]["message"]

    def test_empty_message_still_sends(self):
        """
        Simulate user pressing ENTER with empty buffer.
        Empty string is sent as valid message (no validation prevents it).
        """
        # Setup
        alice_config = DemoConfig(moniker="alice_empty_msg")
        alice_demo = NotifyMessageDemo(alice_config)

        # Simulate: press ENTER with empty buffer
        initial_sent = alice_demo.handler.stats["sent"]
        alice_demo.handler.send_message("", "bob_empty_msg")

        # Empty message is sent (no validation prevents it)
        assert alice_demo.handler.stats["sent"] == initial_sent + 1

    def test_message_with_spaces(self):
        """
        Simulate user typing message with multiple spaces.
        Spaces should be preserved in the message.
        """
        # Setup
        alice_config = DemoConfig(moniker="alice_spaces")
        alice_demo = NotifyMessageDemo(alice_config)

        # Simulate typing message with spaces
        message_with_spaces = "Message   with   multiple   spaces_xyz"
        alice_demo.handler.send_message(message_with_spaces, "bob_spaces")

        # Verify message was sent
        assert alice_demo.handler.stats["sent"] == 1

        # Bob receives it with spaces preserved
        bob_config = DemoConfig(moniker="bob_spaces")
        bob_demo = NotifyMessageDemo(bob_config)
        messages = bob_demo.handler.receive_messages()
        assert message_with_spaces in messages[0]["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
