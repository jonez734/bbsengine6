# bbsengine6 Architecture Specification

**Version:** 0.0.1.dev  
**Last Updated:** 2026-02-23

## Table of Contents

1. [Layered Architecture](#layered-architecture)
2. [Domain-Based Organization](#domain-based-organization)
3. [Data Flow Between Layers](#data-flow-between-layers)
4. [Module System Architecture](#module-system-architecture)
5. [Visual Architecture Diagrams](#visual-architecture-diagrams)

---

## Layered Architecture

bbsengine6 follows a **4-layer architectural pattern**:

### Layer 1: Data Layer (Foundation)

**Responsibility:** Database connectivity and persistence

**Primary Modules:**
- `database.py` - PostgreSQL connection management, query execution, OID handling

**Capabilities:**
- Connection pooling with psycopg_pool
- Query building and execution with parameter safety
- Transaction management (commit/rollback)
- OID type lookups for PostgreSQL custom types
- Result formatting (dict_row conversion)

**Key Functions:**
```python
connect(args, **kwargs) -> ConnectionPool
  "Create or reuse PostgreSQL connection pool"

cursor(conn, **kwargs) -> Cursor
  "Get a cursor from connection for query execution"

insert(args, table, rec, **kwargs) -> Any
  "Insert record into table, return inserted row ID"

update(args, table, rec, **kwargs) -> bool
  "Update record in table"

delete(args, table, rec, **kwargs) -> bool
  "Delete record from table"

query(args, sql, params, **kwargs) -> list[dict]
  "Execute SQL query, return results as list of dicts"

getoid(args, typ, cur=None) -> int | None
  "Get PostgreSQL OID for a type"

mogrifysql(cur, query, params) -> str
  "Format SQL query with params for debugging"

parse_dsn(dsn) -> dict
  "Parse PostgreSQL DSN string"

make_dsn(args, **kwargs) -> str
  "Build PostgreSQL DSN from args"
```

**Depends On:**
- psycopg3 (PostgreSQL driver)
- psycopg_pool (connection pooling)
- io module (logging via echo)

---

### Layer 2: Business Logic Layer

**Responsibility:** Application-domain logic, state management, permission checking

**Primary Modules:**

#### 2a. Session Management (`bbsengine6.session`)
- **In-memory WebSocket sessions:** `SessionManager` class in `session/lib.py` — generic base for mapping session IDs to auth state. Extended by game-specific subclasses (`CasinoSessionManager`, `EmpyreSessionManager`).
- **DB-backed sessions:** Functions in `session/lib.py` (`start`, `read`, `write`, `garbagecollect`) — PostgreSQL-backed session lifecycle for CLI/web.
- Session expiration and garbage collection
- Member session tracking

**Key Functions:**
```python
start(args, **kwargs) -> bool
  "Initialize or resume user session"

build(rec) -> dict
  "Build session dict from database record"

read(args, sessionid, **kwargs) -> dict | None
  "Read session data by ID"

delete(args, sessionid, **kwargs) -> bool
  "Delete session by ID"

getmembersession(args, **kwargs) -> dict | bool | None
  "Get session for current member (None=new, False=multiple, dict=found)"

buildsession(args, **kwargs) -> dict
  "Create new session dict with defaults"

garbagecollect(args, **kwargs) -> bool
  "Remove expired sessions"
```

**Depends On:**
- database.py (persistence)
- member.py (member info)
- io module (logging)

#### 2b. Member Management (`member.py`)
- User profile and authentication
- Member credentials, flags, permissions
- Member creation and updates

**Key Functions:**
```python
build(args, row={}, **kwargs) -> dict
  "Build member dict with defaults"

getcurrentmoniker(args, **kwargs) -> str | None
  "Get current logged-in member's moniker"

getcurrentid(args, **kwargs) -> int | None
  "Get current member's database ID"

getflags(args, moniker, **kwargs) -> dict
  "Get member flags (permissions/capabilities)"

createmember(args, **kwargs) -> int | None
  "Create new member, return ID"

updatemember(args, memberid, **kwargs) -> bool
  "Update member record"
```

**Depends On:**
- database.py (persistence)
- util.py (utilities)
- io module (logging)

#### 2c. Module System (`module.py`)
- Plugin loading and execution framework
- Access control per module
- Module validation and error handling

**Key Functions:**
```python
check(args, modulename, op="run", **kwargs) -> bool
  "Check if module operation is allowed"

load(args, modulepath) -> module
  "Load and return a Python module dynamically"

run(args, modulename, **kwargs) -> Any
  "Execute module main() function with args"

runcallback(args, callback, optional=False, **kwargs) -> Any
  "Execute a callback function with error handling"

validate_function(module_name, func_name, required_signature) -> bool
  "Validate module function matches required signature"

_check_params(func_name, params, required, optional_kwargs=False) -> bool
  "Check function parameters against requirements"
```

**Depends On:**
- database.py (access control data)
- io module (logging, error display)
- importlib (module loading)

#### 2d. Utility Functions (`util.py`)
- General-purpose helpers (format, encode, parse)
- Logging integration
- Password encryption
- Date/time handling

**Key Functions:**
```
hr(acs=True, width=None, end="\n", color="{boxcolor}") -> bool
  "Display a horizontal rule (box-drawing or ASCII) to the terminal"

heading(title, **kwargs) -> str
  "Format title as heading"

pluralize(amount, singular, plural, **kwargs) -> str
  "Return singular or plural form"

datestamp(t=None, format="%Y-%m-%d %I:%M%P %Z (%a)") -> str
  "Format timestamp as string"

inputpassword(prompt, mask="X", **kwargs) -> str
  "Prompt for password with masked input"

logentry(message, *, level=logging.INFO, handler=None) -> None
  "Log message to application logger"

collapserange(lst) -> str
  "Convert [1,2,3,5,6,7] to '1-3,5-7'"

expandrange(txt) -> list
  "Convert '1-3,5-7' to [1,2,3,5,6,7]"

filedisplay(res, **kw) -> None
  "Display file content with paging"

getencryptedpassword(args, plaintextpassword) -> str
  "Hash password for storage"

checksum(data) -> str
  "Calculate checksum/hash of data"

ltree_to_path(ltree) -> str
  "Convert PostgreSQL ltree to filesystem path"

tobool(value) -> bool
  "Convert string/int/bool to boolean"

getremoteaddr() -> str
  "Get client IP address"

getcurrentloginid(args, **kwargs) -> str | None
  "Get current user's login ID"

load_sql(args, resource_name, *, package=None) -> str
  "Load SQL from resource file"
```

**Depends On:**
- io module (logging)
- logging module (Python standard)
- hashlib (password hashing)

#### 2e. Message/Blurb Management (`blurb.py`)
- Message creation and storage
- Message attributes and metadata

**Key Functions:**
```python
insert(args, **kwargs) -> int | None
  "Insert new message/blurb, return ID"

updatesigs(args, blurbid, **kwargs) -> bool
  "Update message signatures"

updateattributes(args, blurbid, attributes, **kwargs) -> bool
  "Update message attributes"
```

**Depends On:**
- database.py (persistence)
- util.py (utilities)

#### 2f. Folder Management (`folder.py`)
- Directory structure management
- Folder metadata

**Depends On:**
- database.py (persistence)

---

### Layer 3: Presentation Layer

**Responsibility:** User interaction (terminal UI and web interface)

#### 3a. Terminal UI Widgets

##### Menu Widget (`menu.py`)
Interactive menu system with keyboard navigation

**Classes:**
```python
class Menu:
  items: list[Item]
  display(**kwargs) -> None
    "Render menu to terminal"
  
  run(**kwargs) -> Item | None
    "Display menu and get user selection"

class Item:
  label: str
  description: str
  requires: str | None
  help: str | None

class Op(Enum):
  DISPLAY = auto()
  INPUT_SELECT = auto()
  QUIT = auto()
```

**Depends On:**
- util.py (formatting)
- io module (output, input)

##### Listbox Widget (`listbox.py`)
Database-backed paginated list with keyboard navigation

**Classes:**
```python
class Listbox:
  def fetchpage(page_num, page_size) -> list[ListboxItem]
    "Fetch a page of items from query"
  
  def display(**kwargs) -> None
    "Render listbox to terminal"
  
  def handle(key_code) -> None
    "Handle keyboard input (arrow keys, page up/down)"
  
  def run(**kwargs) -> ListboxResult | None
    "Display and manage listbox interaction"

class ListboxItem:
  pk: Any
  label: str
  detail: str | None
  
class ListboxResult:
  item: ListboxItem
  op: Op

class Op(Enum):
  UNKNOWN = auto()
  SELECT = auto()
  EDIT = auto()
  DELETE = auto()
  ESCAPE = auto()
```

**Depends On:**
- database.py (fetching data)
- util.py (formatting)
- io module (output, input, keyboard)

##### Form Widget (`form.py`)
Form handling and validation (QuickForm2 integration)

**Classes:**
```python
class Form:
  items: list[FormItem]
  validate() -> bool
  get_values() -> dict

class FormItem:
  name: str
  label: str
  value: Any

class FormItemCheckbox(FormItem): ...
class FormItemRadioButton(FormItem): ...
class FormItemTextbox(FormItem): ...
```

**Depends On:**
- util.py (utilities)
- io module (input validation)

##### Editor (`editor.py`)
Line-based text editor

**Functions:**
```python
init(args, **kwargs) -> None
  "Initialize editor"

access(args, **kwargs) -> bool
  "Check if user has access to editor"

line(args, **kwargs) -> str | None
  "Edit a single line of text"

help(args, **kwargs) -> str
  "Return editor help text"
```

**Depends On:**
- io.getch (character input)
- io.echo (output)

##### Input Helpers (`input.py`)
Date, datetime, email input parsing

**Functions:**
```python
inputdate(**kwargs) -> date | None
  "Prompt for and parse date"

inputdatetime(**kwargs) -> datetime | None
  "Prompt for and parse datetime"

inputemail(**kwargs) -> str | None
  "Prompt for and validate email"
```

**Depends On:**
- io module (input/output)

#### 3b. Terminal I/O Library (`io` subpackage)

Core I/O abstractions for terminal interaction

##### Output (`io/echo.py`)
Primary output function with advanced features

```python
echo(text, level="normal", end="\n", file=None, **kwargs) -> None
  "Output text with:
   - Word wrapping at terminal width
   - ANSI color code support
   - Command expansion {cmd:...}
   - Variable substitution {var:...}
   - File paging {file:...}
   - Recursive command evaluation"

echo_file(path, **kwargs) -> None
  "Display file content with paging"

setvar(name, value) -> None
  "Set echo variable for substitution"

getvar(name) -> str
  "Get echo variable value"

rendered_length(text) -> int
  "Calculate display length (accounting for ANSI codes)"

echo_traceback(exc) -> None
  "Display exception traceback"
```

**Depends On:**
- io.terminal (width detection)
- io.palette (color codes)
- io.const (ANSI constants)

##### Screen Control (`io/screen.py`)
Cursor positioning and screen management

```python
setbottombar(text) -> None
  "Set status bar at screen bottom"

setcursor(row, col) -> None
  "Move cursor to position (CUP)"

cursordown(count=1) -> None
  "Move cursor down (CUD)"

cursorforward(count=1) -> None
  "Move cursor right (CUF)"

cursorback(count=1) -> None
  "Move cursor left (CUB)"

home() -> None
  "Move cursor to top-left (HOME)"

clearscreen() -> None
  "Clear entire screen (CLS)"

eraseline() -> None
  "Clear from cursor to end of line"

erasedisplay() -> None
  "Clear from cursor to end of display"

setscrollregion(top, bottom) -> None
  "Set DECSTBM scroll region"
```

**Depends On:**
- io.terminal (capabilities)
- io.const (ANSI codes)

##### Character Input (`io/getch.py`)
Single character input with key code mapping

```python
getch() -> str
  "Read single character from terminal"

getch_str(prompt="") -> str
  "Read string from keyboard with echo"
```

**Depends On:**
- io.keymap (key codes)

##### String Input (`io/inputstring.py`)
User text input with editing

```python
inputstring(prompt="", initial="", **kwargs) -> str
  "Prompt user to enter text"
```

**Depends On:**
- io.getch (character input)
- io.echo (output)

##### Integer Input (`io/inputinteger.py`)
Numeric input with validation

```python
inputinteger(prompt="", min=None, max=None, **kwargs) -> int | None
  "Prompt user for integer in range"
```

**Depends On:**
- io.inputstring (base input)
- io.echo (output)

##### Boolean Input (`io/inputboolean.py`)
Yes/No prompts

```python
inputboolean(prompt="", default=None, **kwargs) -> bool
  "Prompt user for yes/no response"
```

**Depends On:**
- io.getch (character input)
- io.echo (output)

##### Choice Input (`io/inputchoice.py`)
Multiple choice selection

```python
inputchoice(prompt="", choices=[], **kwargs) -> str | None
  "Let user select from list of choices"
```

**Depends On:**
- io.getch (character input)
- io.echo (output)

##### Terminal Detection (`io/terminal.py`)
Terminal capabilities and characteristics

```python
get_width() -> int
  "Get terminal width in columns"

get_height() -> int
  "Get terminal height in rows"

get_termtype() -> str
  "Get terminal type (e.g., 'xterm')"

has_capability(name) -> bool
  "Check if terminal supports capability"
```

**Depends On:**
- stty (system command)
- terminfo (POSIX terminal database)

##### Color Palette (`io/palette.py`)
Color management

```python
set_palette(palette_type) -> None
  "Set color palette (ANSI, C64, RGB)"

get_color_code(name) -> str
  "Get ANSI code for color name"
```

**Supports:** ANSI 16, C64, RGB (24-bit true color)

##### Keyboard Mapping (`io/keymap.py`)
Key code definitions and mapping

```python
Key codes for:
- Arrow keys (UP, DOWN, LEFT, RIGHT)
- Function keys (F1-F12)
- Special keys (HOME, END, PAGE_UP, PAGE_DOWN)
- Ctrl+key combinations
```

**Depends On:**
- io.getch (raw input)

##### Constants (`io/const.py`)
ANSI escape sequences and control codes

---

### Layer 4: Module System (Cross-Layer)

**Responsibility:** Runtime plugin loading and execution framework

The module system overlays across layers 2 and 3, allowing dynamic loading of modules at runtime.

**Key Concepts:**
- Modules are Python packages with standardized interface
- Required functions: `init()`, `access()`, `buildargs()`, `main()`
- Access control via database queries
- Error handling and validation

**Module Lifecycle:**
```
1. check() - Verify access permission
2. load() - Load module from filesystem
3. validate_function() - Check required functions exist
4. runcallback() - Execute with error handling
5. run() - Call main() with validated arguments
```

**Depends On:**
- All lower layers (can call anything)

---

## Domain-Based Organization

bbsengine6 can also be viewed as a collection of **feature domains**, each with supporting modules:

### Domain 1: Session Management

**Purpose:** Manage user session lifecycle and persistence

**Modules:**
- `bbsengine6.session` (package: `session/lib.py`)
- `database.py` (persistence)
- `member.py` (session member info)
- `io.echo` (logging)

**Workflows:**
- Start session (login)
- Read session state
- Update session activity
- Expire session (logout/timeout)

**Data Structures:**
```python
{
  "id": "session-uuid",
  "expiry": "2026-02-24T10:30:00",
  "lastactivity": "2026-02-23T18:40:00",
  "data": {...},  # JSONB in database
  "ipaddress": "192.168.1.1",
  "useragent": "Mozilla/5.0...",
  "datecreated": "2026-02-23T09:00:00",
  "dateupdated": "2026-02-23T18:40:00",
  "moniker": "username"
}
```

---

### Domain 2: Member Management

**Purpose:** User authentication, profiles, permissions

**Modules:**
- `member.py` (primary)
- `database.py` (persistence)
- `util.py` (password hashing, utilities)
- `io.echo` (logging)

**Workflows:**
- Create member account
- Authenticate credentials
- Read member profile
- Update member info
- Check member permissions (flags)

**Data Structures:**
```python
{
  "id": 123,
  "loginid": "username",
  "moniker": "Display Name",
  "email": "user@example.com",
  "password": "hashed_password",
  "credits": 500,
  "flags": {"admin": False, "moderator": False},
  "attrs": {},  # JSONB for custom attributes
  "datecreated": "2026-01-01T00:00:00",
  "dateupdated": "2026-02-23T18:40:00",
  "ui": ["term", "web"]  # Available interfaces
}
```

---

### Domain 3: Message Storage & Display

**Purpose:** Store, retrieve, and display messages/posts

**Modules:**
- `blurb.py` (message operations)
- `database.py` (persistence)
- `folder.py` (organization)
- `listbox.py` (display/navigation)
- `util.py` (formatting)
- `io.*` (terminal display)

**Workflows:**
- Create message
- Store in folder/thread
- Retrieve for display
- Update attributes/signatures
- Navigate via listbox widget

**Data Structures:**
```python
{
  "id": 456,
  "folderid": 789,
  "from": "sender",
  "to": "recipient",
  "subject": "Title",
  "body": "Message content",
  "attributes": {
    "read": True,
    "replied": False
  },
  "datecreated": "2026-02-23T10:15:00"
}
```

---

### Domain 4: Module/Plugin System

**Purpose:** Extensibility through runtime-loaded plugins

**Modules:**
- `module.py` (primary)
- `database.py` (access control)
- `util.py` (logging, utilities)
- `io.echo` (error display)

**Workflows:**
- Check user has access to module
- Load module from filesystem
- Validate required functions exist
- Execute module with error handling
- Return results to caller

**Module Requirements:**
```python
# Every module must implement:

def init(args, **kwargs) -> None:
  """Initialize module"""

def access(args, **kwargs) -> bool:
  """Check if current user can access this module"""

def buildargs(args, **kwargs) -> argparse.Namespace:
  """Build and validate arguments for main()"""

def main(args, **kwargs) -> Any:
  """Execute module functionality"""
```

---

### Domain 5: Terminal I/O

**Purpose:** Rich terminal interaction (colors, widgets, keyboard)

**Modules:**
- `menu.py` (interactive menus)
- `listbox.py` (paginated lists)
- `form.py` (forms)
- `editor.py` (text editing)
- `input.py` (input parsing)
- `io.*` (low-level I/O)

**Features:**
- ANSI color support (16-color, 256-color, 24-bit RGB)
- C64 palette option
- Keyboard navigation (arrows, page up/down, home/end)
- Word wrapping and pagination
- Interactive widgets

---

### Domain 6: Web Interface

**Purpose:** HTTP-based access to BBS features

**Modules:**
- `engine.php` (request handling)
- `database.php` (persistence)
- `session.php` (session management)
- `libmember.php` (member utilities)
- Smarty templates
- JavaScript libraries

**Workflows:**
- HTTP request arrives
- PHP maps to page template
- Smarty renders with Twig-like syntax
- JavaScript handles client-side interaction
- Session/member data flows through PHP layer
- Can call back to Python backend if needed

---

## Data Flow Between Layers

### Scenario 1: User Login Flow

```
Terminal I/O Layer (menu.py)
  ↓ (user selects "Login")
Business Logic (module.py)
  ↓ (load login module)
Business Logic (member.py)
  ↓ (authenticate credentials)
Data Layer (database.py)
  ↓ (query member table)
PostgreSQL
  ↓ (return member record)
Data Layer (database.py)
  ↓ (return dict)
Business Logic (session/lib.py)
  ↓ (create new session)
Data Layer (database.py)
  ↓ (insert session)
PostgreSQL
  ↓ (confirm insert)
Data Layer (database.py)
  ↓ (return session ID)
Business Logic (session/lib.py)
  ↓ (store currentsessionid)
Terminal I/O (io.echo)
  ↓ (display success message)
User's Terminal
```

### Scenario 2: Message Display Flow

```
Terminal I/O (menu.py)
  ↓ (user selects "Messages")
Business Logic (module.py)
  ↓ (load messages module)
Business Logic (blurb.py)
  ↓ (query messages)
Data Layer (database.py)
  ↓ (build listbox query)
PostgreSQL
  ↓ (return message list)
Data Layer (database.py)
  ↓ (return list of dicts)
Terminal I/O (listbox.py)
  ↓ (create ListboxItem objects)
Terminal I/O (menu loop)
  ↓ (wait for user selection)
Terminal (keyboard input)
  ↓ (user presses arrow keys)
Terminal I/O (listbox.handle)
  ↓ (page up/down)
Terminal I/O (listbox.display)
  ↓ (render updated view)
User's Terminal
```

### Scenario 3: Web Request Flow

```
Browser HTTP Request
  ↓
Apache Web Server
  ↓ (route to PHP)
PHP (index.php)
  ↓
PHP (engine.php - displaypage)
  ↓
Smarty Template Engine
  ↓ (load .tpl file)
Smarty (apply modifiers)
  ↓
PHP (render HTML)
  ↓ (insert JavaScript)
Browser
  ↓ (JavaScript executes)
Browser (AJAX to PHP endpoint)
  ↓ (optional async request)
PHP
  ↓
Database/Backend Processing
  ↓
PHP (return JSON)
  ↓
Browser (update DOM)
  ↓
User's Browser
```

---

## Module System Architecture

### Module Loading Process

```
module.run(modulename, **kwargs)
  │
  ├─ check(modulename, op, **kwargs)
  │    ├─ importlib.reload() if args.debug is True
  │    ├─ importlib.import_module(modulename)
  │    ├─ Verify init(), access(), buildargs(), main() exist + callable
  │    ├─ _check_params() + inspect.signature() to validate signatures
  │    └─ m.access(args, op, **kwargs) — return False if not True
  │
  ├─ runcallback("modulename.init", **kwargs)
  │
  ├─ [if --help/-h in argv]
  │    ├─ runcallback("modulename.buildargs") → parser
  │    ├─ parser.print_help() (or auto-generated from docstring)
  │    └─ return True
  │
  ├─ runcallback("modulename.buildargs", **kwargs) → parser
  │    └─ parser.parse_args() (whitespace-stripped argv)
  │
  └─ runcallback("modulename.main", **kwargs)
       └─ Return result to caller
```

Note: `validate_function()` is a standalone utility (uses `get_type_hints()`) and is **not** part of the `check()`/`run()` flow. Those use `_check_params()` + `inspect.signature()` instead.

### Module File Structure

Modules are Python packages discovered via `sys.path`. There is no `bbsengine6/modules/` directory -- the module system uses `importlib.import_module()` with the full module name. User plugins are typically installed in a separate package (e.g., `mygame/`, `plugins/`) added to `PYTHONPATH`.

```
mymodule/
├── __init__.py
│   ├── init(args, **kwargs)
│   ├── access(args, **kwargs) -> bool
│   ├── buildargs(args, **kwargs) -> argparse.Namespace
│   └── main(args, **kwargs) -> Any
│
├── submodule1.py
├── submodule2.py
└── data/
    └── resource.sql
```

---

## Visual Architecture Diagrams

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Web Browser                          │
└────────────┬──────────────────────┬────────────────────┘
             │ HTTP Request         │ HTTP Response
             ▼                      ▲
┌─────────────────────────────────────────────────────────┐
│                  Apache Web Server                       │
│ (Route to PHP endpoints: index.php, login.php, etc.)    │
└────────────┬──────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│             PHP Layer (engine.php)                       │
│ ┌────────────────────────────────────────────────────┐ │
│ │ database.php   ← ─ ─ ─ ─ ─ ─ ─ ─ ┐               │ │
│ │ session.php    ← ─ ─ ─ ─ ─ ─ ─ ─ ├─ Queries     │ │
│ │ libmember.php  ← ─ ─ ─ ─ ─ ─ ─ ─ ┘               │ │
│ └────────────────────────────────────────────────────┘ │
│            │                        │                   │
│            ├─ Smarty Template ──────┤                   │
│            │   (page*.tpl)          │                   │
│            └─ JavaScript ───────────┘                   │
└────────────┬──────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│         Python Backend (Core Business Logic)            │
│                                                          │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│ │session/lib.py│  │   member.py  │  │  module.py   │  │
│ │              │  │              │  │              │  │
│ │  blurb.py    │  │   folder.py  │  │   util.py    │  │
│ │  listbox.py  │  │   menu.py    │  │   form.py    │  │
│ │  editor.py   │  │   input.py   │  │              │  │
│ └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                │                  │            │
│         └────────────────┼──────────────────┘            │
│                          ▼                               │
│         ┌────────────────────────────┐                  │
│         │   database.py              │                  │
│         │   (Connection Pool, ORM)   │                  │
│         └────────────────┬───────────┘                  │
│                          │                               │
│  ┌──────────────────────┴──────────────────────┐        │
│  │   io subpackage (Terminal I/O)              │        │
│  │ echo.py, screen.py, getch.py,              │        │
│  │ inputstring.py, inputinteger.py, etc.      │        │
│  └──────────────────────────────────────────┘        │
│                                                          │
│  ┌──────────────────────────────────────────┐         │
│  │   console subpackage (Admin Tools)        │        │
│  │ checkdatabase.py, checkroles.py,          │        │
│  │ member.py, createdatabase.py, etc.        │        │
│  └──────────────────────────────────────────┘         │
│                                                          │
└────────────┬──────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│       PostgreSQL Database                              │
│ (Sessions, Members, Messages, Folders, Permissions)    │
└─────────────────────────────────────────────────────────┘
```

### Layer Dependencies

```
Layer 4: MODULE SYSTEM (module.py)
  │ Uses everything below
  │
Layer 3: PRESENTATION
  ├─ Terminal UI:   menu.py, listbox.py, form.py, editor.py
  ├─ Terminal I/O:  io.*
  └─ Web:           PHP, Smarty, JavaScript
  │ Depends on Layers 1-2
  │
Layer 2: BUSINESS LOGIC
  ├─ session/lib.py, member.py, blurb.py, folder.py
  ├─ util.py (shared utilities)
  └─ input.py
  │ Depends on Layer 1
  │
Layer 1: DATA LAYER
  └─ database.py → psycopg → PostgreSQL
    (Connection pooling, query execution, ORM)
```

### Module Flow Through System

```
User Input
    │
    ▼
Terminal I/O (io.getch)
    │
    ▼
Presentation Widget (menu.py / listbox.py)
    │
    ▼
Module System (module.py)
    │
    ├─ Check access (database.py query)
    ├─ Load module (importlib)
    ├─ Validate functions
    │
    ▼
Business Logic Layer
    │
    ├─ Session (session/lib.py)
    ├─ Member (member.py)
    ├─ Messages (blurb.py)
    └─ Utilities (util.py)
    │
    ▼
Data Layer (database.py)
    │
    ▼
PostgreSQL
    │
    ▼
Back up through layers...
    │
    ▼
Terminal I/O (io.echo)
    │
    ▼
User's Terminal Display
```

---

## Key Architectural Properties

1. **Layering:** Clear separation of concerns (data ↔ logic ↔ presentation)
2. **Modularity:** Plugin system allows runtime code loading
3. **Reusability:** Shared utilities and widgets across all modules
4. **Abstraction:** Database layer abstract from business logic
5. **Extensibility:** New modules can be added without modifying core
6. **Terminal-First:** Rich terminal UI as primary interface, web as secondary

---

## Cross-Cutting Concerns

**Logging & Debugging:**
- All layers use `util.logentry()` for logging
- `io.echo()` supports debug level output
- `database.mogrifysql()` shows executed queries

**Error Handling:**
- Module system catches and displays errors
- Database layer raises exceptions
- I/O layer handles terminal errors gracefully

**Access Control:**
- Member flags checked via `member.getflags()`
- Module system enforces permissions
- Database queries validated before execution

**State Management:**
- Global `currentsessionid` in `session/lib.py`
- Global `currentmoniker` in `member.py`
- JSONB fields in PostgreSQL for flexible attributes

---

*Specification for bbsengine6 Architecture*
