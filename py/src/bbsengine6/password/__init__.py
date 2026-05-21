# password/__init__.py
# Pluggable password management system with strategy pattern
# Supports swappable cipher and storage implementations
#
# IMPORTANT: Two Different Password Systems
# ============================================
# 1. SHA-256 Hashing (bbsengine6.password_hash)
#    - For member login passwords (bbsengine6 authentication)
#    - One-way hashing with salt
#    - Can verify but NOT decrypt
#    - Use for: Storing member passwords for login
#
# 2. AES-256-GCM Encryption (bbsengine6.password & bbsengine6.util)
#    - For IMAP/SMTP credentials
#    - Reversible encryption
#    - Can encrypt AND decrypt
#    - Use for: Storing passwords needed for external server authentication

from .cipher import PasswordCipher
from .storage import PasswordStorage
from .manager import PasswordManager
from .config import get_password_manager

__all__ = [
    "PasswordCipher",
    "PasswordStorage",
    "PasswordManager",
    "get_password_manager",
]
