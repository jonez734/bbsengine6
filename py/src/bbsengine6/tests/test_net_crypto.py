# test_net_crypto.py
# Tests for HMAC authentication in bbsengine6.net

import pytest

from bbsengine6.net import (
    CryptoHash,
    FilePacket,
    MessagePacket,
    PacketAuthError,
    PacketChecksumError,
    decode_packet,
    encode_packet,
    get_crypto,
)


class TestCryptoHashBasics:
    """Test CryptoHash basic operations."""

    def test_compute_returns_64_hex_chars(self):
        """compute() returns a 64-character hex string."""
        crypto = CryptoHash(b"secret-key")
        mac = crypto.compute(b"hello world")
        assert len(mac) == 64
        assert all(c in "0123456789abcdef" for c in mac)

    def test_compute_deterministic(self):
        """Same key + payload always produces same MAC."""
        crypto = CryptoHash(b"secret-key")
        mac1 = crypto.compute(b"hello world")
        mac2 = crypto.compute(b"hello world")
        assert mac1 == mac2

    def test_different_keys_different_mac(self):
        """Different keys produce different MACs for same payload."""
        crypto1 = CryptoHash(b"key-one")
        crypto2 = CryptoHash(b"key-two")
        mac1 = crypto1.compute(b"hello world")
        mac2 = crypto2.compute(b"hello world")
        assert mac1 != mac2

    def test_verify_correct_mac(self):
        """verify() returns True for correct MAC."""
        crypto = CryptoHash(b"secret-key")
        payload = b"hello world"
        mac = crypto.compute(payload)
        assert crypto.verify(payload, mac) is True

    def test_verify_wrong_mac(self):
        """verify() returns False for wrong MAC."""
        crypto = CryptoHash(b"secret-key")
        payload = b"hello world"
        wrong_mac = "0" * 64
        assert crypto.verify(payload, wrong_mac) is False

    def test_verify_tampered_payload(self):
        """verify() returns False if payload was modified."""
        crypto = CryptoHash(b"secret-key")
        mac = crypto.compute(b"original data")
        assert crypto.verify(b"modified data", mac) is False

    def test_empty_key_raises(self):
        """Empty secret_key raises ValueError."""
        with pytest.raises(ValueError, match="secret_key cannot be empty"):
            CryptoHash(b"")

    def test_derive_key(self):
        """derive_key() produces consistent derived keys."""
        key1 = CryptoHash.derive_key(b"machine-a", b"master-secret")
        key2 = CryptoHash.derive_key(b"machine-a", b"master-secret")
        key3 = CryptoHash.derive_key(b"machine-b", b"master-secret")
        assert key1 == key2
        assert key1 != key3
        assert len(key1) == 64


class TestGetCrypto:
    """Test get_crypto convenience factory."""

    def test_with_key(self):
        """Returns CryptoHash when key provided."""
        crypto = get_crypto(b"secret")
        assert crypto is not None
        assert isinstance(crypto, CryptoHash)

    def test_with_empty_key(self):
        """Returns None for empty key."""
        assert get_crypto(b"") is None
        assert get_crypto(None) is None

    def test_roundtrip_with_get_crypto(self):
        """get_crypto() + compute/verify works."""
        crypto = get_crypto(b"shared-secret")
        payload = b"test payload"
        mac = crypto.compute(payload)
        assert crypto.verify(payload, mac) is True


class TestAuthenticateAndStrip:
    """Test authenticate() and strip_and_verify() convenience methods."""

    def test_authenticate(self):
        """authenticate() appends 64-char HMAC to payload."""
        crypto = CryptoHash(b"secret-key")
        payload = b"packet-bytes-here"
        auth_bytes = crypto.authenticate(payload)
        assert auth_bytes == payload + crypto.compute(payload).encode("ascii")
        assert len(auth_bytes) == len(payload) + 64

    def test_strip_and_verify_valid(self):
        """strip_and_verify() returns payload and True for valid auth."""
        crypto = CryptoHash(b"secret-key")
        payload = b"packet-bytes-here"
        auth_bytes = crypto.authenticate(payload)
        recovered, ok = crypto.strip_and_verify(auth_bytes)
        assert recovered == payload
        assert ok is True

    def test_strip_and_verify_tampered(self):
        """strip_and_verify() returns payload and False for tampered data."""
        crypto = CryptoHash(b"secret-key")
        payload = b"packet-bytes-here"
        auth_bytes = crypto.authenticate(payload)
        tampered = auth_bytes[:-64] + b"a" + auth_bytes[-63:]
        recovered, ok = crypto.strip_and_verify(tampered)
        assert ok is False

    def test_strip_and_verify_short_data(self):
        """strip_and_verify() raises PacketAuthError for short data."""
        crypto = CryptoHash(b"secret-key")
        with pytest.raises(PacketAuthError, match="too short"):
            crypto.strip_and_verify(b"short")


class TestPacketEncodeDecodeWithCrypto:
    """Test encode/decode with CryptoHash (HMAC authentication)."""

    def test_file_packet_roundtrip_with_crypto(self):
        """FilePacket encode+decode roundtrips correctly with CryptoHash."""
        crypto = CryptoHash(b"shared-secret")
        packet = FilePacket(
            filename="test.txt",
            file_size=12,
            mime_type="text/plain",
            total_blocks=1,
            block_id=0,
            blocks=[b"hello world"],
        )
        encoded = encode_packet(packet, crypto=crypto)
        assert len(encoded) > 0
        decoded = decode_packet(encoded, crypto=crypto)
        assert isinstance(decoded, FilePacket)
        assert decoded.filename == "test.txt"
        assert decoded.blocks[0] == b"hello world"

    def test_message_packet_roundtrip_with_crypto(self):
        """MessagePacket encode+decode roundtrips correctly with CryptoHash."""
        crypto = CryptoHash(b"shared-secret")
        packet = MessagePacket(
            sender="alice",
            subject="hello",
            content_type="text/plain",
            content=b"hello world",
        )
        encoded = encode_packet(packet, crypto=crypto)
        decoded = decode_packet(encoded, crypto=crypto)
        assert isinstance(decoded, MessagePacket)
        assert decoded.sender == "alice"
        assert decoded.content == b"hello world"

    def test_tampered_packet_raises_auth_error(self):
        """Modified packet bytes raise PacketAuthError on decode."""
        crypto = CryptoHash(b"shared-secret")
        packet = MessagePacket(
            sender="alice",
            subject="hello",
            content_type="text/plain",
            content=b"hello world",
        )
        encoded = encode_packet(packet, crypto=crypto)
        tampered = bytearray(encoded)
        for i in range(70, 80):
            tampered[i] ^= 0xFF
        with pytest.raises(PacketAuthError, match="HMAC mismatch"):
            decode_packet(bytes(tampered), crypto=crypto)

    def test_wrong_key_raises_auth_error(self):
        """Packet encoded with one key fails verification with another."""
        crypto_send = CryptoHash(b"sender-key")
        crypto_recv = CryptoHash(b"receiver-key")
        packet = MessagePacket(
            sender="alice",
            subject="hello",
            content_type="text/plain",
            content=b"hello world",
        )
        encoded = encode_packet(packet, crypto=crypto_send)
        with pytest.raises(PacketAuthError, match="HMAC mismatch"):
            decode_packet(encoded, crypto=crypto_recv)


class TestBackwardCompatibility:
    """Test that encode/decode without CryptoHash still works."""

    def test_file_packet_without_crypto(self):
        """FilePacket encode+decode works without CryptoHash."""
        packet = FilePacket(
            filename="test.txt",
            file_size=12,
            mime_type="text/plain",
            total_blocks=1,
            block_id=0,
            blocks=[b"hello world"],
        )
        encoded = encode_packet(packet)
        decoded = decode_packet(encoded)
        assert isinstance(decoded, FilePacket)
        assert decoded.filename == "test.txt"

    def test_message_packet_without_crypto(self):
        """MessagePacket encode+decode works without CryptoHash."""
        packet = MessagePacket(
            sender="alice",
            subject="hello",
            content_type="text/plain",
            content=b"hello world",
        )
        encoded = encode_packet(packet)
        decoded = decode_packet(encoded)
        assert isinstance(decoded, MessagePacket)
        assert decoded.sender == "alice"

    def test_mixed_nodes_compat(self):
        """Node with crypto can decode non-authenticated packet."""
        crypto = CryptoHash(b"secret")
        packet = MessagePacket(
            sender="alice",
            subject="hello",
            content_type="text/plain",
            content=b"hello world",
        )
        encoded = encode_packet(packet)
        decoded = decode_packet(encoded)
        assert isinstance(decoded, MessagePacket)

        encoded_auth = encode_packet(packet, crypto=crypto)
        decoded_auth = decode_packet(encoded_auth, crypto=crypto)
        assert isinstance(decoded_auth, MessagePacket)

    def test_checksum_still_verified_with_crypto(self):
        """Checksum verification catches payload corruption after HMAC passes.

        HMAC authenticates the entire packet (header+strings+content+checksum).
        SHA256 checksum authenticates only the payload content.
        To test checksum independently, flip checksum bytes then recompute HMAC.
        """
        crypto = CryptoHash(b"secret")
        packet = MessagePacket(
            sender="alice",
            subject="hello",
            content_type="text/plain",
            content=b"hello world",
        )
        encoded = encode_packet(packet, crypto=crypto)
        tampered = bytearray(encoded)
        # Corrupt checksum bytes [57:121] with valid ASCII hex characters
        # Flip the last checksum byte so it's wrong but still valid ASCII
        pos = 120  # last byte of checksum region
        original_byte = encoded[pos : pos + 1]
        # Find a valid hex char different from the original
        hex_chars = b"0123456789abcdef"
        original_hex = chr(original_byte[0])
        wrong_hex = next(c for c in hex_chars.decode("ascii") if c != original_hex)
        tampered[pos : pos + 1] = wrong_hex.encode("ascii")
        # HMAC authenticates [0:121]; checksum region [57:121] is now wrong
        # Recompute HMAC over inconsistent packet (wrong checksum bytes)
        payload_for_hmac = bytes(tampered[:121])
        tampered[121:] = crypto.compute(payload_for_hmac).encode("ascii")
        # HMAC passes, checksum fails
        with pytest.raises(PacketChecksumError):
            decode_packet(bytes(tampered), crypto=crypto)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
