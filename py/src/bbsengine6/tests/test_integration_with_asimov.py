# test_integration_with_asimov.py
# Integration tests demonstrating frame transmission between asimov and bbsengine6

import pytest
import socket
import threading
import time

# Import asimov frame code
from asimov.net import (
    Frame,
    FrameAddress,
    FrameAddressParser,
    TCPSender,
    TCPReceiver,
    UDPSender,
    UDPReceiver,
    encode_frame_packet,
    decode_frame_packet,
    FramePacket,
    frame_from_any,
    frames_equal,
    FrameScheme,
    default_port_for_scheme,
)

# Import bbsengine6 routing
from bbsengine6.net import InternetRouter, AddressParser


class TestFrameTypes:
    """Test frame type abstractions from asimov.net"""

    def test_frame_from_bytes(self):
        """Test creating Frame from raw bytes"""
        # Frame expects width*height*3 bytes (RGB)
        # 10x20x3 = 600 bytes
        data = b"\x00\x01\x02" * 200  # 600 bytes
        frame = Frame(data, width=10, height=20)

        assert frame.width == 10 and frame.height == 20
        assert frame.to_bytes() == data
        assert len(frame.to_bytes()) == 600

    def test_frame_numpy_optional(self):
        """Test NumpyFrame when numpy is available"""
        try:
            import numpy as np
            from asimov.net import NumpyFrame

            array = np.zeros((480, 640, 3), dtype=np.uint8)
            frame = NumpyFrame(array)

            assert frame.width == 640 and frame.height == 480
            bytes_data = frame.to_bytes()
            assert isinstance(bytes_data, bytes)
        except ImportError:
            pytest.skip("numpy not available")

    def test_frame_from_any(self):
        """Test frame_from_any helper"""
        # 10x10x3 = 300 bytes
        data = b"\x00\x01\x02" * 100
        frame1 = frame_from_any(data, 10, 10)
        assert isinstance(frame1, Frame)
        assert frame1.width == 10 and frame1.height == 10

    def test_frame_equality(self):
        """Test frame equality check"""
        data = b"\x00\x01\x02" * 100
        frame1 = Frame(data, 10, 10)
        frame2 = Frame(data, 10, 10)

        assert frames_equal(frame1, frame2)


class TestFrameAddressing:
    """Test RFC 3986 DSN frame addressing from asimov.net"""

    def test_parse_tcp_dsn(self):
        """Test parsing TCP DSN address"""
        parser = FrameAddressParser()
        result = parser.parse("tcp://camera.local:5000/")

        assert result.success
        assert result.value.scheme.name == "TCP"
        assert result.value.host == "camera.local"
        assert result.value.port == 5000

    def test_parse_udp_dsn_with_params(self):
        """Test parsing UDP DSN with query parameters"""
        parser = FrameAddressParser()
        result = parser.parse("udp://192.168.1.100:6000?timeout=30&retry=5")

        assert result.success
        assert result.value.scheme.name == "UDP"
        assert result.value.host == "192.168.1.100"
        assert result.value.port == 6000
        assert result.value.timeout == 30
        assert result.value.retry == 5

    def test_parse_invalid_dsn(self):
        """Test parsing invalid DSN"""
        parser = FrameAddressParser()
        result = parser.parse("http://invalid-scheme.com")

        assert not result.success
        assert result.error is not None

    def test_default_port_for_scheme(self):
        """Test default port selection for schemes"""
        assert default_port_for_scheme(FrameScheme.TCP) == 4200
        assert default_port_for_scheme(FrameScheme.UDP) == 4200


class TestHybridRouting:
    """Test hybrid routing of notifications and frames"""

    def test_route_mixed_addresses(self):
        """Test routing mixed notification and frame addresses"""
        router = InternetRouter(local_machine="test-host")

        addresses = [
            "alice@test-host",
            "bob@remote.org",
            "tcp://camera.local:5000/",
            "udp://sensor.local:6000/",
        ]

        local_notif, remote_notif, frames, errors = router.route(addresses)

        # Check local notifications
        assert "alice" in local_notif

        # Check remote notifications
        assert "remote.org" in remote_notif
        assert "bob" in remote_notif["remote.org"]

        # Check frames
        assert "tcp://camera.local:5000/" in frames
        assert "udp://sensor.local:6000/" in frames

    def test_router_frame_address_type(self):
        """Test that router returns proper FrameAddress objects"""
        router = InternetRouter()

        local, remote, frames, errors = router.route(
            ["tcp://host:5000/", "udp://other:6000/"]
        )

        assert len(frames) == 2
        for addr_str, frame_addr in frames.items():
            assert isinstance(frame_addr, FrameAddress)
            assert frame_addr.host is not None
            assert frame_addr.port is not None

    def test_separate_notification_and_frame_routing(self):
        """Test that notifications and frames are properly separated"""
        router = InternetRouter(local_machine="hub")

        addresses = [
            "user1@hub",
            "user2@other",
            "tcp://cam1:5000",
            "user3@hub",
            "udp://sensor:6000",
        ]

        local, remote, frames, errors = router.route(addresses)

        # Should have 2 local notifications
        assert len(local) == 2
        assert "user1" in local
        assert "user3" in local

        # Should have 1 remote notification
        assert "other" in remote
        assert len(remote["other"]) == 1

        # Should have 2 frames
        assert len(frames) == 2

        # Should have no errors
        assert len(errors) == 0


class TestAddressingIntegration:
    """Test SMTP-like addressing integration"""

    def test_parse_local_address(self):
        """Test parsing local SMTP address"""
        parser = AddressParser("my-host")
        addr = parser.parse("alice@my-host")

        assert addr is not None
        assert addr.user == "alice"
        assert addr.is_local()

    def test_parse_remote_address(self):
        """Test parsing remote SMTP address"""
        parser = AddressParser("my-host")
        addr = parser.parse("bob@other-host")

        assert addr is not None
        assert addr.user == "bob"
        assert not addr.is_local()

    def test_parse_federated_address(self):
        """Test parsing federated SMTP address"""
        parser = AddressParser("local")
        addr = parser.parse("user@domain.example.com")

        assert addr is not None
        assert addr.user == "user"
        assert addr.is_federated()


class TestPacketProtocol:
    """Test packet encoding/decoding"""

    def test_encode_decode_frame_packet(self):
        """Test frame packet serialization"""
        # Create a frame packet
        packet = FramePacket(
            frame_id=1,
            block_id=0,
            cols=2,
            rows=2,
            block_w=320,
            block_h=240,
            width=640,
            height=480,
            total_blocks=4,
            is_delta=False,
            compressed=False,
            blocks=[b"block1", b"block2"],
            timestamp=time.time(),
            blocks_in_packet=2,
            block_sizes=[6, 6],
        )

        # Encode
        encoded = encode_frame_packet(packet)
        assert isinstance(encoded, bytes)
        assert len(encoded) > 26

        # Decode
        decoded = decode_frame_packet(encoded)
        assert decoded.frame_id == 1
        assert decoded.width == 640
        assert decoded.height == 480
        assert decoded.blocks_in_packet == 2


class TestCrossProjectIntegration:
    """Test complete workflow using both asimov and bbsengine6"""

    def test_complete_notification_and_frame_workflow(self):
        """Test end-to-end workflow with both notifications and frames"""
        # Step 1: Parse frame addresses using asimov
        frame_parser = FrameAddressParser()

        tcp_result = frame_parser.parse("tcp://camera1.local:5000?timeout=30")
        assert tcp_result.success

        udp_result = frame_parser.parse("udp://sensor2.local:6000?retry=3")
        assert udp_result.success

        # Step 2: Parse notification addresses using bbsengine6
        notif_parser = AddressParser("control-center")

        local_addr = notif_parser.parse("operator@control-center")
        assert local_addr.is_local()

        remote_addr = notif_parser.parse("supervisor@remote.office")
        assert not remote_addr.is_local()

        # Step 3: Route mixed recipients
        router = InternetRouter(local_machine="control-center")

        recipients = [
            "operator@control-center",
            "supervisor@remote.office",
            "tcp://camera1.local:5000",
            "udp://sensor2.local:6000",
        ]

        local, remote, frames, errors = router.route(recipients)

        # Verify routing
        assert len(local) == 1
        assert len(remote) == 1
        assert len(frames) == 2
        assert len(errors) == 0

    def test_frame_creation_and_serialization(self):
        """Test creating, serializing, and deserializing frame data"""
        # Step 1: Create frame from bytes (10x10x3 = 300 bytes)
        raw_frame = b"\x00\x01\x02" * 100
        frame = frame_from_any(raw_frame, 10, 10)

        assert frame.width == 10 and frame.height == 10
        assert frame.to_bytes() == raw_frame

        # Step 2: Create FramePacket for transmission
        packet = FramePacket(
            frame_id=1,
            block_id=0,
            cols=1,
            rows=1,
            block_w=10,
            block_h=10,
            width=10,
            height=10,
            total_blocks=1,
            is_delta=False,
            compressed=False,
            blocks=[raw_frame],
            timestamp=time.time(),
            blocks_in_packet=1,
            block_sizes=[len(raw_frame)],
        )

        # Step 3: Encode for transmission
        encoded = encode_frame_packet(packet)
        assert len(encoded) > 0

        # Step 4: Decode received data
        decoded = decode_frame_packet(encoded)
        assert decoded.frame_id == 1
        assert decoded.width == 10
        assert decoded.height == 10

    def test_hybrid_routing_with_frame_addresses(self):
        """Test router can classify and route frame addresses"""
        router = InternetRouter()

        addresses = [
            "alice@local",
            "bob@remote",
            "tcp://cam1:5000",
            "charlie@federated.example.com",
            "udp://sensor:6000",
            "dave@local",
            "tcp://cam2:5001?timeout=30",
        ]

        local, remote, frames, errors = router.route(addresses)

        # Verify proper classification
        assert len(local) == 2
        assert len(remote) >= 1
        assert len(frames) == 3
        assert len(errors) == 0

        # Verify frame addresses are correct type
        for addr_str, frame_addr in frames.items():
            assert isinstance(frame_addr, FrameAddress)
            assert frame_addr.port in [5000, 5001, 6000]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
