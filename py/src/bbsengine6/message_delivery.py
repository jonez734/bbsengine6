# message_delivery.py
# Phase 1D: Multi-Channel Delivery handlers for message system

from __future__ import annotations

import logging
import os
import smtplib
import threading
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from typing import Any, Callable, Dict, List, Optional

from .message import _message_enabled, _make_args, _resolve_db, getpool
from .net.transport import channel_register_callback

logger = logging.getLogger(__name__)

_delivery_enabled: bool = True


def is_enabled() -> bool:
    return _delivery_enabled


def enable() -> None:
    global _delivery_enabled
    _delivery_enabled = True


def disable() -> None:
    global _delivery_enabled
    _delivery_enabled = False


class DeliveryHandler(ABC):
    """Abstract base class for message delivery handlers."""
    
    @abstractmethod
    def can_deliver(self, message: Dict[str, Any], recipient: str) -> bool:
        """Check if this handler can deliver to this recipient."""
        pass
    
    @abstractmethod
    def deliver(self, message: Dict[str, Any], recipient: str) -> bool:
        """Deliver the message. Returns True on success."""
        pass
    
    @property
    @abstractmethod
    def handler_name(self) -> str:
        """Unique name for this handler."""
        pass


class EmailDeliveryHandler(DeliveryHandler):
    """Email delivery handler - sends messages via SMTP.
    
    Subscribes to channels and delivers messages to users' email addresses.
    """
    
    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 25,
        from_address: str = "noreply@example.com",
        use_tls: bool = False,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_address = from_address
        self.use_tls = use_tls
        self.username = username
        self.password = password
        self._recipient_emails: Dict[str, str] = {}  # moniker -> email
    
    @property
    def handler_name(self) -> str:
        return "email"
    
    def register_email(self, moniker: str, email: str) -> None:
        """Register an email address for a user."""
        self._recipient_emails[moniker] = email
    
    def unregister_email(self, moniker: str) -> None:
        """Unregister a user's email."""
        self._recipient_emails.pop(moniker, None)
    
    def get_email(self, moniker: str) -> Optional[str]:
        """Get registered email for a user."""
        return self._recipient_emails.get(moniker)
    
    def can_deliver(self, message: Dict[str, Any], recipient: str) -> bool:
        """Check if we have an email for this recipient."""
        if not _delivery_enabled:
            return False
        return recipient in self._recipient_emails
    
    def deliver(self, message: Dict[str, Any], recipient: str) -> bool:
        """Send message via email."""
        if not self.can_deliver(message, recipient):
            return False
        
        email = self._recipient_emails.get(recipient)
        if not email:
            return False
        
        try:
            subject = message.get("content", "")[:100]
            if message.get("template"):
                subject = f"Message: {message.get('template')}"
            
            body = self._format_message(message)
            
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = self.from_address
            msg["To"] = email
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email delivered to {email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deliver email to {email}: {e}")
            return False
    
    def _format_message(self, message: Dict[str, Any]) -> str:
        """Format message for email."""
        lines = []
        lines.append("You have a new message:")
        lines.append("")
        lines.append(f"From: {message.get('sender_moniker', 'Unknown')}")
        lines.append(f"Channel: {message.get('channel', 'Unknown')}")
        lines.append(f"Time: {message.get('datestamp', '')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(message.get("content", ""))
        lines.append("")
        lines.append("---")
        lines.append("This is an automated message from the BBS.")
        return "\n".join(lines)


class SMSDeliveryHandler(DeliveryHandler):
    """SMS delivery handler - sends messages via SMS gateway.
    
    Subscribes to channels and delivers messages to users' phone numbers.
    Requires SMS gateway configuration (e.g., Twilio, AWS SNS).
    """
    
    def __init__(
        self,
        sms_gateway_url: Optional[str] = None,
        sms_api_key: Optional[str] = None,
        from_number: Optional[str] = None,
    ):
        self.sms_gateway_url = sms_gateway_url
        self.sms_api_key = sms_api_key
        self.from_number = from_number
        self._recipient_phones: Dict[str, str] = {}  # moniker -> phone
    
    @property
    def handler_name(self) -> str:
        return "sms"
    
    def register_phone(self, moniker: str, phone: str) -> None:
        """Register a phone number for a user."""
        self._recipient_phones[moniker] = phone
    
    def unregister_phone(self, moniker: str) -> None:
        """Unregister a user's phone."""
        self._recipient_phones.pop(moniker, None)
    
    def get_phone(self, moniker: str) -> Optional[str]:
        """Get registered phone for a user."""
        return self._recipient_phones.get(moniker)
    
    def can_deliver(self, message: Dict[str, Any], recipient: str) -> bool:
        """Check if we have a phone for this recipient."""
        if not _delivery_enabled:
            return False
        if not self.sms_gateway_url:
            return False
        return recipient in self._recipient_phones
    
    def deliver(self, message: Dict[str, Any], recipient: str) -> bool:
        """Send message via SMS."""
        if not self.can_deliver(message, recipient):
            return False
        
        phone = self._recipient_phones.get(recipient)
        if not phone:
            return False
        
        try:
            text = self._format_message(message)
            
            if self.sms_gateway_url and self.sms_api_key:
                self._send_via_gateway(phone, text)
            else:
                logger.warning(f"SMS gateway not configured, message to {phone} not sent")
                return False
            
            logger.info(f"SMS delivered to {phone}: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deliver SMS to {phone}: {e}")
            return False
    
    def _send_via_gateway(self, phone: str, text: str) -> None:
        """Send SMS via configured gateway."""
        import requests
        
        payload = {
            "to": phone,
            "from": self.from_number,
            "message": text,
        }
        headers = {
            "Authorization": f"Bearer {self.sms_api_key}",
            "Content-Type": "application/json",
        }
        
        response = requests.post(self.sms_gateway_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
    
    def _format_message(self, message: Dict[str, Any]) -> str:
        """Format message for SMS (truncated to 160 chars)."""
        sender = message.get("sender_moniker", "Unknown")
        content = message.get("content", "")
        
        text = f"BBS: {sender}: {content}"
        return text[:160]


class InMemoryQueueHandler(DeliveryHandler):
    """In-memory queue for messages - delivers to connected users.
    
    This is the default handler that works with the WebSocket channel system.
    """
    
    def __init__(self):
        self._handlers: List[Callable] = []
    
    @property
    def handler_name(self) -> str:
        return "inmemory"
    
    def add_handler(self, handler: Callable[[Dict[str, Any], str], None]) -> None:
        """Add a message handler callback."""
        self._handlers.append(handler)
    
    def can_deliver(self, message: Dict[str, Any], recipient: str) -> bool:
        """Always can deliver - handlers decide."""
        return True
    
    def deliver(self, message: Dict[str, Any], recipient: str) -> bool:
        """Deliver to registered handlers."""
        if not _delivery_enabled:
            return False
        
        for handler in self._handlers:
            try:
                handler(message, recipient)
            except Exception as e:
                logger.error(f"Handler error: {e}")
                return False
        return True


class DeliveryManager:
    """Manages delivery handlers and coordinates message delivery."""
    
    def __init__(self):
        self._handlers: List[DeliveryHandler] = []
        self._channel_subscriptions: Dict[str, List[DeliveryHandler]] = {}
    
    def register_handler(self, handler: DeliveryHandler) -> None:
        """Register a delivery handler."""
        self._handlers.append(handler)
        logger.info(f"Registered delivery handler: {handler.handler_name}")
    
    def subscribe_channel(self, channel: str, handler: DeliveryHandler) -> None:
        """Subscribe a handler to a channel."""
        if channel not in self._channel_subscriptions:
            self._channel_subscriptions[channel] = []
        
        if handler not in self._channel_subscriptions[channel]:
            self._channel_subscriptions[channel].append(handler)
            logger.info(f"Handler {handler.handler_name} subscribed to {channel}")
    
    def unsubscribe_channel(self, channel: str, handler: DeliveryHandler) -> None:
        """Unsubscribe a handler from a channel."""
        if channel in self._channel_subscriptions:
            self._channel_subscriptions[channel] = [
                h for h in self._channel_subscriptions[channel] if h != handler
            ]
    
    def publish_to_channel(self, channel: str, message: Dict[str, Any]) -> Dict[str, List[str]]:
        """Publish message to all handlers subscribed to channel.
        
        Returns dict mapping handler names to list of recipients that received the message.
        """
        results: Dict[str, List[str]] = {}
        
        handlers = self._channel_subscriptions.get(channel, [])
        
        for handler in handlers:
            handler_name = handler.handler_name
            results[handler_name] = []
            
            recipients = message.get("recipient_monikers", [])
            if not recipients:
                continue
            
            for recipient in recipients:
                if handler.can_deliver(message, recipient):
                    if handler.deliver(message, recipient):
                        results[handler_name].append(recipient)
        
        return results
    
    def deliver_to_recipient(
        self,
        message: Dict[str, Any],
        recipient: str,
        handler_names: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """Deliver message to a specific recipient using specified handlers.
        
        Args:
            message: Message dict
            recipient: Recipient moniker
            handler_names: List of handler names to use (None = all)
        
        Returns:
            Dict mapping handler name to success boolean
        """
        results = {}
        
        for handler in self._handlers:
            if handler_names and handler.handler_name not in handler_names:
                continue
            
            if handler.can_deliver(message, recipient):
                results[handler.handler_name] = handler.deliver(message, recipient)
        
        return results


_default_delivery_manager: Optional[DeliveryManager] = None


def get_delivery_manager() -> DeliveryManager:
    """Get the default delivery manager instance."""
    global _default_delivery_manager
    if _default_delivery_manager is None:
        _default_delivery_manager = DeliveryManager()
    return _default_delivery_manager


def subscribe_channel(channel: str, handler: DeliveryHandler) -> None:
    """Subscribe a delivery handler to a channel."""
    get_delivery_manager().subscribe_channel(channel, handler)


def publish_to_channel(channel: str, message: Dict[str, Any]) -> Dict[str, List[str]]:
    """Publish message to channel handlers."""
    return get_delivery_manager().publish_to_channel(channel, message)


def register_handler(handler: DeliveryHandler) -> None:
    """Register a delivery handler."""
    get_delivery_manager().register_handler(handler)
