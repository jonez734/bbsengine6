# WebSocket Real-time Markdown-to-HTML Conversion Plan

## Executive Summary

Replace the current Flask WSGI app with a **WebSocket-native real-time markdown conversion server** that:
- Serves all handbook markdown files via WebSocket (primary interface)
- Converts markdown to HTML on-demand with live updates
- Maintains backward compatibility with HTTP clients via Apache reverse proxy
- Supports both browser clients (JavaScript) and BBSEngine native clients
- Keeps the current in-memory caching strategy

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Apache 2.4                              │
│                  (Reverse Proxy)                           │
└────────────────────────────────────────────────────────────┘
         │                              │
         ↓ /handbook/*                  ↓ /ws/*
    ┌─────────────────┐        ┌──────────────────────┐
    │  Fallback HTTP  │        │  WebSocket Server    │
    │  (if enabled)   │        │  (Primary Interface) │
    └─────────────────┘        │                      │
                               │ • Real-time conv.    │
                               │ • In-mem cache       │
                               │ • File serving       │
                               │ • Browser + native   │
                               │   clients            │
                               └──────────────────────┘
                                      ↓
                          ┌─────────────────────┐
                          │  Handbook Dir       │
                          │  (markdown files)   │
                          └─────────────────────┘
```

**Key Design Decisions:**
- WebSocket as PRIMARY protocol (replaces Flask)
- Keep Apache as reverse proxy (no loss of SSL, load balancing, caching)
- Single async Python server for all conversions
- HTTP fallback optional for legacy clients
- Reuse current markdown conversion + caching

---

## Phase 1: Architecture

### 1.1 Server Structure

**New WebSocket Server Component:**
```
websocket_server.py
├── AsyncServer (async WebSocket handler)
├── ConnectionManager (track connected clients)
├── MarkdownConverter (wrap existing conversion + cache)
├── FileWatcher (optional file monitoring)
└── MessageRouter (command dispatch)
```

**Keep Existing:**
- `app.py` markdown conversion logic (import + reuse)
- `convert_markdown()` function with LRU cache
- `get_markdown_title()`, `list_directory()` helpers
- HTML template and styling

### 1.2 Apache Proxy Configuration

**Current `handbook-wsgi.conf` becomes `handbook-ws.conf`:**
```apache
# Replace WSGI config with WebSocket routing
ProxyPass /ws/ ws://127.0.0.1:8001/ws/
ProxyPassReverse /ws/ ws://127.0.0.1:8001/ws/

# Optional: HTTP fallback for /handbook/*
ProxyPass /handbook/ http://127.0.0.1:8002/handbook/  # (if keeping Flask)
```

---

## Phase 2: Protocol Design

### 2.1 WebSocket Message Format

**Client → Server:**
```json
{
  "command": "get_file" | "list_dir" | "watch_file",
  "path": "/path/to/file.md",
  "session_token": "uuid-string",
  "options": {
    "include_toc": true,
    "include_breadcrumb": true,
    "format": "html" | "raw_md"
  }
}
```

**Server → Client:**
```json
{
  "type": "success" | "error" | "update",
  "command": "get_file",
  "path": "/path/to/file.md",
  "content": "<html>...</html>",
  "metadata": {
    "title": "Page Title",
    "breadcrumb": [...],
    "last_modified": "2024-01-01T10:00:00Z"
  },
  "timestamp": 1234567890.123
}
```

**For "watch_file" (persistent stream):**
```json
{
  "type": "update",
  "path": "/path/to/file.md",
  "event": "changed" | "deleted",
  "content": "<html>...</html>",
  "timestamp": 1234567890.123
}
```

### 2.2 Message Types

| Command | Direction | Purpose |
|---------|-----------|---------|
| `get_file` | C→S | Convert markdown file to HTML once |
| `list_dir` | C→S | List directory contents |
| `watch_file` | C→S | Subscribe to live updates (opens stream) |
| `unwatch_file` | C→S | Unsubscribe from file updates |
| `ping` | C→S | Heartbeat/keepalive |
| `pong` | S→C | Heartbeat response |
| `success` | S→C | Command completed |
| `error` | S→C | Command failed |
| `update` | S→C | File changed (watch mode) |

---

## Phase 3: File Structure

```
bbsengine6/handbook/
├── app.py                              # Keep as-is (reuse conversion logic)
├── wsgi.py                             # Keep (unused but harmless)
├── websocket_server.py                 # NEW: Main async server
├── websocket_handlers.py               # NEW: Command handlers
├── websocket_session.py                # NEW: Session validation
├── websocket_config.py                 # NEW: Configuration
│
├── handbook-ws.conf                    # NEW: Apache WebSocket config
├── handbook-websocket.service          # NEW: Systemd service
├── handbook-websocket.ini              # NEW: Server config
│
└── tests/
    ├── test_websocket_server.py        # NEW: Server integration tests
    ├── test_websocket_handlers.py      # NEW: Command handler tests
    ├── test_websocket_messages.py      # NEW: Message format tests
    └── test_markdown_conversion.py     # Existing logic still works
```

---

## Phase 4: Implementation Details

### 4.1 websocket_server.py (Main Server)

**Responsibilities:**
- Initialize WebSocket server on port 8001
- Accept client connections
- Route messages to handlers
- Manage connection lifecycle
- Handle graceful shutdown

**Pseudo-code structure:**
```python
class HandbookWebSocketServer:
    def __init__(self, host='127.0.0.1', port=8001):
        self.connections: Dict[str, ClientConnection] = {}
        self.markdown_converter = MarkdownConverter()  # Reuse from app.py
    
    async def handle_connection(self, websocket, path):
        """Handle new client connection."""
        # Authenticate (optional session validation)
        # Register connection
        # Loop: receive messages → route to handlers
        # Cleanup on disconnect
    
    async def route_message(self, connection_id, message):
        """Route message to appropriate handler."""
        # Parse JSON
        # Validate command
        # Call handler
        # Send response
    
    async def start(self):
        """Start WebSocket server."""
        async with websockets.serve(self.handle_connection, ...):
            await asyncio.Future()  # run forever
```

### 4.2 websocket_handlers.py (Command Handlers)

**Handlers to implement:**
```python
async def handle_get_file(path: str, options: dict) -> dict:
    """Load and convert markdown file to HTML."""
    # Validate path (security check)
    # Read file
    # Convert markdown → HTML (use app.convert_markdown)
    # Generate breadcrumb (use app.get_breadcrumb)
    # Return HTML + metadata

async def handle_list_dir(path: str) -> dict:
    """List directory contents."""
    # Validate path
    # List files/dirs
    # Return formatted list (use app.list_directory)

async def handle_watch_file(path: str, connection_id: str) -> None:
    """Subscribe to file updates (persistent stream)."""
    # Register connection for this file
    # On file change: send update to all watching connections
    # (File watching: event-driven on-demand = manual polling or periodic checks)

async def handle_unwatch_file(path: str, connection_id: str) -> None:
    """Unsubscribe from file updates."""
    # Deregister connection for this file
```

### 4.3 websocket_session.py (Session Validation)

**Validate bbsengine6.session tokens:**
```python
async def validate_session(session_token: str) -> Optional[dict]:
    """Check if token is valid session in bbsengine6.session."""
    # Query: SELECT * FROM engine.session WHERE id = %s
    # Check: expiry > now()
    # Return: session dict or None if invalid
```

### 4.4 websocket_config.py (Configuration)

```python
# Network
WS_HOST = "127.0.0.1"
WS_PORT = 8001
WS_TIMEOUT = 60  # seconds

# Markdown conversion
MARKDOWN_EXTENSIONS = [
    'toc', 'tables', 'fenced_code', 'codehilite', 'extra'
]
CACHE_SIZE = 128  # LRU cache (from current app.py)

# File serving
HANDBOOK_DIR = Path(__file__).parent
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Watch mode
FILE_WATCH_ENABLED = True
WATCH_POLL_INTERVAL = 2  # seconds (for event-driven: only on request)
```

---

## Phase 5: Dependencies

**New packages to add:**
```
websockets>=12.0          # WebSocket library
watchdog>=3.0             # File watching (optional)
```

**Existing packages (reuse):**
```
flask                     # Keep for imports (if not removing Flask)
markdown                  # Markdown conversion
psycopg                   # Database (session validation)
```

---

## Phase 6: Migration Path

### Option A: Pure WebSocket (Recommended)
1. Implement WebSocket server alongside Flask
2. Apache routes `/ws/*` → WebSocket (8001)
3. Apache routes `/handbook/*` → Flask fallback (8000) [optional]
4. Deprecate Flask gradually as clients migrate to WebSocket
5. Eventually remove Flask entirely

### Option B: Parallel (Both Active)
1. Keep Flask and WebSocket running simultaneously
2. Apache routes based on path:
   - `/ws/*` → WebSocket server
   - `/handbook/*` → Flask
3. Useful for gradual migration period

### Option C: Immediate Replacement
1. Replace Flask completely with WebSocket
2. Remove WSGI layer
3. Apache only routes to WebSocket (8001)

**Recommendation:** **Option A (Pure WebSocket with fallback)** — safest migration

---

## Phase 7: Client Examples

### 7.1 Browser Client (JavaScript)

```javascript
const ws = new WebSocket('wss://bbsengine.org/ws/');

ws.onopen = () => {
  // Request markdown file
  ws.send(JSON.stringify({
    command: 'get_file',
    path: '/index.md',
    options: { include_toc: true }
  }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'success') {
    document.getElementById('content').innerHTML = msg.content;
  } else if (msg.type === 'error') {
    console.error(msg.error);
  }
};
```

### 7.2 BBSEngine Native Client (Python)

```python
import asyncio
import json
import websockets

async def fetch_handbook_page(path):
    async with websockets.connect('wss://bbsengine.org/ws/') as ws:
        # Request markdown
        await ws.send(json.dumps({
            'command': 'get_file',
            'path': path,
            'session_token': 'uuid-from-bbsengine6'
        }))
        
        # Receive HTML
        response = await ws.recv()
        msg = json.loads(response)
        return msg['content']
```

---

## Phase 8: Deployment

### 8.1 Systemd Service

**File:** `handbook-websocket.service`
```ini
[Unit]
Description=BBSEngine Handbook WebSocket Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/opencode/data/work/bbsengine6/handbook
ExecStart=/usr/bin/python3 websocket_server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 8.2 Apache Configuration

**File:** `handbook-ws.conf`
```apache
# WebSocket route
ProxyPass /ws/ ws://127.0.0.1:8001/ws/
ProxyPassReverse /ws/ ws://127.0.0.1:8001/ws/

# Optional fallback to the handbook Flask app. Production runs uWSGI
# behind mod_proxy_uwsgi; see DEPLOYMENT.md for the canonical config.
# (A gunicorn alternative exists at handbook-gunicorn.service /
# handbook-gunicorn.conf but is not the production path.)
# ProxyPass /handbook/ uwsgi://127.0.0.1:5000/handbook/

# Security headers (keep existing)
# Logging (keep existing)
```

### 8.3 Startup Commands

```bash
# Start WebSocket server
sudo systemctl start handbook-websocket
sudo systemctl enable handbook-websocket

# Reload Apache
sudo systemctl reload apache2

# Monitor logs
sudo journalctl -u handbook-websocket -f
```

---

## Phase 9: Testing Strategy

### 9.1 Unit Tests
- Message parsing (JSON validation)
- Command handlers (isolation)
- Markdown conversion (reuse existing tests)
- Session validation
- Path security (directory traversal)

### 9.2 Integration Tests
- Full connection lifecycle
- File read/convert/return
- Directory listing
- Multiple concurrent clients
- Connection timeout/cleanup
- Error handling

### 9.3 Load Tests
- 10+ concurrent connections
- Sustained load (100+ messages/sec)
- File size scalability (large markdown files)
- Memory usage profiling

---

## Phase 10: Comparison with Current Setup

| Aspect | Flask/WSGI | WebSocket |
|--------|-----------|-----------|
| **Protocol** | HTTP (request/response) | WebSocket (persistent connection) |
| **Latency** | Higher (new connection per request) | Lower (reuse connection) |
| **Real-time** | Polling required | Native push |
| **Scalability** | Single-process (uWSGI handles) | Single async process |
| **Code Reuse** | Import MarkdownConverter from app.py | Import MarkdownConverter from app.py |
| **Apache Proxy** | mod_proxy_http | mod_proxy_ws |
| **Complexity** | Simpler (Flask framework) | More complex (raw async) |

---

## Outstanding Questions Before Implementation

1. **File Watching Details**: For "event-driven on-demand," should the server:
   - Only convert when client explicitly requests via `watch_file`?
   - Or periodically check for changes (every N seconds) when clients are watching?

2. **Authentication**: Should we:
   - Require session tokens for all requests?
   - Allow anonymous access to handbook?
   - Different permissions for different users?

3. **Backward Compatibility**: Should we:
   - Keep Flask running for HTTP fallback indefinitely?
   - Remove Flask immediately?
   - Keep both temporarily during migration?

4. **Broadcasting Updates**: When a markdown file changes and multiple clients are watching:
   - Send update to all watching clients automatically?
   - Or let each client poll independently?

5. **Performance Target**: What's the expected:
   - Number of concurrent clients (you said 10s initially)?
   - Typical markdown file size (small docs vs. large references)?
   - Acceptable latency for conversion (< 100ms? < 1s)?

---

## Summary

This plan replaces the Flask/WSGI approach with a **WebSocket-native server** that:
- ✓ Handles real-time markdown-to-HTML conversion
- ✓ Reuses existing conversion logic and caching
- ✓ Supports browser clients (JavaScript) and native BBSEngine clients
- ✓ Integrates cleanly with Apache via mod_proxy
- ✓ Handles multiple concurrent clients efficiently
- ✓ Event-driven (on-demand) file conversion
- ✓ In-memory caching maintained

**Ready for implementation once you answer the outstanding questions.**
