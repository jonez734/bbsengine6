# BBSEngine6 Master Specification

**Version:** 6.0  
**Last Updated:** 2026-02-23  
**Target Audience:** Developers & Architects

## Overview

BBSEngine6 is a comprehensive Bulletin Board System (BBS) engine written in Python, PHP, and JavaScript with a PostgreSQL database backend. It provides both terminal-based and web-based interfaces for running bulletin board systems with features including user authentication, messaging, forums, and a modular plugin system for extensibility.

### Quick Facts

- **Primary Language:** Python 3.10+
- **Secondary Languages:** PHP 8.1, JavaScript
- **Database:** PostgreSQL (with advanced features: roles, schemas, JSON types)
- **Core Entry Points:** Terminal I/O + Web HTTP endpoints
- **Architecture Pattern:** Layered + Plugin-based modules
- **Module System:** Runtime-loaded plugins with standardized API

---

## Table of Contents

### 1. [Architecture Overview](bbsengine6-architecture.spec)
   - Layered architecture (data, business logic, presentation, modules)
   - Domain-based organization (sessions, members, messaging, module system, I/O)
   - Layer responsibilities and data flow between layers
   - Visual architecture diagrams

### 2. [Module Specifications](bbsengine6-modules.spec)
   - Core Python modules (database, session, member, util, menu, listbox, module system)
   - [util.spec](specs/util.spec) -- General-purpose utilities (display, dates, logging, file ops, passwords)
   - Subpackages (io, console)
   - PHP layer modules
   - JavaScript modules
   - Complete function signatures with brief descriptions
   - Class and method specifications

### 3. [Data Flows & Workflows](bbsengine6-flows.spec)
   - High-level workflows:
     - User login flow
     - Message posting flow
     - Navigation/menu flow
     - Module execution flow
   - Detailed sequence flows showing function calls and state changes
   - State transformations at each layer

### 4. [Web Layer Specification](bbsengine6-web.spec)
   - PHP architecture and bootstrap process
   - HTTP endpoints and their purposes
   - Smarty template integration
   - JavaScript execution and DOM manipulation
   - Connection between web layer and Python backend
   - Request/response lifecycle

### 5. [Module Dependencies](bbsengine6-dependencies.spec)
   - Complete dependency matrix (which modules depend on which)
   - Dependency rationale (why each dependency exists)
   - Layer-to-layer dependencies
   - Inter-module dependencies
   - External package dependencies

### 6. [Architectural Decisions](bbsengine6-decisions.spec)
   - Design decisions and their rationale
   - Architectural alternatives explored
   - Trade-offs documented
   - Why certain patterns were chosen

---

## System Architecture at a Glance

```
┌─────────────────────────────────────────────────┐
│         Web Interface (HTTP)                    │
│  PHP Endpoints → Smarty Templates → JavaScript │
└────────────────────┬────────────────────────────┘
                     │
                     ├── Uses: Theming (SCSS)
                     ├── Uses: JavaScript Libraries
                     └── Uses: PHP Library
                             (engine.php, database.php, session.php)
                                    │
┌───────────────────────────────────┴──────────────────────────┐
│     Python Backend (Core Business Logic)                      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Sessions   │  │   Members    │  │   Messages   │      │
│  │  Persistence │  │  Management  │  │   Storage    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                 │
│                    ┌───────▼────────┐                        │
│                    │  Database API  │                        │
│                    │ (database.py)  │                        │
│                    └───────┬────────┘                        │
│                            │                                 │
│  ┌────────────────────────▼──────────────────────────┐      │
│  │        Module System (module.py)                  │      │
│  │  Runtime plugin loading & execution framework     │      │
│  └─────────────────────────────────────────────────┘      │
│                                                               │
│  ┌────────────────────────────────────────────────┐        │
│  │      Terminal I/O Library (io subpackage)      │        │
│  │  Color, keyboard input, screen control, forms  │        │
│  └─────────────────────────────────────────────────┘       │
│                                                               │
└──────────────────────────┬───────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ PostgreSQL  │
                    │  Database   │
                    │  with roles │
                    └─────────────┘
```

---

## Key Concepts

### Layer Model

1. **Data Layer** - PostgreSQL database with connection pooling (database.py)
2. **Business Logic Layer** - Session, member, module management, utilities
3. **Presentation Layer** - Terminal I/O widgets (menu, listbox, forms) + web HTML/JS
4. **Module System** - Runtime-loadable plugin architecture overlaying all layers

### Domain Model

- **Session Domain** - User session lifecycle and state persistence
- **Member Domain** - User profile, credentials, flags, permissions
- **Message Domain** - Message/blurb creation, storage, display
- **Module Domain** - Plugin system for extensibility
- **Terminal I/O Domain** - Rich terminal interactions (colors, keyboard, widgets)
- **Web Domain** - HTTP request handling, templating, browser interactions

### Critical Paths

1. **User Login** → Session creation → Member authentication → Permission checks
2. **Module Execution** → Module loading → Access validation → Function invocation
3. **Message Posting** → Form input → Validation → Storage → Display
4. **Navigation** → Menu rendering → User input → Menu action → Next state

---

## Module Organization

### Python Core Modules

| Module | Purpose | Dependencies |
|--------|---------|---|
| database.py | PostgreSQL interface & connection pooling | psycopg, psycopg_pool |
| session.py | Session lifecycle management | database.py, member.py |
| member.py | User management & authentication | database.py, util.py |
| module.py | Plugin system & module loading | database.py, io.* |
| util.py | General-purpose utilities | io.echo, logging |
| menu.py | Interactive menu widget | util.py, io.* |
| listbox.py | Paginated list widget | database.py, io.* |
| form.py | Form handling & validation | util.py, io.* |
| blurb.py | Message/post storage & retrieval | database.py, util.py |
| editor.py | Line-based text editor | io.getch, io.echo |
| input.py | User input parsing | io.* |
| folder.py | Directory/folder management | database.py |

### I/O Subpackage (Terminal Interface)

| Module | Purpose |
|--------|---------|
| echo.py | Output with colors, variables, commands |
| screen.py | Cursor positioning, clearing |
| getch.py | Single character input, key codes |
| inputstring.py | String input with editing |
| inputinteger.py | Integer input validation |
| inputboolean.py | Yes/No prompts |
| inputchoice.py | Multiple choice selection |
| terminal.py | Terminal capabilities detection |
| palette.py | Color palette management |
| keymap.py | Keyboard mapping |

### Console Package (Admin Tools)

Database schema checks, member management, configuration validation

---

## Web Stack

- **PHP** - Server-side request handling
- **Smarty** - Template engine
- **JavaScript** - Client-side interactivity
- **SCSS** - Stylesheet preprocessing
- **jQuery** - DOM manipulation & AJAX

---

## How to Use This Specification

1. **New to BBSEngine6?** Start with [Architecture Overview](bbsengine6-architecture.spec)
2. **Need to understand a module?** Go to [Module Specifications](bbsengine6-modules.spec)
3. **Tracing a workflow?** Check [Data Flows](bbsengine6-flows.spec)
4. **Working with web layer?** See [Web Layer Spec](bbsengine6-web.spec)
5. **Understanding dependencies?** Review [Module Dependencies](bbsengine6-dependencies.spec)
6. **Need design rationale?** Read [Architectural Decisions](bbsengine6-decisions.spec)

---

## File Structure Reference

```
bbsengine6/
├── py/                          # Python backend
│   └── src/bbsengine6/
│       ├── database.py          # PostgreSQL interface
│       ├── session.py           # Session management
│       ├── member.py            # User management
│       ├── module.py            # Module/plugin system
│       ├── menu.py              # Menu widget
│       ├── listbox.py           # List widget
│       ├── util.py              # Utilities ([spec](specs/util.spec))
│       ├── io/                  # Terminal I/O subpackage
│       └── console/             # Admin tools
├── php/                         # PHP backend
│   ├── engine.php               # Main engine
│   ├── database.php             # Database layer
│   ├── session.php              # Session handling
│   └── ... (input types, utilities)
├── js/                          # JavaScript
├── www/                         # Web endpoints & pages
├── skin/                        # CSS/SCSS styling
├── smarty/                      # Template plugins
└── handbook/                    # Documentation
    ├── bbsengine6.spec          # Master spec index
    ├── bbsengine6-architecture.spec
    ├── bbsengine6-modules.spec
    ├── bbsengine6-flows.spec
    ├── bbsengine6-web.spec
    ├── bbsengine6-dependencies.spec
    └── bbsengine6-decisions.spec
```

---

## Technology Stack

### Backend
- Python 3.10+ (core application logic)
- PHP 8.1 (web layer)
- PostgreSQL 12+ (database with roles, schemas, JSONB)
- psycopg3 (Python-PostgreSQL driver)
- Smarty (PHP template engine)

### Frontend
- JavaScript/jQuery
- SCSS
- HTML5

### Infrastructure
- Apache 2 (web server)
- Git (version control)
- Make (build automation)

---

## Next Steps

To dive deeper into the system:

1. Read **[bbsengine6-architecture.spec](bbsengine6-architecture.spec)** for a complete architectural overview
2. Explore **[bbsengine6-modules.spec](bbsengine6-modules.spec)** for detailed module APIs, including **[util.spec](specs/util.spec)**
3. Study **[bbsengine6-flows.spec](bbsengine6-flows.spec)** to understand critical workflows
4. Review **[bbsengine6-web.spec](bbsengine6-web.spec)** for web layer integration
5. Check **[bbsengine6-dependencies.spec](bbsengine6-dependencies.spec)** to understand module coupling
6. Reference **[bbsengine6-decisions.spec](bbsengine6-decisions.spec)** for design rationale

---

*Master Specification for BBSEngine6 v6.0*  
*For questions or updates, refer to the main handbook documentation*
