# notifyd/credentials.py
# Credential management with hybrid storage strategy

from __future__ import annotations

import getpass
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class CredentialError(Exception):
    """Raised when credential retrieval fails"""

    pass


def get_password(
    server_name: str,
    username: str,
    storage: str = "hybrid",
    keyring_service: str = "notifyd",
    prompt_on_missing: bool = True,
) -> str:
    """
    Retrieve password using configured storage strategy.
    
    Hybrid strategy tries in order:
        1. ${SERVER_NAME_PASSWORD} environment variable
        2. keyring.get_password(keyring_service, f"{server_name}:{username}")
        3. getpass.getpass() if prompt_on_missing=True
    
    Args:
        server_name: Server identifier (e.g., "Gmail", "Corporate")
        username: IMAP username
        storage: Storage strategy ("env", "keyring", "prompt", "hybrid")
        keyring_service: Keyring service name for storage/retrieval
        prompt_on_missing: Whether to prompt if password not found
    
    Returns:
        Password string
    
    Raises:
        CredentialError: If password not found and prompt_on_missing=False
    """
    # Try environment variable first
    env_var_name = f"{server_name.upper().replace('-', '_')}_PASSWORD"
    env_password = os.environ.get(env_var_name)
    
    if env_password:
        logger.debug(f"Password retrieved from environment variable {env_var_name}")
        return env_password
    
    # Try keyring
    try:
        import keyring
        
        keyring_key = f"{server_name}:{username}"
        keyring_password = keyring.get_password(keyring_service, keyring_key)
        if keyring_password:
            logger.debug(f"Password retrieved from keyring for {server_name}")
            return keyring_password
    except ImportError:
        logger.debug("keyring module not available")
    except Exception as e:
        logger.debug(f"Failed to retrieve from keyring: {e}")
    
    # Prompt user
    if prompt_on_missing:
        prompt_text = f"Password for {server_name} ({username}): "
        password = getpass.getpass(prompt_text)
        if password:
            return password
    
    # Not found
    raise CredentialError(
        f"Password not found for {server_name}:{username}. "
        f"Set {env_var_name} env var or use --prompt-password"
    )


def store_password(
    server_name: str,
    username: str,
    password: str,
    keyring_service: str = "notifyd",
) -> bool:
    """
    Store password in keyring for future use.
    
    Args:
        server_name: Server identifier
        username: IMAP username
        password: Password to store
        keyring_service: Keyring service name
    
    Returns:
        True if stored successfully, False if keyring not available
    """
    try:
        import keyring
        
        keyring_key = f"{server_name}:{username}"
        keyring.set_password(keyring_service, keyring_key, password)
        logger.info(f"Password stored in keyring for {server_name}")
        return True
    except ImportError:
        logger.debug("keyring module not available, password not stored")
        return False
    except Exception as e:
        logger.error(f"Failed to store password in keyring: {e}")
        return False
