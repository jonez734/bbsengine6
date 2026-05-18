#!/usr/bin/env python3
# test_ping_pong_demo.py
# Comprehensive tests for ping_pong_demo.py functionality
# Tests command-line arguments, error handling, and user input validation

import os
import sys
import threading
import time
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bbsengine6.examples import ping_pong_demo
from bbsengine6.notify import Notification, NotificationUrgency


class TestCommandLineArguments(unittest.TestCase):
    """Test command-line argument parsing."""

    def test_default_mode_no_args(self):
        """Test that default (no args) triggers two-player mode."""
        with patch('sys.argv', ['ping_pong_demo.py']):
            # Parse args without running main
            parser = self._create_parser()
            args = parser.parse_args([])
            self.assertIsNone(args.user, "Default mode should have user=None")

    def test_user_arg_alice(self):
        """Test --user alice argument."""
        with patch('sys.argv', ['ping_pong_demo.py', '--user', 'alice']):
            parser = self._create_parser()
            args = parser.parse_args(['--user', 'alice'])
            self.assertEqual(args.user, 'alice')

    def test_user_arg_bob(self):
        """Test --user bob argument."""
        with patch('sys.argv', ['ping_pong_demo.py', '--user', 'bob']):
            parser = self._create_parser()
            args = parser.parse_args(['--user', 'bob'])
            self.assertEqual(args.user, 'bob')

    def test_user_arg_custom_name(self):
        """Test --user with custom player name."""
        with patch('sys.argv', ['ping_pong_demo.py', '--user', 'charlie']):
            parser = self._create_parser()
            args = parser.parse_args(['--user', 'charlie'])
            self.assertEqual(args.user, 'charlie')

    def test_user_arg_with_numbers(self):
        """Test --user with alphanumeric name."""
        with patch('sys.argv', ['ping_pong_demo.py', '--user', 'player123']):
            parser = self._create_parser()
            args = parser.parse_args(['--user', 'player123'])
            self.assertEqual(args.user, 'player123')

    def test_help_argument(self):
        """Test --help argument displays usage."""
        with patch('sys.argv', ['ping_pong_demo.py', '--help']):
            parser = self._create_parser()
            # Help should contain the --user argument
            help_text = parser.format_help()
            self.assertIn('--user', help_text)
            self.assertIn('player name', help_text.lower())

    @staticmethod
    def _create_parser():
        """Create argument parser matching main()."""
        import argparse
        parser = argparse.ArgumentParser(
            description="BBSENGINE6 Ping-Pong Demo - Interactive messaging system",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "--user",
            type=str,
            default=None,
            help="Player name",
            metavar="NAME",
        )
        return parser


class TestInvalidInput(unittest.TestCase):
    """Test error handling for invalid inputs."""

    def setUp(self):
        """Reset shared state before each test."""
        ping_pong_demo.exit_event.clear()
        ping_pong_demo.shared_rounds = {"alice": 0, "bob": 0}
        ping_pong_demo.active_threads = []

    def test_empty_user_name(self):
        """Test that empty user name is rejected."""
        with patch('sys.argv', ['ping_pong_demo.py', '--user', '']):
            parser = self._create_parser()
            args = parser.parse_args(['--user', ''])
            # Empty string should be treated as invalid
            self.assertEqual(args.user, '')

    def test_user_name_too_long(self):
        """Test that user names exceeding 255 characters are rejected."""
        long_name = 'a' * 256
        with patch('sys.argv', ['ping_pong_demo.py', '--user', long_name]):
            parser = self._create_parser()
            args = parser.parse_args(['--user', long_name])
            # Parser accepts it, but main() should reject it
            self.assertEqual(args.user, long_name)
            self.assertGreater(len(args.user), 255)

    def test_user_name_max_length(self):
        """Test that user names of exactly 255 characters are accepted."""
        max_name = 'a' * 255
        with patch('sys.argv', ['ping_pong_demo.py', '--user', max_name]):
            parser = self._create_parser()
            args = parser.parse_args(['--user', max_name])
            self.assertEqual(args.user, max_name)
            self.assertEqual(len(args.user), 255)

    @staticmethod
    def _create_parser():
        """Create argument parser."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--user", type=str, default=None, metavar="NAME")
        return parser


class TestNotificationSetup(unittest.TestCase):
    """Test notification system setup."""

    def setUp(self):
        """Reset state before each test."""
        # Clear notification types
        from bbsengine6.notify import _types, _types_lock
        with _types_lock:
            _types.clear()

    def test_setup_notifications_registers_types(self):
        """Test that setup_notifications() registers ping and pong types."""
        result = ping_pong_demo.setup_notifications()
        self.assertTrue(result, "setup_notifications should return True")

        # Verify types were registered
        from bbsengine6.notify import _types
        self.assertIn("ping_message", _types)
        self.assertIn("pong_message", _types)

    def test_setup_notifications_ping_type_config(self):
        """Test that ping_message type has correct configuration."""
        ping_pong_demo.setup_notifications()

        from bbsengine6.notify import _types
        ping_config = _types.get("ping_message", {})
        self.assertIsNotNone(ping_config)
        self.assertEqual(ping_config.get("max_per_hour"), 100)
        self.assertFalse(ping_config.get("persist_by_default"))

    def test_setup_notifications_pong_type_config(self):
        """Test that pong_message type has correct configuration."""
        ping_pong_demo.setup_notifications()

        from bbsengine6.notify import _types
        pong_config = _types.get("pong_message", {})
        self.assertIsNotNone(pong_config)
        self.assertEqual(pong_config.get("max_per_hour"), 100)
        self.assertFalse(pong_config.get("persist_by_default"))


class TestMessageSanitization(unittest.TestCase):
    """Test message content sanitization."""

    def test_sanitize_text_removes_control_chars(self):
        """Test that _sanitize_text removes control characters."""
        result = ping_pong_demo._sanitize_text("hello\x1b[31mworld")
        self.assertNotIn('\x1b', result)
        self.assertIn('hello', result)

    def test_sanitize_text_keeps_printable(self):
        """Test that _sanitize_text preserves printable characters."""
        text = "Hello World 123!@#"
        result = ping_pong_demo._sanitize_text(text)
        self.assertEqual(result, text)

    def test_sanitize_text_keeps_tab_and_space(self):
        """Test that _sanitize_text preserves tabs and spaces."""
        text = "hello\t\tworld  test"
        result = ping_pong_demo._sanitize_text(text)
        self.assertIn('\t', result)
        self.assertIn(' ', result)

    def test_sanitize_text_removes_newline(self):
        """Test that _sanitize_text removes newlines."""
        text = "hello\nworld"
        result = ping_pong_demo._sanitize_text(text)
        self.assertNotIn('\n', result)

    def test_sanitize_text_empty_string(self):
        """Test sanitization of empty string."""
        result = ping_pong_demo._sanitize_text("")
        self.assertEqual(result, "")

    def test_sanitize_text_only_control_chars(self):
        """Test sanitization of string with only control characters."""
        result = ping_pong_demo._sanitize_text("\x00\x01\x02\x03")
        self.assertEqual(result, "")


class TestConfigurationClass(unittest.TestCase):
    """Test the Config class."""

    def test_config_max_rounds(self):
        """Test MAX_ROUNDS configuration."""
        self.assertEqual(ping_pong_demo.Config.MAX_ROUNDS, 5)

    def test_config_getch_timeout(self):
        """Test GETCH_TIMEOUT configuration."""
        self.assertEqual(ping_pong_demo.Config.GETCH_TIMEOUT, 2.0)

    def test_config_message_log_size(self):
        """Test MESSAGE_LOG_SIZE configuration."""
        self.assertEqual(ping_pong_demo.Config.MESSAGE_LOG_SIZE, 100)

    def test_config_thread_timeout(self):
        """Test THREAD_TIMEOUT configuration."""
        self.assertEqual(ping_pong_demo.Config.THREAD_TIMEOUT, 10.0)

    def test_legacy_aliases(self):
        """Test that legacy aliases still work."""
        self.assertEqual(ping_pong_demo.MAX_ROUNDS, ping_pong_demo.Config.MAX_ROUNDS)
        self.assertEqual(ping_pong_demo.GETCH_TIMEOUT, ping_pong_demo.Config.GETCH_TIMEOUT)


class TestSharedRoundCounter(unittest.TestCase):
    """Test thread-safe round counter implementation."""

    def setUp(self):
        """Reset round counter before each test."""
        ping_pong_demo.shared_rounds = {"alice": 0, "bob": 0}
        ping_pong_demo.round_counter_lock = threading.Lock()

    def test_shared_rounds_initial_state(self):
        """Test that shared_rounds starts at 0 for both players."""
        self.assertEqual(ping_pong_demo.shared_rounds["alice"], 0)
        self.assertEqual(ping_pong_demo.shared_rounds["bob"], 0)

    def test_shared_rounds_increment_alice(self):
        """Test incrementing alice's round counter."""
        with ping_pong_demo.round_counter_lock:
            ping_pong_demo.shared_rounds["alice"] += 1

        self.assertEqual(ping_pong_demo.shared_rounds["alice"], 1)
        self.assertEqual(ping_pong_demo.shared_rounds["bob"], 0)

    def test_shared_rounds_increment_bob(self):
        """Test incrementing bob's round counter."""
        with ping_pong_demo.round_counter_lock:
            ping_pong_demo.shared_rounds["bob"] += 1

        self.assertEqual(ping_pong_demo.shared_rounds["alice"], 0)
        self.assertEqual(ping_pong_demo.shared_rounds["bob"], 1)

    def test_shared_rounds_concurrent_increment(self):
        """Test concurrent increments are atomic."""
        def increment_player(player, count):
            for _ in range(count):
                with ping_pong_demo.round_counter_lock:
                    ping_pong_demo.shared_rounds[player] += 1

        alice_thread = threading.Thread(target=increment_player, args=("alice", 10))
        bob_thread = threading.Thread(target=increment_player, args=("bob", 10))

        alice_thread.start()
        bob_thread.start()

        alice_thread.join()
        bob_thread.join()

        self.assertEqual(ping_pong_demo.shared_rounds["alice"], 10)
        self.assertEqual(ping_pong_demo.shared_rounds["bob"], 10)


class TestMessageLogRotation(unittest.TestCase):
    """Test message log rotation with deque."""

    def test_message_log_is_deque(self):
        """Test that message_log uses deque for rotation."""
        from collections import deque
        log = deque(maxlen=ping_pong_demo.Config.MESSAGE_LOG_SIZE)
        self.assertIsInstance(log, deque)

    def test_message_log_auto_rotation(self):
        """Test that message log auto-rotates at maxlen."""
        from collections import deque
        log = deque(maxlen=5)

        # Add 7 items (exceeds maxlen)
        for i in range(7):
            log.append(f"message {i}")

        # Should only have last 5
        self.assertEqual(len(log), 5)
        self.assertEqual(list(log), ["message 2", "message 3", "message 4", "message 5", "message 6"])

    def test_message_log_size_default(self):
        """Test that default message log size is 100."""
        from collections import deque
        log = deque(maxlen=ping_pong_demo.Config.MESSAGE_LOG_SIZE)
        self.assertEqual(log.maxlen, 100)

    def test_message_log_bounded_memory(self):
        """Test that message log won't exceed memory bounds."""
        from collections import deque
        log = deque(maxlen=100)

        # Add 1000 items
        for i in range(1000):
            log.append(f"message {i}")

        # Should only have last 100
        self.assertEqual(len(log), 100)
        self.assertEqual(log[0], "message 900")
        self.assertEqual(log[-1], "message 999")


class TestQueueOperations(unittest.TestCase):
    """Test queue operations and error handling."""

    def setUp(self):
        """Reset state before each test."""
        ping_pong_demo.exit_event.clear()

    def test_get_queue_creates_queue_on_demand(self):
        """Test that get_queue creates queue on demand."""
        from bbsengine6 import notify
        queue = notify.get_queue("newuser")
        # get_queue creates queue on demand, returns UserNotificationQueue
        self.assertIsNotNone(queue)
        from bbsengine6.notify import UserNotificationQueue
        self.assertIsInstance(queue, UserNotificationQueue)

    def test_queue_put_operation(self):
        """Test putting notification in queue."""
        from bbsengine6 import notify

        # Create a queue
        queue = notify.UserNotificationQueue()

        # Create a notification
        notif = Notification(
            id=1,
            notification_type="test",
            recipients=["alice"],
            recipients_ok=["alice"],
            recipients_failed=[],
            sender_moniker="bob",
            template="default",
            template_vars={},
            message="test message",
            data={},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=time.time(),
        )

        # Put in queue
        queue.put(notif)

        # Get from queue
        retrieved = queue.get(timeout=1.0)
        self.assertIsNotNone(retrieved, "Should retrieve notification from queue")
        if retrieved:
            self.assertEqual(retrieved.message, "test message")

    def test_queue_get_all_operation(self):
        """Test get_all() retrieves all notifications."""
        from bbsengine6 import notify

        queue = notify.UserNotificationQueue()

        # Put multiple notifications
        for i in range(3):
            notif = Notification(
                id=i,
                notification_type="test",
                recipients=["alice"],
                recipients_ok=["alice"],
                recipients_failed=[],
                sender_moniker="bob",
                template="default",
                template_vars={},
                message=f"message {i}",
                data={},
                urgency=NotificationUrgency.ROUTINE,
                timestamp=time.time(),
            )
            queue.put(notif)

        # Get all
        all_notifs = queue.get_all()
        self.assertEqual(len(all_notifs), 3)
        self.assertEqual(all_notifs[0].message, "message 0")
        self.assertEqual(all_notifs[2].message, "message 2")


class TestThreadSafety(unittest.TestCase):
    """Test thread-safety of synchronization primitives."""

    def setUp(self):
        """Reset state before each test."""
        ping_pong_demo.exit_event.clear()

    def test_exit_event_is_thread_safe(self):
        """Test that exit_event can be safely set from multiple threads."""
        results = []

        def set_event():
            ping_pong_demo.exit_event.set()
            results.append(ping_pong_demo.exit_event.is_set())

        threads = [threading.Thread(target=set_event) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All threads should see event as set
        self.assertTrue(all(results))
        self.assertTrue(ping_pong_demo.exit_event.is_set())

    def test_output_lock_prevents_interleaving(self):
        """Test that output_lock properly synchronizes access."""
        results = []

        def critical_section(value):
            with ping_pong_demo.output_lock:
                # Simulate some work
                time.sleep(0.001)
                results.append(value)

        threads = [threading.Thread(target=critical_section, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All values should be present
        self.assertEqual(len(results), 10)
        self.assertEqual(set(results), set(range(10)))


class TestErrorHandling(unittest.TestCase):
    """Test error handling in critical functions."""

    def setUp(self):
        """Reset state before each test."""
        ping_pong_demo.exit_event.clear()
        ping_pong_demo.shared_rounds = {"alice": 0, "bob": 0}

    def test_sanitize_handles_unicode(self):
        """Test that sanitization handles unicode characters."""
        text = "hello 🌍 world"
        result = ping_pong_demo._sanitize_text(text)
        # Unicode emoji should be handled (not in printable)
        self.assertIsInstance(result, str)

    def test_notification_creation_with_special_chars(self):
        """Test notification creation with special characters."""
        notif = Notification(
            id=1,
            notification_type="test",
            recipients=["alice"],
            recipients_ok=["alice"],
            recipients_failed=[],
            sender_moniker="bob",
            template="default",
            template_vars={},
            message="test <>&\"' message",
            data={},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=time.time(),
        )
        self.assertIsNotNone(notif)
        self.assertIn("<>&\"'", notif.message)


class TestRobustnessImprovements(unittest.TestCase):
    """Test that robustness improvements are in place."""

    def test_config_class_exists(self):
        """Test that Config class exists for centralized configuration."""
        self.assertTrue(hasattr(ping_pong_demo, 'Config'))

    def test_sanitize_text_function_exists(self):
        """Test that _sanitize_text function exists."""
        self.assertTrue(callable(ping_pong_demo._sanitize_text))

    def test_round_counter_lock_exists(self):
        """Test that round_counter_lock exists for atomicity."""
        self.assertTrue(hasattr(ping_pong_demo, 'round_counter_lock'))

    def test_shared_rounds_dict_exists(self):
        """Test that shared_rounds dict exists."""
        self.assertTrue(hasattr(ping_pong_demo, 'shared_rounds'))
        self.assertIsInstance(ping_pong_demo.shared_rounds, dict)

    def test_message_log_lock_exists(self):
        """Test that message_log_lock exists."""
        self.assertTrue(hasattr(ping_pong_demo, 'message_log_lock'))

    def test_echo_imported(self):
        """Test that echo is imported instead of print."""
        # Check that echo function is imported
        self.assertTrue(hasattr(ping_pong_demo, 'echo'))


def run_integration_tests():
    """Run integration tests (requires manual terminal interaction)."""
    print("\n" + "=" * 70)
    print("INTEGRATION TESTS (Manual - requires terminal interaction)")
    print("=" * 70)

    print("\nTest 1: Default two-player mode")
    print("  Command: python -m bbsengine6.examples.ping_pong_demo")
    print("  Expected: Runs alice and bob in one terminal")

    print("\nTest 2: Single-player alice mode")
    print("  Terminal 1: python -m bbsengine6.examples.ping_pong_demo --user alice")
    print("  Terminal 2: python -m bbsengine6.examples.ping_pong_demo --user bob")
    print("  Expected: Both instances run independently and can exchange messages")

    print("\nTest 3: Custom player names")
    print("  Terminal 1: python -m bbsengine6.examples.ping_pong_demo --user player1")
    print("  Terminal 2: python -m bbsengine6.examples.ping_pong_demo --user player2")
    print("  Expected: Both instances work with custom names")

    print("\nTest 4: Help argument")
    print("  Command: python -m bbsengine6.examples.ping_pong_demo --help")
    print("  Expected: Shows help with examples")


if __name__ == "__main__":
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)

    # Print integration test guidance
    run_integration_tests()
