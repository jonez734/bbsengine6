# notifyd/config.py
# Configuration loading and validation for notifyd daemon

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when configuration is invalid or missing"""

    pass


def _substitute_env_vars(data: str) -> str:
    """
    Substitute ${VAR_NAME} with environment variables.
    
    Args:
        data: String potentially containing ${VAR_NAME} patterns
    
    Returns:
        String with environment variables substituted
    
    Raises:
        ConfigError: If referenced environment variable is missing
    """
    def replace_var(match):
        var_name = match.group(1)
        if var_name not in os.environ:
            raise ConfigError(
                f"Environment variable ${{{var_name}}} not found"
            )
        return os.environ[var_name]
    
    pattern = r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}'
    return re.sub(pattern, replace_var, data)


def _validate_imap_server(server: Dict[str, Any]) -> None:
    """
    Validate IMAP server configuration.
    
    Args:
        server: Server configuration dictionary
    
    Raises:
        ConfigError: If validation fails
    """
    name = server.get("name", "")
    if not name:
        raise ConfigError("ImapServer: name is required")
    
    host = server.get("host", "")
    if not host:
        raise ConfigError(f"ImapServer '{name}': host is required")
    
    username = server.get("username", "")
    if not username:
        raise ConfigError(f"ImapServer '{name}': username is required")
    
    port = server.get("port", 993)
    if port < 1 or port > 65535:
        raise ConfigError(
            f"ImapServer '{name}': port must be 1-65535, got {port}"
        )
    
    poll_interval = server.get("poll_interval", 30)
    if poll_interval < 1:
        raise ConfigError(
            f"ImapServer '{name}': poll_interval must be >= 1"
        )
    
    timeout = server.get("timeout", 10)
    if timeout < 1:
        raise ConfigError(
            f"ImapServer '{name}': timeout must be >= 1"
        )
    
    urgency = server.get("urgency", "ROUTINE")
    if urgency not in ("ROUTINE", "IMPORTANT", "URGENT", "CRITICAL"):
        raise ConfigError(
            f"ImapServer '{name}': invalid urgency {urgency}"
        )
    
    recipients = server.get("recipients", [])
    if not recipients:
        raise ConfigError(
            f"ImapServer '{name}': recipients list cannot be empty"
        )


def _validate_database_config(db_config: Dict[str, Any]) -> None:
    """
    Validate database configuration.
    
    Args:
        db_config: Database configuration dictionary
    
    Raises:
        ConfigError: If validation fails
    """
    port = db_config.get("port", 5432)
    if port < 1 or port > 65535:
        raise ConfigError(f"Database: port must be 1-65535, got {port}")


def _validate_logging_config(log_config: Dict[str, Any]) -> None:
    """
    Validate logging configuration.
    
    Args:
        log_config: Logging configuration dictionary
    
    Raises:
        ConfigError: If validation fails
    """
    level = log_config.get("level", "INFO")
    valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    if level not in valid_levels:
        raise ConfigError(f"Logging: invalid level {level}")


def _validate_credentials_config(cred_config: Dict[str, Any]) -> None:
    """
    Validate credentials configuration.
    
    Args:
        cred_config: Credentials configuration dictionary
    
    Raises:
        ConfigError: If validation fails
    """
    storage = cred_config.get("storage", "hybrid")
    valid_storage = ("env", "keyring", "prompt", "hybrid")
    if storage not in valid_storage:
        raise ConfigError(f"Credentials: invalid storage {storage}")


def _validate_event_handler_config(event_type: str, handler: Dict[str, Any]) -> None:
    """
    Validate event handler configuration.
    
    Args:
        event_type: Event type identifier
        handler: Event handler configuration dictionary
    
    Raises:
        ConfigError: If validation fails
    """
    template = handler.get("template", "")
    if not template:
        raise ConfigError(f"EventHandler '{event_type}': template is required")
    
    urgency = handler.get("urgency", "ROUTINE")
    if urgency not in ("ROUTINE", "IMPORTANT", "URGENT", "CRITICAL"):
        raise ConfigError(
            f"EventHandler '{event_type}': invalid urgency {urgency}"
        )


def _validate_events_config(events_config: Dict[str, Any]) -> None:
    """
    Validate events configuration.
    
    Args:
        events_config: Events configuration dictionary
    
    Raises:
        ConfigError: If validation fails
    """
    handlers = events_config.get("handlers", {})
    for event_type, handler_config in handlers.items():
        _validate_event_handler_config(event_type, handler_config)


def _get_imap_server_defaults() -> Dict[str, Any]:
    """Get default IMAP server configuration values"""
    return {
        "port": 993,
        "use_ssl": True,
        "password": "",
        "mailbox": "INBOX",
        "poll_interval": 30,
        "notification_type": "imap.message",
        "urgency": "ROUTINE",
        "enabled": True,
        "timeout": 10,
    }


def _get_database_defaults() -> Dict[str, Any]:
    """Get default database configuration values"""
    return {
        "use_bbsengine6_db": True,
        "dbname": "bbsengine6",
        "user": "postgres",
        "host": "localhost",
        "port": 5432,
    }


def _get_logging_defaults() -> Dict[str, Any]:
    """Get default logging configuration values"""
    return {
        "level": "INFO",
        "file": None,
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    }


def _get_credentials_defaults() -> Dict[str, Any]:
    """Get default credentials configuration values"""
    return {
        "storage": "hybrid",
        "keyring_service": "notifyd",
        "prompt_on_missing": True,
    }


def _get_event_handler_defaults() -> Dict[str, Any]:
    """Get default event handler configuration values"""
    return {
        "urgency": "ROUTINE",
        "send_to": ["@everyone"],
    }


def _merge_config(config: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge configuration with defaults (non-recursive).
    
    Args:
        config: Configuration dictionary (overrides defaults)
        defaults: Default configuration dictionary
    
    Returns:
        Merged configuration dictionary
    """
    result = defaults.copy()
    result.update(config)
    return result


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from JSON file with environment variable substitution.
    
    Priority (first found wins):
        1. Explicit config_path argument
        2. NOTIFYD_CONFIG environment variable
        3. ~/.bbsengine6/notifyd/config.json
        4. /etc/notifyd/config.json
    
    Args:
        config_path: Optional explicit path to config.json
    
    Returns:
        Loaded and validated configuration dictionary
    
    Raises:
        ConfigError: If config file not found or invalid
    """
    # Determine config file path
    if config_path:
        paths_to_try = [config_path]
    else:
        env_path = os.environ.get("NOTIFYD_CONFIG")
        user_path = os.path.expanduser("~/.bbsengine6/notifyd/config.json")
        system_path = "/etc/notifyd/config.json"
        
        paths_to_try = [
            env_path,
            user_path,
            system_path,
        ]
    
    config_file = None
    for path in paths_to_try:
        if path and Path(path).exists():
            config_file = path
            break
    
    if not config_file:
        raise ConfigError(
            f"Configuration file not found. Tried: {', '.join(str(p) for p in paths_to_try if p)}"
        )
    
    # Load JSON
    try:
        with open(config_file, "r") as f:
            raw_content = f.read()
    except IOError as e:
        raise ConfigError(f"Failed to read {config_file}: {e}")
    
    # Substitute environment variables
    try:
        content = _substitute_env_vars(raw_content)
    except ConfigError:
        raise
    
    # Parse JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {config_file}: {e}")
    
    # Build configuration with defaults
    try:
        logging_config = _merge_config(
            data.get("logging", {}),
            _get_logging_defaults()
        )
        database_config = _merge_config(
            data.get("database", {}),
            _get_database_defaults()
        )
        credentials_config = _merge_config(
            data.get("credentials", {}),
            _get_credentials_defaults()
        )
        
        # Process IMAP servers with defaults
        imap_servers = []
        imap_data = data.get("imap", {})
        for server_data in imap_data.get("servers", []):
            server = _merge_config(server_data, _get_imap_server_defaults())
            imap_servers.append(server)
        
        # Process event handlers with defaults
        events_data = data.get("events", {})
        handlers = {}
        for event_type, handler_data in events_data.get("handlers", {}).items():
            handler = _merge_config(
                handler_data,
                _get_event_handler_defaults()
            )
            handlers[event_type] = handler
        
        events_config = {
            "enable_key_events": events_data.get("enable_key_events", False),
            "enable_custom_hooks": events_data.get("enable_custom_hooks", True),
            "handlers": handlers,
        }
        
        config = {
            "logging": logging_config,
            "database": database_config,
            "polling_interval": data.get("polling_interval", 30),
            "credentials": credentials_config,
            "imap_servers": imap_servers,
            "events": events_config,
        }
        
        # Validate
        _validate_logging_config(logging_config)
        _validate_database_config(database_config)
        _validate_credentials_config(credentials_config)
        _validate_events_config(events_config)
        
        if config["polling_interval"] < 1:
            raise ConfigError("polling_interval must be >= 1")
        
        if not imap_servers:
            raise ConfigError("At least one IMAP server must be configured")
        
        for server in imap_servers:
            _validate_imap_server(server)
        
        logger.info(f"Configuration loaded from {config_file}")
        return config
    
    except ConfigError:
        raise
    except Exception as e:
        raise ConfigError(f"Failed to parse configuration: {e}")


# Convenience function for backward compatibility with spec
class NotifydConfig:
    """Backward-compatible configuration class that wraps functional API"""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """Initialize config from dictionary"""
        self._config = config_dict or {}
    
    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access"""
        return self._config[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dict-like assignment"""
        self._config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value with default"""
        return self._config.get(key, default)
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> NotifydConfig:
        """Load configuration from file"""
        config_dict = load_config(config_path)
        return cls(config_dict)
