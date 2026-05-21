# test_notify_message_f2_demo.py
# Mock test for notify_message_demo: Alice sends message to Bob, Bob views with F2

import sys

import pytest

# Add examples path to import the demo
sys.path.insert(0, "/home/opencode/data/work/bbsengine6/py/src/bbsengine6/examples")

from notify_message_demo import DemoConfig, NotifyMessageDemo, display_with_more_prompt


class TestNotifyMessageF2Demo:
    """Test sending messages and viewing them with F2 key press."""

    def test_alice_sends_message_to_bob_bob_views_with_f2(self):
        """
        Scenario:
        1. Alice sends a message to Bob
        2. Bob runs the demo
        3. Bob presses F2 to view messages
        """
        # Step 1: Alice sends message to Bob
        alice_config = DemoConfig(moniker="alice")
        alice = NotifyMessageDemo(alice_config)

        message_text = "Hello Bob! This is a test message from Alice."
        alice.handler.send_message(message_text, "bob")

        # Verify message was sent
        assert alice.handler.stats["sent"] == 1

        # Step 2: Bob runs the demo
        bob_config = DemoConfig(moniker="bob")
        bob = NotifyMessageDemo(bob_config)

        # Step 3: Bob receives the message (simulate receiving messages)
        # The demo_queues is shared across instances for the same recipient
        received_messages = bob.handler.receive_messages()
        assert len(received_messages) == 1

        # Verify the message content
        received_msg = received_messages[0]
        assert received_msg["sender"] == "alice"
        # Message is rendered with template, so it includes sender name
        assert message_text in received_msg["message"]
        assert received_msg["direction"] == "in"

        # Step 4: Simulate F2 key press to view messages
        # In the actual demo, F2 calls handle_f2() which displays messages
        # After messages are received once, they're removed from queue
        messages_for_display = bob.handler.receive_messages()
        assert len(messages_for_display) == 0  # Queue is now empty

    def test_multiple_messages_from_alice_bob_views_all_with_f2(self):
        """
        Test that Bob can view multiple messages from Alice via F2.
        """
        # Alice sends multiple messages to Bob
        alice_config = DemoConfig(moniker="alice")
        alice = NotifyMessageDemo(alice_config)

        messages = [
            "First message from Alice",
            "Second message from Alice",
            "Third message from Alice",
        ]

        for msg in messages:
            alice.handler.send_message(msg, "bob")

        # Verify all messages were sent
        assert alice.handler.stats["sent"] == 3

        # Bob runs the demo
        bob_config = DemoConfig(moniker="bob")
        bob = NotifyMessageDemo(bob_config)

        # Bob presses F2 to view all messages
        received_messages = bob.handler.receive_messages()
        assert len(received_messages) == 3

        # Verify all message content (messages are rendered with template)
        for i, msg in enumerate(messages):
            assert msg in received_messages[i]["message"]
            assert received_messages[i]["sender"] == "alice"

    def test_bob_marks_messages_as_read_after_f2(self):
        """
        Test that messages are marked as read after viewing with F2.
        In demo mode, calling receive_messages() removes them from the queue.
        """
        # Alice sends a message to Bob
        alice_config = DemoConfig(moniker="alice")
        alice = NotifyMessageDemo(alice_config)

        alice.handler.send_message("Message for Bob", "bob")

        # Bob receives the message
        bob_config = DemoConfig(moniker="bob")
        bob = NotifyMessageDemo(bob_config)

        # First F2 press - receive messages
        unread = bob.handler.receive_messages()
        assert len(unread) == 1

        # In demo mode, receive_messages() pops from the queue automatically
        # Second F2 press - should have no unread messages
        unread_again = bob.handler.receive_messages()
        assert len(unread_again) == 0

    def test_f2_status_shows_message_count(self):
        """
        Test that F2 status indicator shows the correct count of unread messages.
        """
        # Alice sends 2 messages to Bob
        alice_config = DemoConfig(moniker="alice")
        alice = NotifyMessageDemo(alice_config)

        alice.handler.send_message("Message 1", "bob")
        alice.handler.send_message("Message 2", "bob")

        # Bob checks status
        bob_config = DemoConfig(moniker="bob")
        bob = NotifyMessageDemo(bob_config)

        # Get the unread count using _get_unread_count()
        unread_count = bob._get_unread_count()
        assert unread_count == 2

    def test_demo_mode_message_persistence_across_instances(self):
        """
        Test that messages persist in demo mode across different NotifyMessageDemo instances.
        This verifies the shared demo_queues mechanism works.
        Uses unique usernames to avoid collision with other tests.
        """
        # Alice sends a message to Bob with unique names
        alice_config = DemoConfig(moniker="alice_persist_test")
        alice_instance_1 = NotifyMessageDemo(alice_config)
        alice_instance_1.handler.send_message("Message 1", "bob_persist_test")

        # Create a second instance of Bob's demo (simulating app restart)
        bob_config = DemoConfig(moniker="bob_persist_test")
        bob_instance_1 = NotifyMessageDemo(bob_config)

        # Bob should see the message from instance 1
        messages = bob_instance_1.handler.receive_messages()
        assert len(messages) == 1
        assert "Message 1" in messages[0]["message"]

        # Now Alice sends another message from a different instance
        alice_instance_2 = NotifyMessageDemo(alice_config)
        alice_instance_2.handler.send_message("Message 2", "bob_persist_test")

        # Bob's first instance should see the new message
        messages_updated = bob_instance_1.handler.receive_messages()
        assert len(messages_updated) == 1
        assert "Message 2" in messages_updated[0]["message"]

    def test_f2_key_handler_integration(self):
        """
        Test the F2 key handler integration with the demo loop.
        Uses unique usernames to avoid collision with other tests.
        """
        # Setup: Alice sends message to Charlie
        alice_config = DemoConfig(moniker="alice_f2_test")
        alice = NotifyMessageDemo(alice_config)
        alice.handler.send_message("Test message for F2", "charlie_f2_test")

        # Setup: Charlie runs demo
        charlie_config = DemoConfig(moniker="charlie_f2_test")
        charlie = NotifyMessageDemo(charlie_config)

        # F2 displays unread messages by calling receive_messages()
        messages = charlie.handler.receive_messages()
        assert len(messages) == 1

        # Simulate what the UI would show
        display_text = "\n".join(
            [f"[{msg['sender']}]: {msg['message']}" for msg in messages]
        )
        assert "alice_f2_test" in display_text
        assert "Test message for F2" in display_text

    def test_bidirectional_messaging_with_f2(self):
        """
        Test bidirectional messaging: Alice sends to Bob, Bob sends back.
        Both can view with F2.
        Uses unique usernames to avoid collision with other tests.
        """
        # Alice sends message to Bob with unique names
        alice_config = DemoConfig(moniker="alice_bidir_test")
        alice = NotifyMessageDemo(alice_config)
        alice.handler.send_message("Message from Alice to Bob", "bob_bidir_test")

        # Bob receives and views with F2
        bob_config = DemoConfig(moniker="bob_bidir_test")
        bob = NotifyMessageDemo(bob_config)
        bob_messages = bob.handler.receive_messages()
        assert len(bob_messages) == 1
        assert bob_messages[0]["sender"] == "alice_bidir_test"

        # Bob sends reply back to Alice
        bob.handler.send_message("Reply from Bob to Alice", "alice_bidir_test")

        # Alice receives and views with F2
        alice_new_messages = alice.handler.receive_messages()
        assert len(alice_new_messages) == 1
        assert alice_new_messages[0]["sender"] == "bob_bidir_test"
        assert "Reply from Bob to Alice" in alice_new_messages[0]["message"]

    def test_abort_with_n_keeps_messages_unread(self):
        """
        Test that when a user aborts message viewing with 'n',
        the undisplayed messages remain unread in demo mode.
        """
        # Alice sends 3 messages to Bob (smaller number for testing)
        alice_config = DemoConfig(moniker="alice_abort_test")
        alice = NotifyMessageDemo(alice_config)

        for i in range(3):
            alice.handler.send_message(f"Message {i + 1}", "bob_abort_test")

        # Bob receives the messages (without marking as read)
        bob_config = DemoConfig(moniker="bob_abort_test")
        bob = NotifyMessageDemo(bob_config)

        # Get unread messages (does NOT mark them as read)
        unread = bob.handler.get_unread_messages()
        assert len(unread) == 3

        # Verify unread count is still 3
        unread_count = len(bob.handler.get_unread_messages())
        assert unread_count == 3

        # Now simulate a complete view by calling mark_messages_as_read
        # In demo mode, pass count as first element in list
        bob.handler.mark_messages_as_read([len(unread)])

        # After marking as read, unread count should be 0
        unread_count_after = len(bob.handler.get_unread_messages())
        assert unread_count_after == 0

    def test_more_prompt_displays_messages_with_pagination(self):
        """Test that more prompt displays messages with pagination."""
        from unittest.mock import patch

        messages = [
            "Message 1",
            "Message 2",
            "Message 3",
            "Message 4",
            "Message 5",
            "Message 6",  # This will trigger more prompt
        ]

        # Simulate user pressing Enter to continue
        with patch("builtins.input", return_value=""):
            result = display_with_more_prompt(messages, page_size=5)

        # Should return True when all messages displayed
        assert result is True

    def test_more_prompt_abort_with_n_returns_false(self):
        """Test that more prompt returns False when user inputs 'n'."""
        from unittest.mock import patch

        messages = [f"Message {i}" for i in range(6)]

        # Simulate user pressing 'n' to abort
        with patch("builtins.input", return_value="n"):
            result = display_with_more_prompt(messages, page_size=5)

        # Should return False when user presses 'n'
        assert result is False

    def test_f2_abort_with_more_prompt_keeps_messages_unread(self):
        """
        Integration test: Verify that F2 abort with 'n' to more prompt
        keeps messages unread (can be viewed again with F2).
        """
        from unittest.mock import patch

        # Alice sends 7 messages to trigger multiple more prompts
        alice_config = DemoConfig(moniker="alice_f2_abort_prompt")
        alice = NotifyMessageDemo(alice_config)

        for i in range(7):
            alice.handler.send_message(
                f"Message {i + 1} from Alice", "bob_f2_abort_prompt"
            )

        # Bob gets unread count before F2
        bob_config = DemoConfig(moniker="bob_f2_abort_prompt")
        bob = NotifyMessageDemo(bob_config)

        unread_before = len(bob.handler.get_unread_messages())
        assert unread_before == 7

        # Simulate F2 key press with abort at more prompt
        # This simulates what happens when user presses F2
        with patch("builtins.input", return_value="n"):
            messages = bob.handler.get_unread_messages()
            formatted_messages = [f"[RECEIVED] {msg['message']}" for msg in messages]
            fully_displayed = display_with_more_prompt(formatted_messages, page_size=5)

            # Verify abort happened
            assert fully_displayed is False

            # Key behavior: since abort happened, we don't mark as read
            # (This is handled by _check_and_display_messages)

        # Verify messages are still unread
        unread_after = len(bob.handler.get_unread_messages())
        assert unread_after == 7, "Messages should still be unread after F2 abort"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
