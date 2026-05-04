# Module Registration System Specification

## Overview

A registration system in bbsengine6 that allows modules (vulcan, teos, future modules) to discover each other at runtime and interoperate. Interoperation is **optional** - modules work independently if others aren't installed.

## Architecture

### Components

| Component | File | Status |
|-----------|------|--------|
| `ModuleRegistry` class | `bbsengine6/py/src/bbsengine6/module.py:118-157` | ✅ Done |
| Registration check in `module.check()` | `bbsengine6/py/src/bbsengine6/module.py:375-380` | ✅ Done |
| `--require-registration` flag | `bbsengine6/py/src/bbsengine6/console/lib.py:121-126` | ✅ Done |
| CLI handler for flag | `bbsengine6/py/src/bbsengine6/console/main.py:131-135` | ✅ Done |
| teos `init()` with registration | `teos/tools/teos/main.py:8-20` | ✅ Done |
| vulcan `init()` with registration | `vulcan/tools/vulcan/main.py:8-34` | ✅ Done |
| teos integration example | `vulcan/tools/vulcan/teos_integration.py` | ✅ Done |
| ModuleRegistry export | `bbsengine6/py/src/bbsengine6/__init__.py:13` | ✅ Done |

### Implementation: Functional with Global Variables (Thread-Safe)

Located in `bbsengine6/module.py` - uses global variables and RLock for thread safety:

```python
import threading

@dataclass
class ModuleAPI:
    """API version and callable functions registered by a module."""
    version: str
    apis: dict[str, Callable]
    module_path: str


# Global variables with thread-safe access
_module_registry: dict[str, ModuleAPI] = {}
_require_registration: bool = False
_registry_lock = threading.RLock()


def register_module(name: str, module_path: str, version: str, apis: dict) -> None:
    """Register a module with its API. Thread-safe."""
    global _module_registry
    with _registry_lock:
        _module_registry[name] = ModuleAPI(
            version=version, apis=apis, module_path=module_path
        )


def is_module_registered(name: str) -> bool:
    """Check if module is registered. Thread-safe."""
    with _registry_lock:
        return name in _module_registry


def get_module(name: str) -> ModuleAPI | None:
    """Get registered module API. Thread-safe."""
    with _registry_lock:
        return _module_registry.get(name)


def set_require_registration(required: bool) -> None:
    """Set flag to require module registration."""
    global _require_registration
    _require_registration = required


def get_require_registration() -> bool:
    """Get current require_registration flag."""
    global _require_registration
    return _require_registration


# Backwards-compatible class (delegates to functions)
class ModuleRegistry:
    """Central registry for BBS modules - tied to module system."""
    # ...delegates to global functions
```

## Module Registration Protocol

### 1. Required: init(args) Function

Each module must implement an `init(args)` function that is called by `module.run()`:

```python
def init(args, **kwargs):
    """Register module with bbsengine6 registry."""
    ModuleRegistry.register(
        name="modulename",
        module_path="modulename",
        version="1.0.0",
        apis={
            "function_name": module.function,
            ...
        },
    )
    return True
```

### 2. Module Structure

```
bbsengine6/
  module.py          # Contains ModuleRegistry
    
teos/
  tools/teos/
    main.py         # Has init() that registers teos
    
vulcan/
  tools/vulcan/
    main.py         # Has init() that registers vulcan
```

## Registration in module.check()

When `get_require_registration()` returns True (set via CLI flag), `module.check()` verifies the module is registered:

```python
if get_require_registration() is True:
    if not is_module_registered(modulename):
        io.echo(f"module {modulename} is not registered (required by config)", level="error")
        return False
    io.echo(f"module.check: {modulename} is registered", level="debug")
```

## CLI Usage

```bash
# Enable registration enforcement
python -m bbsengine6.console --require-registration

# Run specific module with enforcement
python -m bbsengine6.console --require-registration vulcan
```

## Module Interoperation Example

### vulcan discovering teos

```python
from bbsengine6 import ModuleRegistry, io


def get_valid_sigs(args):
    """Get valid sigs from teos if available, else fallback."""
    
    teos_api = ModuleRegistry.get("teos")
    
    if teos_api is not None:
        io.echo("using teos for sig list", level="debug")
        exists = teos_api.apis.get("exists")
        
        if exists is not None and exists(args, "top.entertainment"):
            io.echo("sig exists in teos", level="debug")
        
        return {"source": "teos", "version": teos_api.version}
    
    # Fallback: query vulcan's stored sigs directly
    io.echo("teos not available, using vulcan fallback", level="debug")
    return {"source": "vulcan_fallback"}


def validate_link_sigs(args, sigs: list[str]) -> tuple[bool, list[str]]:
    """Validate that link sigs exist in teos (if available)."""
    
    teos_api = ModuleRegistry.get("teos")
    errors = []
    
    if teos_api is not None:
        exists = teos_api.apis.get("exists")
        if exists is not None:
            for sig_path in sigs:
                if not exists(args, sig_path):
                    errors.append(f"sig {sig_path!r} not found in teos")
    
    return (len(errors) == 0, errors)
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     bbsengine6                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 ModuleRegistry                     │   │
│  │  _registered: dict[str, ModuleAPI]                 │   │
│  │  _require_registration: bool                        │   │
│  │                                                    │   │
│  │  register(name, module_path, version, apis)       │   │
│  │  get(name) → ModuleAPI                              │   │
│  │  is_registered(name) → bool                         │   │
│  │  set_require_registration(bool)                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                         ↑                                   │
│         module.check() ← enforces _require_registration     │
└─────────────────────────────────────────────────────────────┘
          ↓                       ↓
    ┌──────────┐            ┌──────────┐
    │   teos   │            │  vulcan  │
    │ init()   │            │ init()   │
    │ registers│            │ registers│
    │ "teos"   │            │ "vulcan" │
    └──────────┘            └──────────┘
                                   ↓
                            discovers teos via
                            ModuleRegistry.get("teos")
```

## Remaining Work

### 1. ✅ Fix lib Function References - DONE

Updated vulcan registration to use actual lib functions:
- `lib.insert`, `lib.update`, `lib.exists`, `lib.setsigs`, `lib.getlinkflags`, `lib.setflag`

### 2. ✅ Fix teos getcurrentpath Registration - DONE

Used wrapper function approach:
```python
def getcurrentpath_wrapper(registry_args, **kw):
    pool = getattr(registry_args, "pool", None)
    return lib.getcurrentpath(registry_args, pool=pool)
```

### 3. ✅ Add Optional Dependency - DONE

Added to `vulcan/tools/setup.py`:
```python
extras_require={
    "teos": ["teos"],  # Optional: enables teos integration
},
```

### 4. Integrate into add.py/lib.py

Import and use `get_valid_sigs()` and `validate_link_sigs()` in vulcan's add.py when selecting sigs for a new link.

### 5. Testing

```bash
# Test registration from bbsengine6 package
python -c "from bbsengine6 import get_module, is_module_registered; print(is_module_registered('vulcan'))"

# Test with enforcement flag
python -m bbsengine6.console --require-registration vulcan
```

### 6. Export functional API in __init__.py

The following are exported from `bbsengine6/__init__.py`:
- `register_module`, `unregister_module`, `is_module_registered`
- `get_module`, `get_module_api`
- `set_require_registration`, `get_require_registration`
- `ModuleRegistry` (class, for backwards compatibility)

---

## Future Enhancements: Inspired by GNOME Introspection (gi)

GNOME Introspection provides powerful patterns for dynamic module loading and observable data. While gi is designed for GObject/C libraries, some concepts can inspire future bbsengine6 enhancements.

### 1. Observable List Pattern (Gio.ListStore-style)

Inspired by `Gio.ListModel` / `Gio.ListStore` - provides observable collections with change signals.

**Use case**: teos sig tree, vulcan link list

```python
from typing import TypeVar, Generic, Callable
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class ListChange:
    position: int
    removed: int
    added: int


class ObservableList(Generic[T]):
    """Observable list with change notifications - inspired by Gio.ListStore."""
    
    def __init__(self, item_type: type):
        self._items: list[T] = []
        self._item_type = item_type
        self._listeners: list[Callable[[ListChange], None]] = []
    
    def append(self, item: T) -> None:
        self._items.append(item)
        self._notify(ListChange(len(self._items) - 1, 0, 1))
    
    def insert(self, position: int, item: T) -> None:
        self._items.insert(position, item)
        self._notify(ListChange(position, 0, 1))
    
    def remove(self, position: int) -> T:
        item = self._items.pop(position)
        self._notify(ListChange(position, 1, 0))
        return item
    
    def items_changed(self, position: int, removed: int, added: int) -> None:
        """Emit items-changed signal - like Gio.ListModel."""
        self._notify(ListChange(position, removed, added))
    
    def add_listener(self, callback: Callable[[ListChange], None]) -> None:
        self._listeners.append(callback)
    
    def _notify(self, change: ListChange) -> None:
        for listener in self._listeners:
            listener(change)
    
    def get_item(self, position: int) -> T:
        return self._items[position]
    
    def get_n_items(self) -> int:
        return len(self._items)


# Example: Sig list in teos
class SigList(ObservableList[dict]):
    def __init__(self):
        super().__init__(dict)
    
    def find_by_path(self, path: str) -> dict | None:
        for item in self._items:
            if item.get("path") == path:
                return item
        return None
```

**Benefits**:
- UI components can subscribe to data changes
- Decouples data layer from presentation
- Enables reactive UI updates

### 2. Dynamic Module Discovery (gi-style imports)

Inspired by `gi.repository` generating Python modules from typelibs:

```python
def discover_modules(base_package: str) -> dict[str, ModuleType]:
    """Discover all modules in a package dynamically - like gi.repository."""
    discovered = {}
    
    import importlib.util
    import os
    
    # Find all .py modules in package directory
    package_path = importlib.util.find_spec(base_package).submodule_search_paths[0]
    
    for filename in os.listdir(package_path):
        if filename.endswith('.py') and not filename.startswith('_'):
            module_name = filename[:-3]
            full_name = f"{base_package}.{module_name}"
            try:
                discovered[module_name] = importlib.import_module(full_name)
            except ImportError:
                pass
    
    return discovered
```

### 3. Menu Model (GMenuModel-style)

Inspired by `GMenuModel` - declarative, serializable menu definitions:

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MenuItem:
    """A menu item - inspired by GMenuModel."""
    label: str
    action: Optional[str] = None
    icon: Optional[str] = None
    submenu: list["MenuItem"] = field(default_factory=list)
    

@dataclass
class MenuModel:
    """A menu model - inspired by GMenuModel."""
    items: list[MenuItem] = field(default_factory=list)
    
    def append_item(self, item: MenuItem) -> None:
        self.items.append(item)
    
    def to_xml(self) -> str:
        """Serialize to XML for storage/transmission."""
        def render(items: list[MenuItem], indent: int = 0) -> str:
            result = []
            for item in items:
                attrs = []
                if item.label:
                    attrs.append(f'label="{item.label}"')
                if item.action:
                    attrs.append(f'action="{item.action}"')
                if item.icon:
                    attrs.append(f'icon="{item.icon}"')
                    
                if item.submenu:
                    result.append(f'{"  " * indent}<menu {" ".join(attrs)}>')
                    result.append(render(item.submenu, indent + 1))
                    result.append(f'{"  " * indent}</menu>')
                else:
                    result.append(f'{"  " * indent}<item {" ".join(attrs)}/>')
            return "\n".join(result)
        
        return f'<menu xmlns="bbsengine">\n{render(self.items, 1)}\n</menu>'


# Example: Main menu
main_menu = MenuModel()
main_menu.append_item(MenuItem(
    label="File",
    submenu=[
        MenuItem(label="New", action="file.new"),
        MenuItem(label="Open", action="file.open"),
        MenuItem(label="Quit", action="file.quit"),
    ]
))
main_menu.append_item(MenuItem(
    label="Help",
    submenu=[
        MenuItem(label="About", action="help.about"),
    ]
))
```

### 4. Schema-based Configuration (GSettings-style)

Inspired by `GSettings` - schema-validated, observable configuration:

```python
from typing import Any, Callable
from dataclasses import dataclass


@dataclass
class SettingSchema:
    """A configuration setting schema - inspired by GSettings."""
    name: str
    type: type
    default: Any
    description: str = ""


class SettingsBackend:
    """Schema-based settings - inspired by GSettings."""
    
    def __init__(self, schema: dict[str, SettingSchema]):
        self._schema = schema
        self._values: dict[str, Any] = {}
        self._listeners: dict[str, list[Callable[[str, Any], None]]] = {}
        
        # Initialize with defaults
        for name, setting in schema.items():
            self._values[name] = setting.default
    
    def get(self, key: str) -> Any:
        return self._values.get(key)
    
    def set(self, key: str, value: Any) -> None:
        if key not in self._schema:
            raise KeyError(f"Unknown setting: {key}")
        
        expected_type = self._schema[key].type
        if not isinstance(value, expected_type):
            raise TypeError(f"{key} expects {expected_type}, got {type(value)}")
        
        old_value = self._values.get(key)
        self._values[key] = value
        
        # Notify listeners
        if key in self._listeners:
            for listener in self._listeners[key]:
                listener(key, value)
    
    def add_listener(self, key: str, callback: Callable[[str, Any], None]) -> None:
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(callback)


# Example: BBS settings
bbs_settings = SettingsBackend({
    "debug": SettingSchema("debug", bool, False, "Enable debug mode"),
    "database_host": SettingSchema("database_host", str, "localhost", "Database hostname"),
    "max_links_per_page": SettingSchema("max_links_per_page", int, 50, "Links per page"),
})

# Subscribe to changes
def on_debug_change(key: str, value: bool):
    print(f"Debug mode changed to: {value}")

bbs_settings.add_listener("debug", on_debug_change)
```

### 5. Implementation Priority

| Feature | Priority | Rationale |
|---------|----------|-----------|
| Observable List | Medium | Useful for teos sig tree, vulcan link list |
| Dynamic Discovery | Low | Current explicit init works well |
| Menu Model | Low | Current menu system is adequate |
| Schema Settings | Low | Could enhance config management |

The **Observable List** pattern would provide the most immediate benefit for your existing data structures.