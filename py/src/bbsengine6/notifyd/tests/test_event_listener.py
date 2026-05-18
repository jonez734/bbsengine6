# notifyd/tests/test_event_listener.py
# Tests for event listener and handler registration

import pytest
from unittest.mock import MagicMock, patch, call
from typing import Dict, Any

from bbsengine6.notifyd import event_listener


class TestEventListener:
    """Test EventListener class"""

    def test_init(self):
        """Initialize event listener"""
        mock_config = {"events": {}}
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        assert listener.config == mock_config
        assert listener.dispatcher == mock_dispatcher

    def test_register_handlers_no_events(self):
        """Register handlers when no events configured"""
        mock_config = {}
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        # Should not raise
        listener.register_handlers()

    def test_register_handlers_empty_events(self):
        """Register handlers with empty events dict"""
        mock_config = {"events": {}}
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        listener.register_handlers()

    def test_register_handlers_single_event(self):
        """Register handler for single event"""
        mock_config = {
            "events": {
                "user.login": [
                    {
                        "recipients": ["admin"],
                        "template": "user-login",
                        "urgency": "ROUTINE",
                    }
                ]
            }
        }
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        with patch("bbsengine6.notifyd.hooks.register_event_handler") as mock_register:
            listener.register_handlers()
            
            # Verify handler registered
            assert mock_register.called
            event_type = mock_register.call_args[0][0]
            assert event_type == "user.login"

    def test_register_handlers_multiple_events(self):
        """Register handlers for multiple events"""
        mock_config = {
            "events": {
                "user.login": [
                    {
                        "recipients": ["admin"],
                        "template": "user-login",
                    }
                ],
                "user.logout": [
                    {
                        "recipients": ["admin"],
                        "template": "user-logout",
                    }
                ],
            }
        }
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        with patch("bbsengine6.notifyd.hooks.register_event_handler") as mock_register:
            listener.register_handlers()
            
            assert mock_register.call_count == 2

    def test_register_handlers_multiple_handlers_per_event(self):
        """Register multiple handlers for same event"""
        mock_config = {
            "events": {
                "user.login": [
                    {
                        "recipients": ["admin1"],
                        "template": "user-login",
                    },
                    {
                        "recipients": ["admin2"],
                        "template": "user-login",
                    },
                ]
            }
        }
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        with patch("bbsengine6.notifyd.hooks.register_event_handler") as mock_register:
            listener.register_handlers()
            
            # Should register both handlers
            assert mock_register.call_count == 2

    def test_register_handlers_invalid_handler_config(self):
        """Handle invalid handler config gracefully"""
        mock_config = {
            "events": {
                "user.login": "not a list"  # Invalid: should be list
            }
        }
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        # Should not raise
        listener.register_handlers()

    def test_register_handlers_missing_recipients(self):
        """Handle handler with missing recipients"""
        mock_config = {
            "events": {
                "user.login": [
                    {
                        # Missing recipients
                        "template": "user-login",
                    }
                ]
            }
        }
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        with patch("bbsengine6.notifyd.hooks.register_event_handler") as mock_register:
            listener.register_handlers()
            
            # Should not register invalid handler
            assert not mock_register.called

    def test_register_handlers_missing_template(self):
        """Handle handler with missing template"""
        mock_config = {
            "events": {
                "user.login": [
                    {
                        "recipients": ["admin"],
                        # Missing template
                    }
                ]
            }
        }
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        with patch("bbsengine6.notifyd.hooks.register_event_handler") as mock_register:
            listener.register_handlers()
            
            assert not mock_register.called


class TestMakeHandler:
    """Test _make_handler method"""

    def test_make_handler_basic(self):
        """Create basic event handler"""
        mock_config = {}
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        handler_config = {
            "recipients": ["user1"],
            "template": "test-template",
            "urgency": "ROUTINE",
        }
        
        handler = listener._make_handler("test.event", handler_config)
        
        assert callable(handler)

    def test_make_handler_sends_notification(self):
        """Handler function sends notification"""
        mock_config = {}
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        handler_config = {
            "recipients": ["user1", "user2"],
            "template": "test-template",
            "urgency": "IMPORTANT",
        }
        
        handler = listener._make_handler("test.event", handler_config)
        
        # Call handler with event data
        event_data = {"key": "value"}
        handler(event_data)
        
        # Verify dispatcher was called
        mock_dispatcher.send_custom_notification.assert_called_once()
        
        call_kwargs = mock_dispatcher.send_custom_notification.call_args[1]
        assert call_kwargs["event_type"] == "test.event"
        assert call_kwargs["recipients"] == ["user1", "user2"]
        assert call_kwargs["template"] == "test-template"
        assert call_kwargs["urgency"] == "IMPORTANT"
        assert call_kwargs["template_vars"] == event_data

    def test_make_handler_default_urgency(self):
        """Handler uses default urgency"""
        mock_config = {}
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        handler_config = {
            "recipients": ["user1"],
            "template": "test-template",
            # No urgency specified
        }
        
        handler = listener._make_handler("test.event", handler_config)
        handler({})
        
        call_kwargs = mock_dispatcher.send_custom_notification.call_args[1]
        assert call_kwargs["urgency"] == "ROUTINE"

    def test_make_handler_missing_recipients_error(self):
        """Handler creation fails without recipients"""
        mock_config = {}
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        handler_config = {
            "template": "test-template",
            # Missing recipients
        }
        
        with pytest.raises(ValueError) as exc_info:
            listener._make_handler("test.event", handler_config)
        
        assert "recipients required" in str(exc_info.value)

    def test_make_handler_missing_template_error(self):
        """Handler creation fails without template"""
        mock_config = {}
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        handler_config = {
            "recipients": ["user1"],
            # Missing template
        }
        
        with pytest.raises(ValueError) as exc_info:
            listener._make_handler("test.event", handler_config)
        
        assert "template required" in str(exc_info.value)

    def test_make_handler_recipients_not_list_error(self):
        """Handler creation fails if recipients not list"""
        mock_config = {}
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        handler_config = {
            "recipients": "user1",  # Should be list
            "template": "test-template",
        }
        
        with pytest.raises(ValueError) as exc_info:
            listener._make_handler("test.event", handler_config)
        
        assert "must be list" in str(exc_info.value)

    def test_make_handler_passes_event_data(self):
        """Handler passes full event data to dispatcher"""
        mock_config = {}
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        handler_config = {
            "recipients": ["user1"],
            "template": "test-template",
        }
        
        handler = listener._make_handler("custom.event", handler_config)
        
        event_data = {
            "field1": "value1",
            "field2": 42,
            "field3": {"nested": "dict"},
        }
        
        handler(event_data)
        
        call_kwargs = mock_dispatcher.send_custom_notification.call_args[1]
        assert call_kwargs["template_vars"] == event_data

    def test_make_handler_error_handling(self):
        """Handler catches and logs dispatcher errors"""
        mock_config = {}
        mock_dispatcher = MagicMock()
        mock_dispatcher.send_custom_notification.side_effect = Exception("dispatch failed")
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        handler_config = {
            "recipients": ["user1"],
            "template": "test-template",
        }
        
        handler = listener._make_handler("test.event", handler_config)
        
        # Should not raise
        handler({"key": "value"})

    def test_make_handler_with_empty_recipients(self):
        """Handler creation fails with empty recipients list"""
        mock_config = {}
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        handler_config = {
            "recipients": [],  # Empty list
            "template": "test-template",
        }
        
        with pytest.raises(ValueError):
            listener._make_handler("test.event", handler_config)

    def test_make_handler_with_none_recipients(self):
        """Handler creation fails with None recipients"""
        mock_config = {}
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        handler_config = {
            "recipients": None,
            "template": "test-template",
        }
        
        with pytest.raises(ValueError):
            listener._make_handler("test.event", handler_config)


class TestEventListenerIntegration:
    """Integration tests for event listener"""

    def test_register_and_fire_event(self):
        """Register handler and verify it would be called on event"""
        mock_config = {
            "events": {
                "game.started": [
                    {
                        "recipients": ["admin"],
                        "template": "game-started",
                        "urgency": "IMPORTANT",
                    }
                ]
            }
        }
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        with patch("bbsengine6.notifyd.hooks.register_event_handler") as mock_register:
            listener.register_handlers()
            
            # Get registered handler
            assert mock_register.called
            handler = mock_register.call_args[0][1]
            
            # Fire event through handler
            handler({"game_name": "Test Game"})
            
            # Verify notification sent
            mock_dispatcher.send_custom_notification.assert_called_once()

    def test_multiple_handlers_for_same_event(self):
        """Multiple handlers registered for same event type"""
        mock_config = {
            "events": {
                "user.login": [
                    {
                        "recipients": ["admin1"],
                        "template": "admin-login-alert",
                    },
                    {
                        "recipients": ["supervisor1"],
                        "template": "supervisor-login-alert",
                    },
                ]
            }
        }
        mock_dispatcher = MagicMock()
        
        listener = event_listener.EventListener(mock_config, mock_dispatcher)
        
        with patch("bbsengine6.notifyd.hooks.register_event_handler") as mock_register:
            listener.register_handlers()
            
            # Both handlers registered
            assert mock_register.call_count == 2
            
            # Get both handlers
            handler1 = mock_register.call_args_list[0][0][1]
            handler2 = mock_register.call_args_list[1][0][1]
            
            # Fire both handlers
            event_data = {"username": "player1"}
            handler1(event_data)
            handler2(event_data)
            
            # Verify both sent notifications
            assert mock_dispatcher.send_custom_notification.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
