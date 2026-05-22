# test_net_crypto_integration.py
# Comprehensive integration tests for bbsengine6.net HMAC authentication.
# Tests use the public API end-to-end to verify real-world usage patterns.

import pytest

from bbsengine6.net import (
    CryptoHash,
    FilePacket,
    MessagePacket,
    PacketAuthError,
    PacketChecksumError,
    PacketDecodeError,
    WebSocketProtocol,
    WebSocketTransport,
    decode_packet,
    encode_packet,
    get_crypto,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def shared_secret():
    return b"super-secret-key-for-hmac"


@pytest.fixture
def other_secret():
    return b"different-secret-key-for-hmac"


@pytest.fixture
def crypto(shared_secret):
    return CryptoHash(shared_secret)


@pytest.fixture
def crypto_other(other_secret):
    return CryptoHash(other_secret)


@pytest.fixture
def message_packet():
    return MessagePacket(
        sender="alice@bbs.local",
        subject="Meeting at 3pm",
        content_type="text/plain",
        content=b"Room 302, bring coffee.",
    )


@pytest.fixture
def file_packet():
    return FilePacket(
        filename="report.csv",
        file_size=37,
        mime_type="text/csv",
        total_blocks=1,
        block_id=0,
        blocks=[b"date,amount\n2026-05-22,42.50\n"],
    )


# ---------------------------------------------------------------------------
# CryptoHash API - core operations
# ---------------------------------------------------------------------------


class TestCryptoHashComputeVerify:
    """Test CryptoHash.compute() and verify() against known values."""

    def test_compute_hex_format(self, crypto):
        """MAC is 64 lowercase hex characters."""
        mac = crypto.compute(b"any payload")
        assert len(mac) == 64
        assert mac == mac.lower()
        assert all(c in "0123456789abcdef" for c in mac)

    def test_compute_idempotent(self, crypto):
        """Same key + payload always produces the same MAC."""
        payload = b"idempotent test payload"
        assert crypto.compute(payload) == crypto.compute(payload)

    def test_different_payloads_different_mac(self, crypto):
        """Different payloads produce different MACs."""
        mac1 = crypto.compute(b"payload one")
        mac2 = crypto.compute(b"payload two")
        assert mac1 != mac2

    def test_verify_correct_mac(self, crypto):
        """verify() returns True for the correct MAC."""
        payload = b"verify test"
        mac = crypto.compute(payload)
        assert crypto.verify(payload, mac) is True

    def test_verify_wrong_mac(self, crypto):
        """verify() returns False for an incorrect MAC."""
        payload = b"verify test"
        wrong_mac = "0" * 64
        assert crypto.verify(payload, wrong_mac) is False

    def test_verify_tampered_payload(self, crypto):
        """verify() returns False if payload bytes were changed."""
        original = b"original data here"
        mac = crypto.compute(original)
        tampered = b"modified data here"
        assert crypto.verify(tampered, mac) is False

    def test_verify_case_sensitive(self, crypto):
        """MAC verification is case-sensitive."""
        payload = b"test"
        mac = crypto.compute(payload)
        wrong_case = mac.upper()
        assert crypto.verify(payload, wrong_case) is False


class TestCryptoHashAuthenticate:
    """Test CryptoHash.authenticate() appends HMAC correctly."""

    def test_authenticate_increases_length_by_64(self, crypto):
        """authenticate() adds exactly 64 bytes."""
        payload = b"test packet bytes"
        auth_bytes = crypto.authenticate(payload)
        assert len(auth_bytes) == len(payload) + 64
        assert auth_bytes[: len(payload)] == payload

    def test_authenticate_hmac_matches(self, crypto):
        """authenticate() stores the correct HMAC."""
        payload = b"auth test"
        auth_bytes = crypto.authenticate(payload)
        stored_mac = auth_bytes[len(payload) :].decode("ascii")
        assert crypto.verify(payload, stored_mac) is True

    def test_authenticate_empty_payload(self, crypto):
        """authenticate() works with empty payload."""
        auth_bytes = crypto.authenticate(b"")
        assert len(auth_bytes) == 64


class TestCryptoHashStripAndVerify:
    """Test CryptoHash.strip_and_verify() extracts and verifies HMAC."""

    def test_strip_and_verify_valid(self, crypto):
        """Valid authenticated data returns (payload, True)."""
        payload = b"verified payload"
        auth_bytes = crypto.authenticate(payload)
        recovered, ok = crypto.strip_and_verify(auth_bytes)
        assert recovered == payload
        assert ok is True

    def test_strip_and_verify_tampered(self, crypto):
        """Tampered authenticated data returns (payload, False)."""
        payload = b"original payload"
        auth_bytes = bytearray(crypto.authenticate(payload))
        auth_bytes[10] ^= 0xFF
        recovered, ok = crypto.strip_and_verify(bytes(auth_bytes))
        assert recovered[:10] == payload[:10]
        assert ok is False

    def test_strip_and_verify_truncated_hmac(self, crypto):
        """Truncated HMAC raises PacketAuthError."""
        payload = b"test"
        auth_bytes = crypto.authenticate(payload)
        short = auth_bytes[: len(payload) + 10]
        with pytest.raises(PacketAuthError, match="too short"):
            crypto.strip_and_verify(short)

    def test_strip_and_verify_truncated_payload(self, crypto):
        """Truncated payload raises PacketAuthError."""
        auth_bytes = crypto.authenticate(b"some payload")
        short = auth_bytes[:10]
        with pytest.raises(PacketAuthError, match="too short"):
            crypto.strip_and_verify(short)

    def test_strip_and_verify_empty(self, crypto):
        """Empty bytes raises PacketAuthError."""
        with pytest.raises(PacketAuthError, match="too short"):
            crypto.strip_and_verify(b"")


# ---------------------------------------------------------------------------
# CryptoHash key derivation
# ---------------------------------------------------------------------------


class TestCryptoHashDeriveKey:
    """Test CryptoHash.derive_key() for HKDF-lite key derivation."""

    def test_derive_key_deterministic(self, shared_secret):
        """Same inputs always produce the same derived key."""
        key1 = CryptoHash.derive_key(b"machine-a", shared_secret)
        key2 = CryptoHash.derive_key(b"machine-a", shared_secret)
        assert key1 == key2

    def test_derive_key_different_machines_different_keys(self, shared_secret):
        """Different machine IDs produce different keys."""
        key1 = CryptoHash.derive_key(b"machine-a", shared_secret)
        key2 = CryptoHash.derive_key(b"machine-b", shared_secret)
        assert key1 != key2

    def test_derive_key_different_secrets_different_keys(self):
        """Different master secrets produce different keys."""
        key1 = CryptoHash.derive_key(b"machine-a", b"secret-one")
        key2 = CryptoHash.derive_key(b"machine-a", b"secret-two")
        assert key1 != key2

    def test_derive_key_format(self, shared_secret):
        """Derived key is a 64-char hex string."""
        key = CryptoHash.derive_key(b"node-1", shared_secret)
        assert len(key) == 64
        assert key == key.lower()

    def test_derive_key_usable_as_secret(self, shared_secret):
        """Derived key can be used as a CryptoHash secret_key."""
        derived = CryptoHash.derive_key(b"node-1", shared_secret)
        crypto = CryptoHash(derived.encode("ascii"))
        payload = b"test payload"
        mac = crypto.compute(payload)
        assert len(mac) == 64


# ---------------------------------------------------------------------------
# get_crypto factory
# ---------------------------------------------------------------------------


class TestGetCrypto:
    """Test get_crypto() convenience factory."""

    def test_returns_cryptohash_for_valid_key(self):
        """get_crypto(key) returns a CryptoHash instance."""
        result = get_crypto(b"valid-key")
        assert isinstance(result, CryptoHash)

    def test_returns_none_for_empty_bytes(self):
        """get_crypto(b'') returns None."""
        assert get_crypto(b"") is None

    def test_returns_none_for_none(self):
        """get_crypto(None) returns None."""
        assert get_crypto(None) is None

    def test_result_is_functional(self):
        """get_crypto() result can compute and verify."""
        crypto = get_crypto(b"factory-test")
        payload = b"factory payload"
        mac = crypto.compute(payload)
        assert crypto.verify(payload, mac) is True


# ---------------------------------------------------------------------------
# encode_packet / decode_packet with CryptoHash
# ---------------------------------------------------------------------------


class TestEncodeDecodeMessageWithCrypto:
    """Test MessagePacket round-trip with HMAC authentication."""

    def test_roundtrip_authenticated(self, crypto, message_packet):
        """Authenticated encode/decode recovers packet exactly."""
        encoded = encode_packet(message_packet, crypto=crypto)
        assert len(encoded) > 0
        decoded = decode_packet(encoded, crypto=crypto)
        assert decoded.sender == message_packet.sender
        assert decoded.subject == message_packet.subject
        assert decoded.content == message_packet.content
        assert decoded.content_type == message_packet.content_type

    def test_roundtrip_without_crypto(self, message_packet):
        """Unauthenticated encode/decode still works."""
        encoded = encode_packet(message_packet)
        decoded = decode_packet(encoded)
        assert decoded.sender == message_packet.sender

    def test_roundtrip_mixed_auth_sender(self, crypto, message_packet):
        """Sender with crypto, receiver without - works."""
        encoded = encode_packet(message_packet, crypto=crypto)
        decoded = decode_packet(encoded)
        assert decoded.sender == message_packet.sender

    def test_roundtrip_mixed_auth_receiver(self, crypto, message_packet):
        """Sender without crypto, receiver with crypto - raises PacketDecodeError.

        When crypto is provided to decode but the packet has no HMAC tag,
        the decoder expects the extra 64 bytes and raises PacketDecodeError.
        This is by design: a crypto-enabled receiver rejects unauthenticated
        packets. Senders must also use crypto if receivers require it.
        """
        encoded = encode_packet(message_packet)
        with pytest.raises(PacketDecodeError, match="truncated"):
            decode_packet(encoded, crypto=crypto)


class TestEncodeDecodeFileWithCrypto:
    """Test FilePacket round-trip with HMAC authentication."""

    def test_roundtrip_authenticated(self, crypto, file_packet):
        """Authenticated FilePacket encode/decode recovers packet."""
        encoded = encode_packet(file_packet, crypto=crypto)
        assert len(encoded) > 0
        decoded = decode_packet(encoded, crypto=crypto)
        assert decoded.filename == file_packet.filename
        assert decoded.file_size == file_packet.file_size
        assert decoded.mime_type == file_packet.mime_type
        assert decoded.blocks[0] == file_packet.blocks[0]

    def test_roundtrip_without_crypto(self, file_packet):
        """Unauthenticated FilePacket encode/decode still works."""
        encoded = encode_packet(file_packet)
        decoded = decode_packet(encoded)
        assert decoded.filename == file_packet.filename


# ---------------------------------------------------------------------------
# Tampering detection
# ---------------------------------------------------------------------------


class TestTamperingDetection:
    """Verify that tampering with authenticated packets is detected."""

    def test_tampered_content_raises_auth_error_message(self, crypto, message_packet):
        """Modified content bytes raise PacketAuthError."""
        encoded = encode_packet(message_packet, crypto=crypto)
        tampered = bytearray(encoded)
        tampered[70:80] = bytes(b ^ 0xFF for b in tampered[70:80])
        with pytest.raises(PacketAuthError, match="HMAC mismatch"):
            decode_packet(bytes(tampered), crypto=crypto)

    def test_tampered_content_raises_auth_error_file(self, crypto, file_packet):
        """Modified FilePacket bytes raise PacketAuthError."""
        encoded = encode_packet(file_packet, crypto=crypto)
        tampered = bytearray(encoded)
        tampered[60:70] = bytes(b ^ 0xFF for b in tampered[60:70])
        with pytest.raises(PacketAuthError, match="HMAC mismatch"):
            decode_packet(bytes(tampered), crypto=crypto)

    def test_wrong_key_raises_auth_error(self, crypto, crypto_other, message_packet):
        """Packet authenticated with one key fails verification with another."""
        encoded = encode_packet(message_packet, crypto=crypto)
        with pytest.raises(PacketAuthError, match="HMAC mismatch"):
            decode_packet(encoded, crypto=crypto_other)

    def test_stripped_hmac_raises_auth_error(self, crypto, message_packet):
        """Packet with HMAC stripped off raises PacketDecodeError (short data)."""
        encoded = encode_packet(message_packet, crypto=crypto)
        without_hmac = encoded[: -CryptoHash.HMAC_HEX_LEN]
        with pytest.raises(PacketDecodeError, match="truncated"):
            decode_packet(without_hmac, crypto=crypto)

    def test_extra_bytes_after_hmac_ignored(self, crypto, message_packet):
        """Extra bytes after HMAC tag are ignored during verification."""
        encoded = encode_packet(message_packet, crypto=crypto)
        with_extra = encoded + b"extra trailing garbage"
        decoded = decode_packet(with_extra, crypto=crypto)
        assert decoded.sender == message_packet.sender


# ---------------------------------------------------------------------------
# WebSocketTransport with secret_key
# ---------------------------------------------------------------------------


class TestWebSocketTransportCrypto:
    """Test WebSocketTransport with HMAC authentication."""

    def test_transport_with_secret_key(self, shared_secret):
        """WebSocketTransport accepts secret_key and creates CryptoHash."""
        transport = WebSocketTransport(timeout=5.0, secret_key=shared_secret)
        assert transport._crypto is not None
        assert isinstance(transport._crypto, CryptoHash)

    def test_transport_without_secret_key(self):
        """WebSocketTransport without secret_key has no crypto."""
        transport = WebSocketTransport()
        assert transport._crypto is None

    def test_transport_timeout_preserved(self, shared_secret):
        """secret_key does not affect timeout setting."""
        transport = WebSocketTransport(timeout=15.0, secret_key=shared_secret)
        assert transport.timeout == 15.0

    def test_transport_send_packet_creates_authenticated_bytes(self, shared_secret):
        """send_packet accepts crypto from transport and produces HMAC."""
        import asyncio

        transport = WebSocketTransport(timeout=10.0, secret_key=shared_secret)
        packet = MessagePacket(
            sender="alice",
            subject="test",
            content_type="text/plain",
            content=b"hello",
        )

        async def run():
            success, msg = await transport.send_packet(
                "example.com", 8765, packet
            )
            assert success

        asyncio.run(run())

    def test_transport_no_crypto_has_none(self):
        """WebSocketTransport without secret_key has no crypto."""
        transport = WebSocketTransport(timeout=10.0)
        assert transport._crypto is None


    def test_transport_send_packet_sync_authenticated(self, shared_secret):
        """send_packet_sync produces authenticated output."""
        transport = WebSocketTransport(timeout=10.0, secret_key=shared_secret)
        packet = MessagePacket(
            sender="alice",
            subject="sync test",
            content_type="text/plain",
            content=b"hello sync",
        )
        success, msg = transport.send_packet_sync(
            "example.com", 8765, packet
        )
        assert success
        assert "authenticated" in msg


# ---------------------------------------------------------------------------
# WebSocketProtocol with secret_key
# ---------------------------------------------------------------------------


class TestWebSocketProtocolCrypto:
    """Test WebSocketProtocol.handle_packet with HMAC verification."""

    def test_protocol_with_secret_key(self, shared_secret):
        """WebSocketProtocol accepts secret_key and creates CryptoHash."""
        transport = WebSocketTransport()
        protocol = WebSocketProtocol(transport, secret_key=shared_secret)
        assert protocol._crypto is not None
        assert isinstance(protocol._crypto, CryptoHash)

    def test_protocol_without_secret_key(self):
        """WebSocketProtocol without secret_key has no crypto."""
        transport = WebSocketTransport()
        protocol = WebSocketProtocol(transport)
        assert protocol._crypto is None

    def test_handle_packet_authenticated(self, shared_secret, message_packet):
        """handle_packet with crypto verifies HMAC before decoding."""
        import asyncio

        transport = WebSocketTransport()
        protocol = WebSocketProtocol(transport, secret_key=shared_secret)
        crypto = CryptoHash(shared_secret)

        encoded = encode_packet(message_packet, crypto=crypto)
        auth_bytes = crypto.authenticate(encoded)

        async def run():
            ok, msg, pkt = await protocol.handle_packet(auth_bytes)
            assert ok
            assert pkt is not None
            assert pkt.sender == message_packet.sender

        asyncio.run(run())

    def test_handle_packet_tampered_rejected(self, shared_secret, message_packet):
        """handle_packet rejects tampered packets."""
        import asyncio

        transport = WebSocketTransport()
        protocol = WebSocketProtocol(transport, secret_key=shared_secret)
        crypto = CryptoHash(shared_secret)

        encoded = encode_packet(message_packet, crypto=crypto)
        auth_bytes = bytearray(crypto.authenticate(encoded))
        auth_bytes[50] ^= 0xFF

        async def run():
            ok, msg, pkt = await protocol.handle_packet(bytes(auth_bytes))
            assert ok is False
            assert "HMAC" in msg
            assert pkt is None

        asyncio.run(run())

    def test_handle_packet_wrong_key_rejected(self, shared_secret, message_packet):
        """handle_packet rejects packets authenticated with wrong key."""
        import asyncio

        transport = WebSocketTransport()
        protocol = WebSocketProtocol(transport, secret_key=shared_secret)
        crypto_wrong = CryptoHash(b"wrong-key")

        encoded = encode_packet(message_packet, crypto=crypto_wrong)
        auth_bytes = crypto_wrong.authenticate(encoded)

        async def run():
            ok, msg, pkt = await protocol.handle_packet(auth_bytes)
            assert ok is False
            assert pkt is None

        asyncio.run(run())

    def test_handle_packet_no_crypto_passes_through(self, message_packet):
        """handle_packet without crypto on protocol decodes normally."""
        import asyncio

        transport = WebSocketTransport()
        protocol = WebSocketProtocol(transport, secret_key=None)

        encoded = encode_packet(message_packet)

        async def run():
            ok, msg, pkt = await protocol.handle_packet(encoded)
            assert ok
            assert pkt is not None
            assert pkt.sender == message_packet.sender

        asyncio.run(run())


# ---------------------------------------------------------------------------
# End-to-end: sender and receiver using API
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """End-to-end tests simulating a complete send/receive cycle."""

    def test_message_sent_and_received(self, shared_secret, message_packet):
        """Full send/receive cycle recovers packet exactly."""
        crypto = CryptoHash(shared_secret)

        packet_data = encode_packet(message_packet, crypto=crypto)
        auth_bytes = crypto.authenticate(packet_data)

        recovered_payload, ok = crypto.strip_and_verify(auth_bytes)
        assert ok is True

        decoded = decode_packet(recovered_payload, crypto=crypto)
        assert decoded.sender == message_packet.sender
        assert decoded.subject == message_packet.subject
        assert decoded.content == message_packet.content

    def test_file_sent_and_received(self, shared_secret, file_packet):
        """Full send/receive cycle for FilePacket recovers file exactly."""
        crypto = CryptoHash(shared_secret)

        packet_data = encode_packet(file_packet, crypto=crypto)
        auth_bytes = crypto.authenticate(packet_data)

        recovered_payload, ok = crypto.strip_and_verify(auth_bytes)
        assert ok is True

        decoded = decode_packet(recovered_payload, crypto=crypto)
        assert decoded.filename == file_packet.filename
        assert decoded.file_size == file_packet.file_size
        assert decoded.blocks[0] == file_packet.blocks[0]

    def test_derive_and_use_per_machine_key(self, shared_secret, message_packet):
        """derive_key() produces a key that works for send/receive."""
        machine_id = b"node-bbs-01"
        derived_key_hex = CryptoHash.derive_key(machine_id, shared_secret)
        derived_key = derived_key_hex.encode("ascii")

        sender_crypto = CryptoHash(derived_key)
        receiver_crypto = CryptoHash(derived_key)

        packet_data = encode_packet(message_packet, crypto=sender_crypto)
        auth_bytes = sender_crypto.authenticate(packet_data)

        recovered_payload, ok = receiver_crypto.strip_and_verify(auth_bytes)
        assert ok is True

        decoded = decode_packet(recovered_payload, crypto=receiver_crypto)
        assert decoded.sender == message_packet.sender

    def test_get_crypto_integration(self, shared_secret, message_packet):
        """get_crypto() returns a functional authenticator."""
        sender_crypto = get_crypto(shared_secret)
        receiver_crypto = get_crypto(shared_secret)

        packet_data = encode_packet(message_packet, crypto=sender_crypto)
        auth_bytes = sender_crypto.authenticate(packet_data)

        recovered_payload, ok = receiver_crypto.strip_and_verify(auth_bytes)
        assert ok is True
        decoded = decode_packet(recovered_payload, crypto=receiver_crypto)
        assert decoded.sender == message_packet.sender

    def test_mixed_environment_auth_and_no_auth(self, shared_secret, message_packet):
        """Authenticated and unauthenticated nodes can coexist."""
        crypto = CryptoHash(shared_secret)

        encoded_auth = encode_packet(message_packet, crypto=crypto)
        decoded_auth = decode_packet(encoded_auth, crypto=crypto)
        assert decoded_auth.sender == message_packet.sender

        encoded_no_auth = encode_packet(message_packet)
        decoded_no_auth = decode_packet(encoded_no_auth)
        assert decoded_no_auth.sender == message_packet.sender


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------


class TestExceptionHandling:
    """Test that exceptions are raised correctly."""

    def test_auth_error_on_tamper(self, crypto, message_packet):
        """PacketAuthError raised on tampered packet."""
        encoded = encode_packet(message_packet, crypto=crypto)
        tampered = bytearray(encoded)
        tampered[50] ^= 0xFF
        with pytest.raises(PacketAuthError):
            decode_packet(bytes(tampered), crypto=crypto)

    def test_checksum_error_after_hmac_passes(self, shared_secret):
        """PacketChecksumError when HMAC passes but checksum bytes are corrupted.

        HMAC is computed over [0:N] (header+strings+content+checksum).
        Corrupt a checksum byte, recompute HMAC, then verify checksum fails.
        """
        crypto = CryptoHash(shared_secret)
        fresh = MessagePacket(
            sender="alice",
            subject="test",
            content_type="text/plain",
            content=b"hello world",
        )
        plain = encode_packet(fresh)
        decoded = decode_packet(plain)
        encoded = encode_packet(decoded, crypto=crypto)
        tampered = bytearray(encoded)
        pos = 119
        original = chr(encoded[pos])
        hex_chars = "0123456789abcdef"
        wrong = next(c for c in hex_chars if c != original)
        tampered[pos : pos + 1] = wrong.encode("ascii")
        checksum_end = len(encoded) - 64
        payload = bytes(tampered[:checksum_end])
        tampered[checksum_end:] = crypto.compute(payload).encode("ascii")
        with pytest.raises(PacketChecksumError):
            decode_packet(bytes(tampered), crypto=crypto)


# ---------------------------------------------------------------------------
# PingPacket / PongPacket - no HMAC (too small)
# ---------------------------------------------------------------------------


class TestPingPongNoHmac:
    """Ping/Pong packets are not HMAC-authenticated (too small, no payload)."""

    def test_ping_encode_decode_without_crypto(self):
        """PingPacket round-trips without crypto."""
        from bbsengine6.net import PingPacket, encode_packet, decode_packet
        import time

        ping = PingPacket(timestamp=time.time() * 1000)
        encoded = encode_packet(ping, crypto=None)
        decoded = decode_packet(encoded, crypto=None)
        assert decoded.packet_type == 1

    def test_ping_encode_decode_with_crypto(self):
        """PingPacket also works with crypto provided (no HMAC added)."""
        from bbsengine6.net import PingPacket, encode_packet
        import time

        crypto = CryptoHash(b"key")
        ping = PingPacket(timestamp=time.time() * 1000)
        encoded_with = encode_packet(ping, crypto=crypto)
        encoded_without = encode_packet(ping)
        assert encoded_with == encoded_without


# ---------------------------------------------------------------------------
# Backwards compatibility
# ---------------------------------------------------------------------------


class TestBackwardsCompatibility:
    """Ensure backwards compatibility with existing code."""

    def test_existing_packets_still_work(self, message_packet):
        """encode/decode without crypto unchanged from before."""
        encoded = encode_packet(message_packet)
        decoded = decode_packet(encoded)
        assert decoded.sender == message_packet.sender
        assert decoded.subject == message_packet.subject
        assert decoded.content == message_packet.content

    def test_transport_without_key_still_works(self):
        """WebSocketTransport without secret_key still functions."""
        transport = WebSocketTransport(timeout=5.0)
        assert transport._crypto is None
        assert transport.timeout == 5.0

    def test_protocol_without_key_still_works(self, message_packet):
        """WebSocketProtocol without secret_key still decodes."""
        import asyncio

        transport = WebSocketTransport()
        protocol = WebSocketProtocol(transport, secret_key=None)
        encoded = encode_packet(message_packet)

        async def run():
            ok, msg, pkt = await protocol.handle_packet(encoded)
            assert ok
            assert pkt.sender == message_packet.sender

        asyncio.run(run())

    def test_get_crypto_with_none_backward_compat(self):
        """get_crypto(None) returns None (safe to call unconditionally)."""
        assert get_crypto(None) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
