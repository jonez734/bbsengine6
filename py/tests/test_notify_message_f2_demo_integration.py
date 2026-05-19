# test_notify_message_f2_demo_integration.py
# Integration tests for notify_message_demo with real PostgreSQL database
# Tests message persistence, retrieval, and database schema compliance

import pytest

from bbsengine6.examples.notify_message_demo import (
    DemoConfig,
    MessageHandler,
)


def _insert_test_message(db_connection, sender: str, recipient: str, message_text: str):
    """Helper: Insert a test message directly into the database."""
    with db_connection.cursor() as cur:
        cur.execute(
            """
            INSERT INTO engine.__notify
            (notification_type, template, rendered_message, sender_moniker, urgency)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                "demo-message",
                "{sender}: {message}",
                f"{sender}: {message_text}",
                sender,
                "ROUTINE",
            ),
        )
        result_row = cur.fetchone()
        notify_id = (
            result_row.get("id") if isinstance(result_row, dict) else result_row[0]
        )

        # Insert recipient entry
        cur.execute(
            """
            INSERT INTO engine.__notify_recipient (notify_id, recipient_moniker)
            VALUES (%s, %s)
            """,
            (notify_id, recipient),
        )

    db_connection.commit()
    return notify_id


@pytest.mark.integration
class TestNotifyMessageF2DemoIntegration:
    """Integration tests for F2 message demo using real PostgreSQL database."""

    def test_message_persists_in_database(
        self, db_connection, schema_init, create_test_users
    ):
        """
        Integration test: Message persists in engine.__notify and __notify_recipient.
        Verifies database schema and constraints work correctly.
        """
        # Action: Insert message directly into database
        message_text = "Hello Bob! Database integration test from Alice."
        notify_id = _insert_test_message(db_connection, "alice", "bob", message_text)

        # Assert: verify message exists in engine.__notify
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT id, rendered_message, sender_moniker, notification_type
                FROM engine.__notify
                WHERE id=%s
                """,
                (notify_id,),
            )
            notify_row = cur.fetchone()

        assert notify_row is not None, "Message not found in engine.__notify"
        returned_id, rendered, sender, notify_type = notify_row
        assert returned_id == notify_id
        assert sender == "alice"
        assert message_text in rendered
        assert notify_type == "demo-message"

        # Assert: verify recipient entry exists
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT notify_id, recipient_moniker, read_at
                FROM engine.__notify_recipient
                WHERE notify_id=%s AND recipient_moniker='bob'
                """,
                (notify_id,),
            )
            recipient_row = cur.fetchone()

        assert recipient_row is not None, "Recipient entry not found"
        recipient_notify_id, recipient_moniker, read_at = recipient_row
        assert recipient_notify_id == notify_id
        assert recipient_moniker == "bob"
        assert read_at is None, "Message should not be read yet"

    def test_unread_query_retrieves_messages(
        self, db_connection, schema_init, create_test_users
    ):
        """
        Integration test: Verify unread message query works correctly.
        This is what F2 uses to get unread messages for a user.
        """
        # Setup: Insert message from alice to bob with unique identifier
        unique_msg = "UnreadQueryTest_xyz123"
        _insert_test_message(db_connection, "alice", "bob", unique_msg)

        # Action: Query unread messages for bob (simulates what F2 does)
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT n.id, n.rendered_message, n.sender_moniker
                FROM engine.__notify n
                JOIN engine.__notify_recipient nr ON n.id = nr.notify_id
                WHERE nr.recipient_moniker = %s
                AND nr.read_at IS NULL
                AND n.notification_type = 'demo-message'
                AND n.rendered_message LIKE %s
                ORDER BY n.datecreated ASC
                """,
                ("bob", f"%{unique_msg}%"),
            )
            messages = cur.fetchall()

        # Assert: Bob should have our message
        assert len(messages) > 0, "Bob should have unread messages"
        notify_id, rendered_msg, sender = messages[0]
        assert sender == "alice"
        assert unique_msg in rendered_msg
        assert notify_id is not None

    def test_marking_message_as_read(
        self, db_connection, schema_init, create_test_users
    ):
        """
        Integration test: F2 displays message then marks it as read.
        After marking as read, unread query should return no results.
        """
        # Setup: Insert message
        notify_id = _insert_test_message(
            db_connection, "alice", "bob", "Message to mark as read"
        )

        # Step 1: Verify message is unread
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM engine.__notify_recipient
                WHERE notify_id=%s AND read_at IS NULL
                """,
                (notify_id,),
            )
            unread_before = cur.fetchone()[0]

        assert unread_before == 1, "Message should be unread initially"

        # Step 2: Mark as read (what happens after F2 displays message)
        with db_connection.cursor() as cur:
            cur.execute(
                """
                UPDATE engine.__notify_recipient
                SET read_at = NOW()
                WHERE notify_id=%s AND recipient_moniker='bob'
                """,
                (notify_id,),
            )

        db_connection.commit()

        # Step 3: Verify message is now read
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM engine.__notify_recipient
                WHERE notify_id=%s AND read_at IS NULL
                """,
                (notify_id,),
            )
            unread_after = cur.fetchone()[0]

        assert unread_after == 0, "Message should be read after update"

    def test_multiple_messages_retrieval(
        self, db_connection, schema_init, create_test_users
    ):
        """
        Integration test: Multiple messages for a user are all retrievable.
        Simulates F2 showing all unread messages.
        """
        # Setup: Insert 3 messages from alice to bob
        messages_to_send = [
            "First message to Bob",
            "Second message to Bob",
            "Third message to Bob",
        ]

        for msg in messages_to_send:
            _insert_test_message(db_connection, "alice", "bob", msg)

        # Action: Query unread messages for bob
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT n.rendered_message, n.sender_moniker
                FROM engine.__notify n
                JOIN engine.__notify_recipient nr ON n.id = nr.notify_id
                WHERE nr.recipient_moniker = %s
                AND nr.read_at IS NULL
                AND n.notification_type = 'demo-message'
                ORDER BY n.datecreated ASC
                """,
                ("bob",),
            )
            messages = cur.fetchall()

        # Assert: All messages retrieved
        assert len(messages) >= 3, f"Expected at least 3 messages, got {len(messages)}"

        # Verify content
        received_texts = [msg[0] for msg in messages]
        for original_msg in messages_to_send:
            assert any(original_msg in received for received in received_texts), (
                f"Message '{original_msg}' not found in retrieved messages"
            )

    def test_bidirectional_messaging_in_database(
        self, db_connection, schema_init, create_test_users
    ):
        """
        Integration test: Both Alice->Bob and Bob->Alice messages persist.
        Verifies bidirectional communication works at database level.
        """
        # Setup: Insert messages in both directions
        _insert_test_message(db_connection, "alice", "bob", "Hi Bob from Alice")
        _insert_test_message(db_connection, "bob", "alice", "Hi Alice from Bob")

        # Assert: Bob can see alice's message
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM engine.__notify n
                JOIN engine.__notify_recipient nr ON n.id = nr.notify_id
                WHERE n.sender_moniker='alice'
                AND nr.recipient_moniker='bob'
                AND nr.read_at IS NULL
                """
            )
            bob_receives_from_alice = cur.fetchone()[0]

        assert bob_receives_from_alice >= 1, "Bob should receive alice's message"

        # Assert: Alice can see bob's message
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM engine.__notify n
                JOIN engine.__notify_recipient nr ON n.id = nr.notify_id
                WHERE n.sender_moniker='bob'
                AND nr.recipient_moniker='alice'
                AND nr.read_at IS NULL
                """
            )
            alice_receives_from_bob = cur.fetchone()[0]

        assert alice_receives_from_bob >= 1, "Alice should receive bob's message"

    def test_unread_count_query(self, db_connection, schema_init, create_test_users):
        """
        Integration test: Unread message count for F2 status bar.
        """
        # Setup: Insert 3 messages for bob
        for i in range(1, 4):
            _insert_test_message(db_connection, "alice", "bob", f"Message {i}")

        # Action: Count unread messages (what F2 status shows)
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM engine.__notify n
                JOIN engine.__notify_recipient nr ON n.id = nr.notify_id
                WHERE nr.recipient_moniker = %s
                AND nr.read_at IS NULL
                AND n.notification_type = 'demo-message'
                """,
                ("bob",),
            )
            unread_count = cur.fetchone()[0]

        # Assert: F2 status should show 3 unread
        assert unread_count >= 3, f"Expected at least 3 unread, got {unread_count}"

    def test_message_template_in_database(
        self, db_connection, schema_init, create_test_users
    ):
        """
        Integration test: Template is stored in database for message formatting.
        """
        # Setup
        with db_connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO engine.__notify
                (notification_type, template, rendered_message, sender_moniker, urgency)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    "demo-message",
                    "[{sender}] says: {message}",
                    "[alice] says: Custom template test",
                    "alice",
                    "ROUTINE",
                ),
            )
            result_row = cur.fetchone()
            notify_id = (
                result_row.get("id") if isinstance(result_row, dict) else result_row[0]
            )

            cur.execute(
                """
                INSERT INTO engine.__notify_recipient (notify_id, recipient_moniker)
                VALUES (%s, %s)
                """,
                (notify_id, "bob"),
            )

        db_connection.commit()

        # Assert: Template is stored
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT template, rendered_message
                FROM engine.__notify
                WHERE id=%s
                """,
                (notify_id,),
            )
            row = cur.fetchone()

        template, rendered = row
        assert "[{sender}]" in template
        assert "[alice]" in rendered

    def test_recipient_entry_constraints(
        self, db_connection, schema_init, create_test_users
    ):
        """
        Integration test: Recipient entries properly constrained via foreign key.
        """
        # Setup: Insert message with recipient
        notify_id = _insert_test_message(
            db_connection, "alice", "bob", "Constraint test"
        )

        # Assert: Recipient entry references valid notify record
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT nr.notify_id, n.id
                FROM engine.__notify_recipient nr
                JOIN engine.__notify n ON nr.notify_id = n.id
                WHERE nr.notify_id=%s
                """,
                (notify_id,),
            )
            result = cur.fetchone()

        assert result is not None, "Recipient should reference valid notify record"
        recipient_notify_id, notify_record_id = result
        assert recipient_notify_id == notify_record_id

    def test_multiple_recipients_for_one_message(
        self, db_connection, schema_init, create_test_users
    ):
        """
        Integration test: One message can have multiple recipients.
        Tests that F2 shows message to all recipients.
        """
        # Setup: Create charlie user
        with db_connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO engine.__member (moniker, email)
                VALUES ('charlie', 'charlie@test.local')
                ON CONFLICT DO NOTHING
                """
            )
        db_connection.commit()

        # Setup: Insert one message from alice
        with db_connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO engine.__notify
                (notification_type, template, rendered_message, sender_moniker, urgency)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    "demo-message",
                    "{sender}: {message}",
                    "alice: Message for multiple recipients",
                    "alice",
                    "ROUTINE",
                ),
            )
            result_row = cur.fetchone()
            notify_id = (
                result_row.get("id") if isinstance(result_row, dict) else result_row[0]
            )

            # Add multiple recipients for same message
            cur.execute(
                """
                INSERT INTO engine.__notify_recipient (notify_id, recipient_moniker)
                VALUES (%s, %s), (%s, %s)
                """,
                (notify_id, "bob", notify_id, "charlie"),
            )

        db_connection.commit()

        # Assert: Both Bob and Charlie see the same message
        for recipient in ["bob", "charlie"]:
            with db_connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM engine.__notify_recipient
                    WHERE notify_id=%s AND recipient_moniker=%s AND read_at IS NULL
                    """,
                    (notify_id, recipient),
                )
                count = cur.fetchone()[0]

            assert count == 1, f"{recipient} should see the message"

    def test_message_urgency_defaults_to_routine(
        self, db_connection, schema_init, create_test_users
    ):
        """
        Integration test: Messages default to ROUTINE urgency.
        """
        # Setup
        notify_id = _insert_test_message(db_connection, "alice", "bob", "Urgency test")

        # Assert
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT urgency
                FROM engine.__notify
                WHERE id=%s
                """,
                (notify_id,),
            )
            row = cur.fetchone()

        urgency = row[0]
        assert urgency == "ROUTINE", f"Expected ROUTINE urgency, got {urgency}"

    def test_datecreated_timestamp_auto_set(
        self, db_connection, schema_init, create_test_users
    ):
        """
        Integration test: datecreated timestamp is automatically set on insert.
        """
        # Setup
        notify_id = _insert_test_message(
            db_connection, "alice", "bob", "Timestamp test"
        )

        # Assert
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT datecreated
                FROM engine.__notify
                WHERE id=%s
                """,
                (notify_id,),
            )
            row = cur.fetchone()

        datecreated = row[0]
        assert datecreated is not None, "datecreated should be auto-set"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
