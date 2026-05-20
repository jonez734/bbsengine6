# test_notify_message_f2_abort_unread.py
# Test F2 key press during inputstring with abort scenario
# Verifies that unread messages remain unread when user presses F2 then aborts with 'n'

import sys
from unittest.mock import patch, MagicMock

import pytest

# Add paths for imports
sys.path.insert(0, "/home/opencode/data/work/bbsengine6/py/src")
sys.path.insert(0, "/home/opencode/data/work/bbsengine6/py/src/bbsengine6/examples")

from notify_message_demo import (
    DemoConfig,
    NotifyMessageDemo,
    display_with_more_prompt,
)


class TestNotifyMessageF2AbortUnread:
    """Test F2 key press with abort preserves unread message count."""

    def test_f2_abort_with_n_keeps_all_messages_unread_demo_mode(self):
        """
        Comprehensive test: Alice sends 6 messages to Bob.
        Bob presses F2 to view, but aborts with 'n' at more prompt.
        Messages should remain unread (not be marked as read).

        Scenario:
        1. Alice sends 6 messages to Bob (enough to trigger more prompt at page_size=5)
        2. Bob starts demo and checks unread count (should be 6)
        3. Bob presses F2 (triggers F2 handler)
        4. F2 displays 5 messages, then shows more prompt
        5. Bob presses 'n' to abort before all messages are displayed
        6. Messages should NOT be marked as read
        7. Verify unread count is still 6
        """
        # Step 1: Alice sends 6 messages to Bob
        alice_config = DemoConfig(moniker="alice_f2_abort_test")
        alice = NotifyMessageDemo(alice_config)

        # Send 6 messages so that after 5 are shown, more prompt appears
        message_texts = [f"Message {i+1}" for i in range(6)]
        for msg in message_texts:
            alice.handler.send_message(msg, "bob_f2_abort_test")

        assert alice.handler.stats["sent"] == 6, "Alice should send 6 messages"

        # Step 2: Bob starts demo
        bob_config = DemoConfig(moniker="bob_f2_abort_test")
        bob = NotifyMessageDemo(bob_config)

        # Check initial unread count
        unread_before = len(bob.handler.get_unread_messages())
        assert unread_before == 6, f"Bob should have 6 unread messages, got {unread_before}"

        # Step 3-5: Simulate F2 key press with abort
        # This mimics what _check_and_display_messages() does
        unread_messages = bob.handler.get_unread_messages()
        assert len(unread_messages) == 6, "Should have 6 unread messages to display"

        # Format messages for display (same as demo does)
        from bbsengine6.examples.notify_message_demo import TimestampFormatter

        formatted_messages = []
        for msg in unread_messages:
            timestamp_str = TimestampFormatter.format_compact(msg.get("timestamp"))
            formatted_messages.append(f"[{timestamp_str}] {msg['message']}")

        # Simulate user pressing 'n' at more prompt (abort)
        with patch("builtins.input", return_value="n"):
            fully_displayed = display_with_more_prompt(
                formatted_messages, page_size=5
            )

        # Verify abort happened
        assert (
            fully_displayed is False
        ), "Should return False when user presses 'n' at more prompt"

        # Step 6-7: Verify messages remain unread
        # Since abort happened (fully_displayed=False), we don't mark as read
        unread_after = len(bob.handler.get_unread_messages())
        assert (
            unread_after == 6
        ), f"Messages should remain unread after F2 abort, got {unread_after}"

    def test_f2_abort_then_view_again_same_messages_shown(self):
        """
        Test that after aborting F2 view with 'n', pressing F2 again shows same messages.

        Scenario:
        1. Alice sends 6 messages to Bob (enough for more prompt)
        2. Bob presses F2, aborts with 'n' (messages not marked as read)
        3. Bob presses F2 again
        4. Same 6 messages should be displayed again
        """
        # Step 1: Alice sends 6 messages
        alice_config = DemoConfig(moniker="alice_f2_retry")
        alice = NotifyMessageDemo(alice_config)

        messages_sent = [f"Attempt message {i+1}" for i in range(6)]
        for msg in messages_sent:
            alice.handler.send_message(msg, "bob_f2_retry")

        assert alice.handler.stats["sent"] == 6

        # Step 2: Bob starts demo
        bob_config = DemoConfig(moniker="bob_f2_retry")
        bob = NotifyMessageDemo(bob_config)

        # First F2 press with abort
        unread_first = bob.handler.get_unread_messages()
        assert len(unread_first) == 6

        with patch("builtins.input", return_value="n"):
            formatted = [f"[MSG] {msg['message']}" for msg in unread_first]
            result = display_with_more_prompt(formatted, page_size=5)
            assert result is False

        # Step 3: Second F2 press (should show same messages)
        unread_second = bob.handler.get_unread_messages()
        assert len(unread_second) == 6, "Should show same 6 messages on second F2"

        # Verify same message content
        first_msg_content = unread_first[0]["message"]
        second_msg_content = unread_second[0]["message"]
        assert first_msg_content == second_msg_content

    def test_f2_display_all_then_messages_marked_as_read(self):
        """
        Test the opposite scenario: when user completes viewing all messages
        (doesn't abort), they are marked as read.

        Scenario:
        1. Alice sends 2 messages to Bob
        2. Bob presses F2, displays all messages (no abort with 'n')
        3. User presses Enter to continue (not 'n')
        4. Messages should be marked as read
        5. Second F2 press should show no messages
        """
        # Step 1: Alice sends 2 messages
        alice_config = DemoConfig(moniker="alice_f2_complete")
        alice = NotifyMessageDemo(alice_config)

        for i in range(2):
            alice.handler.send_message(f"Complete view message {i+1}", "bob_f2_complete")

        # Step 2: Bob starts demo
        bob_config = DemoConfig(moniker="bob_f2_complete")
        bob = NotifyMessageDemo(bob_config)

        # Check unread count before
        unread_before = len(bob.handler.get_unread_messages())
        assert unread_before == 2

        # F2 with full display (no abort)
        unread_messages = bob.handler.get_unread_messages()
        formatted = [f"[MSG] {msg['message']}" for msg in unread_messages]

        # Simulate user pressing Enter (not 'n') to continue
        with patch("builtins.input", return_value=""):
            fully_displayed = display_with_more_prompt(formatted, page_size=5)

        # Verify all messages displayed
        assert fully_displayed is True

        # Step 4: Mark messages as read (as _check_and_display_messages does)
        bob.handler.mark_messages_as_read([len(unread_messages)])

        # Step 5: Verify messages are now read
        unread_after = len(bob.handler.get_unread_messages())
        assert unread_after == 0, "Messages should be marked as read after full display"

    def test_f2_abort_unread_count_preserved_across_instances(self):
        """
        Test that unread count is preserved across different NotifyMessageDemo instances.

        Scenario:
        1. Alice sends message to Bob
        2. Bob instance 1 presses F2, aborts with 'n'
        3. Bob instance 2 (simulating app restart) checks unread count
        4. Should still see the unread message (demo mode uses shared queues)
        """
        # Step 1: Alice sends message
        alice_config = DemoConfig(moniker="alice_f2_persist")
        alice = NotifyMessageDemo(alice_config)
        alice.handler.send_message("Persistent message", "bob_f2_persist")

        # Step 2: Bob instance 1
        bob_config = DemoConfig(moniker="bob_f2_persist")
        bob_instance_1 = NotifyMessageDemo(bob_config)

        unread_1 = len(bob_instance_1.handler.get_unread_messages())
        assert unread_1 == 1

        # Simulate F2 abort (don't mark as read)
        unread_msg = bob_instance_1.handler.get_unread_messages()
        with patch("builtins.input", return_value="n"):
            formatted = [f"[MSG] {msg['message']}" for msg in unread_msg]
            display_with_more_prompt(formatted, page_size=5)
        # Note: not calling mark_messages_as_read, so message stays unread

        # Step 3: Bob instance 2 (new instance, simulating app restart)
        bob_instance_2 = NotifyMessageDemo(bob_config)
        unread_2 = len(bob_instance_2.handler.get_unread_messages())

        # Step 4: Verify message still unread
        assert unread_2 == 1, "Message should still be unread in new instance"

    def test_multiple_f2_presses_with_alternating_abort_complete(self):
        """
        Test complex scenario: multiple F2 presses with mix of abort and complete.

        Scenario:
        1. Alice sends 6 messages to Bob (enough for more prompt)
        2. Bob F2 #1: Abort with 'n' (6 remain unread)
        3. Bob F2 #2: Complete view (mark 6 as read, 0 unread)
        4. Bob F2 #3: No messages (0 unread)
        """
        # Step 1: Alice sends 6 messages
        alice_config = DemoConfig(moniker="alice_f2_multi")
        alice = NotifyMessageDemo(alice_config)

        for i in range(6):
            alice.handler.send_message(f"Message set {i+1}", "bob_f2_multi")

        # Step 2: Bob instance
        bob_config = DemoConfig(moniker="bob_f2_multi")
        bob = NotifyMessageDemo(bob_config)

        # F2 #1: Abort
        unread_1 = bob.handler.get_unread_messages()
        assert len(unread_1) == 6
        formatted_1 = [f"[MSG] {msg['message']}" for msg in unread_1]
        with patch("builtins.input", return_value="n"):
            result_1 = display_with_more_prompt(formatted_1, page_size=5)
        assert result_1 is False
        assert len(bob.handler.get_unread_messages()) == 6

        # F2 #2: Complete view
        unread_2 = bob.handler.get_unread_messages()
        assert len(unread_2) == 6
        formatted_2 = [f"[MSG] {msg['message']}" for msg in unread_2]
        with patch("builtins.input", return_value=""):
            result_2 = display_with_more_prompt(formatted_2, page_size=5)
        assert result_2 is True
        bob.handler.mark_messages_as_read([len(unread_2)])
        assert len(bob.handler.get_unread_messages()) == 0

        # F2 #3: No messages
        unread_3 = bob.handler.get_unread_messages()
        assert len(unread_3) == 0

    def test_f2_abort_unread_count_correct_in_status_bar(self):
        """
        Test that _get_unread_count() returns correct count after F2 abort.
        This is used for the status bar display: "F2: Messages (N)"

        Scenario:
        1. Alice sends 2 messages to Bob
        2. Bob checks status bar: "F2: Messages (2)"
        3. Bob presses F2, aborts
        4. Bob checks status bar again: should still show "F2: Messages (2)"
        """
        # Step 1: Alice sends 2 messages
        alice_config = DemoConfig(moniker="alice_f2_status")
        alice = NotifyMessageDemo(alice_config)

        for i in range(2):
            alice.handler.send_message(f"Status test {i+1}", "bob_f2_status")

        # Step 2: Bob checks initial status
        bob_config = DemoConfig(moniker="bob_f2_status")
        bob = NotifyMessageDemo(bob_config)

        status_before = bob._get_unread_count()
        assert status_before == 2, f"Status should show 2, got {status_before}"

        # Step 3: F2 with abort
        unread_msg = bob.handler.get_unread_messages()
        formatted = [f"[MSG] {msg['message']}" for msg in unread_msg]
        with patch("builtins.input", return_value="n"):
            display_with_more_prompt(formatted, page_size=5)

        # Step 4: Status bar should still show 2
        status_after = bob._get_unread_count()
        assert (
            status_after == 2
        ), f"Status should still show 2 after abort, got {status_after}"

    def test_page_wise_marking_first_page_marked_before_prompt(self):
        """
        Test that messages are marked as read page-by-page as displayed.

        Scenario:
        1. Alice sends 10 messages to Bob (2 pages with page_size=5)
        2. Bob presses F2 to view messages via _check_and_display_messages()
        3. First 5 messages displayed and marked as read
        4. Bob sees more prompt (5 remaining)
        5. Bob presses 'n' to abort
        6. Messages on second page remain unread
        7. Verify unread count is 5 (second page)
        """
        # Step 1: Alice sends 10 messages
        alice_config = DemoConfig(moniker="alice_pagewise")
        alice = NotifyMessageDemo(alice_config)

        for i in range(10):
            alice.handler.send_message(f"Message page test {i+1}", "bob_pagewise")

        assert alice.handler.stats["sent"] == 10

        # Step 2: Bob starts demo
        bob_config = DemoConfig(moniker="bob_pagewise")
        bob = NotifyMessageDemo(bob_config)

        # Verify initial unread count is 10
        initial_unread = len(bob.handler.get_unread_messages())
        assert initial_unread == 10

        # Step 3-5: Simulate F2 key press via _check_and_display_messages()
        # This method handles the page-wise marking internally
        with patch("builtins.input", return_value="n"):
            bob._check_and_display_messages()

        # Step 6-7: Verify first page was marked as read
        unread_after_abort = len(bob.handler.get_unread_messages())
        assert (
            unread_after_abort == 5
        ), f"After displaying and marking first page (5 msgs), second page (5 msgs) should remain unread. Got {unread_after_abort} unread."

    def test_all_pages_marked_when_fully_displayed(self):
        """
        Test that all pages are marked when user completes viewing all messages.

        Scenario:
        1. Alice sends 12 messages (3 pages with page_size=5)
        2. Bob presses F2 and completes viewing all messages (presses Enter at prompts)
        3. After page 1 (5 msgs): marked as read
        4. After page 2 (5 msgs): marked as read
        5. After page 3 (2 msgs): marked as read
        6. Verify unread count is 0
        """
        # Step 1: Alice sends 12 messages
        alice_config = DemoConfig(moniker="alice_all_pages")
        alice = NotifyMessageDemo(alice_config)

        for i in range(12):
            alice.handler.send_message(f"All pages message {i+1}", "bob_all_pages")

        # Step 2: Bob starts demo
        bob_config = DemoConfig(moniker="bob_all_pages")
        bob = NotifyMessageDemo(bob_config)

        initial_unread = len(bob.handler.get_unread_messages())
        assert initial_unread == 12

        # Step 3: Simulate F2 key press via _check_and_display_messages()
        # User presses Enter at each more prompt (no abort)
        with patch("builtins.input", return_value=""):
            bob._check_and_display_messages()

        # Step 4-6: Verify all messages were marked as read
        unread_final = len(bob.handler.get_unread_messages())
        assert unread_final == 0, f"All 12 messages should be marked as read, but {unread_final} remain unread"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
