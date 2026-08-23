# password/__init__.py
# Pluggable password management system with strategy pattern
# Supports swappable cipher and storage implementations
#
# IMPORTANT: Two Different Password Systems
# ============================================
# 1. bcrypt Hashing (bbsengine6.password + bbsengine6.util.encryptpassword)
#    - For member login passwords (bbsengine6 authentication)
#    - One-way hashing (cost factor in lock-step with PHP bbsengine6\\password
#      and PG gen_salt('bf'))
#    - Can verify but NOT decrypt
#    - Use for: Storing member passwords for login
#    - PHP analog: bbsengine6\\password\libpassword.php
#
# 2. AES-256-GCM Encryption (this package & bbsengine6.util)
#    - For IMAP/SMTP credentials
#    - Reversible encryption
#    - Can encrypt AND decrypt
#    - Use for: Storing passwords needed for external server authentication
#
# Renamed from bbsengine6.password to bbsengine6.password_cipher in 20260823
# to free up the bbsengine6.password namespace for the bcrypt single-source-
# of-truth module that mirrors PHP bbsengine6\\password.

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
