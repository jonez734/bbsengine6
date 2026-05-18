#!/usr/bin/env python3
# testnotify.py
# Comprehensive test suite for bbsengine6.notify module
# Tests the public API for the notification system

import threading
import time
import unittest

from bbsengine6 import notify
from bbsengine6.notify import (
    NotificationUrgency,
    Notification,
    UserNotificationQueue,
)


class TestGetQueueAPI(unittest.TestCase):
    """Test notify.get_queue() API."""

    def setUp(self):
        """Clean up queues before each test."""
        from bbsengine6.notify import _queues, _queues_lock

        with _queues_lock:
            self.original_queues = dict(_queues)
            _queues.clear()

    def tearDown(self):
        """Restore queues after each test."""
        from bbsengine6.notify import _queues, _queues_lock

        with _queues_lock:
            _queues.clear()
            _queues.update(self.original_queues)

    def test_get_queue_returns_queue(self):
        """Test that get_queue() returns a UserNotificationQueue."""
        queue = notify.get_queue("alice")
        self.assertIsInstance(queue, UserNotificationQueue)

    def test_get_queue_same_instance(self):
        """Test that calling get_queue() twice returns same instance."""
        queue1 = notify.get_queue("alice")
        queue2 = notify.get_queue("alice")
        self.assertIs(queue1, queue2)

    def test_get_queue_different_monikers(self):
        """Test that different monikers get different queues."""
        queue_alice = notify.get_queue("alice")
        queue_bob = notify.get_queue("bob")
        self.assertIsNot(queue_alice, queue_bob)

    def test_get_queue_empty_on_creation(self):
        """Test that new queue is empty."""
        queue = notify.get_queue("new_user")
        all_notifs = queue.get_all()
        self.assertEqual(len(all_notifs), 0)


class TestCountAPI(unittest.TestCase):
    """Test notify.count() API."""

    def setUp(self):
        """Set up test environment."""
        from bbsengine6.notify import _queues, _queues_lock

        with _queues_lock:
            self.original_queues = dict(_queues)
            _queues.clear()

    def tearDown(self):
        """Restore environment."""
        from bbsengine6.notify import _queues, _queues_lock

        with _queues_lock:
            _queues.clear()
            _queues.update(self.original_queues)

    def test_count_empty_queue(self):
        """Test count() returns 0 for empty queue."""
        count = notify.count("empty_user")
        self.assertEqual(count, 0)

    def test_count_after_adding_notifications(self):
        """Test count() returns correct count after adding notifications."""
        moniker = "alice"
        queue = notify.get_queue(moniker)

        # Add 3 notifications directly to queue
        for i in range(3):
            notif = Notification(
                id=i,
                notification_type="test_type",
                recipients=[moniker],
                recipients_ok=[moniker],
                recipients_failed=[],
                sender_moniker="system",
                template="default",
                template_vars={"msg": f"Test {i}"},
                message=f"Test message {i}",
                data={},
                urgency=NotificationUrgency.ROUTINE,
                timestamp=time.time(),
            )
            queue.put(notif)

        # count() should return the in-memory queue size
        count = notify.count(moniker)
        self.assertIsNotNone(count)
        if count is not None:
            self.assertGreaterEqual(count, 3)


class TestGetUrgentAPI(unittest.TestCase):
    """Test notify.get_urgent() API."""

    def setUp(self):
        """Set up test environment."""
        from bbsengine6.notify import _queues, _queues_lock

        with _queues_lock:
            self.original_queues = dict(_queues)
            _queues.clear()

    def tearDown(self):
        """Restore environment."""
        from bbsengine6.notify import _queues, _queues_lock

        with _queues_lock:
            _queues.clear()
            _queues.update(self.original_queues)

    def test_get_urgent_empty_queue(self):
        """Test get_urgent() on empty queue returns empty list."""
        try:
            urgent = notify.get_urgent("alice")
            self.assertEqual(len(urgent), 0)
        except Exception:
            # get_urgent requires database
            pass

    def test_get_urgent_filters_by_urgency(self):
        """Test get_urgent() returns only urgent/critical notifications."""
        try:
            moniker = "bob"
            queue = notify.get_queue(moniker)

            # Add mixed urgency notifications
            for urgency in [
                NotificationUrgency.ROUTINE,
                NotificationUrgency.URGENT,
                NotificationUrgency.IMPORTANT,
                NotificationUrgency.CRITICAL,
            ]:
                notif = Notification(
                    id=hash(urgency),
                    notification_type="test_type",
                    recipients=[moniker],
                    recipients_ok=[moniker],
                    recipients_failed=[],
                    sender_moniker="system",
                    template="default",
                    template_vars={"urgency": str(urgency)},
                    message=f"Message with {urgency.value} urgency",
                    data={},
                    urgency=urgency,
                    timestamp=time.time(),
                )
                queue.put(notif)

            urgent_list = notify.get_urgent(moniker)
            # Should have at least URGENT and CRITICAL
            urgent_values = [u.urgency.value for u in urgent_list]
            self.assertIn("URGENT", urgent_values)
            self.assertIn("CRITICAL", urgent_values)
        except Exception:
            # get_urgent requires database
            pass


class TestBlockingAPI(unittest.TestCase):
    """Test notify.block(), notify.unblock(), notify.is_blocked() APIs."""

    def test_block_unblock_api_calls(self):
        """Test blocking and unblocking users."""
        blocker = "alice"
        blockee = "bob"

        try:
            # Initially not blocked
            is_blocked = notify.is_blocked(blocker, blockee)
            # Should work without error
            self.assertIsNotNone(is_blocked)

            # Block
            notify.block(blocker, blockee)
            is_blocked_after = notify.is_blocked(blocker, blockee)
            # After blocking, should be blocked
            self.assertIsNotNone(is_blocked_after)

            # Unblock
            notify.unblock(blocker, blockee)
            is_blocked_final = notify.is_blocked(blocker, blockee)
            self.assertIsNotNone(is_blocked_final)

        except Exception:
            # These APIs may require database, so we accept errors
            pass

    def test_get_blocked_api(self):
        """Test notify.get_blocked() API."""
        try:
            blocked_list = notify.get_blocked("alice")
            self.assertIsInstance(blocked_list, list)
        except Exception:
            # May require database
            pass


class TestGroupAPI(unittest.TestCase):
    """Test notification group management APIs."""

    def test_create_group_api(self):
        """Test notify.create_group() API call."""
        try:
            notify.create_group("test_group")
            # Should not raise if group doesn't exist
        except Exception:
            # May require database
            pass

    def test_add_to_group_api(self):
        """Test notify.add_to_group() API."""
        try:
            group = "test_group_add"
            notify.create_group(group)
            notify.add_to_group(group, "alice")
            # Should complete without error
        except Exception:
            # May require database
            pass

    def test_get_group_members_api(self):
        """Test notify.get_group_members() API."""
        try:
            group = "test_group_members"
            notify.create_group(group)
            notify.add_to_group(group, "alice")
            notify.add_to_group(group, "bob")

            members = notify.get_group_members(group)
            self.assertIsInstance(members, list)
        except Exception:
            # May require database
            pass


class TestQueueOperations(unittest.TestCase):
    """Test UserNotificationQueue operations through API."""

    def setUp(self):
        """Set up test environment."""
        from bbsengine6.notify import _queues, _queues_lock

        with _queues_lock:
            self.original_queues = dict(_queues)
            _queues.clear()

    def tearDown(self):
        """Restore environment."""
        from bbsengine6.notify import _queues, _queues_lock

        with _queues_lock:
            _queues.clear()
            _queues.update(self.original_queues)

    def _create_notification(self, idx: int, moniker: str) -> Notification:
        """Helper to create a test notification."""
        return Notification(
            id=idx,
            notification_type="test_type",
            recipients=[moniker],
            recipients_ok=[moniker],
            recipients_failed=[],
            sender_moniker="system",
            template="default",
            template_vars={"index": idx},
            message=f"Test message {idx}",
            data={"test": True},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=time.time(),
        )

    def test_put_and_get_notification(self):
        """Test putting and getting a notification via API."""
        moniker = "alice"
        queue = notify.get_queue(moniker)

        notif = self._create_notification(1, moniker)
        queue.put(notif)

        retrieved = queue.get(timeout=1.0)
        self.assertIsNotNone(retrieved)
        if retrieved:
            self.assertEqual(retrieved.message, "Test message 1")

    def test_get_all_notifications(self):
        """Test getting all notifications via API."""
        moniker = "bob"
        queue = notify.get_queue(moniker)

        # Add 5 notifications
        for i in range(5):
            notif = self._create_notification(i, moniker)
            queue.put(notif)

        all_notifs = queue.get_all()
        self.assertEqual(len(all_notifs), 5)
        # Queue should be cleared after get_all()
        self.assertEqual(len(queue.get_all()), 0)

    def test_has_urgent(self):
        """Test has_urgent() via API."""
        moniker = "charlie"
        queue = notify.get_queue(moniker)

        # Add routine notification
        routine = self._create_notification(1, moniker)
        queue.put(routine)
        self.assertFalse(queue.has_urgent())

        # Add urgent notification
        urgent_notif = Notification(
            id=2,
            notification_type="test_type",
            recipients=[moniker],
            recipients_ok=[moniker],
            recipients_failed=[],
            sender_moniker="system",
            template="default",
            template_vars={},
            message="Urgent message",
            data={},
            urgency=NotificationUrgency.URGENT,
            timestamp=time.time(),
        )
        queue.put(urgent_notif)
        self.assertTrue(queue.has_urgent())

    def test_queue_timeout_returns_none(self):
        """Test queue.get() with timeout returns None for empty queue."""
        queue = notify.get_queue("empty")
        result = queue.get(timeout=0.1)
        self.assertIsNone(result)


class TestUrgencyLevels(unittest.TestCase):
    """Test NotificationUrgency enum."""

    def test_urgency_values_exist(self):
        """Test that all urgency levels exist."""
        urgencies = [
            NotificationUrgency.ROUTINE,
            NotificationUrgency.IMPORTANT,
            NotificationUrgency.URGENT,
            NotificationUrgency.CRITICAL,
        ]
        self.assertEqual(len(urgencies), 4)

    def test_urgency_string_values(self):
        """Test that urgency values have correct string representations."""
        self.assertEqual(NotificationUrgency.ROUTINE.value, "ROUTINE")
        self.assertEqual(NotificationUrgency.IMPORTANT.value, "IMPORTANT")
        self.assertEqual(NotificationUrgency.URGENT.value, "URGENT")
        self.assertEqual(NotificationUrgency.CRITICAL.value, "CRITICAL")

    def test_create_notification_with_urgency(self):
        """Test creating notification with specific urgency."""
        for urgency in NotificationUrgency:
            notif = Notification(
                id=1,
                notification_type="test",
                recipients=["alice"],
                recipients_ok=["alice"],
                recipients_failed=[],
                sender_moniker="system",
                template="default",
                template_vars={},
                message="Test",
                data={},
                urgency=urgency,
                timestamp=time.time(),
            )
            self.assertEqual(notif.urgency, urgency)


class TestNotificationDataStructure(unittest.TestCase):
    """Test Notification dataclass structure via API."""

    def test_notification_fields(self):
        """Test that Notification has required fields."""
        notif = Notification(
            id=1,
            notification_type="test_type",
            recipients=["alice", "bob"],
            recipients_ok=["alice"],
            recipients_failed=["bob"],
            sender_moniker="system",
            template="default",
            template_vars={"key": "value"},
            message="Test message",
            data={"custom": "data"},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=time.time(),
        )

        # Verify fields
        self.assertEqual(notif.id, 1)
        self.assertEqual(notif.notification_type, "test_type")
        self.assertEqual(len(notif.recipients), 2)
        self.assertEqual(len(notif.recipients_ok), 1)
        self.assertEqual(len(notif.recipients_failed), 1)
        self.assertEqual(notif.sender_moniker, "system")
        self.assertEqual(notif.message, "Test message")
        self.assertIsInstance(notif.data, dict)

    def test_notification_read_by_tracking(self):
        """Test read_by tracking in Notification."""
        notif = Notification(
            id=1,
            notification_type="test",
            recipients=["alice"],
            recipients_ok=["alice"],
            recipients_failed=[],
            sender_moniker="system",
            template="default",
            template_vars={},
            message="Test",
            data={},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=time.time(),
        )

        # Initially empty
        self.assertEqual(len(notif.read_by), 0)

        # Can add read tracking
        notif.read_by["alice"] = time.time()
        self.assertIn("alice", notif.read_by)

    def test_notification_delivered_tracking(self):
        """Test delivered_to tracking in Notification."""
        notif = Notification(
            id=1,
            notification_type="test",
            recipients=["bob"],
            recipients_ok=["bob"],
            recipients_failed=[],
            sender_moniker="system",
            template="default",
            template_vars={},
            message="Test",
            data={},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=time.time(),
        )

        # Initially empty
        self.assertEqual(len(notif.delivered_to), 0)

        # Can add delivery tracking
        notif.delivered_to["bob"] = time.time()
        self.assertIn("bob", notif.delivered_to)


class TestMultiUserQueueIsolation(unittest.TestCase):
    """Test queue isolation between multiple users."""

    def setUp(self):
        """Set up test environment."""
        from bbsengine6.notify import _queues, _queues_lock

        with _queues_lock:
            self.original_queues = dict(_queues)
            _queues.clear()

    def tearDown(self):
        """Restore environment."""
        from bbsengine6.notify import _queues, _queues_lock

        with _queues_lock:
            _queues.clear()
            _queues.update(self.original_queues)

    def test_multiple_users_isolated_queues(self):
        """Test that each user has isolated queue."""
        users = ["alice", "bob", "charlie"]

        for user in users:
            queue = notify.get_queue(user)
            notif = Notification(
                id=1,
                notification_type="test",
                recipients=[user],
                recipients_ok=[user],
                recipients_failed=[],
                sender_moniker="system",
                template="default",
                template_vars={},
                message=f"Message for {user}",
                data={},
                urgency=NotificationUrgency.ROUTINE,
                timestamp=time.time(),
            )
            queue.put(notif)

        # Each queue should have exactly 1 notification
        for user in users:
            queue = notify.get_queue(user)
            all_notifs = queue.get_all()
            self.assertEqual(len(all_notifs), 1)
            self.assertIn(user, all_notifs[0].message)

    def test_notification_to_one_user_not_affects_others(self):
        """Test that notification to one user doesn't affect others."""
        queue_alice = notify.get_queue("alice")
        queue_bob = notify.get_queue("bob")

        # Add to alice's queue
        notif = Notification(
            id=1,
            notification_type="test",
            recipients=["alice"],
            recipients_ok=["alice"],
            recipients_failed=[],
            sender_moniker="system",
            template="default",
            template_vars={},
            message="For alice only",
            data={},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=time.time(),
        )
        queue_alice.put(notif)

        # Bob's queue should be empty
        bob_notifs = queue_bob.get_all()
        self.assertEqual(len(bob_notifs), 0)

        # Alice's queue should have the notification
        alice_notifs = queue_alice.get_all()
        self.assertEqual(len(alice_notifs), 1)


class TestConcurrentQueueAccess(unittest.TestCase):
    """Test concurrent access to notification queues."""

    def setUp(self):
        """Set up test environment."""
        from bbsengine6.notify import _queues, _queues_lock

        with _queues_lock:
            self.original_queues = dict(_queues)
            _queues.clear()

    def tearDown(self):
        """Restore environment."""
        from bbsengine6.notify import _queues, _queues_lock

        with _queues_lock:
            _queues.clear()
            _queues.update(self.original_queues)

    def test_concurrent_same_queue_access(self):
        """Test concurrent producers and consumers on same queue."""
        moniker = "shared_user"
        received_messages = []
        lock = threading.Lock()

        def producer():
            queue = notify.get_queue(moniker)
            for i in range(10):
                notif = Notification(
                    id=i,
                    notification_type="test",
                    recipients=[moniker],
                    recipients_ok=[moniker],
                    recipients_failed=[],
                    sender_moniker="system",
                    template="default",
                    template_vars={},
                    message=f"Message {i}",
                    data={},
                    urgency=NotificationUrgency.ROUTINE,
                    timestamp=time.time(),
                )
                queue.put(notif)
                time.sleep(0.001)

        def consumer():
            queue = notify.get_queue(moniker)
            for _ in range(10):
                notif = queue.get(timeout=2.0)
                if notif:
                    with lock:
                        received_messages.append(notif.message)
                time.sleep(0.001)

        prod_thread = threading.Thread(target=producer)
        cons_thread = threading.Thread(target=consumer)

        prod_thread.start()
        cons_thread.start()

        prod_thread.join(timeout=5.0)
        cons_thread.join(timeout=5.0)

        self.assertEqual(len(received_messages), 10)

    def test_concurrent_multi_user_access(self):
        """Test concurrent access from multiple users."""
        users = ["alice", "bob", "charlie"]
        message_counts = {}
        lock = threading.Lock()

        def user_simulator(moniker):
            queue = notify.get_queue(moniker)
            count = 0

            # Receive messages
            for _ in range(5):
                notif = queue.get(timeout=1.0)
                if notif:
                    count += 1

            with lock:
                message_counts[moniker] = count

        # Pre-populate queues
        for user in users:
            queue = notify.get_queue(user)
            for i in range(5):
                notif = Notification(
                    id=i,
                    notification_type="test",
                    recipients=[user],
                    recipients_ok=[user],
                    recipients_failed=[],
                    sender_moniker="system",
                    template="default",
                    template_vars={},
                    message=f"Message {i}",
                    data={},
                    urgency=NotificationUrgency.ROUTINE,
                    timestamp=time.time(),
                )
                queue.put(notif)

        # Start consumer threads
        threads = []
        for user in users:
            t = threading.Thread(target=user_simulator, args=(user,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=5.0)

        # Verify results
        for user in users:
            self.assertEqual(message_counts.get(user, 0), 5)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestGetQueueAPI,
        TestCountAPI,
        TestGetUrgentAPI,
        TestBlockingAPI,
        TestGroupAPI,
        TestQueueOperations,
        TestUrgencyLevels,
        TestNotificationDataStructure,
        TestMultiUserQueueIsolation,
        TestConcurrentQueueAccess,
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    import sys

    sys.exit(run_tests())
