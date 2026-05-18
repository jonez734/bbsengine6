# notifyd/imap_monitor.py
# IMAP server monitoring for detecting new emails

from __future__ import annotations

import email
import imaplib
import logging
import time
from email.message import Message
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ImapError(Exception):
    """Raised when IMAP operation fails"""

    pass


def parse_email(raw_email: bytes) -> Dict[str, Any]:
    """
    Parse RFC822 email message into dictionary.
    
    Args:
        raw_email: Raw email bytes from IMAP FETCH
    
    Returns:
        Dictionary with email fields: subject, from, to, body, date, etc.
    """
    try:
        msg = email.message_from_bytes(raw_email)
        
        # Extract headers
        subject = msg.get("Subject", "")
        from_addr = msg.get("From", "")
        to_addr = msg.get("To", "")
        date = msg.get("Date", "")
        message_id = msg.get("Message-ID", "")
        
        # Extract body (prefer plain text)
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    except Exception:
                        body = part.get_payload()
                    break
            # If no plain text, try HTML
            if not body:
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        try:
                            body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        except Exception:
                            body = part.get_payload()
                        break
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            except Exception:
                body = msg.get_payload()
        
        # Truncate body for notifications (first 500 chars)
        body = body[:500] if body else ""
        
        return {
            "subject": subject,
            "from": from_addr,
            "to": to_addr,
            "date": date,
            "message_id": message_id,
            "body": body,
        }
    except Exception as e:
        logger.error(f"Failed to parse email: {e}")
        return {
            "subject": "",
            "from": "",
            "to": "",
            "date": "",
            "message_id": "",
            "body": "",
        }


def connect_imap(
    host: str,
    port: int,
    username: str,
    password: str,
    timeout: int = 10,
) -> imaplib.IMAP4_SSL:
    """
    Connect to IMAP server.
    
    Args:
        host: IMAP server hostname
        port: IMAP server port
        username: Login username
        password: Login password
        timeout: Connection timeout in seconds
    
    Returns:
        IMAP4_SSL connection object
    
    Raises:
        ImapError: If connection fails
    """
    try:
        imap = imaplib.IMAP4_SSL(host, port, timeout=timeout)
        imap.login(username, password)
        logger.debug(f"Connected to IMAP server {host}:{port}")
        return imap
    except imaplib.IMAP4.error as e:
        raise ImapError(f"IMAP login failed: {e}") from e
    except Exception as e:
        raise ImapError(f"Failed to connect to IMAP server: {e}") from e


def get_mailbox_uids(
    imap: imaplib.IMAP4_SSL,
    mailbox: str = "INBOX",
) -> List[int]:
    """
    Get all email UIDs in mailbox.
    
    Args:
        imap: Connected IMAP4_SSL object
        mailbox: Mailbox name (default: INBOX)
    
    Returns:
        List of UID integers (sorted ascending)
    
    Raises:
        ImapError: If IMAP operation fails
    """
    try:
        imap.select(mailbox)
        status, data = imap.uid("SEARCH", None, "ALL")
        
        if status != "OK":
            raise ImapError(f"Failed to search UIDs: {status}")
        
        uid_list = []
        if data and data[0]:
            uid_list = [int(uid) for uid in data[0].split()]
        
        return sorted(uid_list)
    except ImapError:
        raise
    except Exception as e:
        raise ImapError(f"Failed to get mailbox UIDs: {e}") from e


def fetch_email(
    imap: imaplib.IMAP4_SSL,
    uid: int,
) -> bytes:
    """
    Fetch raw email for a given UID.
    
    Args:
        imap: Connected IMAP4_SSL object
        uid: Email UID
    
    Returns:
        Raw email bytes (RFC822 format)
    
    Raises:
        ImapError: If fetch fails
    """
    try:
        status, data = imap.uid("FETCH", str(uid), "(RFC822)")
        
        if status != "OK" or not data or not data[0]:
            raise ImapError(f"Failed to fetch UID {uid}")
        
        # Data format: (b'uid UID (RFC822 {size})', b'raw_email_bytes')
        return data[0][1] if len(data[0]) > 1 else b""
    except ImapError:
        raise
    except Exception as e:
        raise ImapError(f"Failed to fetch email {uid}: {e}") from e


def poll_imap(
    host: str,
    port: int,
    username: str,
    password: str,
    mailbox: str,
    last_uid: int,
    timeout: int = 10,
) -> List[Dict[str, Any]]:
    """
    Poll IMAP server for new emails since last_uid.
    
    Connects to IMAP, fetches emails with UIDs > last_uid,
    parses them into dictionaries with UID attached.
    
    Args:
        host: IMAP server hostname
        port: IMAP server port
        username: Login username
        password: Login password
        mailbox: Mailbox to check (e.g., "INBOX")
        last_uid: Last processed UID (0 for all emails)
        timeout: Connection timeout in seconds
    
    Returns:
        List of email dictionaries with "uid" key added
    
    Raises:
        ImapError: If connection or polling fails
    """
    imap = None
    try:
        imap = connect_imap(host, port, username, password, timeout)
        
        # Get all UIDs in mailbox
        all_uids = get_mailbox_uids(imap, mailbox)
        
        # Filter to new emails (UID > last_uid)
        new_uids = [uid for uid in all_uids if uid > last_uid]
        
        # Fetch and parse emails
        emails = []
        for uid in new_uids:
            try:
                raw_email = fetch_email(imap, uid)
                email_data = parse_email(raw_email)
                email_data["uid"] = uid
                emails.append(email_data)
            except ImapError as e:
                logger.warning(f"Failed to fetch email UID {uid}: {e}")
                # Continue to next email on fetch failure
                continue
        
        logger.debug(f"Found {len(emails)} new emails in {mailbox} (last_uid={last_uid})")
        return emails
    
    finally:
        if imap:
            try:
                imap.close()
                imap.logout()
            except Exception:
                pass


def poll_imap_all_mailboxes(
    host: str,
    port: int,
    username: str,
    password: str,
    mailboxes: List[str],
    get_last_uid: Callable[[str, str], int],
    timeout: int = 10,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Poll multiple IMAP mailboxes for new emails.
    
    Args:
        host: IMAP server hostname
        port: IMAP server port
        username: Login username
        password: Login password
        mailboxes: List of mailbox names to poll
        get_last_uid: Callable that retrieves last UID for (mailbox, server)
        timeout: Connection timeout in seconds
    
    Returns:
        Dictionary mapping mailbox name to list of new email dicts
    
    Raises:
        ImapError: If connection fails (partial failures are logged)
    """
    results = {}
    
    for mailbox in mailboxes:
        try:
            # Get last processed UID for this mailbox
            last_uid = get_last_uid(mailbox, mailbox)
            
            # Poll this mailbox
            emails = poll_imap(
                host,
                port,
                username,
                password,
                mailbox,
                last_uid,
                timeout,
            )
            
            results[mailbox] = emails
        except ImapError as e:
            logger.error(f"Failed to poll mailbox {mailbox}: {e}")
            results[mailbox] = []
    
    return results
