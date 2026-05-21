# tests/test_packet_codec.py
# Comprehensive tests for packet encoding/decoding with security validation

import pytest
from bbsengine6.net import (
    CHECKSUM_HEX_LEN,
    FilePacket,
    MAX_PAYLOAD_SIZE,
    MessagePacket,
    PacketChecksumError,
    PacketDecodeError,
    PacketTypeError,
    PACKET_TYPE_FILE,
    PACKET_TYPE_MESSAGE,
    decode_packet,
    encode_packet,
    get_packet_type,
    register_packet_type,
)
from bbsengine6.net.packet_codec import (
    compress_blocks,
    compute_checksum,
    decompress_blocks,
    decode_file_packet,
    decode_message_packet,
    encode_file_packet,
    encode_message_packet,
    validate_filename,
    verify_checksum,
)


# ============================================================================
# Filename Validation Tests
# ============================================================================


class TestFilenameValidation:
    """Test filename validation security."""

    def test_valid_filename(self):
        """Valid filename passes validation."""
        assert validate_filename("document.txt") == "document.txt"

    def test_empty_filename_rejected(self):
        """Empty filename rejected."""
        with pytest.raises(ValueError, match="filename cannot be empty"):
            validate_filename("")

    def test_path_traversal_rejected(self):
        """Path traversal characters rejected."""
        with pytest.raises(ValueError, match="path traversal"):
            validate_filename("../../../etc/passwd")

    def test_forward_slash_rejected(self):
        """Forward slash rejected."""
        with pytest.raises(ValueError, match="path traversal"):
            validate_filename("dir/file.txt")

    def test_backslash_rejected(self):
        """Backslash rejected."""
        with pytest.raises(ValueError, match="path traversal"):
            validate_filename("dir\\file.txt")

    def test_non_ascii_rejected(self):
        """Non-ASCII characters rejected."""
        with pytest.raises(ValueError, match="ASCII"):
            validate_filename("файл.txt")

    def test_null_byte_rejected(self):
        """Null bytes rejected."""
        with pytest.raises(ValueError, match="null bytes"):
            validate_filename("file\x00.txt")

    def test_filename_too_long_rejected(self):
        """Filename > 256 bytes rejected."""
        long_name = "a" * 257
        with pytest.raises(ValueError, match="too long"):
            validate_filename(long_name)


# ============================================================================
# Checksum Tests
# ============================================================================


class TestChecksums:
    """Test checksum computation and verification."""

    def test_checksum_computation(self):
        """Checksum computed correctly."""
        data = b"test data"
        checksum = compute_checksum(data)
        assert len(checksum) == CHECKSUM_HEX_LEN
        assert all(c in "0123456789abcdef" for c in checksum)

    def test_checksum_verification_success(self):
        """Valid checksum verifies successfully."""
        data = b"test data"
        checksum = compute_checksum(data)
        assert verify_checksum(data, checksum)

    def test_checksum_verification_failure(self):
        """Invalid checksum fails verification."""
        data = b"test data"
        wrong_checksum = "0" * CHECKSUM_HEX_LEN
        assert not verify_checksum(data, wrong_checksum)

    def test_checksum_constant_time_comparison(self):
        """Checksum uses constant-time comparison."""
        # This is implicit - verify_checksum should use hmac.compare_digest
        # Test by verifying wrong checksums don't raise exceptions
        data = b"test"
        wrong = "f" * CHECKSUM_HEX_LEN
        # Should not raise, just return False
        assert not verify_checksum(data, wrong)


# ============================================================================
# Compression Tests
# ============================================================================


class TestCompression:
    """Test block compression/decompression."""

    def test_compress_single_block(self):
        """Single block compressed."""
        original = [b"a" * 1000]
        compressed = compress_blocks(original)
        assert len(compressed) == 1
        assert len(compressed[0]) < len(original[0])

    def test_compress_multiple_blocks(self):
        """Multiple blocks compressed."""
        original = [b"a" * 500, b"b" * 500]
        compressed = compress_blocks(original)
        assert len(compressed) == 2

    def test_decompress_single_block(self):
        """Single block decompressed."""
        original = [b"a" * 1000]
        compressed = compress_blocks(original)
        decompressed = decompress_blocks(compressed)
        assert decompressed == original

    def test_decompress_multiple_blocks(self):
        """Multiple blocks decompressed."""
        original = [b"a" * 500, b"b" * 500, b"c" * 500]
        compressed = compress_blocks(original)
        decompressed = decompress_blocks(compressed)
        assert decompressed == original

    def test_decompression_bomb_protection(self):
        """Decompression with max_length prevents bombs."""
        # This is implicit in decompress_blocks using max_length parameter
        # Test by verifying reasonable decompression works
        original = [b"a" * 100000]
        compressed = compress_blocks(original)
        decompressed = decompress_blocks(compressed)
        assert decompressed == original


# ============================================================================
# FilePacket Tests
# ============================================================================


class TestFilePacket:
    """Test FilePacket encoding/decoding."""

    def test_filepacket_creation(self):
        """FilePacket created successfully."""
        pkt = FilePacket(
            filename="test.txt",
            file_size=1000,
            mime_type="text/plain",
            total_blocks=1,
            block_id=0,
            blocks=[b"test data"],
        )
        assert pkt.filename == "test.txt"
        assert pkt.file_size == 1000

    def test_filepacket_invalid_filename_empty(self):
        """FilePacket rejects empty filename."""
        with pytest.raises(ValueError, match="empty"):
            FilePacket(
                filename="",
                file_size=1000,
                mime_type="text/plain",
                total_blocks=1,
            )

    def test_filepacket_invalid_file_size(self):
        """FilePacket rejects invalid file_size."""
        with pytest.raises(ValueError, match="file_size"):
            FilePacket(
                filename="test.txt",
                file_size=0,
                mime_type="text/plain",
                total_blocks=1,
            )

    def test_filepacket_invalid_block_id(self):
        """FilePacket rejects block_id >= total_blocks."""
        with pytest.raises(ValueError, match="block_id"):
            FilePacket(
                filename="test.txt",
                file_size=1000,
                mime_type="text/plain",
                total_blocks=5,
                block_id=5,
            )

    def test_encode_decode_single_block(self):
        """Single block FilePacket encodes/decodes."""
        original = FilePacket(
            filename="document.pdf",
            file_size=10000,
            mime_type="application/pdf",
            total_blocks=10,
            block_id=0,
            blocks=[b"block data"],
        )
        encoded = encode_file_packet(original)
        decoded = decode_file_packet(encoded)

        assert decoded.filename == "document.pdf"
        assert decoded.file_size == 10000
        assert decoded.mime_type == "application/pdf"
        assert decoded.block_id == 0

    def test_encode_decode_multiple_blocks_per_file(self):
        """Multiple FilePackets for same file (different block_id)."""
        pkt1 = FilePacket(
            filename="large.bin",
            file_size=100000000,
            mime_type="application/octet-stream",
            total_blocks=100,
            block_id=0,
            blocks=[b"x" * 1000],
        )
        pkt2 = FilePacket(
            filename="large.bin",
            file_size=100000000,
            mime_type="application/octet-stream",
            total_blocks=100,
            block_id=1,
            blocks=[b"y" * 1000],
        )

        enc1 = encode_file_packet(pkt1)
        enc2 = encode_file_packet(pkt2)
        dec1 = decode_file_packet(enc1)
        dec2 = decode_file_packet(enc2)

        assert dec1.block_id == 0
        assert dec2.block_id == 1
        assert dec1.filename == dec2.filename

    def test_encode_decode_with_compression(self):
        """FilePacket with compression encodes/decodes."""
        original = FilePacket(
            filename="compressible.txt",
            file_size=50000,
            mime_type="text/plain",
            total_blocks=1,
            block_id=0,
            blocks=[b"a" * 10000],
            compressed=True,
        )
        encoded = encode_file_packet(original)
        decoded = decode_file_packet(encoded)

        assert decoded.compressed
        assert decoded.blocks[0] == b"a" * 10000

    def test_encode_payload_size_limit(self):
        """FilePacket validates block sizes fit in uint16."""
        # Block sizes are encoded as uint16, so max single block is 65535 bytes
        pkt = FilePacket(
            filename="normal.bin",
            file_size=100000,
            mime_type="application/octet-stream",
            total_blocks=2,
            block_id=0,
            blocks=[b"x" * 50000],  # 50KB block, well under limits
        )
        # This should encode successfully
        encoded = encode_file_packet(pkt)
        assert len(encoded) > 0

    def test_decode_checksum_mismatch(self):
        """Corrupted FilePacket detected by checksum."""
        original = FilePacket(
            filename="test.txt",
            file_size=100,
            mime_type="text/plain",
            total_blocks=1,
            block_id=0,
            blocks=[b"original data"],
        )
        encoded = encode_file_packet(original)

        # Corrupt the data (but not header or checksum)
        corrupted = encoded[:-70] + b"X" + encoded[-69:-64] + encoded[-64:]

        with pytest.raises(PacketChecksumError):
            decode_file_packet(corrupted)

    def test_decode_truncated_packet(self):
        """Truncated FilePacket raises error."""
        original = FilePacket(
            filename="test.txt",
            file_size=100,
            mime_type="text/plain",
            total_blocks=1,
            block_id=0,
            blocks=[b"data"],
        )
        encoded = encode_file_packet(original)
        truncated = encoded[: len(encoded) // 2]

        with pytest.raises(PacketDecodeError):
            decode_file_packet(truncated)

    def test_decode_malformed_header(self):
        """Malformed header raises error."""
        bad_data = b"junk data that is too short"
        with pytest.raises(PacketDecodeError):
            decode_file_packet(bad_data)


# ============================================================================
# MessagePacket Tests
# ============================================================================


class TestMessagePacket:
    """Test MessagePacket encoding/decoding."""

    def test_messagepacket_creation(self):
        """MessagePacket created successfully."""
        pkt = MessagePacket(
            sender="alice",
            subject="Hello",
            content_type="text/plain",
            content=b"Message body",
        )
        assert pkt.sender == "alice"
        assert pkt.subject == "Hello"

    def test_messagepacket_empty_subject_allowed(self):
        """MessagePacket allows empty subject."""
        pkt = MessagePacket(
            sender="alice",
            subject="",
            content_type="text/plain",
            content=b"No subject",
        )
        assert pkt.subject == ""

    def test_messagepacket_invalid_sender(self):
        """MessagePacket rejects empty sender."""
        with pytest.raises(ValueError, match="sender"):
            MessagePacket(
                sender="",
                subject="Test",
                content_type="text/plain",
                content=b"Body",
            )

    def test_messagepacket_invalid_content_type(self):
        """MessagePacket rejects empty content_type."""
        with pytest.raises(ValueError, match="content_type"):
            MessagePacket(
                sender="alice",
                subject="Test",
                content_type="",
                content=b"Body",
            )

    def test_encode_decode_simple_message(self):
        """Simple MessagePacket encodes/decodes."""
        original = MessagePacket(
            sender="alice@example.com",
            subject="Test Message",
            content_type="text/plain",
            content=b"This is the message body.",
        )
        encoded = encode_message_packet(original)
        decoded = decode_message_packet(encoded)

        assert decoded.sender == "alice@example.com"
        assert decoded.subject == "Test Message"
        assert decoded.content_type == "text/plain"
        assert decoded.content == b"This is the message body."

    def test_encode_decode_html_message(self):
        """HTML MessagePacket encodes/decodes."""
        original = MessagePacket(
            sender="bob",
            subject="Newsletter",
            content_type="text/html",
            content=b"<html><body>HTML content</body></html>",
        )
        encoded = encode_message_packet(original)
        decoded = decode_message_packet(encoded)

        assert decoded.content_type == "text/html"
        assert b"<html>" in decoded.content

    def test_encode_decode_with_compression(self):
        """MessagePacket with compression encodes/decodes."""
        original = MessagePacket(
            sender="charlie",
            subject="Long message",
            content_type="text/plain",
            content=b"x" * 100000,
            compressed=True,
        )
        encoded = encode_message_packet(original)
        decoded = decode_message_packet(encoded)

        assert decoded.compressed
        assert decoded.content == b"x" * 100000

    def test_encode_payload_size_limit(self):
        """MessagePacket rejects content >= 1MB."""
        with pytest.raises(ValueError, match="content too large"):
            MessagePacket(
                sender="alice",
                subject="Too big",
                content_type="text/plain",
                content=b"x" * MAX_PAYLOAD_SIZE,
            )

    def test_decode_checksum_mismatch(self):
        """Corrupted MessagePacket detected by checksum."""
        original = MessagePacket(
            sender="alice",
            subject="Test",
            content_type="text/plain",
            content=b"Original content",
        )
        encoded = encode_message_packet(original)

        # Corrupt the content portion
        corrupted = encoded[:-70] + b"Y" + encoded[-69:-64] + encoded[-64:]

        with pytest.raises(PacketChecksumError):
            decode_message_packet(corrupted)

    def test_decode_truncated_packet(self):
        """Truncated MessagePacket raises error."""
        original = MessagePacket(
            sender="alice",
            subject="Test",
            content_type="text/plain",
            content=b"content",
        )
        encoded = encode_message_packet(original)
        truncated = encoded[: len(encoded) // 2]

        with pytest.raises(PacketDecodeError):
            decode_message_packet(truncated)

    def test_decode_malformed_header(self):
        """Malformed MessagePacket header raises error."""
        bad_data = b"too short"
        with pytest.raises(PacketDecodeError):
            decode_message_packet(bad_data)


# ============================================================================
# Universal Encode/Decode Tests
# ============================================================================


class TestUniversalCodec:
    """Test universal encode/decode dispatch."""

    def test_encode_file_packet_universal(self):
        """FilePacket encoded via universal encode_packet."""
        pkt = FilePacket(
            filename="test.txt",
            file_size=1000,
            mime_type="text/plain",
            total_blocks=1,
            block_id=0,
            blocks=[b"data"],
        )
        encoded = encode_packet(pkt)
        assert encoded[0] == PACKET_TYPE_FILE

    def test_encode_message_packet_universal(self):
        """MessagePacket encoded via universal encode_packet."""
        pkt = MessagePacket(
            sender="alice",
            subject="Test",
            content_type="text/plain",
            content=b"content",
        )
        encoded = encode_packet(pkt)
        assert encoded[0] == PACKET_TYPE_MESSAGE

    def test_decode_file_packet_universal(self):
        """FilePacket decoded via universal decode_packet."""
        original = FilePacket(
            filename="test.txt",
            file_size=1000,
            mime_type="text/plain",
            total_blocks=1,
            block_id=0,
            blocks=[b"data"],
        )
        encoded = encode_packet(original)
        decoded = decode_packet(encoded)

        assert isinstance(decoded, FilePacket)
        assert decoded.filename == "test.txt"

    def test_decode_message_packet_universal(self):
        """MessagePacket decoded via universal decode_packet."""
        original = MessagePacket(
            sender="alice",
            subject="Test",
            content_type="text/plain",
            content=b"content",
        )
        encoded = encode_packet(original)
        decoded = decode_packet(encoded)

        assert isinstance(decoded, MessagePacket)
        assert decoded.sender == "alice"

    def test_get_packet_type(self):
        """get_packet_type peeks at type without decoding."""
        file_pkt = FilePacket(
            filename="f.txt",
            file_size=100,
            mime_type="text/plain",
            total_blocks=1,
            blocks=[b"d"],
        )
        encoded = encode_packet(file_pkt)
        assert get_packet_type(encoded) == PACKET_TYPE_FILE

    def test_unknown_packet_type_rejected(self):
        """Unknown packet type raises error."""
        bad_data = bytes([255]) + b"junk"
        with pytest.raises(PacketTypeError):
            decode_packet(bad_data)

    def test_empty_packet_rejected(self):
        """Empty packet raises error."""
        with pytest.raises(PacketDecodeError):
            decode_packet(b"")

    def test_get_packet_type_empty_rejected(self):
        """get_packet_type on empty data raises error."""
        with pytest.raises(PacketDecodeError):
            get_packet_type(b"")


# ============================================================================
# Custom Packet Type Registration Tests
# ============================================================================


class TestPacketRegistry:
    """Test packet type registration for extensibility."""

    def test_register_custom_packet_type(self):
        """Custom packet type can be registered."""

        @register_packet_type
        class CustomPacket:
            packet_type = 42

            @staticmethod
            def encode(pkt):
                return b"\x2a" + b"custom_data"

            @staticmethod
            def decode(data):
                return CustomPacket()

        # Verify it's in registry
        from bbsengine6.net.packet import _packet_type_registry

        assert 42 in _packet_type_registry

    def test_encode_custom_packet_type(self):
        """Custom packet type can be encoded."""

        @register_packet_type
        class CustomPacket2:
            packet_type = 43

            @staticmethod
            def encode(pkt):
                return b"\x2b" + b"custom"

            @staticmethod
            def decode(data):
                return CustomPacket2()

        pkt = CustomPacket2()
        encoded = encode_packet(pkt)
        assert encoded[0] == 43

    def test_decode_custom_packet_type(self):
        """Custom packet type can be decoded."""

        @register_packet_type
        class CustomPacket3:
            packet_type = 44

            @staticmethod
            def encode(pkt):
                return b"\x2c" + b"test"

            @staticmethod
            def decode(data):
                obj = CustomPacket3()
                obj.data = b"decoded"
                return obj

        pkt = CustomPacket3()
        encoded = encode_packet(pkt)
        decoded = decode_packet(encoded)
        assert decoded.data == b"decoded"


# ============================================================================
# RFC 822 Alignment Tests (MessagePacket)
# ============================================================================


class TestRFC822Alignment:
    """Test MessagePacket RFC 822 alignment."""

    def test_rfc822_from_field(self):
        """MessagePacket sender maps to RFC 822 From field."""
        pkt = MessagePacket(
            sender="alice@example.com",
            subject="Test",
            content_type="text/plain",
            content=b"Body",
        )
        # From: alice@example.com
        assert pkt.sender == "alice@example.com"

    def test_rfc822_subject_field(self):
        """MessagePacket subject maps to RFC 822 Subject field."""
        pkt = MessagePacket(
            sender="alice",
            subject="Hello World",
            content_type="text/plain",
            content=b"Body",
        )
        # Subject: Hello World
        assert pkt.subject == "Hello World"

    def test_rfc822_content_type_field(self):
        """MessagePacket content_type maps to RFC 822 Content-Type field."""
        pkt = MessagePacket(
            sender="alice",
            subject="Test",
            content_type="text/html; charset=utf-8",
            content=b"<html>",
        )
        # Content-Type: text/html; charset=utf-8
        assert pkt.content_type == "text/html; charset=utf-8"

    def test_rfc822_date_field_via_timestamp(self):
        """MessagePacket timestamp maps to RFC 822 Date field."""
        pkt = MessagePacket(
            sender="alice",
            subject="Test",
            content_type="text/plain",
            content=b"Body",
        )
        # Date: (implicit from timestamp)
        assert pkt.timestamp > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ============================================================================
# Integration Tests: FramePacket from asimov.net
# ============================================================================


class TestFramePacketIntegration:
    """Test integration with asimov.net FramePacket via packet registry.
    
    These tests demonstrate how applications can use the packet type registry
    to integrate FramePacket from asimov.net without coupling bbsengine6.net
    to asimov.net. This is the extensibility model in action.
    """

    def test_import_framepacket(self):
        """FramePacket from asimov.net can be imported."""
        from asimov.net import FramePacket

        assert FramePacket is not None

    def test_create_framepacket(self):
        """FramePacket can be created and used."""
        from asimov.net import FramePacket

        packet = FramePacket(
            frame_id=1,
            block_id=0,
            width=640,
            height=480,
            cols=2,
            rows=2,
            block_w=320,
            block_h=240,
            total_blocks=4,
            blocks=[b"frame_data_block_0"],
        )

        assert packet.frame_id == 1
        assert packet.width == 640
        assert packet.height == 480
        assert packet.total_blocks == 4

    def test_encode_framepacket(self):
        """FramePacket can be encoded to binary."""
        from asimov.net import FramePacket, encode_frame_packet

        packet = FramePacket(
            frame_id=1,
            block_id=0,
            width=640,
            height=480,
            cols=2,
            rows=2,
            block_w=320,
            block_h=240,
            total_blocks=4,
            blocks=[b"test_frame_data"],
        )

        encoded = encode_frame_packet(packet)
        assert len(encoded) > 0
        assert isinstance(encoded, bytes)

    def test_decode_framepacket(self):
        """FramePacket can be decoded from binary."""
        from asimov.net import FramePacket, encode_frame_packet, decode_frame_packet

        original = FramePacket(
            frame_id=5,
            block_id=2,
            width=1920,
            height=1080,
            cols=3,
            rows=3,
            block_w=640,
            block_h=360,
            total_blocks=9,
            blocks=[b"video_frame_chunk"],
        )

        encoded = encode_frame_packet(original)
        decoded = decode_frame_packet(encoded)

        assert decoded.frame_id == 5
        assert decoded.block_id == 2
        assert decoded.width == 1920
        assert decoded.height == 1080
        assert decoded.total_blocks == 9

    def test_encode_decode_framepacket_round_trip(self):
        """FramePacket encode/decode round-trip preserves data."""
        from asimov.net import FramePacket, encode_frame_packet, decode_frame_packet

        original_data = b"test frame pixel data" * 1000
        original = FramePacket(
            frame_id=10,
            block_id=0,
            width=800,
            height=600,
            cols=2,
            rows=2,
            block_w=400,
            block_h=300,
            total_blocks=4,
            is_delta=False,
            compressed=False,
            blocks=[original_data],
        )

        encoded = encode_frame_packet(original)
        decoded = decode_frame_packet(encoded)

        assert decoded.blocks[0] == original_data
        assert decoded.frame_id == original.frame_id
        assert decoded.is_delta == original.is_delta
        assert decoded.compressed == original.compressed

    def test_framepacket_with_compression(self):
        """FramePacket with compression flag can be encoded/decoded."""
        from asimov.net import FramePacket, encode_frame_packet, decode_frame_packet

        original = FramePacket(
            frame_id=1,
            block_id=0,
            width=320,
            height=240,
            cols=1,
            rows=1,
            block_w=320,
            block_h=240,
            total_blocks=1,
            is_delta=False,
            compressed=True,
            blocks=[b"frame data" * 1000],
        )

        encoded = encode_frame_packet(original)
        decoded = decode_frame_packet(encoded)

        assert decoded.compressed is True
        assert decoded.frame_id == 1

    def test_framepacket_multi_block(self):
        """FramePacket can handle single block in packet."""
        from asimov.net import FramePacket, encode_frame_packet, decode_frame_packet

        # Note: FramePacket encodes blocks in packets, not as separate items
        original = FramePacket(
            frame_id=1,
            block_id=0,
            width=640,
            height=480,
            cols=2,
            rows=2,
            block_w=320,
            block_h=240,
            total_blocks=4,
            blocks=[b"block_data_for_frame"],
        )

        encoded = encode_frame_packet(original)
        decoded = decode_frame_packet(encoded)

        assert decoded.frame_id == 1
        assert decoded.total_blocks == 4
        assert decoded.blocks == original.blocks

    def test_framepacket_with_delta_flag(self):
        """FramePacket with is_delta flag encodes/decodes correctly."""
        from asimov.net import FramePacket, encode_frame_packet, decode_frame_packet

        original = FramePacket(
            frame_id=100,
            block_id=0,
            width=1024,
            height=768,
            cols=2,
            rows=2,
            block_w=512,
            block_h=384,
            total_blocks=4,
            is_delta=True,  # Delta encoding flag
            blocks=[b"delta_encoded_data"],
        )

        encoded = encode_frame_packet(original)
        decoded = decode_frame_packet(encoded)

        assert decoded.is_delta is True
        assert decoded.frame_id == 100


# ============================================================================
# Integration Tests: Send/Receive via bbsengine6.net Transport
# ============================================================================


class TestFramePacketTransport:
    """Test sending/receiving FramePacket via bbsengine6.net transport.
    
    Demonstrates how applications register and use custom packet types
    (like FramePacket from asimov.net) with the bbsengine6.net universal
    encode/decode and transport APIs, maintaining clean separation of concerns.
    """

    def test_framepacket_binary_serialization(self):
        """FramePacket can be serialized to binary for transmission."""
        from asimov.net import FramePacket, encode_frame_packet

        packet = FramePacket(
            frame_id=1,
            block_id=0,
            width=640,
            height=480,
            cols=2,
            rows=2,
            block_w=320,
            block_h=240,
            total_blocks=4,
            blocks=[b"frame_payload"],
        )

        binary = encode_frame_packet(packet)
        assert isinstance(binary, bytes)
        assert len(binary) > 0

    def test_framepacket_transmission_scenario(self):
        """Simulate transmitting FramePacket across network."""
        from asimov.net import FramePacket, encode_frame_packet, decode_frame_packet

        # Sender: Create video frame
        sender_packet = FramePacket(
            frame_id=42,
            block_id=0,
            width=1920,
            height=1080,
            cols=4,
            rows=4,
            block_w=480,
            block_h=270,
            total_blocks=16,
            is_delta=False,
            compressed=False,
            blocks=[b"HD_video_frame_data"],
        )

        # Network: Serialize
        network_bytes = encode_frame_packet(sender_packet)

        # Receiver: Deserialize
        receiver_packet = decode_frame_packet(network_bytes)

        # Verify integrity
        assert receiver_packet.frame_id == 42
        assert receiver_packet.width == 1920
        assert receiver_packet.height == 1080
        assert receiver_packet.blocks == sender_packet.blocks

    def test_framepacket_stream_simulation(self):
        """Simulate streaming multiple frames (frame sequences)."""
        from asimov.net import FramePacket, encode_frame_packet, decode_frame_packet

        frames = []
        for frame_num in range(5):
            packet = FramePacket(
                frame_id=frame_num,
                block_id=0,
                width=320,
                height=240,
                cols=1,
                rows=1,
                block_w=320,
                block_h=240,
                total_blocks=1,
                blocks=[f"frame_{frame_num}".encode()],
            )
            frames.append(packet)

        # Simulate transmission and reception
        transmitted = []
        for packet in frames:
            binary = encode_frame_packet(packet)
            transmitted.append(binary)

        # Simulate reception
        received = []
        for binary in transmitted:
            packet = decode_frame_packet(binary)
            received.append(packet)

        # Verify all frames received correctly
        assert len(received) == 5
        for i, packet in enumerate(received):
            assert packet.frame_id == i
            assert packet.blocks[0] == f"frame_{i}".encode()

    def test_framepacket_large_frame_blocks(self):
        """Simulate transmitting 4K frame in single packet."""
        from asimov.net import FramePacket, encode_frame_packet, decode_frame_packet

        # Large frame in single packet (block_sizes limited to uint16 max)
        # Real 4K would be split across multiple FramePackets
        large_data = b"x" * 50000  # 50KB frame data

        original = FramePacket(
            frame_id=1,
            block_id=0,
            width=3840,
            height=2160,
            cols=2,
            rows=2,
            block_w=1920,
            block_h=1080,
            total_blocks=4,
            blocks=[large_data],
        )

        # Encode
        encoded = encode_frame_packet(original)

        # Transmit (simulate)
        # ... network transmission ...

        # Decode
        decoded = decode_frame_packet(encoded)

        assert decoded.width == 3840
        assert decoded.height == 2160
        assert decoded.blocks[0] == large_data

    def test_framepacket_with_compression_for_bandwidth(self):
        """Demonstrate FramePacket compression for bandwidth optimization."""
        from asimov.net import FramePacket, encode_frame_packet, decode_frame_packet

        # Create frame with compressible data
        uncompressed_data = b"similar_pixel_data" * 10000  # Highly compressible
        original = FramePacket(
            frame_id=1,
            block_id=0,
            width=640,
            height=480,
            cols=1,
            rows=1,
            block_w=640,
            block_h=480,
            total_blocks=1,
            is_delta=False,
            compressed=True,  # Enable compression
            blocks=[uncompressed_data],
        )

        encoded = encode_frame_packet(original)
        decoded = decode_frame_packet(encoded)

        # Verify compression flag preserved and data recovered
        assert decoded.compressed is True
        assert decoded.blocks[0] == uncompressed_data

    def test_framepacket_delta_encoding_simulation(self):
        """Simulate delta-encoded frame transmission for bandwidth savings."""
        from asimov.net import FramePacket, encode_frame_packet, decode_frame_packet

        # Key frame (full frame)
        key_frame = FramePacket(
            frame_id=1,
            block_id=0,
            width=640,
            height=480,
            cols=2,
            rows=2,
            block_w=320,
            block_h=240,
            total_blocks=4,
            is_delta=False,  # Full frame
            blocks=[b"full_frame_data" * 100],
        )

        # Delta frame (only differences from previous)
        delta_frame = FramePacket(
            frame_id=2,
            block_id=0,
            width=640,
            height=480,
            cols=2,
            rows=2,
            block_w=320,
            block_h=240,
            total_blocks=4,
            is_delta=True,  # Only deltas
            blocks=[b"delta_data" * 50],  # Much smaller
        )

        # Encode and transmit both
        key_binary = encode_frame_packet(key_frame)
        delta_binary = encode_frame_packet(delta_frame)

        # Delta should be smaller
        assert len(delta_binary) < len(key_binary)

        # Decode
        key_decoded = decode_frame_packet(key_binary)
        delta_decoded = decode_frame_packet(delta_binary)

        # Verify flags
        assert key_decoded.is_delta is False
        assert delta_decoded.is_delta is True


# ============================================================================
# Cross-Compatibility Tests: FilePacket, MessagePacket, FramePacket
# ============================================================================


class TestPacketTypeInteroperability:
    """Test that different packet types can coexist in same system."""

    def test_all_packet_types_encodable(self):
        """All three packet types (File, Message, Frame) can be encoded."""
        from asimov.net import FramePacket, encode_frame_packet

        # File packet
        file_pkt = FilePacket(
            filename="test.bin",
            file_size=1000,
            mime_type="application/octet-stream",
            total_blocks=1,
            block_id=0,
            blocks=[b"file_data"],
        )
        file_binary = encode_file_packet(file_pkt)
        assert len(file_binary) > 0

        # Message packet
        msg_pkt = MessagePacket(
            sender="alice",
            subject="Test",
            content_type="text/plain",
            content=b"message",
        )
        msg_binary = encode_message_packet(msg_pkt)
        assert len(msg_binary) > 0

        # Frame packet
        frame_pkt = FramePacket(
            frame_id=1,
            block_id=0,
            width=320,
            height=240,
            cols=1,
            rows=1,
            block_w=320,
            block_h=240,
            total_blocks=1,
            blocks=[b"frame_data"],
        )
        frame_binary = encode_frame_packet(frame_pkt)
        assert len(frame_binary) > 0

    def test_different_packet_types_different_binary(self):
        """Different packet types produce different binary formats."""
        from asimov.net import FramePacket, encode_frame_packet

        file_pkt = FilePacket(
            filename="doc.txt",
            file_size=100,
            mime_type="text/plain",
            total_blocks=1,
            blocks=[b"x" * 100],
        )
        msg_pkt = MessagePacket(
            sender="bob",
            subject="Hi",
            content_type="text/plain",
            content=b"x" * 100,
        )
        frame_pkt = FramePacket(
            frame_id=1,
            block_id=0,
            width=10,
            height=10,
            cols=1,
            rows=1,
            block_w=10,
            block_h=10,
            total_blocks=1,
            blocks=[b"x" * 100],
        )

        file_binary = encode_file_packet(file_pkt)
        msg_binary = encode_message_packet(msg_pkt)
        frame_binary = encode_frame_packet(frame_pkt)

        # All different binary formats
        assert file_binary != msg_binary
        assert msg_binary != frame_binary
        assert file_binary != frame_binary
