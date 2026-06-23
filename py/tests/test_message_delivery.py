# test_message_delivery.py
# Tests for message delivery handlers (Phase 1D)

import pytest
from unittest.mock import MagicMock, patch


class TestDeliveryHandler:
    """Tests for base delivery handler and manager."""

    def test_delivery_manager_creation(self):
        """Delivery manager can be created."""
        from bbsengine6.message_delivery import DeliveryManager
        
        manager = DeliveryManager()
        assert manager is not None

    def test_register_handler(self):
        """Handlers can be registered."""
        from bbsengine6.message_delivery import DeliveryManager, InMemoryQueueHandler
        
        manager = DeliveryManager()
        handler = InMemoryQueueHandler()
        
        manager.register_handler(handler)
        
        assert handler in manager._handlers

    def test_subscribe_channel(self):
        """Handlers can subscribe to channels."""
        from bbsengine6.message_delivery import DeliveryManager, InMemoryQueueHandler
        
        manager = DeliveryManager()
        handler = InMemoryQueueHandler()
        
        manager.subscribe_channel("test-channel", handler)
        
        assert "test-channel" in manager._channel_subscriptions
        assert handler in manager._channel_subscriptions["test-channel"]

    def test_unsubscribe_channel(self):
        """Handlers can unsubscribe from channels."""
        from bbsengine6.message_delivery import DeliveryManager, InMemoryQueueHandler
        
        manager = DeliveryManager()
        handler = InMemoryQueueHandler()
        
        manager.subscribe_channel("test-channel", handler)
        manager.unsubscribe_channel("test-channel", handler)
        
        assert handler not in manager._channel_subscriptions.get("test-channel", [])


class TestEmailDeliveryHandler:
    """Tests for email delivery handler."""

    def test_email_handler_creation(self):
        """Email handler can be created."""
        from bbsengine6.message_delivery import EmailDeliveryHandler
        
        handler = EmailDeliveryHandler(
            smtp_host="smtp.example.com",
            from_address="noreply@example.com",
        )
        
        assert handler.smtp_host == "smtp.example.com"
        assert handler.from_address == "noreply@example.com"

    def test_register_email(self):
        """Email can be registered for user."""
        from bbsengine6.message_delivery import EmailDeliveryHandler
        
        handler = EmailDeliveryHandler()
        handler.register_email("alice", "alice@example.com")
        
        assert handler.get_email("alice") == "alice@example.com"

    def test_unregister_email(self):
        """Email can be unregistered."""
        from bbsengine6.message_delivery import EmailDeliveryHandler
        
        handler = EmailDeliveryHandler()
        handler.register_email("alice", "alice@example.com")
        handler.unregister_email("alice")
        
        assert handler.get_email("alice") is None

    def test_can_deliver_with_email(self):
        """Can deliver if email is registered."""
        from bbsengine6.message_delivery import EmailDeliveryHandler
        
        handler = EmailDeliveryHandler()
        handler.register_email("alice", "alice@example.com")
        
        message = {"content": "Test", "channel": "test"}
        
        assert handler.can_deliver(message, "alice") is True
        assert handler.can_deliver(message, "bob") is False

    @patch("bbsengine6.message_delivery.smtplib.SMTP")
    def test_deliver_email(self, mock_smtp):
        """Email is sent on deliver."""
        from bbsengine6.message_delivery import EmailDeliveryHandler
        
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        handler = EmailDeliveryHandler(
            smtp_host="smtp.example.com",
            from_address="noreply@example.com",
        )
        handler.register_email("alice", "alice@example.com")
        
        message = {
            "content": "Hello Alice!",
            "sender_moniker": "bob",
            "channel": "test",
            "datestamp": "2024-01-01 12:00:00",
        }
        
        result = handler.deliver(message, "alice")
        
        assert result is True
        mock_server.send_message.assert_called_once()


class TestSMSDeliveryHandler:
    """Tests for SMS delivery handler."""

    def test_sms_handler_creation(self):
        """SMS handler can be created."""
        from bbsengine6.message_delivery import SMSDeliveryHandler
        
        handler = SMSDeliveryHandler(
            sms_gateway_url="https://sms.example.com/api",
            from_number="+15551234567",
        )
        
        assert handler.sms_gateway_url == "https://sms.example.com/api"
        assert handler.from_number == "+15551234567"

    def test_register_phone(self):
        """Phone can be registered for user."""
        from bbsengine6.message_delivery import SMSDeliveryHandler
        
        handler = SMSDeliveryHandler()
        handler.register_phone("alice", "+15551234567")
        
        assert handler.get_phone("alice") == "+15551234567"

    def test_can_deliver_with_phone(self):
        """Can deliver if phone is registered."""
        from bbsengine6.message_delivery import SMSDeliveryHandler
        
        handler = SMSDeliveryHandler(sms_gateway_url="https://sms.example.com")
        handler.register_phone("alice", "+15551234567")
        
        message = {"content": "Test", "channel": "test"}
        
        assert handler.can_deliver(message, "alice") is True
        assert handler.can_deliver(message, "bob") is False

    def test_can_deliver_no_gateway(self):
        """Cannot deliver without gateway configured."""
        from bbsengine6.message_delivery import SMSDeliveryHandler
        
        handler = SMSDeliveryHandler()  # No gateway
        handler.register_phone("alice", "+15551234567")
        
        message = {"content": "Test", "channel": "test"}
        
        assert handler.can_deliver(message, "alice") is False

    def test_format_message_truncates(self):
        """SMS message is truncated to 160 chars."""
        from bbsengine6.message_delivery import SMSDeliveryHandler
        
        handler = SMSDeliveryHandler()
        
        message = {
            "sender_moniker": "bob",
            "content": "x" * 200,
        }
        
        formatted = handler._format_message(message)
        
        assert len(formatted) == 160


class TestInMemoryQueueHandler:
    """Tests for in-memory queue handler."""

    def test_inmemory_handler_creation(self):
        """In-memory handler can be created."""
        from bbsengine6.message_delivery import InMemoryQueueHandler
        
        handler = InMemoryQueueHandler()
        
        assert handler.handler_name == "inmemory"
        assert handler._handlers == []

    def test_add_handler(self):
        """Message handler can be added."""
        from bbsengine6.message_delivery import InMemoryQueueHandler
        
        handler = InMemoryQueueHandler()
        
        callback_called = []
        def callback(msg, recipient):
            callback_called.append((msg, recipient))
        
        handler.add_handler(callback)
        
        message = {"content": "test"}
        handler.deliver(message, "alice")
        
        assert len(callback_called) == 1
        assert callback_called[0] == (message, "alice")


class TestDeliveryManagerIntegration:
    """Integration tests for delivery manager."""

    def test_publish_to_channel(self):
        """Messages published to channel reach subscribed handlers."""
        from bbsengine6.message_delivery import DeliveryManager, InMemoryQueueHandler
        
        manager = DeliveryManager()
        handler = InMemoryQueueHandler()
        
        received = []
        def callback(msg, recipient):
            received.append((msg, recipient))
        
        handler.add_handler(callback)
        
        manager.subscribe_channel("test-channel", handler)
        
        message = {
            "content": "Hello!",
            "sender_moniker": "alice",
            "recipient_monikers": ["bob", "charlie"],
        }
        
        results = manager.publish_to_channel("test-channel", message)
        
        assert "inmemory" in results
        assert len(received) == 2

    def test_deliver_to_recipient(self):
        """Can deliver to specific recipient with handler."""
        from bbsengine6.message_delivery import DeliveryManager, InMemoryQueueHandler
        
        manager = DeliveryManager()
        handler = InMemoryQueueHandler()
        
        received = []
        def callback(msg, recipient):
            received.append((msg, recipient))
        
        handler.add_handler(callback)
        manager.register_handler(handler)
        
        message = {"content": "Hello bob!"}
        
        results = manager.deliver_to_recipient(message, "bob")
        
        assert results["inmemory"] is True
        assert len(received) == 1
        assert received[0][1] == "bob"


def test_get_delivery_manager_singleton():
    """get_delivery_manager returns singleton."""
    from bbsengine6.message_delivery import get_delivery_manager, DeliveryManager
    
    mgr1 = get_delivery_manager()
    mgr2 = get_delivery_manager()
    
    assert mgr1 is mgr2
    assert isinstance(mgr1, DeliveryManager)
