# module — Plugin System

Modules are Python packages loaded at runtime via `importlib`. Every module must define:

- `init(args, **kwargs) -> None`
- `access(args, op="run", **kwargs) -> bool`
- `buildargs(args, **kwargs) -> ArgumentParser | None`
- `main(args, **kwargs) -> Any`

All four must accept `**kwargs`. `access()` receives `op` for granular permission control.

## bbsengine6.module API

| Function | Signature | Purpose |
|---|---|---|
| `check()` | `(args, modulename, op="run", **kwargs) -> bool` | Verify module is valid and access is granted |
| `load()` | `(args, modulepath) -> ModuleType` | Import module via `importlib.import_module()` |
| `runcallback()` | `(args, callback, optional=False, **kwargs) -> Any` | Execute `module.func` string or callable |
| `run()` | `(args, modulename, **kwargs) -> Any` | Full lifecycle: check → init → buildargs → main |

`runmodule` is an alias for `run`.

## Execution Flow

`module.run()` performs:

1. `check()` — verifies functions exist, signatures valid, access passes
2. `runcallback("modulename.init")`
3. If `--help` or `-h` in `argv`: call `buildargs()`, print help, return
4. `runcallback("modulename.buildargs")` → `parse_args()`
5. `runcallback("modulename.main")`

Signature validation uses `_check_params()` + `inspect.signature()`, not `validate_function()`. The `validate_function()` function is a standalone utility.

## Module Discovery

Modules are discovered via `importlib.import_module()` with the full module name. There is no `bbsengine6/modules/` directory.
