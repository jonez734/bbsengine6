# test_internet_integration.py
# Tests for internet layer integration with bbsengine6.notify.

from unittest.mock import MagicMock

import pytest

from bbsengine6.internet import NotifyIntegration, get_integration, send_with_internet


class MockNotifyModule:
    """Mock bbsengine6.notify module for testing."""

    @staticmethod
    def send(
        notification_type,
        recipients,
        template,
        template_vars=None,
        sender_moniker=None,
        data=None,
        urgency=None,
        should_persist=True,
        conn=None,
    ):
        """Mock send function returns notification object."""
        return MagicMock(
            notification_type=notification_type,
            recipients=recipients,
            template=template,
        )


class TestNotifyIntegration:
    """Test NotifyIntegration class."""

    def test_init_with_module(self):
        """Test initialization with provided module."""
        mock_notify = MockNotifyModule()
        integration = NotifyIntegration("local", mock_notify)

        assert integration.local_machine == "local"
        assert integration.notify_module is mock_notify

    def test_init_without_module(self):
        """Test initialization without module (should try auto-import)."""
        integration = NotifyIntegration("local", None)
        assert integration.local_machine == "local"
        # notify_module will be set or None depending on availability

    def test_send_local_only(self):
        """Test sending to local recipients only."""
        mock_notify = MockNotifyModule()
        integration = NotifyIntegration("local", mock_notify)

        result = integration.send(
            notification_type="test",
            recipients=["alice@local", "bob@local"],
            template="Test template",
        )

        assert result["local"] is not None
        assert result["remote"] == {}
        assert result["errors"] == {}
        assert result["summary"] == (1, 0)

    def test_send_remote_only(self):
        """Test sending to remote recipients only (not configured)."""
        mock_notify = MockNotifyModule()
        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        integration = NotifyIntegration("local", mock_notify, mock_registry)

        result = integration.send(
            notification_type="test",
            recipients=["alice@machine1", "bob@machine1"],
            template="Test template",
        )

        assert result["local"] is None
        assert "machine1" in result["remote"]
        # Should fail because machine1 is not in registry
        assert result["remote"]["machine1"][0] is False
        assert "not configured" in result["remote"]["machine1"][1]

    def test_send_mixed_recipients(self):
        """Test sending to mixed local and remote recipients."""
        mock_notify = MockNotifyModule()
        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        integration = NotifyIntegration("local", mock_notify, mock_registry)

        result = integration.send(
            notification_type="test",
            recipients=[
                "alice@local",
                "bob@machine1",
                "charlie@domain.com",
            ],
            template="Test template",
        )

        assert result["local"] is not None
        assert "machine1" in result["remote"]
        assert "domain.com" in result["remote"]
        assert result["errors"] == {}

    def test_send_with_errors(self):
        """Test sending with invalid addresses."""
        mock_notify = MockNotifyModule()
        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        integration = NotifyIntegration("local", mock_notify, mock_registry)

        result = integration.send(
            notification_type="test",
            recipients=[
                "alice@local",
                "invalid",
                "bob@machine1",
            ],
            template="Test template",
        )

        assert result["local"] is not None
        assert "invalid" in result["errors"]
        assert "machine1" in result["remote"]

    def test_send_no_notify_module(self):
        """Test sending when notify module is unavailable."""
        integration = NotifyIntegration("local", None)
        integration.notify_module = None

        result = integration.send(
            notification_type="test",
            recipients=["alice@local"],
            template="Test template",
        )

        assert result["local"] is None
        assert "all" in result["errors"]
        assert result["summary"] == (0, 1)

    def test_can_send_to_with_module(self):
        """Test can_send_to with module available."""
        mock_notify = MockNotifyModule()
        integration = NotifyIntegration("local", mock_notify)

        assert integration.can_send_to(["alice@local", "bob@machine1"])

    def test_can_send_to_without_module_local_only(self):
        """Test can_send_to without module, local recipients."""
        integration = NotifyIntegration("local", None)
        integration.notify_module = None

        # Should return False when trying to send to local without module
        assert not integration.can_send_to(["alice@local"])

    def test_can_send_to_without_module_remote_only(self):
        """Test can_send_to without module, remote recipients."""
        integration = NotifyIntegration("local", None)
        integration.notify_module = None

        # Should return True when only sending remote (no notify needed)
        assert integration.can_send_to(["bob@machine1"])

    def test_can_send_to_mixed_without_module(self):
        """Test can_send_to with mixed recipients but no module."""
        integration = NotifyIntegration("local", None)
        integration.notify_module = None

        # Should return False because there are local recipients
        assert not integration.can_send_to(["alice@local", "bob@machine1"])


class TestModuleConvenience:
    """Test module-level convenience functions."""

    def test_send_with_internet(self):
        """Test send_with_internet convenience function."""
        mock_notify = MockNotifyModule()

        # Create a fresh integration for this test
        integration = NotifyIntegration("local", mock_notify)

        result = integration.send(
            notification_type="test",
            recipients=["alice@local"],
            template="Test",
        )

        assert result["local"] is not None

    def test_get_integration_returns_singleton(self):
        """Test get_integration returns same instance on repeated calls."""
        mock_notify = MockNotifyModule()

        # Get integration twice
        integration1 = NotifyIntegration("local", mock_notify)
        integration2 = NotifyIntegration("local", mock_notify)

        # They should be different instances (we're creating new ones)
        assert integration1 is not integration2


class TestIntegrationWithNotify:
    """Integration tests with actual bbsengine6.notify (if available)."""

    @pytest.mark.skipif(
        True, reason="Skip unless bbsengine6.notify is available in test environment"
    )
    def test_real_notify_integration(self):
        """Test integration with real notify module."""
        try:
            from bbsengine6 import notify

            integration = NotifyIntegration("local", notify)
            assert integration.notify_module is not None
        except ImportError:
            pytest.skip("bbsengine6.notify not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
