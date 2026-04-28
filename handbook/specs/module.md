# bbsengine6.module Specification

## Overview

`module.py` provides the runtime plugin loading, validation, access control, and execution framework for bbsengine6. It handles dynamic module discovery, lifecycle management, and user-facing help.

**File:** `bbsengine6/module.py`
**Size:** ~359 lines

## Core Architecture

### Module Discovery

Modules are discovered via `importlib.import_module()` with the full Python module name. There is no `bbsengine6/modules/` directory — user plugins are installed as separate packages (e.g., `mygame/`, `plugins/`) added to `PYTHONPATH`. The module system has no special discovery mechanism; it relies entirely on Python's standard import system.

### Module Lifecycle

Every module must implement four functions. `access()` receives an `op` parameter (e.g., `"run"`, `"edit"`) for granular permission control:

```python
def init(args: object, **kwargs) -> None:
    """Initialize module (called once at startup)."""

def access(args: object, op: str = "run", **kwargs) -> bool:
    """Check if current user has access. Returns True to grant access."""

def buildargs(args: object, **kwargs) -> argparse.ArgumentParser | None:
    """Build and validate arguments for main(). Returns parser or None."""

def main(args: object, **kwargs) -> Any:
    """Execute module functionality."""
```

All four functions must accept `**kwargs` (keyword args catcher).

## Public API

---

```python
def check(args: object, modulename: str, op: str = "run", **kwargs) -> bool
```

Verify a module is valid and accessible. Performs these checks in order:

1. **Module import** — `importlib.import_module(modulename)`; conditionally `importlib.reload()` if `args.debug is True`
2. **Function existence** — `init`, `access`, `buildargs`, `main` must all exist and be callable
3. **Signature validation** — uses `_check_params()` + `inspect.signature()` to verify each function has `args` and `**kwargs`
4. **Access check** — calls `m.access(args, op, **kwargs)`; returns `False` if it does not return `True`

Returns `True` on success, `False` on any failure. Returns `None` on exception.

---

```python
def is_importable(modulepath: str) -> bool
```

Check if a module can be imported without side effects. Uses `importlib.import_module()` and captures the return value to verify the module loads successfully. Returns `True` if importable, `False` otherwise. Does not add the module to `sys.modules`.

---

```python
def load(args: object, modulepath: str) -> types.ModuleType
```

Load and return a Python module by full module path using `importlib.import_module()`. Raises `ModuleNotFoundError` on failure.

---

```python
def runcallback(args: object, callback: Callable, optional: bool = False, **kwargs) -> Any
```

Execute a callback function with error handling. `callback` can be:
- A callable object — invoked directly
- A dotted string `"module.funcname"` — the module is loaded and the named function is invoked

Returns the result of the callback, or `None` if the function was not found. Exceptions are caught and displayed via `io.echo_traceback()`.

---

```python
def run(args: object, modulename: str, **kwargs) -> Any
```

Full module execution lifecycle:

```
module.run()
  ├─ check()           # verify module is valid and access is granted
  ├─ runcallback("modulename.init")
  ├─ [if --help/-h in argv] runcallback("modulename.buildargs") → print help → return True
  ├─ runcallback("modulename.buildargs") → parse_args()
  └─ runcallback("modulename.main")
```

**Help handling:** If `--help` or `-h` appears in `argv` (passed via `kwargs`), `buildargs()` is called and the resulting parser's help is printed. If `buildargs()` returns `None`, a fallback parser is auto-generated from the module's `__doc__` string.

`argv` is cleaned (whitespace stripped) before being passed to `parse_args()`. `argparse.ArgumentError` and `SystemExit` are caught and handled gracefully.

---

```python
def validate_function(module_name: str, func_name: str, required_signature: Callable) -> bool
```

Standalone signature validator. Verifies a function exists in a module, is callable, and its parameters and type hints match `required_signature`. Uses `get_type_hints()` for type comparison.

**Note:** This function is a standalone utility. It is **not** part of the `check()`/`run()` execution flow — those use `_check_params()` + `inspect.signature()` instead.

---

## Private Helpers

```python
def _check_params(func_name: str, params: dict, required: list, optional_kwargs: bool = False) -> bool
```

Verify a function's signature has required parameters and a keyword args catcher (`kw` or `kwargs`). Logs errors via `io.echo()` if checks fail.

---

```python
def _is_help_request(argv: list) -> bool
```

Returns `True` if `argv` contains `--help` or `-h`.

---

```python
def _create_help_from_docstring(module) -> argparse.ArgumentParser | None
```

Auto-generate an `ArgumentParser` from a module's `__doc__` string. Returns `None` if the module has no docstring.

## Aliases

- `runmodule = run` (line 303) — provided for backward compatibility with the term `runmodule`

## Error Handling

- `ModuleNotFoundError` from `importlib.import_module()`: logs error if `silent=False`, returns `False`
- Other exceptions from module functions: caught by `runcallback()`, displayed via `io.echo_traceback()`, returns `None`
- Signature validation failures: logged via `io.echo()` with level `"error"`

## Dependencies

- `sys`, `importlib` — module loading and caching
- `inspect`, `typing.get_type_hints` — signature validation
- `argparse` — help generation
- `bbsengine6.io` — logging and error display
