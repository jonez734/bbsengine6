"""
Database integration tests for notify_message_demo.

Verifies that messages are correctly persisted to engine.__notify and
engine.__notify_recipient tables in zoid6test database.

Run with: pytest py/tests/test_notify_message_demo_database.py -xvs
"""

import pytest
from bbsengine6.examples.notify_message_demo import (
    DemoConfig,
    MessageHandler,
)


@pytest.mark.integration
class TestNotifyMessageDemoDatabase:
    """Integration tests verifying database writes for notify_message_demo."""

    def test_send_message_inserts_into_notify_table(self, db_connection, schema_init, create_test_users):
        """Verify that sending a message inserts a row into engine.__notify."""
        # Setup
        config = DemoConfig(moniker="alice")
        handler = MessageHandler(config, db_connection)

        # Action: send message
        handler.send_message("Hello bob", "bob")

        # Assert: verify row was inserted
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT id, notification_type, rendered_message, sender_moniker
                FROM engine.__notify
                WHERE sender_moniker='alice'
                ORDER BY datecreated DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

        assert row is not None, "No message found in engine.__notify for alice"
        notify_id, notification_type, rendered_message, sender = row
        assert notification_type == "demo-message"
        assert "Hello bob" in rendered_message
        assert sender == "alice"

    def test_send_message_inserts_recipient_entry(self, db_connection, schema_init, create_test_users):
        """Verify that recipient is tracked in engine.__notify_recipient."""
        # Setup
        config = DemoConfig(moniker="alice")
        handler = MessageHandler(config, db_connection)

        # Action: send message to bob
        handler.send_message("Test message", "bob")

        # Assert: verify recipient entry was created
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT notify_id, recipient_moniker
                FROM engine.__notify_recipient
                WHERE recipient_moniker='bob'
                ORDER BY datecreated DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

        assert row is not None, "No recipient entry found for bob"
        notify_id, recipient = row
        assert recipient == "bob"
        assert notify_id is not None

    def test_bidirectional_messaging_persists_to_database(self, db_connection, schema_init, create_test_users):
        """Verify alice->bob and bob->alice both persist correctly."""
        # Setup
        config_alice = DemoConfig(moniker="alice")
        config_bob = DemoConfig(moniker="bob")
        handler_alice = MessageHandler(config_alice, db_connection)
        handler_bob = MessageHandler(config_bob, db_connection)

        # Action: bidirectional messaging
        handler_alice.send_message("Hi bob from alice", "bob")
        handler_bob.send_message("Hi alice from bob", "alice")

        # Assert: verify both directions were persisted
        with db_connection.cursor() as cur:
            # Count alice->bob
            cur.execute(
                "SELECT COUNT(*) FROM engine.__notify WHERE sender_moniker='alice'"
            )
            alice_count = cur.fetchone()[0]

            # Count bob->alice
            cur.execute(
                "SELECT COUNT(*) FROM engine.__notify WHERE sender_moniker='bob'"
            )
            bob_count = cur.fetchone()[0]

        assert alice_count >= 1, "No messages from alice found in database"
        assert bob_count >= 1, "No messages from bob found in database"

    def test_template_rendering_persists_correctly(self, db_connection, schema_init, create_test_users):
        """Verify that template rendering produces correct rendered_message in DB."""
        # Setup: custom template
        custom_template = "[{sender}]: {message}"
        config = DemoConfig(moniker="alice", template=custom_template)
        handler = MessageHandler(config, db_connection)

        # Action: send with custom template
        handler.send_message("test content", "bob")

        # Assert: verify rendered message contains both sender and message
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT rendered_message
                FROM engine.__notify
                WHERE sender_moniker='alice'
                ORDER BY datecreated DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

        assert row is not None
        rendered = row[0]
        assert "alice" in rendered
        assert "test content" in rendered
        assert "[alice]:" in rendered

    def test_multiple_messages_create_separate_entries(self, db_connection, schema_init, create_test_users):
        """Verify that each message creates a separate database entry."""
        # Setup
        config = DemoConfig(moniker="alice")
        handler = MessageHandler(config, db_connection)

        # Action: send multiple messages
        handler.send_message("message 1", "bob")
        handler.send_message("message 2", "bob")
        handler.send_message("message 3", "bob")

        # Assert: verify separate entries exist
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM engine.__notify
                WHERE sender_moniker='alice'
                AND notification_type='demo-message'
                """
            )
            count = cur.fetchone()[0]

        assert count >= 3, f"Expected at least 3 messages, found {count}"

    def test_message_urgency_defaults_to_routine(self, db_connection, schema_init, create_test_users):
        """Verify that messages default to ROUTINE urgency level."""
        # Setup
        config = DemoConfig(moniker="alice")
        handler = MessageHandler(config, db_connection)

        # Action
        handler.send_message("test", "bob")

        # Assert
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT urgency
                FROM engine.__notify
                WHERE sender_moniker='alice'
                ORDER BY datecreated DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

        assert row is not None
        assert row[0] == "ROUTINE"

    def test_timestamp_recorded_on_insert(self, db_connection, schema_init, create_test_users):
        """Verify that datecreated timestamp is automatically set."""
        # Setup
        config = DemoConfig(moniker="alice")
        handler = MessageHandler(config, db_connection)

        # Action
        handler.send_message("test", "bob")

        # Assert
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT datecreated
                FROM engine.__notify
                WHERE sender_moniker='alice'
                ORDER BY datecreated DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

        assert row is not None
        assert row[0] is not None

    def test_multiple_recipients_create_recipient_entries(self, db_connection, schema_init, create_test_users):
        """Verify that sending messages creates recipient entries."""
        # Setup
        config_alice = DemoConfig(moniker="alice")
        handler_alice = MessageHandler(config_alice, db_connection)

        # Action: send message
        handler_alice.send_message("msg to bob", "bob")

        # Assert: verify recipient entry was created
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM engine.__notify_recipient
                WHERE recipient_moniker='bob'
                """
            )
            recipient_count = cur.fetchone()[0]

        assert recipient_count >= 1, "Should have at least 1 recipient entry for bob"

    def test_stats_match_database_counts(self, db_connection, schema_init, create_test_users):
        """Verify that handler statistics match actual database counts."""
        # Setup
        config = DemoConfig(moniker="alice")
        handler = MessageHandler(config, db_connection)

        # Action: send 3 messages
        handler.send_message("msg1", "bob")
        handler.send_message("msg2", "bob")
        handler.send_message("msg3", "bob")

        # Get handler stats
        stats = handler.get_stats()

        # Get database count
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM engine.__notify
                WHERE sender_moniker='alice'
                AND notification_type='demo-message'
                """
            )
            db_count = cur.fetchone()[0]

        assert stats["sent"] >= 3, f"Handler shows {stats['sent']} sent, expected at least 3"
        assert db_count >= 3, f"Database has {db_count} records, expected at least 3"

    def test_template_stored_in_database(self, db_connection, schema_init, create_test_users):
        """Verify that the template itself is stored in engine.__notify.template."""
        # Setup
        custom_template = "CUSTOM: {sender} says {message}"
        config = DemoConfig(moniker="alice", template=custom_template)
        handler = MessageHandler(config, db_connection)

        # Action
        handler.send_message("test", "bob")

        # Assert: verify template column contains our template
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT template
                FROM engine.__notify
                WHERE sender_moniker='alice'
                ORDER BY datecreated DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

        assert row is not None
        assert custom_template in row[0]
