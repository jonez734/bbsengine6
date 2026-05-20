# notifyd/tests/test_credentials.py
# Comprehensive tests for credential management

import os
from unittest import mock

import pytest

from bbsengine6.notifyd.credentials import (
    CredentialError,
    get_password,
    store_password,
)


class TestGetPasswordFromEnv:
    """Test retrieving passwords from environment variables"""

    def test_get_password_from_env(self):
        """Test getting password from environment variable"""
        os.environ["GMAIL_PASSWORD"] = "env_secret123"

        password = get_password("Gmail", "user@gmail.com", storage="env")
        assert password == "env_secret123"

    def test_env_var_name_conversion(self):
        """Test environment variable name conversion"""
        os.environ["MY_SERVER_PASSWORD"] = "secret"

        password = get_password("my-server", "user@example.com", storage="env")
        assert password == "secret"

    def test_env_var_uppercase(self):
        """Test that server name is converted to uppercase"""
        os.environ["CORPORATE_PASSWORD"] = "corporate_secret"

        password = get_password("corporate", "user@corp.com", storage="env")
        assert password == "corporate_secret"


class TestGetPasswordFromKeyring:
    """Test retrieving passwords from keyring"""

    def test_get_password_from_keyring(self):
        """Test getting password from keyring"""
        # Clear env var so it uses keyring
        if "GMAIL_PASSWORD" in os.environ:
            del os.environ["GMAIL_PASSWORD"]

        import sys

        mock_keyring = mock.MagicMock()
        mock_keyring.get_password.return_value = "keyring_secret"

        with mock.patch.dict(sys.modules, {"keyring": mock_keyring}):
            password = get_password(
                "Gmail",
                "user@gmail.com",
                storage="keyring",
                keyring_service="notifyd",
            )
            assert password == "keyring_secret"
            mock_keyring.get_password.assert_called_once_with(
                "notifyd", "Gmail:user@gmail.com"
            )

    def test_keyring_not_available(self):
        """Test graceful fallback when keyring not available"""
        if "GMAIL_PASSWORD" in os.environ:
            del os.environ["GMAIL_PASSWORD"]

        import sys

        mock_keyring = mock.MagicMock()
        mock_keyring.get_password.side_effect = Exception("keyring error")

        with mock.patch.dict(sys.modules, {"keyring": mock_keyring}):
            # Should raise since no other source
            with pytest.raises(CredentialError):
                get_password(
                    "Gmail",
                    "user@gmail.com",
                    storage="keyring",
                    prompt_on_missing=False,
                )


class TestGetPasswordFromPrompt:
    """Test retrieving passwords via user prompt"""

    @mock.patch("bbsengine6.notifyd.credentials.getpass.getpass")
    def test_get_password_from_prompt(self, mock_getpass):
        """Test getting password from user prompt"""
        mock_getpass.return_value = "prompted_secret"

        if "GMAIL_PASSWORD" in os.environ:
            del os.environ["GMAIL_PASSWORD"]

        password = get_password(
            "Gmail",
            "user@gmail.com",
            storage="prompt",
            prompt_on_missing=True,
        )
        assert password == "prompted_secret"
        mock_getpass.assert_called_once()

    @mock.patch("bbsengine6.notifyd.credentials.getpass.getpass")
    def test_no_prompt_when_disabled(self, mock_getpass):
        """Test that prompt is not called when disabled"""
        if "GMAIL_PASSWORD" in os.environ:
            del os.environ["GMAIL_PASSWORD"]

        with pytest.raises(CredentialError):
            get_password(
                "Gmail",
                "user@gmail.com",
                storage="prompt",
                prompt_on_missing=False,
            )

        mock_getpass.assert_not_called()


class TestHybridPasswordRetrieval:
    """Test hybrid password retrieval strategy"""

    def test_hybrid_tries_env_first(self):
        """Test that hybrid strategy tries env var first"""
        os.environ["MYSERVER_PASSWORD"] = "env_secret"

        import sys

        mock_keyring = mock.MagicMock()

        with mock.patch.dict(sys.modules, {"keyring": mock_keyring}):
            with mock.patch("getpass.getpass") as mock_prompt:
                password = get_password(
                    "myserver",
                    "user@example.com",
                    storage="hybrid",
                    prompt_on_missing=True,
                )

                assert password == "env_secret"
                # Other sources should not be tried
                mock_keyring.get_password.assert_not_called()
                mock_prompt.assert_not_called()

    def test_hybrid_falls_back_to_keyring(self):
        """Test that hybrid strategy falls back to keyring"""
        # Clear env var
        if "MYSERVER_PASSWORD" in os.environ:
            del os.environ["MYSERVER_PASSWORD"]

        import sys

        mock_keyring = mock.MagicMock()
        mock_keyring.get_password.return_value = "keyring_secret"

        with mock.patch.dict(sys.modules, {"keyring": mock_keyring}):
            with mock.patch("getpass.getpass") as mock_prompt:
                password = get_password(
                    "myserver",
                    "user@example.com",
                    storage="hybrid",
                    prompt_on_missing=False,
                )

                assert password == "keyring_secret"
                # Prompt should not be called since keyring provided password
                mock_prompt.assert_not_called()

    def test_hybrid_falls_back_to_prompt(self):
        """Test that hybrid strategy falls back to prompt"""
        # Clear env var
        if "MYSERVER_PASSWORD" in os.environ:
            del os.environ["MYSERVER_PASSWORD"]

        import sys

        mock_keyring = mock.MagicMock()
        mock_keyring.get_password.return_value = None  # Keyring has no password

        with mock.patch.dict(sys.modules, {"keyring": mock_keyring}):
            with mock.patch("getpass.getpass") as mock_prompt:
                mock_prompt.return_value = "prompted_secret"

                password = get_password(
                    "myserver",
                    "user@example.com",
                    storage="hybrid",
                    prompt_on_missing=True,
                )

                assert password == "prompted_secret"
                mock_keyring.get_password.assert_called_once()
                mock_prompt.assert_called_once()


class TestStorePassword:
    """Test storing passwords in keyring"""

    def test_store_password_success(self):
        """Test successfully storing password in keyring"""
        import sys

        mock_keyring = mock.MagicMock()

        with mock.patch.dict(sys.modules, {"keyring": mock_keyring}):
            result = store_password("Gmail", "user@gmail.com", "secret")

            assert result is True
            mock_keyring.set_password.assert_called_once_with(
                "notifyd", "Gmail:user@gmail.com", "secret"
            )

    def test_store_password_failure(self):
        """Test handling keyring store failure"""
        import sys

        mock_keyring = mock.MagicMock()
        mock_keyring.set_password.side_effect = Exception("Keyring error")

        with mock.patch.dict(sys.modules, {"keyring": mock_keyring}):
            result = store_password("Gmail", "user@gmail.com", "secret")

            assert result is False

    def test_store_password_keyring_unavailable(self):
        """Test graceful handling when keyring not available"""
        import sys

        mock_keyring = mock.MagicMock()
        mock_keyring.set_password.side_effect = ImportError("keyring not available")

        with mock.patch.dict(sys.modules, {"keyring": mock_keyring}):
            result = store_password("Gmail", "user@gmail.com", "secret")
            # Should return False when keyring not available
            assert result is False


class TestPasswordErrors:
    """Test error handling in password retrieval"""

    def test_credential_error_message(self):
        """Test error message includes helpful info"""
        if "MYSERVER_PASSWORD" in os.environ:
            del os.environ["MYSERVER_PASSWORD"]

        with pytest.raises(CredentialError) as exc_info:
            get_password(
                "MyServer",
                "user@example.com",
                storage="env",
                prompt_on_missing=False,
            )

        error_msg = str(exc_info.value)
        assert "MYSERVER_PASSWORD" in error_msg
        assert "MyServer" in error_msg

    def test_empty_prompt_response(self):
        """Test handling empty password from prompt"""
        if "MYSERVER_PASSWORD" in os.environ:
            del os.environ["MYSERVER_PASSWORD"]

        import sys

        mock_keyring = mock.MagicMock()
        mock_keyring.get_password.return_value = None

        with mock.patch.dict(sys.modules, {"keyring": mock_keyring}):
            with mock.patch("getpass.getpass") as mock_prompt:
                mock_prompt.return_value = ""  # Empty password

                with pytest.raises(CredentialError):
                    get_password(
                        "MyServer",
                        "user@example.com",
                        storage="hybrid",
                        prompt_on_missing=True,
                    )


class TestMultipleServers:
    """Test credentials for multiple servers"""

    def test_different_servers_different_passwords(self):
        """Test retrieving different passwords for different servers"""
        os.environ["GMAIL_PASSWORD"] = "gmail_secret"
        os.environ["CORPORATE_PASSWORD"] = "corporate_secret"

        gmail_pwd = get_password("Gmail", "user@gmail.com", storage="env")
        corporate_pwd = get_password("Corporate", "user@corp.com", storage="env")

        assert gmail_pwd == "gmail_secret"
        assert corporate_pwd == "corporate_secret"
        assert gmail_pwd != corporate_pwd

    def test_same_server_different_usernames(self):
        """Test same server with different usernames"""
        os.environ["GMAIL_PASSWORD"] = "shared_secret"

        pwd1 = get_password("Gmail", "user1@gmail.com", storage="env")
        pwd2 = get_password("Gmail", "user2@gmail.com", storage="env")

        # Same env var used for both users (both get same password)
        assert pwd1 == pwd2 == "shared_secret"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
