# bbsengine6/net/frame_address.py
# Frame address parser: RFC 3986 DSN-like URI scheme with hybrid query parameter handling

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Union
from urllib.parse import urlparse, parse_qs, urlencode, quote, unquote


class FrameScheme(Enum):
    """Supported frame address schemes."""
    TCP = "tcp"
    UDP = "udp"
    UNIX = "unix"
    WS = "ws"
    WSS = "wss"


@dataclass
class ParseResult:
    """Result object for parsing operations (error handling without exceptions)."""
    success: bool
    value: Optional[Union["FrameAddress", str, Dict]] = None
    error: Optional[str] = None
    code: Optional[str] = None  # Machine-readable error code


@dataclass
class FrameAddress:
    """
    Parsed frame address with standard and custom query parameters.
    
    Transport layer interprets standard parameters, passes custom parameters to app.
    """
    scheme: FrameScheme
    host: Optional[str]
    port: Optional[int]
    socket_path: Optional[str]
    user: Optional[str]
    password: Optional[str]
    path: str = "/"
    
    # Standard transport parameters (transport interprets these)
    timeout: Optional[int] = None  # Seconds
    retry: Optional[int] = None  # Count
    keepalive: Optional[int] = None  # Seconds
    backoff: Optional[float] = None  # Exponential backoff factor
    
    # Custom parameters (passed to application)
    custom_params: Dict[str, str] = field(default_factory=dict)
    
    def to_string(self) -> str:
        """Reconstruct DSN string from components."""
        if self.scheme == FrameScheme.UNIX:
            return f"unix://{self.socket_path}"
        
        auth = ""
        if self.user:
            if self.password:
                auth = f"{quote(self.user, safe='')}:{quote(self.password, safe='')}@"
            else:
                auth = f"{quote(self.user, safe='')}@"
        
        port_str = ""
        if self.port:
            port_str = f":{self.port}"
        
        # Build query string
        query_parts = {}
        if self.timeout is not None:
            query_parts["timeout"] = str(self.timeout)
        if self.retry is not None:
            query_parts["retry"] = str(self.retry)
        if self.keepalive is not None:
            query_parts["keepalive"] = str(self.keepalive)
        if self.backoff is not None:
            query_parts["backoff"] = str(self.backoff)
        query_parts.update(self.custom_params)
        
        query_str = ""
        if query_parts:
            query_str = "?" + urlencode(query_parts)
        
        path_str = self.path if self.path != "/" else "/"
        
        return f"{self.scheme.value}://{auth}{self.host}{port_str}{path_str}{query_str}"
    
    def validate(self) -> ParseResult:
        """Validate all fields."""
        if self.scheme in [FrameScheme.TCP, FrameScheme.UDP, FrameScheme.WS, FrameScheme.WSS]:
            if not self.host:
                return ParseResult(False, error="Host required for " + self.scheme.value, code="HOST_REQUIRED")
            if self.port and (self.port < 1 or self.port > 65535):
                return ParseResult(False, error="Port out of range", code="INVALID_PORT")
        
        if self.scheme == FrameScheme.UNIX:
            if not self.socket_path:
                return ParseResult(False, error="Socket path required for unix://", code="SOCKET_PATH_REQUIRED")
            if not self.socket_path.startswith("/"):
                return ParseResult(False, error="Unix socket path must be absolute", code="INVALID_UNIX_PATH")
            if self.port:
                return ParseResult(False, error="Port not allowed for unix://", code="PORT_NOT_ALLOWED")
        
        return ParseResult(True, value=self)


class FrameAddressParser:
    """Parser for RFC 3986 compliant frame addresses."""
    
    # Standard parameters interpreted by transport layer
    STANDARD_PARAMS = {"timeout", "retry", "keepalive", "backoff"}
    
    @staticmethod
    def parse(dsn: str) -> ParseResult:
        """
        Parse DSN string into FrameAddress.
        
        Examples:
            tcp://host:4200/
            tcp://user:pass@host:4200/resource?timeout=30&custom=val
            udp://host/
            unix:///run/frame.sock
            ws://host:80/path?token=abc123
        """
        if not dsn or not isinstance(dsn, str):
            return ParseResult(False, error="DSN must be non-empty string", code="INVALID_DSN_FORMAT")
        
        # Validate basic URI format
        if "://" not in dsn:
            return ParseResult(False, error="Invalid DSN format: missing ://", code="INVALID_URI_FORMAT")
        
        try:
            # Parse as URI
            parsed = urlparse(dsn)
            
            # Validate scheme
            scheme_result = FrameAddressParser._validate_scheme(parsed.scheme)
            if not scheme_result.success:
                return scheme_result
            scheme = scheme_result.value
            
            # Handle Unix sockets specially
            if scheme == FrameScheme.UNIX:
                socket_path = parsed.path
                if not socket_path:
                    socket_path = parsed.netloc  # Sometimes parser puts path in netloc
                
                # Check for relative path indicators in netloc
                if parsed.netloc and (parsed.netloc.startswith(".") or parsed.netloc == ""):
                    return ParseResult(False, error="Unix socket path must be absolute", code="INVALID_UNIX_PATH")
                
                if not socket_path or not socket_path.startswith("/"):
                    return ParseResult(False, error="Unix socket path must be absolute", code="INVALID_UNIX_PATH")
                
                # Reject socket paths with colons (port-like syntax)
                if ":" in socket_path:
                    return ParseResult(False, error="Port not allowed for unix://", code="PORT_NOT_ALLOWED")
                
                address = FrameAddress(
                    scheme=scheme,
                    host=None,
                    port=None,
                    socket_path=socket_path,
                    user=None,
                    password=None,
                    path="/"
                )
                return ParseResult(True, value=address)
            
            # Parse authority (user:pass@host:port)
            authority_result = FrameAddressParser._parse_authority(parsed.netloc, scheme)
            if not authority_result.success:
                return authority_result
            user, password, host, port = authority_result.value
            
            # Validate port
            if port:
                port_result = FrameAddressParser._validate_port(port, scheme)
                if not port_result.success:
                    return port_result
                port = port_result.value
            
            # Get default port if not specified
            if not port:
                port = FrameAddressParser._default_port_for_scheme(scheme)
            
            # Parse path
            path = parsed.path if parsed.path else "/"
            
            # Parse query parameters
            query_result = FrameAddressParser._parse_query_parameters(parsed.query)
            if not query_result.success:
                return query_result
            timeout, retry, keepalive, backoff, custom_params = query_result.value
            
            # Create address
            address = FrameAddress(
                scheme=scheme,
                host=host,
                port=port,
                socket_path=None,
                user=user,
                password=password,
                path=path,
                timeout=timeout,
                retry=retry,
                keepalive=keepalive,
                backoff=backoff,
                custom_params=custom_params
            )
            
            # Validate
            return address.validate()
        
        except Exception as e:
            return ParseResult(False, error=f"Parse error: {str(e)}", code="PARSE_ERROR")
    
    @staticmethod
    def _validate_scheme(scheme: str) -> ParseResult:
        """Validate and convert scheme string to FrameScheme."""
        if not scheme:
            return ParseResult(False, error="Scheme required", code="MISSING_SCHEME")
        
        try:
            frame_scheme = FrameScheme(scheme.lower())
            return ParseResult(True, value=frame_scheme)
        except ValueError:
            return ParseResult(False, error=f"Invalid scheme: {scheme}", code="INVALID_SCHEME")
    
    @staticmethod
    def _parse_authority(netloc: str, scheme: FrameScheme) -> ParseResult:
        """Extract user:pass@host:port from authority."""
        if not netloc and scheme != FrameScheme.UNIX:
            return ParseResult(False, error="Host required", code="HOST_REQUIRED")
        
        try:
            user = None
            password = None
            host = None
            port = None
            
            # Split user:pass@host:port
            if "@" in netloc:
                auth, hostport = netloc.rsplit("@", 1)
                if ":" in auth:
                    user, password = auth.split(":", 1)
                    # Decode credentials
                    user = unquote(user)
                    password = unquote(password)
                else:
                    user = unquote(auth)
            else:
                hostport = netloc
            
            # Split host:port
            if ":" in hostport:
                # Handle IPv6 addresses [::1]:port
                if hostport.startswith("["):
                    if "]:" in hostport:
                        host, port = hostport.rsplit("]:", 1)
                        host = host[1:]  # Remove leading [
                    else:
                        host = hostport
                else:
                    parts = hostport.rsplit(":", 1)
                    host = parts[0]
                    if len(parts) > 1:
                        port = parts[1]
            else:
                host = hostport
            
            return ParseResult(True, value=(user, password, host, port))
        
        except Exception as e:
            return ParseResult(False, error=f"Invalid authority: {str(e)}", code="INVALID_AUTHORITY")
    
    @staticmethod
    def _validate_port(port_str: str, scheme: FrameScheme) -> ParseResult:
        """Validate and convert port string to int."""
        if scheme == FrameScheme.UNIX:
            return ParseResult(False, error="Port not allowed for unix://", code="PORT_NOT_ALLOWED")
        
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                return ParseResult(False, error="Port out of range (1-65535)", code="INVALID_PORT")
            return ParseResult(True, value=port)
        except ValueError:
            return ParseResult(False, error="Port must be numeric", code="INVALID_PORT")
    
    @staticmethod
    def _default_port_for_scheme(scheme: FrameScheme) -> Optional[int]:
        """Get default port for scheme."""
        defaults = {
            FrameScheme.TCP: 4200,
            FrameScheme.UDP: 4200,
            FrameScheme.WS: 80,
            FrameScheme.WSS: 443,
            FrameScheme.UNIX: None,
        }
        return defaults.get(scheme)
    
    @staticmethod
    def _parse_query_parameters(query: str) -> ParseResult:
        """
        Parse query parameters into standard + custom.
        
        Transport interprets: timeout, retry, keepalive, backoff
        Everything else goes to custom_params
        """
        timeout = None
        retry = None
        keepalive = None
        backoff = None
        custom_params = {}
        
        if not query:
            return ParseResult(True, value=(timeout, retry, keepalive, backoff, custom_params))
        
        try:
            # Parse query string
            params = parse_qs(query, keep_blank_values=True)
            
            # Extract standard parameters
            if "timeout" in params:
                try:
                    timeout = int(params["timeout"][0])
                    if timeout <= 0:
                        return ParseResult(False, error="timeout must be > 0", code="INVALID_TIMEOUT")
                except (ValueError, IndexError):
                    return ParseResult(False, error="timeout must be integer", code="INVALID_TIMEOUT")
            
            if "retry" in params:
                try:
                    retry = int(params["retry"][0])
                    if retry < 0:
                        return ParseResult(False, error="retry must be >= 0", code="INVALID_RETRY")
                except (ValueError, IndexError):
                    return ParseResult(False, error="retry must be integer", code="INVALID_RETRY")
            
            if "keepalive" in params:
                try:
                    keepalive = int(params["keepalive"][0])
                    if keepalive <= 0:
                        return ParseResult(False, error="keepalive must be > 0", code="INVALID_KEEPALIVE")
                except (ValueError, IndexError):
                    return ParseResult(False, error="keepalive must be integer", code="INVALID_KEEPALIVE")
            
            if "backoff" in params:
                try:
                    backoff = float(params["backoff"][0])
                    if backoff <= 1.0:
                        return ParseResult(False, error="backoff must be > 1.0", code="INVALID_BACKOFF")
                except (ValueError, IndexError):
                    return ParseResult(False, error="backoff must be float > 1.0", code="INVALID_BACKOFF")
            
            # Everything else is custom
            for key, values in params.items():
                if key not in FrameAddressParser.STANDARD_PARAMS:
                    # Take first value (parse_qs returns lists)
                    custom_params[key] = values[0] if values else ""
            
            return ParseResult(True, value=(timeout, retry, keepalive, backoff, custom_params))
        
        except Exception as e:
            return ParseResult(False, error=f"Query parse error: {str(e)}", code="QUERY_PARSE_ERROR")


def default_port_for_scheme(scheme: FrameScheme) -> Optional[int]:
    """Get default port for scheme (utility function)."""
    return FrameAddressParser._default_port_for_scheme(scheme)
