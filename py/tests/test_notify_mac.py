# test_notify_mac.py
# Tests for bbsengine6.notify tamper-proof message authentication (HMAC).

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.notify import (
    NotificationTamperError,
    NotificationUrgency,
    get_notifications,
    register_type,
    send,
)
from bbsengine6.notify.lib import (
    NotificationTamperError as LibTamperError,
    _compute_notify_mac,
    _get_mac_key,
    _notify_mac_column_probe,
)


# =============================================================================
# Unit tests — _get_mac_key
# =============================================================================


class TestGetMacKey:
    def test_get_mac_key_no_env(self):
        with patch.dict(os.environ, {}, clear=True):
            import bbsengine6.notify.lib as lib

            lib._mac_key_cache = None
            key = _get_mac_key()
            assert key is None

    def test_get_mac_key_empty_env(self, monkeypatch):
        monkeypatch.setenv("BBSENGINE6_NOTIFY_MAC_KEY", "")
        import bbsengine6.notify.lib as lib

        lib._mac_key_cache = None
        key = _get_mac_key()
        assert key is None

    def test_get_mac_key_with_value(self, monkeypatch):
        monkeypatch.setenv("BBSENGINE6_NOTIFY_MAC_KEY", "my-secret-key")
        import bbsengine6.notify.lib as lib

        lib._mac_key_cache = None
        key = _get_mac_key()
        assert key == b"my-secret-key"

    def test_get_mac_key_cached(self, monkeypatch):
        monkeypatch.setenv("BBSENGINE6_NOTIFY_MAC_KEY", "cached-key")
        import bbsengine6.notify.lib as lib

        lib._mac_key_cache = b"already-cached"
        key = _get_mac_key()
        assert key == b"already-cached"


# =============================================================================
# Unit tests — _compute_notify_mac
# =============================================================================


class TestComputeNotifyMac:
    def test_no_key_returns_none(self, monkeypatch):
        monkeypatch.setenv("BBSENGINE6_NOTIFY_MAC_KEY", "")
        import bbsengine6.notify.lib as lib

        lib._mac_key_cache = None
        mac = _compute_notify_mac(
            "test_type",
            "sender",
            "template",
            {},
            "message",
            {},
            NotificationUrgency.ROUTINE,
        )
        assert mac is None

    def test_with_key_returns_64_char_hex(self, monkeypatch):
        monkeypatch.setenv("BBSENGINE6_NOTIFY_MAC_KEY", "test-key")
        import bbsengine6.notify.lib as lib

        lib._mac_key_cache = None
        mac = _compute_notify_mac(
            "test_type",
            "sender",
            "template",
            {},
            "message",
            {},
            NotificationUrgency.ROUTINE,
        )
        assert mac is not None
        assert len(mac) == 64
        assert all(c in "0123456789abcdef" for c in mac)

    def test_deterministic_same_inputs(self, monkeypatch):
        monkeypatch.setenv("BBSENGINE6_NOTIFY_MAC_KEY", "test-key")
        import bbsengine6.notify.lib as lib

        lib._mac_key_cache = None
        mac1 = _compute_notify_mac(
            "type",
            "sender",
            "tpl",
            {"a": 1},
            "msg",
            {"b": 2},
            NotificationUrgency.URGENT,
        )
        mac2 = _compute_notify_mac(
            "type",
            "sender",
            "tpl",
            {"a": 1},
            "msg",
            {"b": 2},
            NotificationUrgency.URGENT,
        )
        assert mac1 == mac2

    def test_different_inputs_different_mac(self, monkeypatch):
        monkeypatch.setenv("BBSENGINE6_NOTIFY_MAC_KEY", "test-key")
        import bbsengine6.notify.lib as lib

        lib._mac_key_cache = None
        mac1 = _compute_notify_mac(
            "type1", "sender", "tpl", {}, "msg", {}, NotificationUrgency.ROUTINE
        )
        mac2 = _compute_notify_mac(
            "type2", "sender", "tpl", {}, "msg", {}, NotificationUrgency.ROUTINE
        )
        assert mac1 != mac2

    def test_sender_none_handled(self, monkeypatch):
        monkeypatch.setenv("BBSENGINE6_NOTIFY_MAC_KEY", "test-key")
        import bbsengine6.notify.lib as lib

        lib._mac_key_cache = None
        mac = _compute_notify_mac(
            "type", None, "tpl", {}, "msg", {}, NotificationUrgency.ROUTINE
        )
        assert mac is not None
        assert len(mac) == 64

    def test_complex_template_vars(self, monkeypatch):
        monkeypatch.setenv("BBSENGINE6_NOTIFY_MAC_KEY", "test-key")
        import bbsengine6.notify.lib as lib

        lib._mac_key_cache = None
        mac = _compute_notify_mac(
            "type",
            "sender",
            "tpl {name}",
            {"name": "Alice", "score": 42, "items": ["a", "b"]},
            "rendered",
            {"extra": {"nested": True}},
            NotificationUrgency.CRITICAL,
        )
        assert mac is not None
        assert len(mac) == 64

    def test_json_sort_keys_deterministic(self, monkeypatch):
        monkeypatch.setenv("BBSENGINE6_NOTIFY_MAC_KEY", "test-key")
        import bbsengine6.notify.lib as lib

        lib._mac_key_cache = None
        mac1 = _compute_notify_mac(
            "type",
            "sender",
            "tpl",
            {"z": 1, "a": 2},
            "msg",
            {},
            NotificationUrgency.ROUTINE,
        )
        mac2 = _compute_notify_mac(
            "type",
            "sender",
            "tpl",
            {"a": 2, "z": 1},
            "msg",
            {},
            NotificationUrgency.ROUTINE,
        )
        assert mac1 == mac2


# =============================================================================
# Unit tests — _notify_mac_column_probe
# =============================================================================


class TestNotifyMacColumnProbe:
    def test_probe_has_column(self):
        import bbsengine6.notify.lib as lib

        lib._notify_mac_column_exists = None
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {"exists": 1}
        result = _notify_mac_column_probe(mock_cur)
        assert result is True
        assert lib._notify_mac_column_exists is True

    def test_probe_no_column(self):
        import bbsengine6.notify.lib as lib

        lib._notify_mac_column_exists = None
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        result = _notify_mac_column_probe(mock_cur)
        assert result is False
        assert lib._notify_mac_column_exists is False

    def test_probe_exception(self):
        import bbsengine6.notify.lib as lib

        lib._notify_mac_column_exists = None
        mock_cur = MagicMock()
        mock_cur.execute.side_effect = RuntimeError("connection error")
        result = _notify_mac_column_probe(mock_cur)
        assert result is False
        assert lib._notify_mac_column_exists is False

    def test_probe_cached_true(self):
        import bbsengine6.notify.lib as lib

        lib._notify_mac_column_exists = True
        mock_cur = MagicMock()
        result = _notify_mac_column_probe(mock_cur)
        assert result is True
        mock_cur.execute.assert_not_called()

    def test_probe_cached_false(self):
        import bbsengine6.notify.lib as lib

        lib._notify_mac_column_exists = False
        mock_cur = MagicMock()
        result = _notify_mac_column_probe(mock_cur)
        assert result is False
        mock_cur.execute.assert_not_called()


# =============================================================================
# Unit tests — NotificationTamperError
# =============================================================================


class TestNotificationTamperError:
    def test_is_value_error(self):
        err = LibTamperError("test message")
        assert isinstance(err, ValueError)

    def test_raised_and_caught(self):
        with pytest.raises(NotificationTamperError, match="tampered"):
            raise NotificationTamperError("tampered message")

    def test_raised_from_module(self):
        with pytest.raises(NotificationTamperError):
            raise NotificationTamperError(
                "HMAC verification failed: content has been tampered with"
            )


# =============================================================================
# Unit tests — get_notifications with MAC verification
# =============================================================================


class TestGetNotificationsMacVerification:
    def test_valid_mac_passes_verification(self, monkeypatch):
        import bbsengine6.notify.lib as lib

        lib._notify_mac_column_exists = True
        KNOWN_MAC = "b5c1e8f1a9d47c3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e"
        monkeypatch.setattr(lib, "_compute_notify_mac", lambda *a, **kw: KNOWN_MAC)

        mock_row = {
            "id": 1,
            "notification_type": "test_type",
            "sender_moniker": "sender",
            "template": "",
            "template_vars": None,
            "rendered_message": "Hello",
            "data": None,
            "urgency": "ROUTINE",
            "mac": KNOWN_MAC,
            "datecreated": MagicMock(timestamp=lambda: 0.0),
            "datedelivered": None,
            "dateread": None,
        }

        mock_cur = MagicMock()
        mock_cur.description = [
            ("id",),
            ("notification_type",),
            ("sender_moniker",),
            ("template",),
            ("template_vars",),
            ("rendered_message",),
            ("data",),
            ("urgency",),
            ("mac",),
            ("datecreated",),
            ("dateread",),
            ("datedelivered",),
        ]
        mock_cur.fetchall.return_value = [mock_row]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.pool.putconn.return_value = None

        result = get_notifications("recipient", conn=mock_conn)
        assert len(result) == 1
        assert result[0].id == 1

    def test_tampered_mac_raises(self, monkeypatch):
        monkeypatch.setenv("BBSENGINE6_NOTIFY_MAC_KEY", "test-secret")
        import bbsengine6.notify.lib as lib

        lib._mac_key_cache = None
        lib._notify_mac_column_exists = True

        mock_row = {
            "id": 1,
            "notification_type": "test_type",
            "sender_moniker": "sender",
            "template": "",
            "template_vars": None,
            "rendered_message": "Hello",
            "data": None,
            "urgency": "ROUTINE",
            "mac": "a" * 64,
            "datecreated": MagicMock(timestamp=lambda: 0.0),
            "datedelivered": None,
            "dateread": None,
        }

        mock_cur = MagicMock()
        mock_cur.description = [
            ("id",),
            ("notification_type",),
            ("sender_moniker",),
            ("template",),
            ("template_vars",),
            ("rendered_message",),
            ("data",),
            ("urgency",),
            ("mac",),
            ("datecreated",),
            ("dateread",),
            ("datedelivered",),
        ]
        mock_cur.fetchall.return_value = [mock_row]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.pool.putconn.return_value = None

        with pytest.raises(NotificationTamperError, match="HMAC verification failed"):
            get_notifications("recipient", conn=mock_conn)

    def test_no_key_no_verification(self, monkeypatch):
        monkeypatch.delenv("BBSENGINE6_NOTIFY_MAC_KEY", raising=False)
        import bbsengine6.notify.lib as lib

        lib._mac_key_cache = None
        lib._notify_mac_column_exists = True

        mock_row = {
            "id": 1,
            "notification_type": "test_type",
            "sender_moniker": "sender",
            "template": "",
            "template_vars": None,
            "rendered_message": "Hello",
            "data": None,
            "urgency": "ROUTINE",
            "mac": "any-value",
            "datecreated": MagicMock(timestamp=lambda: 0.0),
            "datedelivered": None,
            "dateread": None,
        }

        mock_cur = MagicMock()
        mock_cur.description = [
            ("id",),
            ("notification_type",),
            ("sender_moniker",),
            ("template",),
            ("template_vars",),
            ("rendered_message",),
            ("data",),
            ("urgency",),
            ("mac",),
            ("datecreated",),
            ("dateread",),
            ("datedelivered",),
        ]
        mock_cur.fetchall.return_value = [mock_row]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.pool.putconn.return_value = None

        result = get_notifications("recipient", conn=mock_conn)
        assert len(result) == 1

    def test_null_mac_no_verification(self, monkeypatch):
        monkeypatch.setenv("BBSENGINE6_NOTIFY_MAC_KEY", "test-secret")
        import bbsengine6.notify.lib as lib

        lib._mac_key_cache = None
        lib._notify_mac_column_exists = True

        mock_row = {
            "id": 1,
            "notification_type": "test_type",
            "sender_moniker": "sender",
            "template": "",
            "template_vars": None,
            "rendered_message": "Hello",
            "data": None,
            "urgency": "ROUTINE",
            "mac": None,
            "datecreated": MagicMock(timestamp=lambda: 0.0),
            "datedelivered": None,
            "dateread": None,
        }

        mock_cur = MagicMock()
        mock_cur.description = [
            ("id",),
            ("notification_type",),
            ("sender_moniker",),
            ("template",),
            ("template_vars",),
            ("rendered_message",),
            ("data",),
            ("urgency",),
            ("mac",),
            ("datecreated",),
            ("dateread",),
            ("datedelivered",),
        ]
        mock_cur.fetchall.return_value = [mock_row]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.pool.putconn.return_value = None

        result = get_notifications("recipient", conn=mock_conn)
        assert len(result) == 1


# =============================================================================
# Integration tests — require real database
# =============================================================================


@pytest.mark.integration
class TestNotifyMacIntegration:
    """Integration tests with real database. Requires mac column in __notify table."""

    @pytest.fixture(scope="class", autouse=True)
    def ensure_mac_column(self, db_connection):
        """Ensure __notify has mac column. Skip class if insufficient privileges."""
        import bbsengine6.notify.lib as lib
        import psycopg

        try:
            with db_connection.cursor() as cur:
                cur.execute("ALTER TABLE engine.__notify ADD COLUMN mac text")
            db_connection.commit()
            lib._notify_mac_column_exists = True
        except psycopg.errors.DuplicateColumn:
            db_connection.rollback()
            lib._notify_mac_column_exists = True
        except psycopg.errors.InsufficientPrivilege:
            db_connection.rollback()
            pytest.skip("mac column requires table owner privileges")

    def test_send_with_mac_key_stores_mac(
        self, pool, db_connection, test_users, monkeypatch
    ):
        """send() computes and stores HMAC when BBSENGINE6_NOTIFY_MAC_KEY is set."""
        import bbsengine6.notify.lib as lib
        from bbsengine6 import database

        type_name = f"TEST_MAC_{uuid.uuid4().hex[:8]}"
        register_type(type_name, NotificationUrgency.ROUTINE, 100)
        recipient = test_users[0]

        KNOWN_KEY = b"integration-test-secret"
        monkeypatch.setattr(lib, "_get_mac_key", lambda: KNOWN_KEY)
        lib._mac_key_cache = KNOWN_KEY
        lib._notify_mac_column_exists = None

        result = send(
            notification_type=type_name,
            recipients=[recipient],
            template="MAC test {name}",
            template_vars={"name": recipient},
            conn=db_connection,
        )
        assert result.id > 0

        with database.cursor(db_connection) as cur:
            cur.execute(
                "SELECT mac FROM engine.__notify WHERE id = %s",
                (result.id,),
            )
            row = cur.fetchone()
            assert row is not None
            assert row["mac"] is not None
            assert len(row["mac"]) == 64

        with database.cursor(db_connection) as cur:
            cur.execute(
                "DELETE FROM engine.__notify WHERE id = %s",
                (result.id,),
            )
        db_connection.commit()

    def test_send_without_mac_key_stores_null(
        self, pool, db_connection, test_users, monkeypatch
    ):
        """send() stores NULL mac when BBSENGINE6_NOTIFY_MAC_KEY is not set."""
        import bbsengine6.notify.lib as lib
        from bbsengine6 import database

        type_name = f"TEST_NOMAC_{uuid.uuid4().hex[:8]}"
        register_type(type_name, NotificationUrgency.ROUTINE, 100)
        recipient = test_users[1]

        monkeypatch.setattr(lib, "_get_mac_key", lambda: None)
        lib._mac_key_cache = None
        lib._notify_mac_column_exists = None

        result = send(
            notification_type=type_name,
            recipients=[recipient],
            template="No MAC test",
            conn=db_connection,
        )

        with database.cursor(db_connection) as cur:
            cur.execute(
                "SELECT mac FROM engine.__notify WHERE id = %s",
                (result.id,),
            )
            row = cur.fetchone()
            assert row is not None
            assert row["mac"] is None

        with database.cursor(db_connection) as cur:
            cur.execute(
                "DELETE FROM engine.__notify WHERE id = %s",
                (result.id,),
            )
        db_connection.commit()

    def test_get_notifications_verifies_valid_mac(
        self, pool, db_connection, test_users, monkeypatch
    ):
        """get_notifications() returns notification when MAC is valid."""
        import bbsengine6.notify.lib as lib
        from bbsengine6 import database

        type_name = f"TEST_VERIFY_{uuid.uuid4().hex[:8]}"
        register_type(type_name, NotificationUrgency.ROUTINE, 100)
        recipient = test_users[2]

        KNOWN_KEY = b"verify-secret-123"
        monkeypatch.setattr(lib, "_get_mac_key", lambda: KNOWN_KEY)
        lib._mac_key_cache = KNOWN_KEY
        lib._notify_mac_column_exists = None

        result = send(
            notification_type=type_name,
            recipients=[recipient],
            template="Verify MAC",
            conn=db_connection,
        )
        notify_id = result.id

        lib._mac_key_cache = KNOWN_KEY
        lib._notify_mac_column_exists = None

        notifications = get_notifications(recipient, conn=db_connection)
        matching = [n for n in notifications if n.id == notify_id]
        assert len(matching) == 1
        assert matching[0].message == "Verify MAC"

        with database.cursor(db_connection) as cur:
            cur.execute("DELETE FROM engine.__notify WHERE id = %s", (notify_id,))
        db_connection.commit()

    def test_get_notifications_rejects_tampered(
        self, pool, db_connection, test_users, monkeypatch
    ):
        """get_notifications() raises NotificationTamperError when MAC does not match."""
        import bbsengine6.notify.lib as lib
        from bbsengine6 import database

        type_name = f"TEST_TAMPER_{uuid.uuid4().hex[:8]}"
        register_type(type_name, NotificationUrgency.ROUTINE, 100)
        recipient = test_users[2]

        KNOWN_KEY = b"tamper-secret"
        monkeypatch.setattr(lib, "_get_mac_key", lambda: KNOWN_KEY)
        lib._mac_key_cache = KNOWN_KEY
        lib._notify_mac_column_exists = None

        result = send(
            notification_type=type_name,
            recipients=[recipient],
            template="Original message",
            conn=db_connection,
        )
        notify_id = result.id

        try:
            with database.cursor(db_connection) as cur:
                cur.execute(
                    "UPDATE engine.__notify SET mac = %s WHERE id = %s",
                    ("f" * 64, notify_id),
                )
            db_connection.commit()

            lib._mac_key_cache = KNOWN_KEY
            lib._notify_mac_column_exists = None

            with pytest.raises(
                NotificationTamperError, match="HMAC verification failed"
            ):
                get_notifications(recipient, conn=db_connection)
        finally:
            try:
                with database.cursor(db_connection) as cur:
                    cur.execute(
                        "DELETE FROM engine.__notify WHERE id = %s", (notify_id,)
                    )
                db_connection.commit()
            except Exception:
                db_connection.rollback()
