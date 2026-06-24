# module.spec - Module ABI Specification

## Overview

This document describes the bbsengine6 module ABI (Application Binary Interface) - the standard pattern for creating modules that can be run via `bbsengine6.module.run()`.

## Package Structure

A bbsengine6 module package follows this structure:

```
packagename/
├── __init__.py       # Package entry point with ABI functions
├── lib.py            # Shared utilities, constants, runmodule()
├── main.py           # Main module logic
└── (other modules)   # Optional submodules
```

## Required ABI Functions

Every module package must define these functions in `__init__.py`:

```python
def init(args, **kwargs) -> bool:
    """Initialize the module. Called before buildargs/main.
    
    Args:
        args: argparse.Namespace with parsed arguments
        **kwargs: Additional keyword arguments
        
    Returns:
        True to proceed, False to abort
    """
    return True


def access(args, op, **kwargs) -> bool:
    """Check if user has access to run this module.
    
    Args:
        args: argparse.Namespace with parsed arguments
        op: Operation type (e.g., "read", "write")
        **kwargs: Additional keyword arguments
        
    Returns:
        True to allow access, False to deny
    """
    return True


def buildargs(args=None, **kwargs):
    """Build and return ArgumentParser for this module.
    
    Args:
        args: Existing args (may be None for initial parse)
        **kwargs: Additional keyword arguments
        
    Returns:
        argparse.ArgumentParser, or None to skip arg parsing
    """
    return None


def main(args, **kwargs):
    """Main entry point for the module.
    
    Args:
        args: argparse.Namespace with parsed arguments
        **kwargs: Additional keyword arguments
        
    Returns:
        bool, int, or None (module runner interprets return value)
    """
    return lib.runmodule(args, "main", **kwargs)
```

## lib.py Requirements

The `lib.py` file must provide:

```python
from bbsengine6 import module

PACKAGENAME = "packagename"  # Must match package name


def runmodule(args, modulename, **kwargs):
    """Run a submodule by name.
    
    Args:
        args: argparse.Namespace with parsed arguments
        modulename: Name of submodule to run (e.g., "main", "edit")
        **kwargs: Additional keyword arguments
        
    Returns:
        Result from module.runmodule()
    """
    return module.runmodule(args, f"{PACKAGENAME}.{modulename}", **kwargs)
```

## main.py Pattern

The `main.py` file contains the actual module logic:

```python
def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    # Module-specific argparse setup
    return None


def main(args, **kwargs):
    # Module-specific logic
    return True
```

## Running Modules

### Via Command Line

```bash
# Direct execution
python -m packagename [options]

# Or via installed script
packagename [options]
```

### Via bbsengine6.module.run()

```python
from bbsengine6 import module

# Run the main module
module.run(args, "packagename")

# Run a specific submodule
module.run(args, "packagename.submodule")
```

### Via lib.runmodule()

```python
from . import lib

# From within the package
lib.runmodule(args, "main")
lib.runmodule(args, "submodule")
```

## Flow: How module.run() Works

1. **Load module**: `module.get(modulename, args)` imports the module
2. **Check access**: Call `module.check()` → calls `__init__.access()`
3. **Initialize**: Call `module.runcallback(args, m.init)` → calls `init()`
4. **Parse args**: 
   - If `buildargs()` returns a parser, parse args from `argv`
   - Otherwise use args directly
5. **Run main**: Call `module.runcallback(prgargs, m.main)` → calls `main()`
6. **Return**: Return value from `main()` becomes module.run() result

## Example: skel Package

See `bbsengine6/py/src/skel/` for a minimal working example:

```
skel/
├── __init__.py    # Delegates to lib.runmodule(args, "main")
├── lib.py         # Provides PACKAGENAME and runmodule()
└── main.py       # Simple demo module
```

## Return Values

| Return | Meaning |
|--------|---------|
| `True` | Success |
| `False` | Failure |
| `0` | Success (numeric) |
| `non-zero int` | Failure (numeric) |
| `None` | No result (depends on context) |

## Best Practices

1. **Keep __init__.py minimal** - Delegate to lib.runmodule()
2. **Use lib.py for shared code** - Constants, helpers, runmodule()
3. **buildargs() returns None** - If no additional args needed
4. **Always pass args to runmodule()** - Don't omit it!
5. **Package name in PACKAGENAME** - Must match import name
