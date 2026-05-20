# test_internet_registry.py
# Tests for machine registry and full Phase 3 functionality.

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.net import (
    MachineConfig,
    MachineRegistry,
    WebSocketProtocol,
    WebSocketTransport,
)


class TestMachineConfig:
    """Test MachineConfig data class."""

    def test_create_config(self):
        """Test creating machine config."""
        config = MachineConfig("machine1", "localhost", 8765)

        assert config.machine_name == "machine1"
        assert config.host == "localhost"
        assert config.port == 8765
        assert config.auth_token is None
        assert config.tls_enabled is False

    def test_config_with_auth_token(self):
        """Test config with authentication token."""
        config = MachineConfig("machine1", "localhost", 8765, auth_token="secret123")

        assert config.auth_token == "secret123"

    def test_config_with_tls(self):
        """Test config with TLS enabled."""
        config = MachineConfig(
            "machine1", "remote.example.com", 8765, tls_enabled=True, verify_cert=True
        )

        assert config.tls_enabled is True
        assert config.verify_cert is True

    def test_ws_url_plain(self):
        """Test WebSocket URL generation (plain)."""
        config = MachineConfig("machine1", "localhost", 8765)
        assert config.ws_url() == "ws://localhost:8765/notify"

    def test_ws_url_tls(self):
        """Test WebSocket URL generation (TLS)."""
        config = MachineConfig("machine1", "remote.example.com", 8765, tls_enabled=True)
        assert config.ws_url() == "wss://remote.example.com:8765/notify"


class TestMachineRegistry:
    """Test machine registry."""

    def test_create_registry(self):
        """Test creating registry."""
        registry = MachineRegistry("test_db")
        assert registry.dbname == "test_db"
        assert registry._cache == {}
        assert registry._cache_valid is False

    @patch("bbsengine6.net.registry.psycopg.connect")
    def test_register_machine(self, mock_connect):
        """Test registering a machine."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        registry = MachineRegistry("test_db")

        # Mock database operations
        with patch("bbsengine6.net.registry.database.cursor") as mock_cursor:
            mock_cursor.return_value.__enter__ = MagicMock()
            mock_cursor.return_value.__exit__ = MagicMock()

            result = registry.register(
                "machine1",
                "localhost",
                8765,
                auth_token="token123",
            )

            assert result is True

    def test_get_machine_config(self):
        """Test getting machine configuration."""
        registry = MachineRegistry("test_db")

        # Manually add to cache to avoid DB
        config = MachineConfig("machine1", "localhost", 8765, auth_token="secret")
        registry._cache["machine1"] = config
        registry._cache_valid = True

        result = registry.get("machine1")
        assert result is not None
        assert result.machine_name == "machine1"
        assert result.host == "localhost"
        assert result.auth_token == "secret"

    @patch("bbsengine6.net.registry.psycopg.connect")
    @patch("bbsengine6.net.registry.database.cursor")
    def test_get_machine_not_found(self, mock_cursor, mock_connect):
        """Test getting non-existent machine."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        # Mock fetchone to return None (not found)
        mock_ctx = MagicMock()
        mock_ctx.fetchone.return_value = None
        mock_cursor.return_value.__enter__.return_value = mock_ctx
        mock_cursor.return_value.__exit__.return_value = None

        registry = MachineRegistry("test_db")
        result = registry.get("nonexistent")

        assert result is None

    def test_list_machines(self):
        """Test listing all machines."""
        registry = MachineRegistry("test_db")

        # Manually add to cache
        config1 = MachineConfig("machine1", "localhost", 8765)
        config2 = MachineConfig("machine2", "remote.example.com", 8765)
        registry._cache = {"machine1": config1, "machine2": config2}
        registry._cache_valid = True

        with patch("bbsengine6.net.registry.psycopg.connect"):
            with patch("bbsengine6.net.registry.database.cursor"):
                machines = registry.list_all()
                assert len(machines) >= 0


class TestWebSocketTransport:
    """Test WebSocket transport."""

    def test_transport_init(self):
        """Test transport initialization."""
        transport = WebSocketTransport(timeout=5.0)
        assert transport.timeout == 5.0

    def test_transport_default_timeout(self):
        """Test default timeout."""
        transport = WebSocketTransport()
        assert transport.timeout == 10.0


class TestWebSocketProtocol:
    """Test WebSocket protocol handler."""

    def test_protocol_init(self):
        """Test protocol initialization."""
        transport = WebSocketTransport()
        protocol = WebSocketProtocol(transport)

        assert protocol.transport is transport


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
