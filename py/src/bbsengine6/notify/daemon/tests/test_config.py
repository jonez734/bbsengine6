# notify/daemon/tests/test_config.py
# Comprehensive tests for configuration loading and validation

import json
import os
import tempfile

import pytest

from bbsengine6.notify.daemon.config import (
    ConfigError,
    NotifydConfig,
    _merge_config,
    _substitute_env_vars,
    _validate_credentials_config,
    _validate_database_config,
    _validate_event_handler_config,
    _validate_events_config,
    _validate_imap_server,
    _validate_logging_config,
    load_config,
)


class TestImapServerValidation:
    """Test IMAP server validation"""

    def test_valid_imap_server(self):
        """Test valid IMAP server"""
        server = {
            "name": "Gmail",
            "host": "imap.gmail.com",
            "username": "user@gmail.com",
            "recipients": ["player1"],
        }
        _validate_imap_server(server)  # Should not raise

    def test_required_name(self):
        """Test that name is required"""
        server = {
            "host": "imap.gmail.com",
            "username": "user@gmail.com",
            "recipients": ["player1"],
        }
        with pytest.raises(ConfigError, match="name is required"):
            _validate_imap_server(server)

    def test_required_host(self):
        """Test that host is required"""
        server = {
            "name": "Gmail",
            "username": "user@gmail.com",
            "recipients": ["player1"],
        }
        with pytest.raises(ConfigError, match="host is required"):
            _validate_imap_server(server)

    def test_required_username(self):
        """Test that username is required"""
        server = {
            "name": "Gmail",
            "host": "imap.gmail.com",
            "recipients": ["player1"],
        }
        with pytest.raises(ConfigError, match="username is required"):
            _validate_imap_server(server)

    def test_required_recipients(self):
        """Test that recipients list cannot be empty"""
        server = {
            "name": "Gmail",
            "host": "imap.gmail.com",
            "username": "user@gmail.com",
            "recipients": [],
        }
        with pytest.raises(ConfigError, match="recipients list cannot be empty"):
            _validate_imap_server(server)

    def test_invalid_port(self):
        """Test port validation"""
        server = {
            "name": "Gmail",
            "host": "imap.gmail.com",
            "port": 99999,
            "username": "user@gmail.com",
            "recipients": ["player1"],
        }
        with pytest.raises(ConfigError, match="port must be 1-65535"):
            _validate_imap_server(server)

    def test_invalid_urgency(self):
        """Test urgency validation"""
        server = {
            "name": "Gmail",
            "host": "imap.gmail.com",
            "username": "user@gmail.com",
            "recipients": ["player1"],
            "urgency": "INVALID",
        }
        with pytest.raises(ConfigError, match="invalid urgency"):
            _validate_imap_server(server)

    def test_valid_urgencies(self):
        """Test all valid urgency levels"""
        for urgency in ("ROUTINE", "IMPORTANT", "URGENT", "CRITICAL"):
            server = {
                "name": "Gmail",
                "host": "imap.gmail.com",
                "username": "user@gmail.com",
                "recipients": ["player1"],
                "urgency": urgency,
            }
            _validate_imap_server(server)  # Should not raise

    def test_invalid_poll_interval(self):
        """Test poll_interval validation"""
        server = {
            "name": "Gmail",
            "host": "imap.gmail.com",
            "username": "user@gmail.com",
            "recipients": ["player1"],
            "poll_interval": 0,
        }
        with pytest.raises(ConfigError, match="poll_interval must be >= 1"):
            _validate_imap_server(server)

    def test_invalid_timeout(self):
        """Test timeout validation"""
        server = {
            "name": "Gmail",
            "host": "imap.gmail.com",
            "username": "user@gmail.com",
            "recipients": ["player1"],
            "timeout": 0,
        }
        with pytest.raises(ConfigError, match="timeout must be >= 1"):
            _validate_imap_server(server)


class TestDatabaseConfigValidation:
    """Test database configuration validation"""

    def test_valid_database_config(self):
        """Test valid database configuration"""
        db_config = {
            "use_bbsengine6_db": True,
            "dbname": "bbsengine6",
            "user": "postgres",
            "port": 5432,
        }
        _validate_database_config(db_config)  # Should not raise

    def test_invalid_port(self):
        """Test invalid port"""
        db_config = {"port": 99999}
        with pytest.raises(ConfigError, match="port must be 1-65535"):
            _validate_database_config(db_config)

    def test_valid_port(self):
        """Test valid port"""
        db_config = {"port": 5432}
        _validate_database_config(db_config)  # Should not raise


class TestLoggingConfigValidation:
    """Test logging configuration validation"""

    def test_valid_logging_config(self):
        """Test valid logging configuration"""
        log_config = {"level": "INFO"}
        _validate_logging_config(log_config)  # Should not raise

    def test_invalid_level(self):
        """Test invalid log level"""
        log_config = {"level": "INVALID"}
        with pytest.raises(ConfigError, match="invalid level"):
            _validate_logging_config(log_config)

    def test_valid_levels(self):
        """Test all valid logging levels"""
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            log_config = {"level": level}
            _validate_logging_config(log_config)  # Should not raise


class TestCredentialsConfigValidation:
    """Test credentials configuration validation"""

    def test_valid_credentials_config(self):
        """Test valid credentials configuration"""
        cred_config = {"storage": "hybrid"}
        _validate_credentials_config(cred_config)  # Should not raise

    def test_invalid_storage(self):
        """Test invalid storage type"""
        cred_config = {"storage": "invalid"}
        with pytest.raises(ConfigError, match="invalid storage"):
            _validate_credentials_config(cred_config)

    def test_valid_storage_types(self):
        """Test all valid storage types"""
        for storage in ("env", "keyring", "prompt", "hybrid"):
            cred_config = {"storage": storage}
            _validate_credentials_config(cred_config)  # Should not raise


class TestEventHandlerConfigValidation:
    """Test event handler configuration validation"""

    def test_valid_event_handler_config(self):
        """Test valid event handler configuration"""
        handler = {
            "template": "user-login",
            "urgency": "ROUTINE",
        }
        _validate_event_handler_config("user.login", handler)  # Should not raise

    def test_required_template(self):
        """Test that template is required"""
        handler = {}
        with pytest.raises(ConfigError, match="template is required"):
            _validate_event_handler_config("user.login", handler)

    def test_invalid_urgency(self):
        """Test invalid urgency"""
        handler = {
            "template": "user-login",
            "urgency": "INVALID",
        }
        with pytest.raises(ConfigError, match="invalid urgency"):
            _validate_event_handler_config("user.login", handler)


class TestEventsConfigValidation:
    """Test events configuration validation"""

    def test_valid_events_config(self):
        """Test valid events configuration"""
        events = {
            "enable_custom_hooks": True,
            "handlers": {
                "user.login": {"template": "user-login"},
            },
        }
        _validate_events_config(events)  # Should not raise

    def test_invalid_handler(self):
        """Test invalid handler in events"""
        events = {
            "handlers": {
                "user.login": {"template": "", "urgency": "ROUTINE"},
            },
        }
        with pytest.raises(ConfigError):
            _validate_events_config(events)

    def test_empty_handlers(self):
        """Test events with empty handlers"""
        events = {"enable_custom_hooks": True, "handlers": {}}
        _validate_events_config(events)  # Should not raise


class TestEnvVarSubstitution:
    """Test environment variable substitution"""

    def test_substitute_single_var(self):
        """Test substituting a single environment variable"""
        os.environ["TEST_VAR"] = "test_value"
        result = _substitute_env_vars("prefix_${TEST_VAR}_suffix")
        assert result == "prefix_test_value_suffix"

    def test_substitute_multiple_vars(self):
        """Test substituting multiple environment variables"""
        os.environ["VAR1"] = "value1"
        os.environ["VAR2"] = "value2"
        result = _substitute_env_vars("${VAR1}_and_${VAR2}")
        assert result == "value1_and_value2"

    def test_no_substitution_needed(self):
        """Test string with no variables"""
        result = _substitute_env_vars("plain_string")
        assert result == "plain_string"

    def test_missing_env_var(self):
        """Test that missing env var raises ConfigError"""
        if "NONEXISTENT_VAR_12345" in os.environ:
            del os.environ["NONEXISTENT_VAR_12345"]

        with pytest.raises(ConfigError, match="not found"):
            _substitute_env_vars("${NONEXISTENT_VAR_12345}")

    def test_env_var_in_password(self):
        """Test environment variable in password field"""
        os.environ["IMAP_PASSWORD"] = "secret123"
        result = _substitute_env_vars("${IMAP_PASSWORD}")
        assert result == "secret123"

    def test_multiple_same_var(self):
        """Test multiple occurrences of same variable"""
        os.environ["VAR"] = "value"
        result = _substitute_env_vars("${VAR}_${VAR}_${VAR}")
        assert result == "value_value_value"


class TestConfigMerging:
    """Test configuration merging with defaults"""

    def test_merge_with_empty_config(self):
        """Test merging empty config with defaults"""
        defaults = {"a": 1, "b": 2}
        result = _merge_config({}, defaults)
        assert result == {"a": 1, "b": 2}

    def test_merge_override_defaults(self):
        """Test that config overrides defaults"""
        defaults = {"a": 1, "b": 2}
        config = {"b": 20}
        result = _merge_config(config, defaults)
        assert result == {"a": 1, "b": 20}

    def test_merge_add_new_keys(self):
        """Test that new keys in config are added"""
        defaults = {"a": 1}
        config = {"b": 2}
        result = _merge_config(config, defaults)
        assert result == {"a": 1, "b": 2}


class TestConfigLoading:
    """Test loading configuration from JSON file"""

    def test_load_valid_minimal_config(self):
        """Test loading valid minimal configuration"""
        config_data = {
            "logging": {"level": "INFO"},
            "database": {"use_bbsengine6_db": True},
            "imap": {
                "servers": [
                    {
                        "name": "Gmail",
                        "host": "imap.gmail.com",
                        "username": "user@gmail.com",
                        "recipients": ["player1"],
                    }
                ]
            },
            "events": {"enable_custom_hooks": True},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            f.flush()

            try:
                config = load_config(f.name)
                assert config["imap_servers"][0]["name"] == "Gmail"
                assert config["logging"]["level"] == "INFO"
            finally:
                os.unlink(f.name)

    def test_load_config_with_env_var_substitution(self):
        """Test loading config with environment variable substitution"""
        os.environ["TEST_PASSWORD"] = "secret123"

        config_data = {
            "logging": {"level": "INFO"},
            "database": {"use_bbsengine6_db": True},
            "imap": {
                "servers": [
                    {
                        "name": "Gmail",
                        "host": "imap.gmail.com",
                        "username": "user@gmail.com",
                        "password": "${TEST_PASSWORD}",
                        "recipients": ["player1"],
                    }
                ]
            },
            "events": {"enable_custom_hooks": True},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            f.flush()

            try:
                config = load_config(f.name)
                assert config["imap_servers"][0]["password"] == "secret123"
            finally:
                os.unlink(f.name)

    def test_load_missing_config_file(self):
        """Test loading non-existent config file"""
        with pytest.raises(ConfigError, match="not found"):
            load_config("/nonexistent/path/config.json")

    def test_load_invalid_json(self):
        """Test loading invalid JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            f.flush()

            try:
                with pytest.raises(ConfigError, match="Invalid JSON"):
                    load_config(f.name)
            finally:
                os.unlink(f.name)

    def test_load_config_from_env_var(self):
        """Test loading config via NOTIFYD_CONFIG env var"""
        config_data = {
            "logging": {"level": "INFO"},
            "database": {"use_bbsengine6_db": True},
            "imap": {
                "servers": [
                    {
                        "name": "Gmail",
                        "host": "imap.gmail.com",
                        "username": "user@gmail.com",
                        "recipients": ["player1"],
                    }
                ]
            },
            "events": {"enable_custom_hooks": True},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            f.flush()

            old_env = os.environ.get("NOTIFYD_CONFIG")
            try:
                os.environ["NOTIFYD_CONFIG"] = f.name

                config = load_config()  # No path argument
                assert config["imap_servers"][0]["name"] == "Gmail"
            finally:
                if old_env:
                    os.environ["NOTIFYD_CONFIG"] = old_env
                elif "NOTIFYD_CONFIG" in os.environ:
                    del os.environ["NOTIFYD_CONFIG"]
                os.unlink(f.name)

    def test_load_full_config(self):
        """Test loading full configuration with all options"""
        config_data = {
            "logging": {
                "level": "DEBUG",
                "file": "/var/log/notifyd.log",
            },
            "database": {
                "use_bbsengine6_db": True,
                "dbname": "bbsengine6",
                "user": "postgres",
                "host": "localhost",
                "port": 5432,
            },
            "polling_interval": 30,
            "credentials": {
                "storage": "hybrid",
                "keyring_service": "notifyd",
                "prompt_on_missing": True,
            },
            "imap": {
                "servers": [
                    {
                        "name": "Gmail",
                        "host": "imap.gmail.com",
                        "port": 993,
                        "use_ssl": True,
                        "username": "user@gmail.com",
                        "password": "${IMAP_PASSWORD}",
                        "mailbox": "INBOX",
                        "poll_interval": 30,
                        "notification_type": "imap.message",
                        "recipients": ["player1", "player2"],
                        "urgency": "ROUTINE",
                        "enabled": True,
                        "timeout": 10,
                    }
                ]
            },
            "events": {
                "enable_key_events": False,
                "enable_custom_hooks": True,
                "handlers": {
                    "user.login": {
                        "template": "user-login",
                        "urgency": "ROUTINE",
                        "send_to": ["@everyone"],
                    },
                    "user.logout": {
                        "template": "user-logout",
                        "urgency": "ROUTINE",
                    },
                },
            },
        }

        os.environ["IMAP_PASSWORD"] = "test_password"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            f.flush()

            try:
                config = load_config(f.name)

                # Verify all sections loaded
                assert config["logging"]["level"] == "DEBUG"
                assert config["database"]["dbname"] == "bbsengine6"
                assert config["polling_interval"] == 30
                assert config["credentials"]["storage"] == "hybrid"
                assert len(config["imap_servers"]) == 1
                assert config["imap_servers"][0]["recipients"] == ["player1", "player2"]
                assert config["imap_servers"][0]["password"] == "test_password"
                assert len(config["events"]["handlers"]) == 2
                assert "user.login" in config["events"]["handlers"]
            finally:
                os.unlink(f.name)


class TestConfigExamples:
    """Test with example configurations"""

    def test_multiple_imap_servers(self):
        """Test configuration with multiple IMAP servers"""
        config_data = {
            "logging": {"level": "INFO"},
            "database": {"use_bbsengine6_db": True},
            "imap": {
                "servers": [
                    {
                        "name": "Gmail",
                        "host": "imap.gmail.com",
                        "username": "user@gmail.com",
                        "recipients": ["player1"],
                    },
                    {
                        "name": "Corporate",
                        "host": "mail.company.com",
                        "username": "user@company.com",
                        "recipients": ["player2"],
                    },
                ]
            },
            "events": {"enable_custom_hooks": True},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            f.flush()

            try:
                config = load_config(f.name)
                assert len(config["imap_servers"]) == 2
                assert config["imap_servers"][0]["name"] == "Gmail"
                assert config["imap_servers"][1]["name"] == "Corporate"
            finally:
                os.unlink(f.name)

    def test_disabled_imap_server(self):
        """Test that disabled servers are included but marked disabled"""
        config_data = {
            "logging": {"level": "INFO"},
            "database": {"use_bbsengine6_db": True},
            "imap": {
                "servers": [
                    {
                        "name": "Gmail",
                        "host": "imap.gmail.com",
                        "username": "user@gmail.com",
                        "recipients": ["player1"],
                        "enabled": False,
                    }
                ]
            },
            "events": {"enable_custom_hooks": True},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            f.flush()

            try:
                config = load_config(f.name)
                assert not config["imap_servers"][0]["enabled"]
            finally:
                os.unlink(f.name)


class TestNotifydConfigClass:
    """Test backward-compatible NotifydConfig class"""

    def test_load_via_class(self):
        """Test loading config via NotifydConfig class"""
        config_data = {
            "logging": {"level": "INFO"},
            "database": {"use_bbsengine6_db": True},
            "imap": {
                "servers": [
                    {
                        "name": "Gmail",
                        "host": "imap.gmail.com",
                        "username": "user@gmail.com",
                        "recipients": ["player1"],
                    }
                ]
            },
            "events": {"enable_custom_hooks": True},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            f.flush()

            try:
                config = NotifydConfig.load(f.name)
                assert config["logging"]["level"] == "INFO"
                assert config.get("polling_interval") == 30
            finally:
                os.unlink(f.name)

    def test_dict_like_access(self):
        """Test dictionary-like access on NotifydConfig"""
        config = NotifydConfig({"key": "value", "number": 42})
        assert config["key"] == "value"
        assert config["number"] == 42
        assert config.get("missing", "default") == "default"

    def test_dict_like_assignment(self):
        """Test dictionary-like assignment on NotifydConfig"""
        config = NotifydConfig({})
        config["new_key"] = "new_value"
        assert config["new_key"] == "new_value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
