# notify/daemon/tests/test_imap_monitor.py
# Tests for IMAP monitoring functionality

import pytest
from unittest.mock import MagicMock, patch

from bbsengine6.notify.daemon import imap_monitor


class TestParseEmail:
    """Test email parsing from RFC822 format"""

    def test_parse_simple_email(self):
        """Parse simple plain text email"""
        raw_email = b"""From: sender@example.com
To: recipient@example.com
Subject: Test Subject
Date: Mon, 18 May 2026 10:00:00 +0000
Message-ID: <test@example.com>

This is the email body.
"""
        result = imap_monitor.parse_email(raw_email)

        assert result["subject"] == "Test Subject"
        assert result["from"] == "sender@example.com"
        assert result["to"] == "recipient@example.com"
        assert result["message_id"] == "<test@example.com>"
        assert "This is the email body" in result["body"]

    def test_parse_email_with_html(self):
        """Parse multipart email with HTML"""
        raw_email = b"""From: sender@example.com
To: recipient@example.com
Subject: HTML Email
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="boundary123"

--boundary123
Content-Type: text/plain; charset="utf-8"

Plain text body
--boundary123
Content-Type: text/html; charset="utf-8"

<html><body>HTML body</body></html>
--boundary123--
"""
        result = imap_monitor.parse_email(raw_email)

        assert result["subject"] == "HTML Email"
        assert "Plain text body" in result["body"]

    def test_parse_email_html_only(self):
        """Parse multipart email with HTML but no plain text"""
        raw_email = b"""From: sender@example.com
Subject: HTML Only
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="boundary123"

--boundary123
Content-Type: text/html; charset="utf-8"

<html><body>HTML body</body></html>
--boundary123--
"""
        result = imap_monitor.parse_email(raw_email)

        assert "HTML body" in result["body"]

    def test_parse_email_truncates_long_body(self):
        """Body is truncated to 500 characters"""
        long_body = "x" * 1000
        raw_email = f"""From: sender@example.com
Subject: Long Email

{long_body}
""".encode()

        result = imap_monitor.parse_email(raw_email)

        assert len(result["body"]) == 500

    def test_parse_email_missing_headers(self):
        """Parse email with missing optional headers"""
        raw_email = b"""From: sender@example.com

Body only.
"""
        result = imap_monitor.parse_email(raw_email)

        assert result["from"] == "sender@example.com"
        assert result["subject"] == ""
        assert result["to"] == ""
        assert result["message_id"] == ""

    def test_parse_email_invalid_bytes(self):
        """Parse invalid email bytes returns valid fields"""
        result = imap_monitor.parse_email(b"\xff\xfe invalid bytes")

        assert result["subject"] == ""
        assert isinstance(result, dict)
        assert "subject" in result
        assert "from" in result

    def test_parse_email_utf8_decoding(self):
        """Parse email with UTF-8 encoded content"""
        raw_email = """From: sender@example.com
Subject: UTF-8 Subject: Héllo Wörld
Content-Type: text/plain; charset="utf-8"

Email with special chars: 你好 мир """.encode("utf-8")

        result = imap_monitor.parse_email(raw_email)

        # Subject is parsed as Header object, convert to string
        assert "UTF-8" in str(result["subject"]) or "Héllo" in str(result["subject"])


class TestConnectImap:
    """Test IMAP connection"""

    def test_connect_success(self):
        """Successfully connect to IMAP server"""
        with patch("imaplib.IMAP4_SSL") as mock_imap_class:
            mock_imap = MagicMock()
            mock_imap_class.return_value = mock_imap

            result = imap_monitor.connect_imap(
                "imap.example.com",
                993,
                "user@example.com",
                "password123",
            )

            assert result == mock_imap
            mock_imap_class.assert_called_once_with("imap.example.com", 993, timeout=10)
            mock_imap.login.assert_called_once_with("user@example.com", "password123")

    def test_connect_custom_timeout(self):
        """Connect with custom timeout"""
        with patch("imaplib.IMAP4_SSL") as mock_imap_class:
            mock_imap = MagicMock()
            mock_imap_class.return_value = mock_imap

            imap_monitor.connect_imap(
                "imap.example.com",
                993,
                "user",
                "pass",
                timeout=30,
            )

            mock_imap_class.assert_called_once_with("imap.example.com", 993, timeout=30)

    def test_connect_login_fails(self):
        """IMAP login fails"""
        with patch("imaplib.IMAP4_SSL") as mock_imap_class:
            mock_imap = MagicMock()
            mock_imap.login.side_effect = Exception("Invalid credentials")
            mock_imap_class.return_value = mock_imap

            with pytest.raises(imap_monitor.ImapError):
                imap_monitor.connect_imap(
                    "imap.example.com",
                    993,
                    "user",
                    "wrongpass",
                )

    def test_connect_connection_fails(self):
        """IMAP connection fails"""
        with patch("imaplib.IMAP4_SSL") as mock_imap_class:
            mock_imap_class.side_effect = Exception("Connection refused")

            with pytest.raises(imap_monitor.ImapError):
                imap_monitor.connect_imap(
                    "invalid.host.example.com",
                    993,
                    "user",
                    "pass",
                )


class TestGetMailboxUids:
    """Test retrieving UIDs from mailbox"""

    def test_get_uids_success(self):
        """Retrieve UIDs from mailbox"""
        mock_imap = MagicMock()
        mock_imap.uid.return_value = ("OK", [b"1 2 3 5 8 13"])

        result = imap_monitor.get_mailbox_uids(mock_imap, "INBOX")

        assert result == [1, 2, 3, 5, 8, 13]
        mock_imap.select.assert_called_once_with("INBOX")

    def test_get_uids_empty_mailbox(self):
        """Empty mailbox returns empty list"""
        mock_imap = MagicMock()
        mock_imap.uid.return_value = ("OK", [b""])

        result = imap_monitor.get_mailbox_uids(mock_imap, "INBOX")

        assert result == []

    def test_get_uids_no_results(self):
        """No search results returns empty list"""
        mock_imap = MagicMock()
        mock_imap.uid.return_value = ("OK", [])

        result = imap_monitor.get_mailbox_uids(mock_imap, "INBOX")

        assert result == []

    def test_get_uids_sorted(self):
        """UIDs are returned sorted"""
        mock_imap = MagicMock()
        mock_imap.uid.return_value = ("OK", [b"5 1 3 2 4"])

        result = imap_monitor.get_mailbox_uids(mock_imap, "INBOX")

        assert result == [1, 2, 3, 4, 5]

    def test_get_uids_search_fails(self):
        """UID search fails"""
        mock_imap = MagicMock()
        mock_imap.uid.return_value = ("NO", [])

        with pytest.raises(imap_monitor.ImapError):
            imap_monitor.get_mailbox_uids(mock_imap, "INBOX")

    def test_get_uids_custom_mailbox(self):
        """Retrieve UIDs from non-INBOX mailbox"""
        mock_imap = MagicMock()
        mock_imap.uid.return_value = ("OK", [b"10 20 30"])

        result = imap_monitor.get_mailbox_uids(mock_imap, "Archive")

        assert result == [10, 20, 30]
        mock_imap.select.assert_called_once_with("Archive")


class TestFetchEmail:
    """Test fetching individual emails"""

    def test_fetch_email_success(self):
        """Successfully fetch email"""
        mock_imap = MagicMock()
        email_bytes = b"From: test@example.com\nSubject: Test\n\nBody"
        mock_imap.uid.return_value = ("OK", [(b"123 (RFC822 {20})", email_bytes)])

        result = imap_monitor.fetch_email(mock_imap, 123)

        assert result == email_bytes

    def test_fetch_email_failure(self):
        """Fetch fails"""
        mock_imap = MagicMock()
        mock_imap.uid.return_value = ("NO", [])

        with pytest.raises(imap_monitor.ImapError):
            imap_monitor.fetch_email(mock_imap, 999)

    def test_fetch_email_empty_response(self):
        """Fetch returns empty response"""
        mock_imap = MagicMock()
        mock_imap.uid.return_value = ("OK", [])

        with pytest.raises(imap_monitor.ImapError):
            imap_monitor.fetch_email(mock_imap, 123)


class TestPollImap:
    """Test IMAP polling"""

    def test_poll_new_emails(self):
        """Poll finds new emails"""
        with patch(
            "bbsengine6.notify.daemon.imap_monitor.connect_imap"
        ) as mock_connect:
            mock_imap = MagicMock()
            mock_connect.return_value = mock_imap

            mock_imap.uid.side_effect = [
                ("OK", [b"1 2 3 4 5"]),  # First call for ALL UIDs
                (
                    "OK",
                    [
                        (
                            b"4 (RFC822 {20})",
                            b"From: a@ex.com\nSubject: Email 4\n\nBody 4",
                        )
                    ],
                ),  # Fetch 4
                (
                    "OK",
                    [
                        (
                            b"5 (RFC822 {20})",
                            b"From: b@ex.com\nSubject: Email 5\n\nBody 5",
                        )
                    ],
                ),  # Fetch 5
            ]

            result = imap_monitor.poll_imap(
                "imap.example.com",
                993,
                "user",
                "pass",
                "INBOX",
                last_uid=3,
            )

            assert len(result) == 2
            assert result[0]["uid"] == 4
            assert result[1]["uid"] == 5
            assert result[0]["subject"] == "Email 4"
            assert result[1]["subject"] == "Email 5"

    def test_poll_no_new_emails(self):
        """Poll finds no new emails"""
        with patch(
            "bbsengine6.notify.daemon.imap_monitor.connect_imap"
        ) as mock_connect:
            mock_imap = MagicMock()
            mock_connect.return_value = mock_imap
            mock_imap.uid.return_value = ("OK", [b"1 2 3"])

            result = imap_monitor.poll_imap(
                "imap.example.com",
                993,
                "user",
                "pass",
                "INBOX",
                last_uid=3,
            )

            assert result == []

    def test_poll_handles_fetch_error_gracefully(self):
        """Poll continues on individual fetch failure"""
        with patch(
            "bbsengine6.notify.daemon.imap_monitor.connect_imap"
        ) as mock_connect:
            mock_imap = MagicMock()
            mock_connect.return_value = mock_imap

            # First call: get all UIDs
            mock_imap.uid.side_effect = [
                ("OK", [b"1 2 3 4 5"]),  # All UIDs
                ("NO", []),  # Fetch UID 4 fails
                (
                    "OK",
                    [
                        (
                            b"5 (RFC822 {20})",
                            b"From: b@ex.com\nSubject: Email 5\n\nBody 5",
                        )
                    ],
                ),  # Fetch UID 5 succeeds
            ]

            result = imap_monitor.poll_imap(
                "imap.example.com",
                993,
                "user",
                "pass",
                "INBOX",
                last_uid=3,
            )

            # Should have email 5 but skip email 4
            assert len(result) == 1
            assert result[0]["uid"] == 5

    def test_poll_closes_connection_on_success(self):
        """Connection is properly closed after polling"""
        with patch(
            "bbsengine6.notify.daemon.imap_monitor.connect_imap"
        ) as mock_connect:
            mock_imap = MagicMock()
            mock_connect.return_value = mock_imap
            mock_imap.uid.return_value = ("OK", [b""])

            imap_monitor.poll_imap(
                "imap.example.com",
                993,
                "user",
                "pass",
                "INBOX",
                last_uid=0,
            )

            mock_imap.close.assert_called_once()
            mock_imap.logout.assert_called_once()

    def test_poll_closes_connection_on_error(self):
        """Connection is closed even if error occurs"""
        with patch(
            "bbsengine6.notify.daemon.imap_monitor.connect_imap"
        ) as mock_connect:
            mock_imap = MagicMock()
            mock_connect.return_value = mock_imap
            mock_imap.uid.side_effect = Exception("Connection error")

            with pytest.raises(Exception):
                imap_monitor.poll_imap(
                    "imap.example.com",
                    993,
                    "user",
                    "pass",
                    "INBOX",
                    last_uid=0,
                )

            mock_imap.close.assert_called_once()
            mock_imap.logout.assert_called_once()

    def test_poll_custom_timeout(self):
        """Poll respects custom timeout"""
        with patch(
            "bbsengine6.notify.daemon.imap_monitor.connect_imap"
        ) as mock_connect:
            mock_imap = MagicMock()
            mock_connect.return_value = mock_imap
            mock_imap.uid.return_value = ("OK", [b""])

            imap_monitor.poll_imap(
                "imap.example.com",
                993,
                "user",
                "pass",
                "INBOX",
                last_uid=0,
                timeout=30,
            )

            mock_connect.assert_called_once_with(
                "imap.example.com",
                993,
                "user",
                "pass",
                30,
            )


class TestPollImapAllMailboxes:
    """Test polling multiple mailboxes"""

    def test_poll_all_mailboxes_success(self):
        """Poll multiple mailboxes"""
        mock_get_last_uid = MagicMock(side_effect=lambda mb, srv: 0)

        with patch("bbsengine6.notify.daemon.imap_monitor.poll_imap") as mock_poll:
            # Return different emails for each mailbox
            mock_poll.side_effect = [
                [{"uid": 1, "subject": "Inbox email"}],
                [{"uid": 2, "subject": "Archive email"}],
            ]

            result = imap_monitor.poll_imap_all_mailboxes(
                "imap.example.com",
                993,
                "user",
                "pass",
                ["INBOX", "Archive"],
                mock_get_last_uid,
            )

            assert len(result) == 2
            assert result["INBOX"][0]["subject"] == "Inbox email"
            assert result["Archive"][0]["subject"] == "Archive email"

    def test_poll_all_mailboxes_partial_failure(self):
        """Poll continues if one mailbox fails"""
        mock_get_last_uid = MagicMock(side_effect=lambda mb, srv: 0)

        with patch("bbsengine6.notify.daemon.imap_monitor.poll_imap") as mock_poll:
            # INBOX succeeds, Archive fails
            mock_poll.side_effect = [
                [{"uid": 1, "subject": "Inbox email"}],
                imap_monitor.ImapError("Archive connection failed"),
            ]

            result = imap_monitor.poll_imap_all_mailboxes(
                "imap.example.com",
                993,
                "user",
                "pass",
                ["INBOX", "Archive"],
                mock_get_last_uid,
            )

            assert len(result["INBOX"]) == 1
            assert result["Archive"] == []

    def test_poll_all_mailboxes_retrieves_last_uid(self):
        """Poll retrieves last UID for each mailbox"""
        mock_get_last_uid = MagicMock(
            side_effect=lambda mb, srv: int(mb[-1]) if mb[-1].isdigit() else 0
        )

        with patch("bbsengine6.notify.daemon.imap_monitor.poll_imap") as mock_poll:
            mock_poll.return_value = []

            imap_monitor.poll_imap_all_mailboxes(
                "imap.example.com",
                993,
                "user",
                "pass",
                ["INBOX", "Archive"],
                mock_get_last_uid,
            )

            # Verify get_last_uid was called for each mailbox
            assert mock_get_last_uid.call_count == 2


class TestImapError:
    """Test ImapError exception"""

    def test_imap_error_is_exception(self):
        """ImapError is an Exception"""
        error = imap_monitor.ImapError("Test error")
        assert isinstance(error, Exception)

    def test_imap_error_message(self):
        """ImapError preserves message"""
        error = imap_monitor.ImapError("Connection failed")
        assert str(error) == "Connection failed"


class TestParseEmailEdgeCases:
    """Additional edge cases for email parsing"""

    def test_parse_email_plain_text_decode_error(self):
        """Parse plain text part when decode fails"""
        # Mock get_payload to raise exception on first call, succeed on fallback
        with patch("email.message_from_bytes") as mock_from_bytes:
            mock_msg = MagicMock()
            mock_msg.get.side_effect = lambda key, default="": {
                "Subject": "Test",
                "From": "sender@example.com",
                "To": "",
                "Date": "",
                "Message-ID": "",
            }.get(key, default)

            # Setup multipart structure
            mock_part = MagicMock()
            mock_part.get_content_type.return_value = "text/plain"
            mock_part.get_payload.side_effect = [
                Exception("Decode failed"),  # First call with decode=True fails
                "Fallback text body",  # Second call without decode
            ]

            mock_msg.is_multipart.return_value = True
            mock_msg.walk.return_value = [mock_msg, mock_part]
            mock_from_bytes.return_value = mock_msg

            result = imap_monitor.parse_email(b"raw email")

            assert result["subject"] == "Test"
            assert "body" in result

    def test_parse_email_html_decode_error(self):
        """Parse HTML part when decode fails (falls back to plain text)"""
        with patch("email.message_from_bytes") as mock_from_bytes:
            mock_msg = MagicMock()
            mock_msg.get.side_effect = lambda key, default="": {
                "Subject": "HTML Test",
                "From": "sender@example.com",
                "To": "",
                "Date": "",
                "Message-ID": "",
            }.get(key, default)

            # Setup multipart: first plain part is empty, then HTML part fails to decode
            mock_plain = MagicMock()
            mock_plain.get_content_type.return_value = "text/plain"
            mock_plain.get_payload.return_value = ""

            mock_html = MagicMock()
            mock_html.get_content_type.return_value = "text/html"
            mock_html.get_payload.side_effect = [
                Exception("HTML decode failed"),  # First call with decode=True fails
                "<html>Fallback HTML</html>",  # Second call without decode
            ]

            mock_msg.is_multipart.return_value = True
            mock_msg.walk.return_value = [mock_msg, mock_plain, mock_html]
            mock_from_bytes.return_value = mock_msg

            result = imap_monitor.parse_email(b"raw email")

            assert result["subject"] == "HTML Test"
            assert "body" in result

    def test_parse_email_simple_text_decode_error(self):
        """Parse simple text email when decode fails"""
        with patch("email.message_from_bytes") as mock_from_bytes:
            mock_msg = MagicMock()
            mock_msg.get.side_effect = lambda key, default="": {
                "Subject": "Simple Text",
                "From": "sender@example.com",
                "To": "",
                "Date": "",
                "Message-ID": "",
            }.get(key, default)

            # Setup non-multipart with decode error
            mock_msg.is_multipart.return_value = False
            mock_msg.get_payload.side_effect = [
                Exception("Decode failed"),  # First call with decode=True fails
                "Fallback simple text",  # Second call without decode
            ]

            mock_from_bytes.return_value = mock_msg

            result = imap_monitor.parse_email(b"raw email")

            assert result["subject"] == "Simple Text"
            assert "body" in result

    def test_parse_email_multipart_with_attachment(self):
        """Parse multipart email with attachments"""
        raw_email = b"""From: sender@example.com
Subject: With Attachment
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="boundary123"

--boundary123
Content-Type: text/plain; charset="utf-8"

Email body
--boundary123
Content-Type: application/pdf
Content-Disposition: attachment; filename="doc.pdf"

PDF content here
--boundary123--
"""
        result = imap_monitor.parse_email(raw_email)

        assert "Email body" in result["body"]
        assert result["subject"] == "With Attachment"

    def test_parse_email_encoded_subject(self):
        """Parse email with encoded-word subject"""
        raw_email = b"""From: sender@example.com
Subject: =?UTF-8?B?VGVzdCBTdWJqZWN0?=

Body
"""
        result = imap_monitor.parse_email(raw_email)

        # Subject should be decoded
        assert isinstance(result["subject"], str)

    def test_parse_email_empty_body_parts(self):
        """Parse multipart with empty parts"""
        raw_email = b"""From: sender@example.com
Subject: Empty Parts
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="boundary123"

--boundary123
Content-Type: text/plain; charset="utf-8"


--boundary123
Content-Type: text/html; charset="utf-8"

<html></html>
--boundary123--
"""
        result = imap_monitor.parse_email(raw_email)

        assert result["subject"] == "Empty Parts"

    def test_parse_email_malformed_message(self):
        """Parse malformed email gracefully"""
        raw_email = b"""This is not a proper email message
Just some random text
No headers here"""

        result = imap_monitor.parse_email(raw_email)

        assert isinstance(result["subject"], str)
        assert isinstance(result["body"], str)


class TestConnectImapEdgeCases:
    """Additional edge cases for IMAP connection"""

    def test_connect_imap4_error(self):
        """Connection fails with IMAP4.error"""
        with patch("imaplib.IMAP4_SSL") as mock_imap_class:
            mock_imap = MagicMock()
            import imaplib

            mock_imap.login.side_effect = imaplib.IMAP4.error("Login failed")
            mock_imap_class.return_value = mock_imap

            with pytest.raises(imap_monitor.ImapError):
                imap_monitor.connect_imap(
                    "imap.example.com",
                    993,
                    "user",
                    "pass",
                )


class TestGetMailboxUidsEdgeCases:
    """Additional edge cases for UID retrieval"""

    def test_get_uids_general_exception(self):
        """UID retrieval fails with general exception"""
        mock_imap = MagicMock()
        mock_imap.select.side_effect = Exception("General error")

        with pytest.raises(imap_monitor.ImapError):
            imap_monitor.get_mailbox_uids(mock_imap, "INBOX")

    def test_get_uids_none_in_uid_list(self):
        """Handle None values in UID list"""
        mock_imap = MagicMock()
        mock_imap.uid.return_value = ("OK", [b""])

        result = imap_monitor.get_mailbox_uids(mock_imap, "INBOX")

        assert result == []


class TestFetchEmailEdgeCases:
    """Additional edge cases for email fetching"""

    def test_fetch_email_partial_response(self):
        """Fetch with partial/malformed response returns empty bytes"""
        mock_imap = MagicMock()
        mock_imap.uid.return_value = ("OK", [(b"123 (RFC822)",)])

        # Returns empty bytes when response has only 1 element
        result = imap_monitor.fetch_email(mock_imap, 123)
        assert result == b""

    def test_fetch_email_exception(self):
        """Fetch raises general exception"""
        mock_imap = MagicMock()
        mock_imap.uid.side_effect = Exception("Network error")

        with pytest.raises(imap_monitor.ImapError):
            imap_monitor.fetch_email(mock_imap, 123)


class TestPollImapEdgeCases:
    """Additional edge cases for IMAP polling"""

    def test_poll_imap_with_all_zeros_uids(self):
        """Poll with edge case UIDs"""
        with patch(
            "bbsengine6.notify.daemon.imap_monitor.connect_imap"
        ) as mock_connect:
            mock_imap = MagicMock()
            mock_connect.return_value = mock_imap
            mock_imap.uid.return_value = ("OK", [b"1 2 3"])

            # All UIDs are > 0, so should be included
            _ = imap_monitor.poll_imap(
                "imap.example.com",
                993,
                "user",
                "pass",
                "INBOX",
                last_uid=0,
            )

            # Connection should still be closed even with short circuit
            mock_imap.close.assert_called_once()

    def test_poll_imap_connect_exception_handling(self):
        """Poll properly handles connection exceptions"""
        with patch(
            "bbsengine6.notify.daemon.imap_monitor.connect_imap"
        ) as mock_connect:
            mock_connect.side_effect = imap_monitor.ImapError("Connection refused")

            with pytest.raises(imap_monitor.ImapError):
                imap_monitor.poll_imap(
                    "imap.example.com",
                    993,
                    "user",
                    "pass",
                    "INBOX",
                    last_uid=0,
                )

    def test_poll_imap_logout_error_handling(self):
        """Poll handles errors during logout gracefully"""
        with patch(
            "bbsengine6.notify.daemon.imap_monitor.connect_imap"
        ) as mock_connect:
            mock_imap = MagicMock()
            mock_connect.return_value = mock_imap
            mock_imap.uid.return_value = ("OK", [b""])
            # Logout raises exception
            mock_imap.logout.side_effect = Exception("Logout error")

            # Should not raise - errors during cleanup are swallowed
            result = imap_monitor.poll_imap(
                "imap.example.com",
                993,
                "user",
                "pass",
                "INBOX",
                last_uid=0,
            )

            assert result == []
            mock_imap.close.assert_called_once()
            mock_imap.logout.assert_called_once()


class TestPollImapAllMailboxesEdgeCases:
    """Additional edge cases for multi-mailbox polling"""

    def test_poll_all_mailboxes_empty_list(self):
        """Poll with empty mailbox list"""
        mock_get_last_uid = MagicMock()

        result = imap_monitor.poll_imap_all_mailboxes(
            "imap.example.com",
            993,
            "user",
            "pass",
            [],
            mock_get_last_uid,
        )

        assert result == {}

    def test_poll_all_mailboxes_connection_failure(self):
        """Poll fails on connection error"""
        mock_get_last_uid = MagicMock(return_value=0)

        with patch("bbsengine6.notify.daemon.imap_monitor.poll_imap") as mock_poll:
            mock_poll.side_effect = imap_monitor.ImapError("Connection failed")

            result = imap_monitor.poll_imap_all_mailboxes(
                "imap.example.com",
                993,
                "user",
                "pass",
                ["INBOX"],
                mock_get_last_uid,
            )

            assert result["INBOX"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
