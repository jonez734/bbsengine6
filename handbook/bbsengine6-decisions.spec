# BBSEngine v6.0 Architectural Decisions Specification

**Version:** 6.0  
**Last Updated:** 2026-02-23

This document explains the major architectural decisions made in BBSEngine v6.0, the rationale behind them, and alternatives that were considered.

## Table of Contents

1. [Decision: Layered Architecture](#decision-1-layered-architecture)
2. [Decision: Module/Plugin System](#decision-2-moduleplugin-system)
3. [Decision: Terminal-First Design](#decision-3-terminal-first-design)
4. [Decision: Multi-Language Stack](#decision-4-multi-language-stack)
5. [Decision: PostgreSQL](#decision-5-postgresql)
6. [Decision: Separation of Web Layer](#decision-6-separation-of-web-layer)
7. [Decision: No Circular Dependencies](#decision-7-no-circular-dependencies)
8. [Decision: Rich Terminal UI](#decision-8-rich-terminal-ui)

---

## Decision 1: Layered Architecture

### The Decision

BBSEngine v6.0 uses a **4-layer architecture**:
1. **Data Layer** - PostgreSQL database
2. **Business Logic Layer** - Session, member, module, message management
3. **Presentation Layer** - Terminal UI widgets and web interface
4. **Module System** - Meta-layer for plugins

### Rationale

**Why layering?**
- **Separation of Concerns**: Each layer has a single responsibility
- **Testability**: Can test database layer without UI layer
- **Maintainability**: Changes in one layer don't affect others
- **Reusability**: Business logic can be used by multiple UIs
- **Flexibility**: Easy to swap implementations

**Example: If testing member authentication:**
```python
# With layering, can test without terminal:
def test_authenticate():
  result = member.authenticate(args, loginid="test", password="secret")
  assert result is not None
  # No UI involved, no terminal I/O needed
  
# Without layering, would need to:
# - Set up terminal environment
# - Mock all UI components
# - Much harder to test
```

### Alternatives Considered

#### Alternative 1: Monolithic Design

**What it looks like:**
```python
# Single huge module
def login():
  display_prompt()
  get_input()
  query_database()
  update_session()
  display_result()
```

**Why rejected:**
- Hard to test (everything interdependent)
- Hard to maintain (changes break multiple things)
- Hard to reuse (can't use database layer without UI)
- Can't add web interface easily

#### Alternative 2: Microservices

**What it looks like:**
```
Service 1: Authentication microservice
Service 2: Message service
Service 3: Session service
...each in separate process/container
```

**Why rejected:**
- Overkill for single application
- Network overhead between services
- Complex deployment
- Requires service discovery, load balancing
- Too heavy for a BBS system

### Decision Outcome

**Layered architecture chosen because:**
- Provides clear structure
- Good balance of separation vs. simplicity
- Easy to test each layer
- Easy to document and understand
- Extensible for multiple UIs

---

## Decision 2: Module/Plugin System

### The Decision

BBSEngine v6.0 implements a **runtime-loadable plugin system** via `module.py`:
- Modules are Python packages with standard interface
- Required functions: `init()`, `access()`, `buildargs()`, `main()`
- Loaded dynamically at runtime
- Access control checked before execution

### Rationale

**Why a plugin system?**
- **Extensibility**: Add features without modifying core
- **Maintainability**: Isolate features in separate modules
- **Distribution**: Users can install custom modules
- **Flexibility**: Enable/disable features per deployment

**Example: Adding a games feature**
```python
# Create modules/games/__init__.py with:
def init(args, **kwargs): pass
def access(args, **kwargs): return True  # Check user permission
def buildargs(args, **kwargs): return args
def main(args, **kwargs):
  # Game logic here
  return game_result

# No changes to core modules needed!
# Just add to menu: Item(label="Games", module="games")
```

### Alternatives Considered

#### Alternative 1: Monolithic Features

**What it looks like:**
```python
# Everything in core modules
class BBS:
  def login(self): ...
  def post_message(self): ...
  def play_game(self): ...
  def edit_profile(self): ...
  # Thousands of lines
```

**Why rejected:**
- Core becomes huge and complex
- Mixing concerns (authentication, games, messaging, etc.)
- Hard to test individual features
- Hard to document
- Can't remove features easily

#### Alternative 2: Separate Python Packages

**What it looks like:**
```
pip install bbsengine-games
pip install bbsengine-forum
# Import separately
import games, forum
# Manually integrate
```

**Why rejected:**
- Doesn't provide single unified interface
- Harder for users to add modules
- Module discovery is complex
- No built-in access control

### Decision Outcome

**Plugin system chosen because:**
- Perfect balance of flexibility and structure
- Clear API for module writers
- Built-in security (access checking)
- Easy for users to add features
- Isolates features for testing/maintenance

---

## Decision 3: Terminal-First Design

### The Decision

BBSEngine v6.0 is **designed primarily for terminal access**:
- Rich terminal UI (colors, widgets, keyboard navigation)
- Web interface is secondary
- Python backend is terminal-optimized

### Rationale

**Why terminal-first?**
- **Historical**: BBSes are inherently terminal systems
- **User Experience**: Classic BBS aesthetic
- **Performance**: Terminal is lightweight
- **Accessibility**: Works with standard terminal emulators
- **Simplicity**: Don't need web framework complexity

**Benefits:**
```
Terminal Advantages:
  ✓ Works over SSH (remote access)
  ✓ Fast and responsive
  ✓ Rich UI without HTML/CSS/JS
  ✓ Simple deployment
  ✓ Works on slow connections
  ✓ Nostalgic for BBS users

Web as Bonus:
  ✓ Same data backend
  ✓ Optional secondary interface
  ✓ Doesn't complicate core
```

### Alternatives Considered

#### Alternative 1: Web-First Design

**What it looks like:**
```
Flask/Django application
  ├─ User authentication
  ├─ HTML rendering
  ├─ JavaScript for interactivity
  └─ Database queries
```

**Why rejected:**
- Web framework introduces complexity
- BBS users expect terminal experience
- Web adds dependencies (ORM, template engine, etc.)
- Defeats the purpose of classic BBS
- Harder to deploy on simple servers

#### Alternative 2: Desktop App (Qt/GTK)

**What it looks like:**
```
PyQt/GTK Desktop Application
  ├─ Native GUI widgets
  ├─ Complex build process
  └─ Requires X11 or Wayland
```

**Why rejected:**
- Loss of text-based aesthetic
- Complex build and distribution
- Reduces accessibility
- Requires desktop environment
- Not suitable for remote servers

### Decision Outcome

**Terminal-first chosen because:**
- Aligns with BBS tradition
- Simpler architecture
- Better user experience for target audience
- Web layer can be added later
- Easy to use over SSH/Telnet

---

## Decision 4: Multi-Language Stack

### The Decision

BBSEngine v6.0 uses **3 languages**:
- **Python** - Core application logic
- **PHP** - Web interface (secondary)
- **JavaScript** - Client-side interactivity (web only)

### Rationale

**Why multiple languages?**
- **Python**: Best for system administration, complex logic, rapid development
- **PHP**: Mature web stack, existing hosting support
- **JavaScript**: Client-side interactivity, browser standard

**Why NOT consolidate?**

```
Option 1: Everything in Python
  - Would need web framework (Flask/Django/FastAPI)
  - Hosting more complex
  - Doesn't make web "simpler"
  ✗ Rejected

Option 2: Everything in PHP
  - Not suitable for complex business logic
  - Poor terminal interface support
  - Reinventing wheels (authentication, module system)
  ✗ Rejected

Option 3: Everything in JavaScript (Node.js)
  - BBS tradition is Python/C
  - Terminal libraries weaker in JS
  - Overkill for what PHP needs
  ✗ Rejected
```

### Alternatives Considered

#### Alternative 1: Single Language (Python)

```python
# Python terminal app
class TerminalBBS:
  def display_menu(self): ...
  def handle_input(self): ...
  
# Flask web app
@app.route('/login', methods=['POST'])
def login():
  # Same code?
```

**Why rejected:**
- Terminal and web have different paradigms
- Forces awkward abstractions
- Trying to serve two masters poorly
- Web becomes complex in Python web framework
- Terminal remains clean, but why add web complexity?

#### Alternative 2: Microservices (Python + Node)

```
Python service: Core logic
Node.js service: Web frontend
  Communicate via REST/gRPC
```

**Why rejected:**
- Massive overkill
- Requires service orchestration
- Complex deployment
- Unnecessary for single-user BBS
- Violates principle of simplicity

### Decision Outcome

**Multi-language stack chosen because:**
- Each language does what it does best
- Python for system complexity
- PHP for web simplicity
- JavaScript for browser interactivity
- Low friction between layers
- Minimal interdependencies

---

## Decision 5: PostgreSQL

### The Decision

BBSEngine v6.0 uses **PostgreSQL 12+** as the primary database:
- Advanced SQL features (JSON, ltree, UUID)
- Roles and permissions system
- Connection pooling support
- ACID compliance
- Free and open source

### Rationale

**Why PostgreSQL?**
- **Reliability**: 30+ years, production-proven
- **Features**: ltree, JSONB, UUID-ossp extensions
- **Security**: Role-based access control
- **Standards**: Follows SQL standard closely
- **Deployment**: Runs on Linux/Unix (BBS preference)

**PostgreSQL-Specific Features Used:**
```sql
-- JSONB for flexible attributes
CREATE TABLE engine.member (
  attrs JSONB,  -- Custom user attributes
  flags JSONB   -- Permission flags
);

-- ltree for hierarchical messages
CREATE TABLE engine.__blurb (
  path ltree    -- Message thread path
);

-- UUID-ossp for session IDs
CREATE TABLE engine.__session (
  id UUID DEFAULT uuid_generate_v4()
);

-- Roles for application permissions
CREATE ROLE bbsengine_webserver;
GRANT SELECT, INSERT ON engine.__session TO bbsengine_webserver;
```

### Alternatives Considered

#### Alternative 1: MySQL/MariaDB

**Pros:**
- Widely hosted
- Good performance
- Simple to deploy

**Cons:**
- Fewer advanced features
- JSONB not as mature
- No ltree
- Weaker ACID guarantees
- ✗ Rejected because: BBS deserves better reliability

#### Alternative 2: SQLite

**Pros:**
- Single file database
- No server needed
- Easy deployment

**Cons:**
- Limited to single user
- No concurrent writes
- Can't run as web service
- No role-based security
- ✗ Rejected because: Web+terminal access requires concurrent writes

#### Alternative 3: NoSQL (MongoDB, etc.)

**Pros:**
- Flexible schema
- Horizontal scaling

**Cons:**
- Overkill for structured data
- Weaker consistency guarantees
- No referential integrity
- Complex querying
- ✗ Rejected because: BBS data is relational

### Decision Outcome

**PostgreSQL chosen because:**
- Features match BBS needs perfectly
- Reliability critical for data
- Advanced features reduce code complexity
- Free and open source
- UNIX philosophy alignment
- Community support strong

---

## Decision 6: Separation of Web Layer

### The Decision

The **web layer is separate from core logic**:
- PHP reads/writes same database as Python
- No forced integration
- Web is optional feature
- Can evolve independently

### Rationale

**Why separate?**
- **Independence**: Web doesn't constrain terminal design
- **Simplicity**: Each layer optimized for its purpose
- **Optionality**: Hosting can run terminal OR web OR both
- **Testing**: Can test each independently

**What separation looks like:**
```
Terminal Interface (Python)
  └─ Queries PostgreSQL
  
Web Interface (PHP)
  └─ Queries same PostgreSQL
  
(Both read/write same tables)
(No forced inter-layer calls)
```

### Alternatives Considered

#### Alternative 1: Web as Thin Client

**What it looks like:**
```
Browser → PHP → Python Backend (REST API)
            ↓
         PostgreSQL
```

**Pros:**
- All logic in Python
- Single source of truth
- Easy to test

**Cons:**
- PHP becomes just marshaling layer
- Adds HTTP overhead
- Complex REST API to maintain
- Requires running Python service

**Status**: Could be future enhancement

#### Alternative 2: Unified ORM

**What it looks like:**
```python
# Same code runs in Python and PHP
class Member(ORM):
  id = Column(Integer)
  loginid = Column(String)
  
# Python uses it
member = Member.query.get(123)

# PHP somehow uses same ORM?
# (Impossible - different languages)
```

**Why rejected:**
- Languages are incompatible
- Would require middleware
- Adds unnecessary layer

### Decision Outcome

**Separation chosen because:**
- Respects language differences
- Allows independent evolution
- Keeps both simple
- Better overall maintainability
- Future API integration possible

---

## Decision 7: No Circular Dependencies

### The Decision

BBSEngine v6.0 is designed to have **zero circular dependencies**:
- Data layer imports nothing upward
- Util layer has no imports of dependent modules
- Module system is cleanly meta-layer
- Prevents initialization problems

### Rationale

**Why avoid circular dependencies?**
- **Initialization**: Can't boot system if cycles exist
- **Testing**: Can't mock one side without the other
- **Clarity**: Dependency graph is a DAG (not a cycle)
- **Maintainability**: Clear what depends on what
- **Refactoring**: Easy to understand impact

**Example problem with cycles:**
```python
# BAD - circular import
# module_a.py:
from module_b import func_b

# module_b.py:
from module_a import func_a

# This breaks Python import system!
```

### Alternatives Considered

#### Alternative 1: Allow Cycles

```python
# database.py imports session.py
# session.py imports database.py
# (Both exist, but careful about order)
```

**Problems:**
- Initialization order issues
- Hard to trace dependencies
- Fragile when refactoring
- Harder to test
- ✗ Rejected

#### Alternative 2: Everything Imports Everything

```python
# Modules import as needed
# Cycles are "managed" via Python's import caching
```

**Problems:**
- Illusion of no cycle (Python caches, but still bad design)
- Makes refactoring terrifying
- Hard to understand module relationships
- Testing becomes nightmare
- ✗ Rejected

### Decision Outcome

**No circular dependencies chosen because:**
- System reliability
- Better design clarity
- Easier testing
- Simpler documentation
- Prevents entire classes of bugs

---

## Decision 8: Rich Terminal UI

### The Decision

BBSEngine v6.0 implements **rich terminal UI** with:
- ANSI color support (16, 256, 24-bit RGB)
- Interactive widgets (menu, listbox, form, editor)
- Keyboard navigation
- Word wrapping
- Mouse support (optional)

### Rationale

**Why rich UI?**
- **User Experience**: More pleasant interaction
- **Usability**: Widgets are faster than text prompts
- **Aesthetic**: Visual appeal for users
- **Accessibility**: Color can indicate state (error, success)
- **Productivity**: Listbox navigation faster than text-based

**Benefits:**
```
Plain text interface:
  "Enter member ID: _"
  (User has to remember/type ID)

Rich interface (listbox):
  "Select member:
   > alice
     bob
     carol"
  (Visual, navigate with arrows)
```

### Alternatives Considered

#### Alternative 1: Plain Text Only

```
Enter login ID: _
Enter password: _
Welcome back!
Main Menu:
1. Read Messages
2. Post Message
3. Edit Profile
```

**Why rejected:**
- Feels 1980s
- Harder to use
- Slower navigation
- Less engaging
- Not utilizing modern terminals

#### Alternative 2: Full GUI (Qt/GTK)

```python
# Full graphical interface
window = QMainWindow()
button = QPushButton("Click me")
window.show()
```

**Why rejected:**
- Defeats BBS aesthetic
- Requires X11/desktop
- Complex build/deployment
- Overkill for terminal system
- Can't use over SSH

### Decision Outcome

**Rich terminal UI chosen because:**
- Best of both worlds
- Retro BBS feel with modern usability
- Works in any terminal
- Fast and responsive
- Visually engaging
- No complex dependencies

---

## Summary of Architectural Decisions

| Decision | Choice | Rationale | Key Benefit |
|----------|--------|-----------|-------------|
| Architecture | Layered (4 layers) | Separation of concerns | Testable, maintainable |
| Extensibility | Module/plugin system | Add features without core changes | Flexibility |
| Primary Interface | Terminal | Historical, simple, accessible | User satisfaction |
| Languages | Python + PHP + JS | Each language's strengths | Pragmatic, simple |
| Database | PostgreSQL | Advanced features, reliability | Power + stability |
| Web Layer | Separate/optional | Independence from core | Evolutionary development |
| Dependencies | No cycles | Clean design | System reliability |
| Terminal UI | Rich (colors, widgets) | User experience | Engagement + usability |

---

## Trade-offs Made

### Trade-off 1: Flexibility vs. Simplicity

```
Chosen: Layered architecture (more flexible)
Cost: Slightly more code, more files
Benefit: Easy to test, modify, extend
Alternative: Monolithic (simpler initially, harder later)
```

### Trade-off 2: Feature Richness vs. Complexity

```
Chosen: Rich terminal UI (more complex)
Cost: More I/O module code
Benefit: Better user experience
Alternative: Plain text (less code, less engaging)
```

### Trade-off 3: PostgreSQL Constraints vs. Flexibility

```
Chosen: PostgreSQL ACID compliance
Cost: Stricter schema, stronger constraints
Benefit: Data consistency, reliability
Alternative: NoSQL (more flexible, less reliable)
```

### Trade-off 4: Web Separation vs. Code Reuse

```
Chosen: Separate web layer
Cost: Some duplication between Python and PHP
Benefit: Each optimized for platform
Alternative: Shared ORM (requires complex middleware)
```

---

## Future Evolution

### Possible Future Decisions

**1. REST API Layer**
- If web layer grows significantly
- Could add Python REST API
- PHP calls Python backend
- Moves logic consolidation

**2. Client-Server Refactor**
- Separate terminal client from server
- Client connects to Python server
- Enables multiplayer BBS features

**3. Containerization**
- Move to Docker/Kubernetes
- Requires rethinking service boundaries
- Maybe split terminal and web services

**4. Expanded Module System**
- Remote module marketplace
- Module versioning
- Dependency management

**5. Multi-Database Support**
- Abstract database layer further
- Support MySQL, SQLite alternatives
- Requires careful schema design

---

*Architectural Decisions for BBSEngine v6.0*
