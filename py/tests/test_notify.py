"""
Unit tests for bbsengine6.notify module.

Covers validation, data structures, and queue operations without database dependencies.
"""

import pytest
import time
from datetime import datetime, timezone

from bbsengine6.notify import (
    NotificationUrgency,
    Notification,
    UserNotificationQueue,
    _validate_moniker,
    _validate_type_name,
    _validate_template,
    _validate_template_vars,
    _render_template,
)


class TestNotificationUrgency:
    """Test NotificationUrgency enum."""

    def test_urgency_values(self):
        assert NotificationUrgency.ROUTINE.value == "ROUTINE"
        assert NotificationUrgency.IMPORTANT.value == "IMPORTANT"
        assert NotificationUrgency.URGENT.value == "URGENT"
        assert NotificationUrgency.CRITICAL.value == "CRITICAL"

    def test_urgency_enum_members(self):
        assert len(NotificationUrgency) == 4

    def test_urgency_comparison(self):
        assert NotificationUrgency.ROUTINE != NotificationUrgency.URGENT
        assert NotificationUrgency.CRITICAL == NotificationUrgency.CRITICAL


class TestNotificationDataclass:
    """Test Notification dataclass."""

    def test_notification_creation(self):
        notif = Notification(
            id=1,
            notification_type="TEST",
            recipients=["jam"],
            recipients_ok=["jam"],
            recipients_failed=[],
            sender_moniker="alice",
            template="Hello {name}",
            template_vars={"name": "jam"},
            message="Hello jam",
            data={"key": "value"},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=time.time(),
            should_persist=True,
            created_at=datetime.now(timezone.utc),
        )

        assert notif.id == 1
        assert notif.notification_type == "TEST"
        assert notif.recipients == ["jam"]
        assert notif.message == "Hello jam"
        assert notif.urgency == NotificationUrgency.ROUTINE

    def test_notification_default_values(self):
        notif = Notification(
            id=1,
            notification_type="TEST",
            recipients=[],
            recipients_ok=[],
            recipients_failed=[],
            sender_moniker=None,
            template="test",
            template_vars={},
            message="test",
            data={},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=0.0,
        )

        assert notif.read_by == {}
        assert notif.delivered_to == {}
        assert notif.blocked_from == set()
        assert notif.errors == {}
        assert notif.should_persist is True

    def test_notification_with_errors(self):
        notif = Notification(
            id=1,
            notification_type="TEST",
            recipients=["jam", "@invalid"],
            recipients_ok=["jam"],
            recipients_failed=["@invalid"],
            sender_moniker=None,
            template="test",
            template_vars={},
            message="test",
            data={},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=0.0,
            errors={"@invalid": "Group does not exist"},
        )

        assert notif.errors["@invalid"] == "Group does not exist"
        assert len(notif.recipients_ok) == 1
        assert len(notif.recipients_failed) == 1


class TestUserNotificationQueue:
    """Test UserNotificationQueue thread-safe operations."""

    def _create_test_notification(self, notify_id=1):
        return Notification(
            id=notify_id,
            notification_type="TEST",
            recipients=[],
            recipients_ok=[],
            recipients_failed=[],
            sender_moniker=None,
            template="",
            template_vars={},
            message="",
            data={},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=0.0,
        )

    def test_queue_creation(self):
        queue = UserNotificationQueue()
        assert queue.size() == 0

    def test_put_and_get(self):
        queue = UserNotificationQueue()
        notif = self._create_test_notification()

        queue.put(notif)
        assert queue.size() == 1

        retrieved = queue.get(timeout=0.1)
        assert retrieved is notif
        assert queue.size() == 0

    def test_get_timeout_empty(self):
        queue = UserNotificationQueue()
        result = queue.get(timeout=0.1)
        assert result is None

    def test_get_all(self):
        queue = UserNotificationQueue()
        notif1 = self._create_test_notification(1)
        notif2 = self._create_test_notification(2)

        queue.put(notif1)
        queue.put(notif2)

        all_notifs = queue.get_all()
        assert len(all_notifs) == 2
        assert queue.size() == 0

    def test_has_urgent(self):
        queue = UserNotificationQueue()
        routine = Notification(
            id=1,
            notification_type="TEST",
            recipients=[],
            recipients_ok=[],
            recipients_failed=[],
            sender_moniker=None,
            template="",
            template_vars={},
            message="",
            data={},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=0.0,
        )
        queue.put(routine)
        assert not queue.has_urgent()

        urgent = Notification(
            id=2,
            notification_type="TEST",
            recipients=[],
            recipients_ok=[],
            recipients_failed=[],
            sender_moniker=None,
            template="",
            template_vars={},
            message="",
            data={},
            urgency=NotificationUrgency.URGENT,
            timestamp=1.0,
        )
        queue.put(urgent)
        assert queue.has_urgent()

    def test_peek_urgent(self):
        queue = UserNotificationQueue()
        routine = Notification(
            id=1,
            notification_type="TEST",
            recipients=[],
            recipients_ok=[],
            recipients_failed=[],
            sender_moniker=None,
            template="",
            template_vars={},
            message="",
            data={},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=0.0,
        )
        queue.put(routine)

        # Peek should return None (only routine)
        assert queue.peek_urgent() is None

        # Add urgent notification
        urgent = Notification(
            id=2,
            notification_type="TEST",
            recipients=[],
            recipients_ok=[],
            recipients_failed=[],
            sender_moniker=None,
            template="",
            template_vars={},
            message="",
            data={},
            urgency=NotificationUrgency.URGENT,
            timestamp=1.0,
        )
        queue.put(urgent)

        # Now peek should find it
        result = queue.peek_urgent()
        assert result is not None
        assert result.urgency == NotificationUrgency.URGENT
        # Queue should still have both items
        assert queue.size() == 2

    def test_queue_size(self):
        queue = UserNotificationQueue()
        assert queue.size() == 0

        for i in range(5):
            queue.put(self._create_test_notification(i))

        assert queue.size() == 5


class TestValidateTypeName:
    """Test notification type name validation."""

    def test_valid_type_names(self):
        assert _validate_type_name("EMPYRE_VICTORY")
        assert _validate_type_name("TEST")
        assert _validate_type_name("TYPE123")
        assert _validate_type_name("_PRIVATE")
        assert _validate_type_name("A")

    def test_invalid_type_names(self):
        assert not _validate_type_name("")
        assert not _validate_type_name(None)
        assert not _validate_type_name("A" * 51)  # > 50 chars
        assert not _validate_type_name("TYPE-NAME")  # Invalid char
        assert not _validate_type_name("TYPE.NAME")  # Invalid char
        assert not _validate_type_name("TYPE NAME")  # Space
        assert not _validate_type_name(123)  # Not a string
        assert not _validate_type_name([])  # Not a string


class TestValidateTemplate:
    """Test template validation."""

    def test_valid_templates(self):
        _validate_template("Hello world")
        _validate_template("Hello {name}")
        _validate_template("Hello {name}, you have {count} messages")
        _validate_template("{name}")

    def test_invalid_templates(self):
        with pytest.raises(ValueError):
            _validate_template("")
        with pytest.raises(ValueError):
            _validate_template(None)
        with pytest.raises(ValueError):
            _validate_template("A" * 501)  # > 500 chars

    def test_template_missing_variables(self):
        with pytest.raises(ValueError):
            _validate_template("{missing_var}", {"other": "value"})

    def test_template_valid_with_variables(self):
        # Should not raise
        _validate_template("{name} has {count} items", {"name": "jam", "count": 5})

    def test_template_invalid_syntax(self):
        with pytest.raises(ValueError):
            _validate_template("{name[0]}")  # Array syntax not allowed
        with pytest.raises(ValueError):
            _validate_template("{name.attr}")  # Attribute syntax not allowed

    def test_template_no_vars_dict(self):
        # Template with no variables and no vars dict should be OK
        _validate_template("Hello world", None)
        _validate_template("Hello world", {})


class TestValidateTemplateVars:
    """Test template variables validation."""

    def test_valid_vars(self):
        _validate_template_vars({"name": "jam"})
        _validate_template_vars({"name": "jam", "count": 5})
        _validate_template_vars({"value": 3.14})
        _validate_template_vars({})
        _validate_template_vars(None)

    def test_invalid_var_keys(self):
        with pytest.raises(ValueError):
            _validate_template_vars({"invalid-name": "value"})
        with pytest.raises(ValueError):
            _validate_template_vars({"invalid.name": "value"})
        with pytest.raises(ValueError):
            _validate_template_vars({"123invalid": "value"})  # Can't start with number

    def test_invalid_var_values(self):
        with pytest.raises(ValueError):
            _validate_template_vars({"name": ["list"]})  # Lists not allowed
        with pytest.raises(ValueError):
            _validate_template_vars({"name": {"dict": "value"}})  # Dicts not allowed
        with pytest.raises(ValueError):
            _validate_template_vars({"name": True})  # Booleans not allowed

    def test_var_size_limits(self):
        with pytest.raises(ValueError):
            _validate_template_vars({"name": "A" * 101})  # > 100 chars
        with pytest.raises(ValueError):
            # Total size > 10KB
            _validate_template_vars({"key": "A" * 5000, "other": "B" * 5000})

    def test_var_with_integers(self):
        # Integers are allowed
        _validate_template_vars({"count": 42})
        _validate_template_vars({"negative": -10})

    def test_var_with_floats(self):
        # Floats are allowed
        _validate_template_vars({"price": 19.99})
        _validate_template_vars({"negative": -3.14})


class TestRenderTemplate:
    """Test template rendering."""

    def test_simple_render(self):
        result = _render_template("Hello {name}", {"name": "jam"})
        assert result == "Hello jam"

    def test_multiple_vars(self):
        result = _render_template(
            "{name} has {count} messages", {"name": "jam", "count": 5}
        )
        assert result == "jam has 5 messages"

    def test_no_vars(self):
        result = _render_template("Hello world", {})
        assert result == "Hello world"

    def test_render_with_none_vars(self):
        result = _render_template("Hello world", None)
        assert result == "Hello world"

    def test_render_with_extra_vars(self):
        # Extra variables in dict are ignored
        result = _render_template("Hello {name}", {"name": "jam", "extra": "ignored"})
        assert result == "Hello jam"

    def test_render_with_numbers(self):
        result = _render_template("Price: {price}", {"price": 19.99})
        assert result == "Price: 19.99"

    def test_render_multiple_same_var(self):
        result = _render_template("{name} is {name}", {"name": "jam"})
        assert result == "jam is jam"

    def test_render_var_at_boundaries(self):
        result = _render_template("{start} middle {end}", {"start": "A", "end": "Z"})
        assert result == "A middle Z"


class TestValidateMoniker:
    """Test moniker validation."""

    def test_valid_moniker_format(self):
        # Without database cursor, should validate format only
        assert _validate_moniker("jam")
        assert _validate_moniker("alice")
        assert _validate_moniker("user_123")
        assert _validate_moniker("a-b-c")
        assert _validate_moniker("A")
        assert _validate_moniker("Z")
        # Special characters now allowed
        assert _validate_moniker("JAM!")  # Exclamation
        assert _validate_moniker("user@host")  # @ symbol
        assert _validate_moniker("test#123")  # Hash
        assert _validate_moniker("price$100")  # Dollar
        assert _validate_moniker("item%off")  # Percent
        assert _validate_moniker("x^2")  # Caret
        assert _validate_moniker("a&b")  # Ampersand
        assert _validate_moniker("test*")  # Asterisk
        assert _validate_moniker("par(en")  # Parens
        assert _validate_moniker("close)par")  # Parens

    def test_invalid_moniker_format(self):
        assert not _validate_moniker("")
        assert not _validate_moniker(None)
        assert not _validate_moniker("A" * 256)  # > 255 chars
        assert not _validate_moniker("invalid name")  # Space
        assert not _validate_moniker("user.name")  # Dot (not in pattern)
        assert not _validate_moniker(123)  # Not a string


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
