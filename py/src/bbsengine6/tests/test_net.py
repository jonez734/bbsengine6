# test_internet.py
# Tests for internet layer address parsing and routing.

import pytest
from bbsengine6.net import (
    AddressParser,
    AddressType,
    InternetAddress,
    InternetRouter,
    WebSocketTransport,
    is_internet_address,
    parse_address,
    route_recipients,
)


class TestAddressParser:
    """Test address parsing."""

    def test_parse_local_address(self):
        """Test parsing local address (user@local)."""
        parser = AddressParser("local")
        addr = parser.parse("alice@local")

        assert addr is not None
        assert addr.user == "alice"
        assert addr.machine == "local"
        assert addr.address_type == AddressType.LOCAL

    def test_parse_remote_address(self):
        """Test parsing remote address (user@machine)."""
        parser = AddressParser("local")
        addr = parser.parse("bob@machine1")

        assert addr is not None
        assert addr.user == "bob"
        assert addr.machine == "machine1"
        assert addr.address_type == AddressType.REMOTE

    def test_parse_federated_address(self):
        """Test parsing federated address (user@machine.domain)."""
        parser = AddressParser("local")
        addr = parser.parse("charlie@remote.example.com")

        assert addr is not None
        assert addr.user == "charlie"
        assert addr.machine == "remote.example.com"
        assert addr.address_type == AddressType.FEDERATED

    def test_parse_invalid_address(self):
        """Test parsing invalid addresses."""
        parser = AddressParser("local")

        # Missing @
        assert parser.parse("alice") is None

        # Missing user
        assert parser.parse("@local") is None

        # Missing machine
        assert parser.parse("alice@") is None

        # Invalid characters
        assert parser.parse("alice@bad!machine") is None

    def test_parse_list_mixed(self):
        """Test parsing mixed valid and invalid addresses."""
        parser = AddressParser("local")
        result = parser.parse_list(
            [
                "alice@local",
                "bob@remote",
                "charlie@domain.com",
                "invalid",
                "@nomachine",
            ]
        )

        assert len(result.valid) == 3
        assert len(result.invalid) == 2
        assert "invalid" in result.invalid
        assert "@nomachine" in result.invalid

    def test_is_internet_address(self):
        """Test internet address detection."""
        parser = AddressParser("local")

        assert parser.is_internet_address("alice@local")
        assert parser.is_internet_address("bob@remote")
        assert parser.is_internet_address("charlie@domain.com")

        assert not parser.is_internet_address("alice")
        assert not parser.is_internet_address("@local")


class TestInternetRouter:
    """Test routing logic."""

    def test_route_single_local(self):
        """Test routing single local recipient."""
        router = InternetRouter("local")
        local, remote, frames, errors = router.route(["alice@local"])

        assert local == ["alice"]
        assert remote == {}
        assert errors == {}

    def test_route_single_remote(self):
        """Test routing single remote recipient."""
        router = InternetRouter("local")
        local, remote, frames, errors = router.route(["bob@machine1"])

        assert local == []
        assert remote == {"machine1": ["bob"]}
        assert errors == {}

    def test_route_mixed_recipients(self):
        """Test routing mixed local and remote."""
        router = InternetRouter("local")
        local, remote, frames, errors = router.route(
            [
                "alice@local",
                "bob@machine1",
                "charlie@machine1",
                "diana@remote.example.com",
            ]
        )

        assert local == ["alice"]
        assert remote == {
            "machine1": ["bob", "charlie"],
            "remote.example.com": ["diana"],
        }
        assert errors == {}

    def test_route_with_errors(self):
        """Test routing with invalid addresses."""
        router = InternetRouter("local")
        local, remote, frames, errors = router.route(
            [
                "alice@local",
                "invalid",
                "bob@machine1",
            ]
        )

        assert local == ["alice"]
        assert remote == {"machine1": ["bob"]}
        assert "invalid" in errors

    def test_route_empty_list(self):
        """Test routing empty recipient list."""
        router = InternetRouter("local")
        local, remote, frames, errors = router.route([])

        assert local == []
        assert remote == {}
        assert errors == {}


class TestAddressType:
    """Test address type classification."""

    def test_is_local(self):
        """Test is_local() method."""
        addr = InternetAddress("alice", "local", "alice@local", AddressType.LOCAL)
        assert addr.is_local()
        assert not addr.is_remote()

    def test_is_remote(self):
        """Test is_remote() method."""
        addr = InternetAddress("bob", "machine1", "bob@machine1", AddressType.REMOTE)
        assert addr.is_remote()
        assert not addr.is_local()

    def test_is_federated(self):
        """Test is_federated() method."""
        addr = InternetAddress(
            "charlie", "domain.com", "charlie@domain.com", AddressType.FEDERATED
        )
        assert addr.is_federated()

    def test_str_representation(self):
        """Test string representation."""
        addr = InternetAddress("alice", "local", "alice@local", AddressType.LOCAL)
        assert str(addr) == "alice@local"


class TestWebSocketTransport:
    """Test WebSocket transport."""

    def test_init(self):
        """Test transport initialization."""
        transport = WebSocketTransport(timeout=5.0)
        assert transport.timeout == 5.0

    def test_default_timeout(self):
        """Test default timeout."""
        transport = WebSocketTransport()
        assert transport.timeout == 10.0


class TestModuleConvenience:
    """Test module-level convenience functions."""

    def test_is_internet_address(self):
        """Test is_internet_address function."""
        assert is_internet_address("alice@local")
        assert is_internet_address("bob@remote")
        assert not is_internet_address("alice")

    def test_parse_address(self):
        """Test parse_address function."""
        addr = parse_address("alice@local")
        assert addr is not None
        assert addr.user == "alice"
        assert addr.address_type == AddressType.LOCAL

        invalid = parse_address("invalid")
        assert invalid is None

    def test_route_recipients(self):
        """Test route_recipients function."""
        local, remote, frames, errors = route_recipients(
            [
                "alice@local",
                "bob@machine1",
            ]
        )

        assert local == ["alice"]
        assert remote == {"machine1": ["bob"]}
        assert frames == {}
        assert errors == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
