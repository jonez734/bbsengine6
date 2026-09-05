# bbsengine6.module — module framework

> **Status:** canonical. Single source of truth for the
> four-function module shape, the registry, and the
> `module.run()` lifecycle. The previous per-function
> reference (`handbook/specs/modules.md`, 1678 lines) is
> superseded; the design sketch in `module_registration.md`
> is historical context only.

`bbsengine6.module` is the runtime plugin loader, validator,
access controller, and execution framework for bbsengine6. Every
BBS package (the engine itself, casino, empyre, murdermotel, bed,
…) is a `module` from this package's perspective: a Python object
exposing `init`, `access`, `buildargs`, and `main`.

## Contents

- [Module shape](#module-shape)
- [Module discovery](#module-discovery)
- [Loading and reloading](#loading-and-reloading)
- [Signature validation](#signature-validation)
- [The registry](#the-registry)
- [Execution lifecycle](#execution-lifecycle)
- [Helper functions](#helper-functions)
- [How the console loads modules](#how-the-console-loads-modules)
- [How startup loads stages](#how-startup-loads-stages)
- [Error handling](#error-handling)

## Module shape

Every bbsengine6 module exposes exactly four callables. They are
called in order by `module.run()`:

```python
def init(args, **kwargs) -> bool:
    """Initialize the module. Called once when the module is loaded."""

def access(args, op: str, **kwargs) -> bool:
    """Check whether the current session is permitted to perform ``op``.
    
    ``op`` is a domain verb (the operation the caller wants to perform),
    not a wire-protocol message type. Examples: ``"run"``, ``"edit"``,
    ``"init"``, ``"buildargs"``, ``"subscribe"``, ``"list_pending"``.
    """

def buildargs(args, **kwargs) -> argparse.ArgumentParser | None:
    """Build and validate arguments for ``main()``.
    
    Returns a configured ``ArgumentParser``; ``None`` if the module has
    no CLI flags. The first line of the module's docstring becomes the
    parser description.
    """

def main(args, **kwargs) -> Any:
    """Execute the module."""
```

All four **must** accept `**kwargs` — the module loader threads
context (pool, conn, kwargs from the caller) through every call.

## Module discovery

Modules are discovered via `importlib.import_module()` against a
fully-qualified Python module name (e.g. `"bbsengine6.console.member"`
or `"bbsengine6.console.checkroles"`). There is no
`bbsengine6/modules/` directory and no plugin manifest — packages
are added to `PYTHONPATH` and discovered by Python's standard
import system.

The registry (`register_module` / `unregister_module` /
`is_module_registered` / `get_module` / `get_module_api`) layers
a name-keyed API index on top of `importlib` so callers can
discover *which* API a module exports (its `access` policy, its
`init` callable, etc.) without doing another `importlib.import_module`
hop. The registry is opt-in via `set_require_registration(True)`;
without it, `module.check` accepts any importable module.

## Loading and reloading

`load(args, modulepath, package=None) -> ModuleType`

Loads a module via `importlib.import_module()`. When `args.debug`
is True, the module is `importlib.reload`-ed on every call so
edits to the source are picked up without restarting the process.

`package=` resolves bare names and relative dotted names:

| `modulepath`         | `package`     | Resolves to                                              |
|----------------------|---------------|----------------------------------------------------------|
| `"checkfunctions"`   | `None`        | `importlib.import_module("checkfunctions")`              |
| `"checkfunctions"`   | `"bbsengine6.backend"` | `bbsengine6.backend.checkfunctions`                  |
| `"checkfunctions"`   | `".backend"`  | `bbsengine6.backend.checkfunctions` (caller's package is `bbsengine6`) |
| `".stage_one"`       | `".backend"`  | `bbsengine6.backend.stage_one` (PEP 328, caller is `bbsengine6.backend`) |
| `"bbsengine6.console.member"` | `None` | `bbsengine6.console.member` (absolute; `package` ignored) |

Relative `package=` values are resolved against the calling frame's
`__package__` via `_caller_package()` so cross-package calls work
without the caller hard-coding the anchor.

`is_importable(modulepath) -> bool` — returns True iff
`import_module(modulepath)` succeeds, without leaving the module
on `sys.modules`.

`get(module_input, args=None, package=None) -> ModuleType` —
accepts either a dotted name (string) or an already-imported
module object; returns the module object.

`files(module_ref) -> pathlib.Path` — returns the module's
on-disk directory (like `importlib.files`). `folder(module_ref,
name) -> pathlib.Path | None` returns the named subdirectory.
`file(module_ref, subdir, name) -> pathlib.Path | None` returns
a specific file inside a subdirectory.

## Signature validation

`check(args, modulename, op="run", *, package=None, **kwargs) -> bool`

`check` is the entry point used by `module.run`. It runs the
following gates, in order:

1. **Registration check.** If `get_require_registration()` is True,
   the module must already be in the registry. If not, `check`
   returns False.
2. **Import.** `get(actual_modpath, args, package=package)` —
   resolves the registered `module_path` (or the input `modulename`
   if unregistered) and imports it.
3. **Required callables.** `init`, `access`, `buildargs`, `main`
   must all exist and be callable. Each is checked via
   `_check_func_signature(func, _stub_X)` against the matching
   stub from `OP_TO_STUB`:

   ```python
   def _stub_access(args, op, **kwargs) -> bool | None: pass
   def _stub_init(args, **kwargs) -> bool | None: pass
   def _stub_buildargs(args, **kwargs) -> argparse.ArgumentParser | None: pass
   def _stub_main(args, **kwargs) -> bool | None: pass
   def _stub_version(args, **kwargs) -> str | None: return None
   ```

   `version` is optional; if present it must match `_stub_version`.
4. **Access.** `m.access(args, op, **kwargs)` is invoked. A
   non-True return value fails the check.

`_check_func_signature(func, stub, *, name=None, allow_extra=True,
enforce_return=True)` accepts the module's callable and the stub,
then enforces:

- positional-only stubs (`_stub_X`) require positional-only real
  functions;
- required stub parameters (`args`, `op`) must be present in the
  real function with no default;
- real functions may add extra parameters beyond the stub
  (unless `allow_extra=False`);
- return annotations must agree (with `Optional[T] | Union[T, None]`
  treated as compatible with `T`).

`_check_params(func_name, params, required, optional_kwargs=False)`
is the simpler parameter-name check used by older `check()` paths.

`check_func(mod_ref, func_name, required_signature, *, allow_extra=True,
enforce_return=True, silent=False) -> bool` is the standalone
validator exported for callers that want to check a specific
function on a specific module. `validate_function(*args, **kwargs)`
is a backward-compatible alias.

## The registry

`bbsengine6.module` keeps a process-global registry of `ModuleAPI`
records keyed by module name. `ModuleAPI` is a frozen dataclass:

```python
@dataclass(frozen=True)
class ModuleAPI:
    version: str
    apis: dict[str, Callable]
    module_path: str
```

| Function                          | Signature                                              | Notes                                                    |
|-----------------------------------|--------------------------------------------------------|----------------------------------------------------------|
| `register_module(name, module_path, version, apis)` | Thread-safe UPSERT                      | Use in `init()` to expose a module's API                  |
| `unregister_module(name)`         | Thread-safe DELETE                                     |                                                           |
| `is_module_registered(name)`      | Thread-safe contains                                   |                                                           |
| `get_module(name) -> ModuleAPI | None` | Thread-safe read                              |                                                           |
| `get_module_api(name, api_name) -> Callable | None` | Thread-safe dict lookup                | The hot-path accessor for `bbsengine6.get_module_api` |
| `set_require_registration(bool)`  | Thread-safe flag                                       | When True, `module.check` requires registration           |
| `get_require_registration() -> bool` | Thread-safe flag read                              |                                                           |
| `get_all_modules() -> list[str]`  | Snapshot of registered names                            |                                                           |

The registry is created by `_create_registry()` which returns a
tuple of eight operations bound to a fresh `RegistryState` and
`threading.RLock`. The module-default registry is the first
instance created at import time.

The registry is what makes `bbsengine6.message.init` callable from
the engine startup path:

```python
from bbsengine6 import register_module

register_module(
    name="bbsengine6.message",
    module_path="bbsengine6.message",
    version=__version__,
    apis={"access": access},
)
```

## Execution lifecycle

`module.run(args, modulename, **kwargs) -> Any`

`run` is the canonical lifecycle orchestrator. The order is:

```
run(args, "modulename", **kwargs)
  ├─ actual_modpath = get_module(modulename).module_path or modulename
  ├─ get(actual_modpath, args, package=kwargs.pop("package", None))
  ├─ check(args, modulename, package=package, **kwargs)
  ├─ runcallback(args, m.init, **kwargs)               # module.init()
  ├─ argv = kwargs.get("argv", [])
  ├─ if _is_help_request(argv):
  │     runcallback(args, m.buildargs, **kwargs)
  │     print_help() and return True
  ├─ prgargparser = runcallback(args, m.buildargs, **kwargs)
  ├─ if prgargparser is not None:
  │     if argv empty and _has_subparser_info(args): use args directly
  │     elif argv and _has_subparser_info(args): warn + prgargparser.parse_args(argv)
  │     else:                                            prgargparser.parse_args(argv)
  │     return runcallback(prgargs, m.main, **kwargs)
  └─ return runcallback(args, m.main, **kwargs)
```

`runmodule` is an alias for `run` (kept for backward compat with
older call sites).

`runcallback(args, callback, optional=False, **kwargs)`:

- If `callback` is `None` and `optional=False`, returns `None`.
- If `callback` is callable, invokes `callback(args, **kwargs)`.
- If `callback` is a string `"mod.func"`, loads the module and
  invokes `m.func(args, **kwargs)`.
- If `callback` is a bare string `"funcname"`, looks up `funcname`
  in the caller's globals (no `eval()`).
- Exceptions are caught and reported via `io.echo_traceback()`,
  returning `None`.

## Helper functions

| Function                          | Signature                                                   | Purpose                                                              |
|-----------------------------------|-------------------------------------------------------------|----------------------------------------------------------------------|
| `check`                           | `(args, modulename, op="run", *, package=None, **kwargs)`   | Verify a module is valid and accessible                              |
| `is_importable`                   | `(modulepath) -> bool`                                      | Import test that does not pollute `sys.modules`                       |
| `load`                            | `(args, modulepath, *, package=None) -> ModuleType`         | Import (or reload in debug mode)                                     |
| `get`                             | `(module_input, args=None, *, package=None) -> ModuleType`  | Resolve a string-or-module reference                                 |
| `files`                           | `(module_ref) -> pathlib.Path`                              | Module directory                                                     |
| `folder`                          | `(module_ref, name) -> pathlib.Path | None`                  | Subdirectory                                                         |
| `file`                            | `(module_ref, subdir, name) -> pathlib.Path | None`         | Subdirectory + filename                                              |
| `get_op`                          | `(module_ref, op, args=None) -> Callable | None`            | Return the `op` function from the module if it matches its stub      |
| `runcallback`                     | `(args, callback, optional=False, **kwargs)`                | Invoke a callable or `"module.func"` string                          |
| `run`                             | `(args, modulename, **kwargs)`                              | Full lifecycle                                                        |
| `runmodule`                       | alias for `run`                                              |                                                                      |
| `register_module` / `unregister_module` / `is_module_registered` / `get_module` / `get_module_api` / `get_all_modules` / `set_require_registration` / `get_require_registration` | registry surface | See [The registry](#the-registry) |
| `check_func` / `validate_function` | signature validators                                       | See [Signature validation](#signature-validation)                   |

`SignatureError` is a dataclass carrying `func_name`, `expected`,
`found`, and optional `reason` fields. It is constructed by
`_check_func_signature` and surfaced through `io.echo(..., level="debug")`.

## How the console loads modules

`bbsengine6.console.lib.runmodule(args, submodule, *, package="bbsengine6.console", **kwargs)`
is a one-liner: `module.runmodule(args, f"{package}.{submodule}", **kwargs)`.
The console `__main__.py` builds a subcommand parser from
`CONSOLE_SUBCOMMANDS` and `BACKEND_SUBCOMMANDS`, then routes the
user's choice to `handle_subcommand(args, subcommand)`. Backend
subcommands dispatch with `package="bbsengine6.backend"`; console
subcommands stay with the default `package="bbsengine6.console"`.

This is the same `module.run` lifecycle every BBS package uses; the
console is just a thin argparse wrapper around it.

## How startup loads stages

`bbsengine6.startup.lib.runmodule(args, submodule, **kwargs)`
delegates to `bbsengine6.console.lib.runmodule(args, submodule,
package="bbsengine6.startup", **kwargs)`. The startup main loop
runs `("stage_zero", "stage_one", "engine", "bank")` via this
helper, threading `conn=conn` through so every stage shares the
same transaction. See `bbsengine6/TODO_BACKEND.md` for the
canonical bring-up sequence.

## Error handling

- `ModuleNotFoundError` from `import_module`: caught in `check`
  via `_check_func_signature`'s traceback path; surfaces via
  `io.echo_traceback()` and returns `None`/`False`.
- Signature validation failure: logged at `level="debug"` with
  expected / found signature side by side.
- `access()` returning non-True: `check` returns `False`.
- `argparse.ArgumentError` / `SystemExit` from `parse_args`:
  caught in `run`; `SystemExit` returns `e.code == 0` if set,
  `argparse.ArgumentError` returns `False`.
- Other exceptions from a module's `init` / `main`: caught by
  `runcallback` and surfaced via `io.echo_traceback()`.
