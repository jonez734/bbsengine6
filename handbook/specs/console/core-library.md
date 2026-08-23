# Core Library (lib.py) Specification

## Overview

`lib.py` is the console module framework providing dynamic module discovery, validation, and execution infrastructure. It implements a plugin-like system where new console commands are auto-discovered without configuration.

**File:** `bbsengine6/console/lib.py`  
**Size:** 311 lines  

---

## Module Discovery & Validation

### discover_console_modules()

```python
def discover_console_modules(args, force_refresh=False) -> list
```

Automatically discovers all valid console modules in the package.

**Behavior:**
1. Scans `bbsengine6.console` package for `.py` files
2. For each file, validates via `validate_module_for_discovery()`
3. Returns list of valid module names (without `.py` extension)
4. Results cached (unless `args.debug=True` or `force_refresh=True`)

**Returns:** List of module names: `["member", "session", "memberapproval", ...]`

**Example:**
```python
modules = lib.discover_console_modules(args)
# Returns: ['member', 'session', 'memberapproval', 'email', ...]
```

---

### validate_module_for_discovery()

```python
def validate_module_for_discovery(module_fullname) -> bool
```

Validates whether a module meets console requirements.

**Checks:**
1. Module can be imported successfully
2. Has `main()` function (callable)
3. Has docstring (provides help text)

**Returns:** `True` if valid, `False` otherwise

**Note:** Does not check `init()`, `buildargs()`, or `access()` — only `main()` and docstring required for discovery.

---

### clear_module_cache()

```python
def clear_module_cache() -> None
```

Clears the module discovery cache. Called in debug mode to reload modules on each run.

---

## Subcommand & Argument Handling

### build_subcommand_parser()

```python
def build_subcommand_parser(parser, **kwargs) -> None
```

Adds discovered console modules as subcommands to an `ArgumentParser`.

**Behavior:**
1. Discovers modules via `discover_console_modules()`
2. For each module, creates a subcommand with:
   - Name: module name (e.g., "member")
   - Help: first line of module docstring
3. Sets module name in parser metadata for later routing

**Parameters:**
- `parser` — `ArgumentParser` to add subcommands to
- `**kwargs` — forwarded to `discover_console_modules()`

**Example:**
```python
parser = ArgumentParser()
lib.build_subcommand_parser(parser, args=args)
# parser now has subcommands: member, session, email, etc.
```

---

### handle_subcommand()

```python
def handle_subcommand(args, subcommand, **kwargs) -> bool
```

Routes to a specific subcommand module and executes it.

**Behavior:**
1. Calls `runmodule(args, f"console.{subcommand}", **kwargs)`
2. Returns result from module execution

**Parameters:**
- `args` — parsed arguments (with subcommand name)
- `subcommand` — module name to execute (e.g., "member")
- `**kwargs` — forwarded to module's `main()` function

**Returns:** Result from module's `main()` function

---

## Module Execution

### runmodule()

```python
def runmodule(args, submodule, **kwargs) -> Any
```

Generic module execution wrapper. Can run any bbsengine6 module with standard interface.

**Behavior:**
1. Imports module via `module.load(submodule)`
2. Calls `init()` if present
3. Calls `buildargs()` to get parser
4. Parses arguments
5. Calls `main()` with parsed args

**Parameters:**
- `args` — arguments object
- `submodule` — full module name (e.g., "console.member")
- `**kwargs` — forwarded to module functions

**Returns:** Return value from module's `main()` function

**Error Handling:** Catches exceptions, logs via `io.echo_traceback()`

**Note:** This is a thin wrapper; most modules use `module.run()` directly for full lifecycle.

---

## Wrapper Functions for Database Checks

All check modules have corresponding wrapper functions in `lib.py`. These provide convenient shortcuts:

### buildargs()

```python
def buildargs(args, **kwargs) -> ArgumentParser | None
```

Standard buildargs wrapper. Returns `None` by default (console lib has no CLI args).

---

### setbottombar()

```python
def setbottombar(args, left, **kwargs) -> None
```

Sets status bar text (left side). Framework integration point for UI.

---

### Check Module Wrappers

Each check module has a wrapper in `lib.py`:

```python
def checkroles(args=None, **kwargs) -> bool:
    return runmodule(args, "console.checkroles", **kwargs)

def checkextensions(args=None, **kwargs) -> bool:
    return runmodule(args, "console.checkextensions", **kwargs)

def checkdatabase(args=None, **kwargs) -> bool:
    return runmodule(args, "console.checkdatabase", **kwargs)

def checksuperuser(args=None, **kwargs) -> bool:
    return runmodule(args, "console.checksuperuser", **kwargs)

def checkfunctions(args=None, **kwargs) -> bool:
    return runmodule(args, "console.checkfunctions", **kwargs)

def checkwebserverrole(args=None, **kwargs) -> bool:
    return runmodule(args, "console.checkwebserverrole", **kwargs)

def checkschema(args=None, **kwargs) -> bool:
    return runmodule(args, "console.checkschema", **kwargs)

def checkclasses(args=None, **kwargs) -> bool:
    return runmodule(args, "console.checkclasses", **kwargs)

def checkpasswordformat(args=None, **kwargs) -> bool:
    return runmodule(args, "console.checkpasswordformat", **kwargs)

def checkflag(args=None, **kwargs) -> bool:
    return runmodule(args, "console.checkflag", **kwargs)

def checkloginid(args=None, **kwargs) -> bool:
    return runmodule(args, "console.checkloginid", **kwargs)

def checknotify(args=None, **kwargs) -> bool:
    return runmodule(args, "console.checknotify", **kwargs)
```

**Purpose:** Provide convenient shortcuts for `main.py` stages while maintaining consistent error handling.

---

## Usage Examples

### Discover Modules

```python
from bbsengine6.console import lib

modules = lib.discover_console_modules(args)
print(modules)
# Output: ['member', 'session', 'memberapproval', 'email', 'notify']
```

### Build Parser with Subcommands

```python
from argparse import ArgumentParser
from bbsengine6.console import lib

parser = ArgumentParser()
lib.build_subcommand_parser(parser, args=args)
```

### Run a Module

```python
lib.runmodule(args, "console.member", pool=pool)
```

### Run a Check in Setup

```python
from bbsengine6.console import lib

if lib.checkroles(args, pool=pool):
    print("Roles verified/created")
else:
    print("Failed to verify roles")
```

---

## Dependencies

**Internal:**
- `bbsengine6.module` — `load()`, `run()` functions
- `bbsengine6.io` — `echo_traceback()` for error display

**Standard Library:**
- `importlib` — module discovery and loading
- `pkgutil` — package scanning

---

## Error Handling

**Module Import Errors:**
- Module not found → logged, module not added to discovery list
- Module has no `main()` → not added to discovery
- Module has no docstring → not added to discovery

**Execution Errors:**
- Module import fails during `runmodule()` → exception caught, logged
- Module function raises → exception caught, logged via `io.echo_traceback()`

**Return Values:**
- Check functions return `True` on success, `False` on failure
- Check functions can be chained: `if lib.checkroles() and lib.checkdb(): ...`

