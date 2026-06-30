# bbsengine6 Module Specifications

**Version:** 0.0.1.dev  
**Last Updated:** 2026-02-23

This document provides complete specifications for all modules in bbsengine6, including function signatures, parameters, return types, and brief descriptions.

## Table of Contents

1. [Core Python Modules](#core-python-modules)
2. [I/O Subpackage](#io-subpackage)
3. [Console Subpackage](#console-subpackage)
4. [PHP Modules](#php-modules)
5. [JavaScript Modules](#javascript-modules)

---

## Core Python Modules

All Python modules located in `py/src/bbsengine6/`

### database.py - PostgreSQL Interface & Connection Management

**Purpose:** Manages PostgreSQL connections, query execution, and ORM-like operations

**File Size:** ~829 lines

#### Functions

```python
def connect(args: object, pool: ConnectionPool = None, **kwargs) 
  -> psycopg.Connection | None
  "Get or create PostgreSQL connection pool connection"
  
def cursor(conn: psycopg.Connection, **kwargs) 
  -> psycopg.Cursor
  "Get cursor from connection for query execution"
  
def insert(args: object, table: str, rec: dict, mogrify: bool = False, **kwargs) 
  -> Any | None
  "Insert record into table, return inserted row ID"
  
def update(args: object, table: str, rec: dict, **kwargs) 
  -> bool
  "Update record in table by primary key"
  
def delete(args: object, table: str, rec: dict, **kwargs) 
  -> bool
  "Delete record from table by primary key"
  
def query(args: object, sql: str, params: tuple = (), **kwargs) 
  -> list[dict]
  "Execute SELECT query, return results as list of dicts"
  
def getoid(args: object, typ: str, cur: psycopg.Cursor = None) 
  -> int | None
  "Get PostgreSQL OID (Object ID) for type name"
  "Example: getoid(args, 'jsonb') returns 3802"
  
def mogrifysql(cur: psycopg.Cursor, query: str, params: tuple) 
  -> str
  "Format SQL query with interpolated parameters for debugging"
  
def parse_dsn(dsn: str) 
  -> dict[str, str]
  "Parse PostgreSQL DSN string into components"
  "Example: 'host=localhost dbname=bbsengine' → {'host': 'localhost', 'dbname': 'bbsengine'}"
  
def make_dsn(args: object, **kwargs) 
  -> str
  "Build PostgreSQL DSN string from args and kwargs"
  "Supports: dbname, user, password, host, port"
```

**Dependencies:**
- psycopg >= 3.0 (PostgreSQL driver)
- psycopg_pool (connection pooling)
- io module (logging)
- util module (utilities)

---

### session.py - User Session Management

**Purpose:** Manages user session lifecycle, persistence, and retrieval

**File Size:** ~313 lines

**Global Variables:**
```python
currentsessionid: str | None = None
  "Current session ID for logged-in user"
```

#### Functions

```python
def build(rec: dict) 
  -> dict
  "Build session dict from database record"
  "Extracts: id, expiry, lastactivity, data, ipaddress, useragent, datecreated, dateupdated, moniker"
  
def start(args: object, **kwargs) 
  -> bool
  "Initialize or resume user session"
  "Creates new session if needed, reuses existing if found"
  
def read(args: object, sessionid: str, **kwargs) 
  -> dict | None
  "Read session data by ID"
  
def delete(args: object, sessionid: str, **kwargs) 
  -> bool
  "Delete session by ID (logout)"
  
def getmembersession(args: object, **kwargs) 
  -> dict | bool | None
  "Get session for current member"
  "Returns: None (new session), dict (found), False (multiple sessions error)"
  
def buildsession(args: object, **kwargs) 
  -> dict
  "Create new session dict with defaults"
  "Sets: id (UUID), expiry, lastactivity, data ({}), ipaddress, useragent, datecreated, dateupdated"
  
def garbagecollect(args: object, **kwargs) 
  -> bool
  "Remove expired sessions from database"
  
def read(args: object, sessionid: str, **kwargs) 
  -> dict | list | None
  "Read session by ID"
```

**Data Structure:**
```python
{
  "id": "550e8400-e29b-41d4-a716-446655440000",  # UUID
  "expiry": "2026-02-24T10:30:00",               # ISO 8601
  "lastactivity": "2026-02-23T18:40:00",         # ISO 8601
  "data": {...},                                  # JSONB in database
  "ipaddress": "192.168.1.1",
  "useragent": "Mozilla/5.0...",
  "datecreated": "2026-02-23T09:00:00",
  "dateupdated": "2026-02-23T18:40:00",
  "moniker": "username"
}
```

**Dependencies:**
- database module (persistence)
- member module (member info)
- io module (logging)
- uuid (Python standard)
- datetime (Python standard)

---

### member.py - User Management & Authentication

**Purpose:** Manages user profiles, authentication, flags, and permissions

**File Size:** ~703 lines

**Global Variables:**
```python
currentmoniker: str | None = None
  "Current logged-in member's display name"
```

#### Functions

```python
def build(args: object, row: dict = {}, **kwargs) 
  -> dict
  "Build member dict with defaults"
  "Default values: refcode=None, flags={}, loginid=None, moniker=None, credits=100, attrs={}"
  
def buildrec(member: dict) 
  -> dict
  "Build database record from member dict"
  "Converts dict/list fields to JSON for storage"
  
def getcurrentmoniker(args: object, **kwargs) 
  -> str | None
  "Get current logged-in member's moniker (display name)"
  
def getcurrentid(args: object, **kwargs) 
  -> int | None
  "Get current member's database ID"
  
def getflags(args: object, moniker: str, **kwargs) 
  -> dict
  "Get member flags (permissions/capabilities)"
  "Example flags: {'admin': False, 'moderator': False, 'verified': True}"
  
def createmember(args: object, **kwargs) 
  -> int | None
  "Create new member account, return ID"
  "Requires: loginid, moniker, email, password (plaintext)"
  
def updatemember(args: object, memberid: int, **kwargs) 
  -> bool
  "Update member record"
  
def getbyloginid(args: object, loginid: str, **kwargs) 
  -> dict | None
  "Get member by login ID"
  
def authenticate(args: object, loginid: str, password: str, **kwargs) 
  -> dict | None
  "Authenticate member by login ID and password"
  "Returns member dict if successful, None otherwise"
```

**Data Structure:**
```python
{
  "id": 123,
  "loginid": "john.doe",
  "moniker": "John",
  "email": "john@example.com",
  "password": "hashed_password_here",
  "credits": 500,
  "flags": {
    "admin": False,
    "moderator": False,
    "verified": True
  },
  "attrs": {},                    # JSONB for custom attributes
  "ui": ["term", "web"],          # Available interfaces
  "datecreated": "2026-01-01T00:00:00",
  "dateupdated": "2026-02-23T18:40:00",
  "lastlogin": "2026-02-23T18:40:00"
}
```

**Dependencies:**
- database module (persistence)
- util module (password hashing, utilities)
- io module (logging)
- pwd (Python standard - user lookup)
- json (Python standard)

---

### module.py - Plugin System & Module Loading

**Purpose:** Runtime plugin loading, validation, access control, and execution

**File Size:** ~359 lines

#### Functions

```python
def check(args: object, modulename: str, op: str = "run", **kwargs)
  -> bool
  "Check if module operation is allowed for current user"
  "Common ops: 'run', 'edit', 'delete'"
  "Uses _check_params() + inspect.signature() to validate function signatures"
   
def load(args: object, modulepath: str)
  -> types.ModuleType
  "Load and return a Python module dynamically"
  "Uses importlib.import_module() to load by full Python module name (e.g. 'mygame.mymodule')"
   
def run(args: object, modulename: str, **kwargs)
  -> Any
  "Execute module main() function with arguments"
  "Handles --help/-h: calls buildargs() and prints help if requested"
  "Calls: check() → init() → buildargs() → main() via runcallback()"
   
def runcallback(args: object, callback: Callable, optional: bool = False, **kwargs)
  -> Any
  "Execute callback function with error handling"
  "Accepts dotted 'module.func' strings or direct callables"
  "Catches exceptions and displays errors via io.echo()"
   
def validate_function(module_name: str, func_name: str, required_signature: Callable)
  -> bool
  "Validate module function exists and matches signature"
  "Standalone utility: NOT part of check()/run() flow; uses get_type_hints()"
   
def _check_params(func_name: str, params: dict, required: list, optional_kwargs: bool = False)
  -> bool
  "Validate function parameters against requirements"
  "Used internally by check() to verify function signatures"
   
def _is_help_request(argv: list) -> bool
  "Check if argv contains --help or -h"
   
def _create_help_from_docstring(module) -> argparse.ArgumentParser | None
  "Auto-generate ArgumentParser from module docstring for --help support"
```

**Alias:** `runmodule = run` (backward compatibility alias)

**Required Module Interface:**
Every module must implement these four functions:

```python
def init(args: object, **kwargs)
  -> None
  "Initialize module (called once at startup)"
   
def access(args: object, op: str = "run", **kwargs)
  -> bool
  "Check if current user has access to module"
  "Receives op parameter for granular permission control (e.g. 'run', 'edit')"
   
def buildargs(args: object, **kwargs)
  -> argparse.ArgumentParser | None
  "Build and validate arguments for main()"
  "Returns ArgumentParser or None"
   
def main(args: object, **kwargs)
  -> Any
  "Execute module functionality"
```

All four functions must accept `**kwargs`.

**Module Execution Flow:**
```
module.run()
  │
  ├─ check(modulename, op)
  │    ├─ importlib.reload() if args.debug is True
  │    ├─ importlib.import_module()
  │    ├─ Verify init(), access(), buildargs(), main() exist + callable
  │    ├─ _check_params() + inspect.signature() to validate each function
  │    └─ Call m.access(args, op, **kwargs); return False if not True
  │
  ├─ runcallback("modulename.init")
  │
  ├─ [if --help/-h in argv]
  │    └─ runcallback("modulename.buildargs") → print help → return True
  │
  ├─ runcallback("modulename.buildargs") → parse_args()
  │
  └─ runcallback("modulename.main")
```

Note: `validate_function()` is a standalone signature validator using `get_type_hints()`. It is **not** part of the `check()`/`run()` execution flow — those use `_check_params()` + `inspect.signature()` directly.

**Dependencies:**
- io module (logging, error display)
- importlib (module loading)
- inspect (signature inspection)
- argparse (argument parsing and help generation)
- sys (module cache)

---

### util.py - General Purpose Utilities

**Purpose:** Shared utilities used across all modules

**File Size:** ~16,001 lines

#### Text & Formatting Functions

```python
def hr(acs: bool = True, width: int | None = None, color: str = "{boxcolor}", end: str = "\n")
  -> None
  "Display a horizontal rule (box-drawing or ASCII) to the terminal"
  
def heading(title: str, **kwargs) 
  -> str
  "Format title as heading with decorative border"
  
def pluralize(amount: int, singular: str, plural: str,
              quantity: bool = True, emoji: str = "", determiner: str = "a", **kw)
  -> str
  "Return singular or plural form with optional count and emoji"
  "Example: pluralize(3, 'message', 'messages') → '3 messages'"
  "Note: singular and plural are required (no footgun defaults)."
  "Emoji is followed by exactly one space when present, none when empty."
  
def oxfordcomma(seq: list, conjunction: str = "and") 
  -> str
  "Format list with Oxford comma"
  "Example: oxfordcomma(['a', 'b', 'c']) → 'a, b, and c'"
```

#### Date & Time Functions

```python
def datestamp(t: datetime | None = None, 
              format: str = "%Y-%m-%d %I:%M%P %Z (%a)") 
  -> str
  "Format timestamp as human-readable string"
  "Example: '2026-02-23 06:40pm EST (Tue)'"
  
def timedelta(delta: datetime.timedelta) 
  -> str
  "Format timedelta as human-readable duration"
```

#### Password & Encryption Functions

```python
def getencryptedpassword(args: object, plaintextpassword: str) 
  -> str
  "Hash password for storage (uses bcrypt or similar)"
  
def inputpassword(prompt: str = "password: ", mask: str = "X", **kwargs) 
  -> str
  "Prompt user for password with masked input"
```

#### Logging Functions

```python
def logentry(message: str, *, level: int = logging.INFO, 
             handler: logging.Handler | None = None,
             formatter: logging.Formatter | None = None) 
  -> None
  "Log message to application logger"
  "Levels: logging.DEBUG, INFO, WARNING, ERROR, CRITICAL"
```

#### Range Functions

```python
def collapserange(lst: list) 
  -> str
  "Convert list of numbers to range string"
  "Example: [1,2,3,5,6,7] → '1-3,5-7'"
  
def expandrange(txt: str) 
  -> list
  "Convert range string to list of numbers"
  "Example: '1-3,5-7' → [1,2,3,5,6,7]"
  
def rangestr(ranges: list) 
  -> str
  "Format range list as string"
  
def printr(ranges: list) 
  -> None
  "Print ranges to stdout"
```

#### File Operations

```python
def filedisplay(res: Any, **kw) 
  -> None
  "Display file content with paging"
  "Options: more=True, width=None"
  
def verifyDirExistsWritable(dirname: str, **kw) 
  -> bool
  "Check if directory exists and is writable"
  
def verifyFileExistsReadable(filename: str, **kw) 
  -> bool
  "Check if file exists and is readable"
  
def verifyFileExistsReadableWritable(filename: str, **kw) 
  -> bool
  "Check if file exists and is readable/writable"
  
def get_safe_path(args: object, *components, **kwargs) 
  -> str
  "Build safe filesystem path from components"
  
def load_sql(args: object, resource_name: str, *, package: str | None = None) 
  -> str
  "Load SQL script from resource file"
```

#### Hashing & Checksums

```python
def checksum(data: bytes) 
  -> str
  "Calculate checksum/hash of data (SHA256)"
  
def ltree_to_path(ltree: str) 
  -> str
  "Convert PostgreSQL ltree to filesystem path"
  "Example: '1.2.3' → '/path/to/node'"
  
def chop_last_element(ltree: str) 
  -> str
  "Remove last element from ltree path"
```

#### Type Conversion

```python
def tobool(value: Any) 
  -> bool
  "Convert string/int/bool to boolean"
  "Accepts: True/False, yes/no, on/off, 1/0"
```

#### System Functions

```python
def getremoteaddr() 
  -> str
  "Get client IP address (from environment/socket)"
  
def getcurrentloginid(args: object, **kwargs) 
  -> str | None
  "Get current user's login ID"
  
def diceroll(sides: int = 6, count: int = 1, mode: str = "single") 
  -> int | list
  "Roll dice (for games/features)"
```

#### String Utilities

```python
def strip_ansi(s: str) 
  -> str
  "Remove ANSI escape sequences from string"
  
def serialize_datetimes(data: Any) 
  -> dict
  "Convert datetime objects to ISO 8601 strings in nested structures"
```

**Dependencies:**
- io module (logging via echo)
- logging (Python standard)
- hashlib (checksums)
- datetime (Python standard)
- random (dice rolls)
- re (regular expressions)

---

### menu.py - Interactive Menu Widget

**Purpose:** Display interactive menus with keyboard navigation

**File Size:** ~272 lines

#### Classes

```python
class Menu:
  """Interactive menu container"""
  items: list[Item]
  
  def display(**kwargs) 
    -> None
    "Render menu to terminal"
    
  def run(**kwargs) 
    -> Item | None
    "Display menu and get user selection"
    
  def resolverequires(args, **kwargs) 
    -> bool
    "Evaluate 'requires' condition for item visibility"

class Item:
  """Menu item"""
  label: str                    # Display text
  description: str              # Help text
  requires: str | None          # Condition to show item
  help: str | None              # Extended help
  callback: Callable | None     # Function to call
  module: str | None            # Module to load and run
  
  def __init__(label, description, requires=None, help=None, ...)

class Op(Enum):
  """Menu operation"""
  DISPLAY = auto()             # Render menu
  INPUT_SELECT = auto()        # Get user selection
  QUIT = auto()                # Exit menu
```

**Keyboard Navigation:**
- Arrow keys (UP/DOWN): Move selection
- ENTER: Select item
- ESC/Q: Quit menu
- ?: Show help
- Number keys: Jump to item (if numbered)

**Dependencies:**
- util module (formatting)
- io module (output, input)
- database module (access control)

---

### listbox.py - Paginated List Widget

**Purpose:** Display database-backed paginated lists with keyboard navigation

**File Size:** ~480 lines

#### Classes

```python
class Listbox:
  """Database-backed paginated list widget"""
  query: str                    # SQL query
  page_size: int               # Items per page
  current_page: int            # Current page number
  
  def fetchpage(page_num: int, page_size: int) 
    -> list[ListboxItem]
    "Fetch a page of items from query"
    
  def display(**kwargs) 
    -> None
    "Render listbox to terminal"
    "Shows: item list, pagination info, status bar"
    
  def handle(key_code: str) 
    -> None
    "Handle keyboard input"
    "Supports: UP/DOWN (movement), PAGEUP/PAGEDOWN, HOME/END, ENTER, ESC"
    
  def run(**kwargs) 
    -> ListboxResult | None
    "Display and manage listbox interaction"
    "Blocking call until user selects or escapes"

class ListboxItem:
  """Item in listbox"""
  pk: Any                       # Primary key (item ID)
  label: str                    # Display text
  detail: str | None            # Optional detail line
  data: dict | None             # Optional data dict
  
  def __init__(pk, label, detail=None, data=None)

class ListboxResult:
  """Result of listbox interaction"""
  item: ListboxItem             # Selected item
  op: Op                        # Operation performed
  
  def __init__(item, op)

class Op(Enum):
  """Listbox operation"""
  UNKNOWN = auto()
  SELECT = auto()              # User pressed ENTER
  EDIT = auto()                # User pressed E (if enabled)
  DELETE = auto()              # User pressed D (if enabled)
  ESCAPE = auto()              # User pressed ESC
```

**Keyboard Navigation:**
- UP/DOWN: Move selection
- PAGEUP/PAGEDOWN: Page through items
- HOME/END: Jump to first/last page
- ENTER: Select item
- ESC: Exit listbox
- E: Edit item (if enabled)
- D: Delete item (if enabled)

**Dependencies:**
- database module (fetching items)
- util module (formatting)
- io module (output, input, keyboard)

---

### form.py - Form Handling

**Purpose:** HTML/QuickForm2 integration for form handling

**File Size:** ~622 lines

#### Classes

```python
class Form:
  """Form container"""
  items: list[FormItem]
  name: str
  method: str                   # 'GET' or 'POST'
  
  def validate() 
    -> bool
    "Validate all form items"
    
  def get_values() 
    -> dict
    "Get validated values as dict"

class FormItem:
  """Base form item"""
  name: str
  label: str
  required: bool = False
  value: Any = None
  error: str | None = None
  
  def validate() 
    -> bool
    "Validate item value"

class FormItemCheckbox(FormItem):
  """Checkbox input"""
  value: bool

class FormItemRadioButton(FormItem):
  """Radio button input"""
  options: list[tuple[str, str]]  # [(value, label), ...]
  value: str

class FormItemTextbox(FormItem):
  """Text input field"""
  maxlength: int | None = None
  pattern: str | None = None
  value: str
```

**Dependencies:**
- util module (utilities)
- io module (input validation)

---

### editor.py - Line-Based Text Editor

**Purpose:** Terminal-based line editor for text input

**File Size:** ~354 lines

#### Functions

```python
def init(args: object, **kwargs) 
  -> None
  "Initialize editor"
  
def access(args: object, **kwargs) 
  -> bool
  "Check if user has access to editor"
  
def buildargs(args: object, **kwargs) 
  -> argparse.Namespace
  "Build arguments for main()"
  
def main(args: object, **kwargs) 
  -> str | None
  "Main editor loop, returns edited text or None"
  
def line(args: object, **kwargs) 
  -> str | None
  "Edit a single line of text"
  
def help(args: object, **kwargs) 
  -> str
  "Return editor help text"
```

**Editor Commands:**
- Text editing: Standard line editing
- ^H or BACKSPACE: Delete character
- ^D or DELETE: Delete character forward
- ^A: Move to start of line
- ^E: Move to end of line
- ^K: Delete to end of line
- ^U: Delete entire line
- ^L: Refresh display
- ENTER: Submit line
- ESC: Cancel

**Dependencies:**
- io.getch (character input)
- io.echo (output)
- io.screen (cursor control)

> **Note:** The old `editor.py` is deprecated. The new `ed/` package (`bbsengine6.ed`) provides both visual and line-based editors with more features. Use `from bbsengine6.ed import run` for the new API.

---

### input.py - Input Parsing

**Purpose:** Parse and validate user input (dates, datetimes, emails)

**File Size:** ~210 lines

#### Functions

```python
def inputdate(prompt: str = "Date (YYYY-MM-DD): ", **kwargs) 
  -> datetime.date | None
  "Parse date input from user"
  
def inputdatetime(prompt: str = "DateTime (YYYY-MM-DD HH:MM): ", **kwargs) 
  -> datetime.datetime | None
  "Parse datetime input from user"
  
def inputemail(prompt: str = "Email: ", **kwargs) 
  -> str | None
  "Prompt and validate email address"
  
def inputurl(prompt: str = "URL: ", **kwargs) 
  -> str | None
  "Prompt and validate URL"
```

**Dependencies:**
- io module (input/output)
- datetime (Python standard)
- re (regex validation)

---

### blurb.py - Message/Post Management

**Purpose:** Create, store, and manage messages/posts

**File Size:** ~130 lines

#### Functions

```python
def insert(args: object, **kwargs) 
  -> int | None
  "Insert new message/blurb, return ID"
  "Requires: folderid, from, to, subject, body"
  
def updatesigs(args: object, blurbid: int, **kwargs) 
  -> bool
  "Update message signatures (quote markers, etc.)"
  
def updateattributes(args: object, blurbid: int, attributes: dict, **kwargs) 
  -> bool
  "Update message attributes (read, replied, flagged, etc.)"
```

**Dependencies:**
- database module (persistence)
- util module (formatting, utilities)

---

### folder.py - Directory/Folder Management

**Purpose:** Manage message folders and directory structure (SIGs). Uses PostgreSQL ltree extension for hierarchical paths.

**File Size:** ~380 lines

#### Functions

```python
def insert(args, folder, **kwargs) -> int | bool
  "Insert a new folder/sig. Sets datecreated, createdbymoniker."

def create(args, folder, **kwargs) -> bool
  "Create a new folder. Skips if folder already exists. Validates path. Returns True if created, False otherwise."

def get(args, path, **kwargs) -> dict | None
  "Get folder by path. Validates path for security."

def update(args, path: str, folder: dict, **kwargs) -> bool
  "Update folder by path."

def delete(args, path: str, **kwargs) -> bool
  "Delete folder by path. Validates path for security."

def buildpath(args, path: str) -> str
  "Convert folder path hyphens to underscores."

def builduri(args, path: str, top: str = "top") -> str
  "Build URI from folder path."

def builddict(args, row) -> dict
  "Build folder dict from database row."

def buildrow(args, folder) -> dict
  "Build database row from folder dict."

def input(prompt: str, oldvalue: str, **kw) -> str
  "Input folder path with autocomplete."

def allexist(buf, **kwargs) -> bool
  "Verify all folder paths in buffer exist."

def noneexist(buf, **kwargs) -> bool
  "Verify no folder paths in buffer exist."

def exists(args, buf: str, **kwargs) -> bool
  "Check if folder exists by path."

def uriexists(args, buf: str, **kwargs) -> bool
  "Check if folder exists by URI."

def getchfoldercompleter(word, **kwargs) -> list
  "Get completions for folder path input."
```

#### Security

- Path validation via `_validate_path()` with regex `^[a-zA-Z0-9._-]+$`
- Prevents ReDoS attacks via malicious regex in SQL ~ operator
- Prevents path traversal attacks

#### sig.py Alias

For backwards compatibility, `sig.py` provides an alias module that delegates to `folder.py`:

```python
from bbsengine6 import sig
sig.get(args, path)  # delegates to folder.get
sig.insert(args, folder)  # delegates to folder.insert
sig.create(args, folder)  # delegates to folder.create
sig.update(args, path, folder)  # delegates to folder.update
sig.delete(args, path)  # delegates to folder.delete
```

**Dependencies:**
- database module (persistence)
- member module (current user tracking)
- io module (error logging)

---

### screen.py - Screen Control

**Purpose:** Terminal cursor positioning and screen management

**File Size:** ~25 lines (mostly imports)

#### Functions

(This module is minimal and delegates to io.screen)

**Dependencies:**
- io.screen (actual implementation)

---

### readfile.py - File Display

**Purpose:** Display file contents with paging

**File Size:** ~158 lines

#### Functions

```python
def display(filepath: str, **kwargs) 
  -> None
  "Display file with paging"
  "Options: width=None, more=True"
```

**Dependencies:**
- util module (filedisplay)
- io module (output)

---

### engine.py - Main Engine

**Purpose:** Core engine initialization and page rendering

**File Size:** ~1 line (mostly stub)

**Note:** This module appears to be largely delegated to PHP layer for web requests

**Dependencies:**
- PHP engine.php (web layer)

---

### conf.py - Configuration

**Purpose:** Application configuration and constants

**File Size:** ~49 lines

**Global Configuration:**
```python
# Database settings (from environment or args)
DATABASE_HOST = os.getenv("BBSENGINE_DB_HOST", "localhost")
DATABASE_PORT = os.getenv("BBSENGINE_DB_PORT", 5432)
DATABASE_NAME = os.getenv("BBSENGINE_DB_NAME", "bbsengine")
DATABASE_USER = os.getenv("BBSENGINE_DB_USER", "bbsengine")
DATABASE_PASSWORD = os.getenv("BBSENGINE_DB_PASSWORD", "")

# Connection pool settings
POOL_MIN_SIZE = 1
POOL_MAX_SIZE = 20
POOL_TIMEOUT = 30
```

**Dependencies:**
- os (Python standard)

---

### common.py - Shared Code

**Purpose:** Common utilities and constants

**File Size:** ~141 lines

**Constants:**
```python
LOGGER_NAME = "bbsengine6"
DEFAULT_TERMINAL_WIDTH = 80
DEFAULT_TERMINAL_HEIGHT = 24
```

**Common Functions:**
```python
def setup_logging(args: object, **kwargs) 
  -> logging.Logger
  "Configure application logging"
```

**Dependencies:**
- logging (Python standard)

---

### _version.py - Version Information

**Purpose:** Version tracking

```python
__version__ = "6.0.0"
```

---

## I/O Subpackage

All modules located in `py/src/bbsengine6/io/`

This subpackage provides the terminal I/O abstraction layer.

### echo.py - Terminal Output

**Purpose:** Output with advanced features (colors, variables, commands)

**Key Function:**
```python
def echo(text: str, level: str = "normal", end: str = "\n", 
         file: TextIO | None = None, **kwargs) 
  -> None
  "Output text with:
   - ANSI color code support
   - Variable substitution {var:name}
   - Command execution {cmd:function}
   - File paging {file:path}
   - Word wrapping at terminal width
   - Recursive command evaluation"
   
  Levels: "normal", "debug", "info", "warning", "error", "critical"
  
  Example:
    echo("Hello {var:username}!", color="green")
    echo("{file:/etc/motd}")  # Display file with paging
```

**Other Functions:**
```python
def echo_file(path: str, **kwargs) 
  -> None
  "Display file content with paging"
  
def setvar(name: str, value: str) 
  -> None
  "Set variable for {var:...} substitution"
  
def getvar(name: str) 
  -> str | None
  "Get variable value"
  
def rendered_length(text: str) 
  -> int
  "Calculate display length (strips ANSI codes)"
  
def echo_traceback(exc: Exception) 
  -> None
  "Display exception traceback"
```

**Dependencies:**
- io.terminal (width detection)
- io.palette (colors)
- io.const (ANSI codes)
- io.echovars (variable storage)

---

### screen.py - Screen Control

**Cursor Positioning:**
```python
def setcursor(row: int, col: int) 
  -> None
  "Move cursor to position (row, col)"
  
def cursordown(count: int = 1) 
  -> None
  "Move cursor down N rows"
  
def cursorforward(count: int = 1) 
  -> None
  "Move cursor right N columns"
  
def cursorback(count: int = 1) 
  -> None
  "Move cursor left N columns"
  
def home() 
  -> None
  "Move cursor to top-left (HOME)"

**Echo Inline Commands:**
- `{cha}` or `{cha:N}` - Cursor horizontal absolute (move to column N, default 1)
```

**Screen Control:**
```python
def clearscreen() 
  -> None
  "Clear entire screen (CLS)"
  
def eraseline() 
  -> None
  "Clear from cursor to end of line"
  
def erasedisplay() 
  -> None
  "Clear from cursor to end of display"
  
def setscrollregion(top: int, bottom: int) 
  -> None
  "Set DECSTBM scroll region"
  
def setbottombar(text: str) 
  -> None
  "Set status bar at screen bottom"
```

**Dependencies:**
- io.terminal (capabilities)
- io.const (ANSI codes)

---

### getch.py - Character Input

**Purpose:** Single character input with key code mapping

```python
def getch() 
  -> str
  "Read single character from terminal"
  "Returns: single char or key code like 'UP', 'DOWN', 'F1', etc."
  
def getch_str(prompt: str = "") 
  -> str
  "Read string from keyboard with echo"
```

**Key Codes Returned:**
- Arrows: "UP", "DOWN", "LEFT", "RIGHT"
- Functions: "F1", "F2", ..., "F12"
- Special: "HOME", "END", "PAGEUP", "PAGEDOWN", "DELETE", "INSERT"
- Control: "TAB", "ENTER", "ESCAPE"

**Dependencies:**
- io.keymap (key code definitions)
- termios, tty (Unix terminal I/O)

---

### inputstring.py - String Input

```python
def inputstring(prompt: str = "", initial: str = "", **kwargs) 
  -> str
  "Prompt user to enter text"
  "Supports: editing, history (if available)"
```

**F1 help:** Pressing F1 displays the `f1_help` string (or calls the callable).
Parameter: `f1_help: str | Callable[[], str] | None = None`

**Dependencies:**
- io.getch (character input)
- io.echo (output)

---

### inputinteger.py - Integer Input

```python
def inputinteger(prompt: str = "", min: int | None = None, 
                 max: int | None = None, **kwargs) 
  -> int | None
  "Prompt user for integer in range"
  "Validates: min <= value <= max"
```

**Dependencies:**
- io.inputstring (base input)
- io.echo (output)

---

### inputboolean.py - Boolean Input

```python
def inputboolean(prompt: str = "", default: bool | None = None, **kwargs) 
  -> bool
  "Prompt user for yes/no response"
  "Accepts: y/n, yes/no, true/false, 1/0"
```

**Dependencies:**
- io.getch (character input)
- io.echo (output)

---

### inputchoice.py - Multiple Choice

```python
def inputchoice(prompt: str = "", choices: list[str] = [], **kwargs) 
  -> str | None
  "Let user select from list of choices"
  "Supports: number keys for selection"
```

**KEY_F1 / KEY_HELP / ? support:** Pressing F1, KEY_HELP, or ? displays the `help` string.
  The `help` parameter accepts `str` or `callable(**kwargs) -> None`.
**KEY_F2 handler:** Pressing F2 calls `f2_handler` (str or callable(**kwargs) -> None).
  NOTE: For F2-F12 support, use dict pattern: `f2_handler={"KEY_F2": fn, ...}`

**Dependencies:**
- io.getch (character input)
- io.echo (output)

---

### terminal.py - Terminal Detection

```python
def get_width() 
  -> int
  "Get terminal width in columns (default: 80)"
  
def get_height() 
  -> int
  "Get terminal height in rows (default: 24)"
  
def get_termtype() 
  -> str
  "Get terminal type (e.g., 'xterm', 'vt100')"
  
def has_capability(name: str) 
  -> bool
  "Check if terminal supports capability (e.g., 'colors')"
```

**Dependencies:**
- shutil (stty command)
- terminfo (POSIX database)

---

### palette.py - Color Management

```python
def set_palette(palette_type: str = "ansi") 
  -> None
  "Set color palette"
  "Options: 'ansi' (16), 'extended' (256), 'rgb' (24-bit)"
  
def get_color_code(name: str, palette: str | None = None) 
  -> str
  "Get ANSI code for color name"
  "Colors: black, red, green, yellow, blue, magenta, cyan, white"
```

**Palette Support:**
- ANSI 16: Standard colors
- 256-color: Extended palette
- 24-bit RGB: True color

---

### keymap.py - Keyboard Mapping

**Key Code Constants:**
```python
KEY_UP = "UP"
KEY_DOWN = "DOWN"
KEY_LEFT = "LEFT"
KEY_RIGHT = "RIGHT"
KEY_HOME = "HOME"
KEY_END = "END"
KEY_PAGEUP = "PAGEUP"
KEY_PAGEDOWN = "PAGEDOWN"
KEY_F1 = "F1"
# ... F2-F12
KEY_DELETE = "DELETE"
KEY_INSERT = "INSERT"
KEY_TAB = "TAB"
KEY_ENTER = "ENTER"
KEY_ESCAPE = "ESCAPE"
```

---

### const.py - ANSI Constants

**ANSI Escape Sequences:**
```python
# Cursor control
CUP = "\033[{row};{col}H"  # Cursor to position
CUD = "\033[{n}B"          # Cursor down
CUF = "\033[{n}C"          # Cursor forward
CUB = "\033[{n}D"          # Cursor back
HOME = "\033[H"            # Cursor home

# Clearing
CLS = "\033[2J"            # Clear screen
ERASELINE = "\033[K"       # Erase to end of line
ERASEDISPLAY = "\033[J"    # Erase to end of display

# Colors (16)
ANSI_COLORS = {
  "black": 30, "red": 31, "green": 32, "yellow": 33,
  "blue": 34, "magenta": 35, "cyan": 36, "white": 37
}
```

---

### echovars.py - Variable Management

```python
def setvar(name: str, value: str) 
  -> None
  "Store variable for echo substitution"
  
def getvar(name: str) 
  -> str | None
  "Retrieve variable value"
  
def clearvar(name: str) 
  -> None
  "Delete variable"
  
def clearall() 
  -> None
  "Delete all variables"
```

---

### Other I/O Modules

- **util.py** - I/O helper utilities
- **common.py** - I/O shared code
- **output.py** - Output utilities
- **lib.py** - I/O library functions

---

## Console Subpackage

All modules located in `py/src/bbsengine6/console/`

Admin and maintenance tools for system administration.

### Console Overview

```python
# Entry point: python -m bbsengine6.console

Main console commands:
  - checkdatabase: Verify database exists and is accessible
  - checkschema: Validate schema objects and structure
  - checkroles: Check PostgreSQL roles and permissions
  - checksuperuser: Verify superuser access
  - checkwebserverrole: Check web server role exists
  - checkextensions: Verify PostgreSQL extensions
  - checkfunctions: Check custom functions exist
  - checkclasses: Verify custom class definitions
  - createdatabase: Initialize new database
  - member: Member management operations
  - memberapproval: Member approval workflow
  - email: Email functionality testing
  - alert: System alerts and notifications
```

### Key Console Functions

```python
def check_database_connectivity(args, **kwargs) 
  -> bool
  "Verify PostgreSQL database is accessible"
  
def check_schema_integrity(args, **kwargs) 
  -> list[str]
  "Validate database schema, return list of issues"
  
def check_roles(args, **kwargs) 
  -> list[str]
  "Check role existence and permissions"
  
def create_database(args, **kwargs) 
  -> bool
  "Initialize new BBSEngine database"
  
def manage_members(args, operation: str, **kwargs) 
  -> Any
  "Member operations: create, delete, approve, flag"
```

**Dependencies:**
- database module (schema access)
- util module (logging, formatting)
- io module (output)

---

## PHP Modules

All modules located in `php/`

These modules provide the web interface layer.

### engine.php - Main PHP Engine

**Key Function:**
```php
function displaypage($page, $data = array()) : void
  "Display a page with template rendering"
  "Maps page name to Smarty template and renders with data"
  
  Example: displaypage('login', array('error' => 'Invalid credentials'))
```

**Other Functions:**
```php
function setcurrentsite($site) : void
  "Set the current site context (org, com, etc.)"
  
function getcurrentsite() : string
  "Get current site name"
```

**Dependencies:**
- Smarty (template engine)
- PEAR Log (logging)
- HTML_QuickForm2 (forms)
- ReCaptcha (CAPTCHA)
- libmember.php (member utilities)
- util.php (utilities)

---

### database.php - PHP Database Layer

```php
function query($sql, $params = array()) : PDOStatement
  "Execute SQL query, return statement"
  
function fetch($sql, $params = array()) : array | false
  "Fetch single row as array"
  
function fetchall($sql, $params = array()) : array
  "Fetch all rows as array of arrays"
  
function insert($table, $data) : int | false
  "Insert record, return ID"
  
function update($table, $data, $where) : int
  "Update records, return count"
  
function delete($table, $where) : int
  "Delete records, return count"
```

**Dependencies:**
- PDO (PHP Data Objects)
- PostgreSQL driver

---

### session.php - Session Management

```php
function start() : bool
  "Start PHP session"
  
function login($loginid, $password) : bool
  "Log user in"
  
function logout() : bool
  "Log user out"
  
function isloggedin() : bool
  "Check if user is logged in"
  
function getcurrentmemberid() : int | null
  "Get logged-in member ID"
```

**Dependencies:**
- database.php (member queries)
- libmember.php (member functions)

---

### libmember.php - Member Utilities

```php
function authenticate($loginid, $password) : array | false
  "Authenticate member by login and password"
  
function getbyid($memberid) : array | false
  "Get member by ID"
  
function getbyloginid($loginid) : array | false
  "Get member by login ID"
  
function getflags($moniker) : array
  "Get member flags (permissions)"
```

**Dependencies:**
- database.php (queries)
- util.php (utilities)

---

### util.php - PHP Utilities

```php
function toboolean($value) : bool
  "Convert value to boolean"
  
function pluralize($amount, $singular, $plural) : string
  "Return singular or plural form"
  
function formatdate($timestamp, $format) : string
  "Format timestamp as date string"
  
function escaphtml($text) : string
  "Escape HTML special characters"
```

---

### Input Helper Classes

**InputDate.php:**
```php
class InputDate extends HTML_QuickForm2_Element_Input
  "HTML5 date input"
```

**InputDateTime.php:**
```php
class InputDateTime extends HTML_QuickForm2_Element_Input
  "HTML5 datetime-local input"
```

**InputEmail.php:**
```php
class InputEmail extends HTML_QuickForm2_Element_Input
  "HTML5 email input with validation"
```

**InputUrl.php:**
```php
class InputUrl extends HTML_QuickForm2_Element_Input
  "HTML5 URL input with validation"
```

---

## JavaScript Modules

All modules located in `js/`

Client-side interactivity and DOM manipulation.

### bbsengine6.js - Main Engine

Core JavaScript functionality and initialization.

---

### Topbar Components

**topbar.js** - Top navigation bar container

**topbar-*.js** - Individual components:
- topbar-alert.js: Alert notifications
- topbar-credits.js: Credit display
- topbar-greetings.js: User greeting
- topbar-join.js: Join/Register button
- topbar-loginlogout.js: Auth UI
- topbar-nav.js: Navigation menu
- topbar-notify.js: Notifications

---

### Other JavaScript Modules

**clock.js** - Real-time clock widget

**checkcurrentmemberid.js** - Validate current user

**redirectpage.js** - Page redirection

**initsmoothstate.js** - Smooth AJAX page transitions

**inittinymce.js** - TinyMCE editor initialization

**jquery.smoothState.js** - jQuery plugin for smooth state transitions

---

## Function Signature Summary

### Common Parameter Patterns

All functions follow these parameter patterns:

```python
def func(args: object, ..., **kwargs)
  """
  args: Command-line arguments (argparse.Namespace)
  **kwargs: Optional parameters including:
    - pool: ConnectionPool object
    - conn: Database connection
    - mogrify: bool (show executed SQL)
    - level: logging level (for console tools)
  """
```

### Return Type Conventions

```
None         - Operation completed successfully
bool         - Success/failure (True/False)
int          - ID or count
str          - Text/identifier
dict         - Single record/object
list[dict]   - Multiple records
Any          - Variable return type
```

---

*Module Specifications for bbsengine6*
