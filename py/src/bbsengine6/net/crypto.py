# bbsengine6/net/crypto.py
# HMAC-SHA256 packet authentication to prevent rogue listeners and packet tampering.
# Works across Python, JavaScript, and PHP via standard HMAC construction.

import hmac
from hashlib import sha256
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    pass


class PacketAuthError(ValueError):
    """Raised when HMAC authentication fails (spoofing or tampering detected)."""

    pass


class CryptoHash:
    """
    HMAC-SHA256 packet authenticator using a pre-shared secret key.

    Provides message authentication to prevent rogue nodes from forging
    or modifying packets. Authenticates the raw packet bytes before transmission.
    The receiver verifies the HMAC tag before accepting the packet.

    Compatible across languages:
      - Python: hmac.new(key, data, sha256).hexdigest()
      - JS:     crypto.createHmac('sha256', key).update(data).digest('hex')
      - PHP:    hash_hmac('sha256', data, key)
      - Ruby:   OpenSSL::HMAC.hexdigest('sha256', key, data)

    All produce identical 64-character hex strings for the same key + data.
    """

    HMAC_HEX_LEN = 64

    def __init__(self, secret_key: bytes) -> None:
        if not secret_key:
            raise ValueError("secret_key cannot be empty")
        self._key = secret_key

    def compute(self, payload: bytes) -> str:
        """
        Compute HMAC-SHA256 of payload.

        Args:
            payload: Raw packet bytes to authenticate

        Returns:
            64-character hex string
        """
        return hmac.new(self._key, payload, sha256).hexdigest()

    def verify(self, payload: bytes, mac_hex: str) -> bool:
        """
        Verify HMAC tag using constant-time comparison.

        Uses hmac.compare_digest to prevent timing attacks.

        Args:
            payload: Raw packet bytes that were authenticated
            mac_hex: Expected HMAC hex string (64 chars)

        Returns:
            True if authentic, False otherwise
        """
        expected = self.compute(payload)
        return hmac.compare_digest(expected, mac_hex)

    def authenticate(self, packet_bytes: bytes) -> bytes:
        """
        Append HMAC tag to packet bytes.

        Convenience method for the common send path:
            auth_bytes = crypto.authenticate(encode_packet(packet))

        Args:
            packet_bytes: Encoded packet bytes

        Returns:
            packet_bytes + HMAC hex tag (appended)
        """
        mac_hex = self.compute(packet_bytes)
        return packet_bytes + mac_hex.encode("ascii")

    def strip_and_verify(self, authenticated_bytes: bytes) -> tuple[bytes, bool]:
        """
        Strip HMAC tag from authenticated bytes and verify it.

        Convenience method for the common receive path:
            payload, ok = crypto.strip_and_verify(received_bytes)
            if not ok:
                raise PacketAuthError("HMAC mismatch")

        Args:
            authenticated_bytes: packet_bytes + HMAC tag

        Returns:
            (payload_bytes, verified_ok)

        Raises:
            PacketAuthError: If authenticated_bytes is too short
        """
        if len(authenticated_bytes) < self.HMAC_HEX_LEN:
            raise PacketAuthError(
                f"Authenticated data too short: {len(authenticated_bytes)} < "
                f"{self.HMAC_HEX_LEN}"
            )
        payload = authenticated_bytes[: -self.HMAC_HEX_LEN]
        mac_hex = authenticated_bytes[-self.HMAC_HEX_LEN :].decode("ascii")
        ok = self.verify(payload, mac_hex)
        return payload, ok

    @staticmethod
    def derive_key(machine_id: bytes, master_secret: bytes) -> str:
        """
        Derive a per-machine HMAC key from a master secret.

        Allows a single master secret to seed unique keys per machine
        without exposing the master secret on the wire.

        Args:
            machine_id: Unique machine identifier (e.g. machine_name as bytes)
            master_secret: Shared master secret (at least 32 bytes recommended)

        Returns:
            64-character hex string for use as a CryptoHash secret_key
        """
        return hmac.new(master_secret, machine_id, sha256).hexdigest()


def get_crypto(secret_key: Optional[bytes] = None) -> Optional["CryptoHash"]:
    """
    Create a CryptoHash instance from a secret key.

    Convenience factory. Returns None if secret_key is None/empty,
    making it safe to call unconditionally:
        crypto = get_crypto(config.auth_token)

    Args:
        secret_key: Shared secret bytes (e.g. from auth_token)

    Returns:
        CryptoHash instance, or None if no key provided
    """
    if secret_key:
        return CryptoHash(secret_key)
    return None
