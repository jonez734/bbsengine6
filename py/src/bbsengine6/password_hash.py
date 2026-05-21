# password_hash.py
# SHA-256 password hashing with salt for secure password storage
# One-way hashing for member authentication (verification only)

import hashlib
import os
import base64
from typing import Tuple


def generate_salt(length: int = 32) -> str:
    """Generate random salt for password hashing.

    Args:
        length: Length of salt in bytes (default: 32).

    Returns:
        Base64-encoded random salt.

    Example:
        >>> salt = generate_salt()
        >>> len(base64.b64decode(salt)) == 32
        True
    """
    return base64.b64encode(os.urandom(length)).decode("utf-8")


def hash_password(plaintext: str, salt: str = None) -> Tuple[str, str]:
    """Hash password with SHA-256 and salt.

    Args:
        plaintext: Plaintext password to hash.
        salt: Base64-encoded salt. If None, generates new salt.

    Returns:
        Tuple of (hashed_password, salt) both base64-encoded.

    Raises:
        ValueError: If inputs are invalid.

    Algorithm:
        - Hash: SHA-256
        - Salt: Random 32 bytes (256 bits)
        - Format: base64(hash)
        - Salt: base64(random_bytes)

    Example:
        >>> hashed, salt = hash_password("mypassword")
        >>> verify_password("mypassword", hashed, salt)
        True
        >>> verify_password("wrongpassword", hashed, salt)
        False
    """
    if not plaintext or not isinstance(plaintext, str):
        raise ValueError("Plaintext must be non-empty string")

    # Generate salt if not provided
    if salt is None:
        salt = generate_salt()

    # Decode salt from base64
    try:
        salt_bytes = base64.b64decode(salt)
    except Exception as e:
        raise ValueError(f"Invalid base64 salt: {e}")

    if len(salt_bytes) != 32:
        raise ValueError(f"Salt must be 32 bytes, got {len(salt_bytes)}")

    # Hash password with salt
    hash_obj = hashlib.sha256()
    hash_obj.update(salt_bytes)
    hash_obj.update(plaintext.encode("utf-8"))
    hashed = base64.b64encode(hash_obj.digest()).decode("utf-8")

    return hashed, salt


def verify_password(plaintext: str, hashed: str, salt: str) -> bool:
    """Verify plaintext password against hash and salt.

    Args:
        plaintext: Plaintext password to verify.
        hashed: Base64-encoded hash from hash_password().
        salt: Base64-encoded salt from hash_password().

    Returns:
        True if password matches, False otherwise.

    Example:
        >>> hashed, salt = hash_password("mypassword")
        >>> verify_password("mypassword", hashed, salt)
        True
        >>> verify_password("wrongpassword", hashed, salt)
        False
    """
    if not plaintext or not isinstance(plaintext, str):
        return False

    try:
        # Hash the provided plaintext with the stored salt
        computed_hashed, _ = hash_password(plaintext, salt)

        # Compare hashes (constant-time comparison)
        return computed_hashed == hashed
    except Exception:
        return False


def is_hashed_password(value: str) -> bool:
    """Check if value looks like a SHA-256 hashed password.

    Args:
        value: String to check.

    Returns:
        True if value appears to be a base64-encoded SHA-256 hash.

    Note:
        This is a heuristic check. Not foolproof.
    """
    if not isinstance(value, str) or len(value) < 40:
        return False

    try:
        decoded = base64.b64decode(value)
        # SHA-256 produces 32-byte hashes
        return len(decoded) == 32
    except Exception:
        return False


__all__ = [
    "generate_salt",
    "hash_password",
    "verify_password",
    "is_hashed_password",
]
