import pathlib
import sys
import argparse
import importlib
import inspect
import threading
from typing import Callable, Union, Any, Optional
from types import ModuleType
from dataclasses import dataclass

from . import io


# --- Help Handling ---


def _is_help_request(argv: list) -> bool:
    """Check if argv contains --help or -h"""
    return "--help" in argv or "-h" in argv


def _has_subparser_info(args) -> bool:
    """Check if args has subparser-related attributes set from parent parser."""
    if args is None:
        return False
    subparser_attrs = ["_subsubparser", "_subparser", "subcommand", "command"]
    return any(
        hasattr(args, attr) and getattr(args, attr) is not None
        for attr in subparser_attrs
    )


def _create_help_from_docstring(module) -> object:
    """Create argparse parser from module docstring for help display"""
    if not hasattr(module, "__doc__") or not module.__doc__:
        return None

    parser = argparse.ArgumentParser(description=module.__doc__.strip(), add_help=True)
    return parser


# --- Signature Error ---


@dataclass
class SignatureError:
    func_name: str
    expected: str
    found: str
    reason: str | None = None

    def __str__(self):
        msg = (
            f"{self.func_name}() signature mismatch\n"
            f"Expected:\n  {self.expected}\n"
            f"Found:\n  {self.found}"
        )
        if self.reason:
            msg += f"\nReason:\n  {self.reason}"
        return msg


# --- Utility Functions ---


# @since 20251221
def get(
    module_input: Union[str, ModuleType],
    args: Any = None,
    package: Optional[str] = None,
) -> ModuleType:
    """
    Utility to resolve a module reference.
    If input is a string, it loads the module via load().
    If it's already a module object, it returns it.

    If ``package`` is provided, it is forwarded to ``load()`` so that bare
    (non-dotted) module names resolve relative to that package.
    """
    if isinstance(module_input, ModuleType):
        return module_input

    if isinstance(module_input, str):
        return load(args, module_input, package=package)

    raise ValueError(
        f"Expected module name (str) or module object, got {type(module_input)=}"
    )


# @since 20250624
def files(module_ref: Union[str, ModuleType]) -> pathlib.Path:
    """
    Return pathlib.Path to module's directory (like importlib.files).
    
    Args:
        module_ref: Module name (str) or module object
    
    Returns:
        pathlib.Path to the module's directory
    """
    m = get(module_ref)
    return pathlib.Path(m.__file__).parent


# @since 20250624
def folder(module_ref: Union[str, ModuleType], name: str) -> pathlib.Path | None:
    """
    Return pathlib.Path to module's subdirectory, or None if missing.

    Args:
        module_ref: Module name (str) or module object
        name: Subdirectory name (e.g., "data", "tpl", "sql")

    Returns:
        Path to subdirectory, or None if it doesn't exist
    """
    p = files(module_ref)
    sub = p / name
    return sub if sub.is_dir() else None


# @since 20260629
def file(module_ref: Union[str, ModuleType], subdir: str, name: str) -> pathlib.Path | None:
    """
    Return pathlib.Path to module_ref/subdir/name, or None if missing.

    Args:
        module_ref: Module name (str) or module object
        subdir: Subdirectory name (e.g., "data", "tpl", "sql")
        name: File name inside subdir (e.g., "notify.sql")

    Returns:
        Path to the file, or None if the subdir or file does not exist
    """
    sub = folder(module_ref, subdir)
    if sub is None:
        return None
    candidate = sub / name
    return candidate if candidate.is_file() else None


def _absolute_package_from_relative(caller_pkg: str, rel: str) -> str:
    """
    Convert a leading-dot relative package reference into an absolute
    package name following PEP 328 import semantics, anchored at
    ``caller_pkg``.

    PEP 328 rules:
      - ``"."``         means the caller's own package
      - ``".x"``        means one level up from the caller, then ``x``
      - ``".x.y"``      means one level up from the caller, then ``x.y``
      - ``".."``        means two levels up from the caller
      - ``"..x"``       means two levels up from the caller, then ``x``

    Examples (caller_pkg="bbsengine6"):
      "."              -> "bbsengine6"
      ".backend"       -> "bbsengine6.backend"
      ".startup"       -> "bbsengine6.startup"

    Examples (caller_pkg="bbsengine6.backend"):
      "."              -> "bbsengine6.backend"
      ".stage_one"     -> "bbsengine6.backend.stage_one"

    The caller is responsible for passing a ``caller_pkg`` deep enough
    that the relative reference can be resolved; if the dots ask to go
    above the top-level package, the empty string is returned.
    """
    if not rel.startswith("."):
        return rel

    leading_dots = 0
    for ch in rel:
        if ch == ".":
            leading_dots += 1
        else:
            break

    rest = rel[leading_dots:]
    up = leading_dots - 1
    if up < 0:
        up = 0

    if up == 0:
        base = caller_pkg
    else:
        parts = caller_pkg.split(".")
        if up >= len(parts):
            base = ""
        else:
            base = ".".join(parts[: len(parts) - up])

    if not rest:
        return base
    if not base:
        return rest
    return base + "." + rest


def _caller_package() -> str:
    """
    Return the ``__package__`` of the frame that called into ``load()``,
    walking past this module's internal frames (``get``, ``check``,
    ``run``) to find the user's frame.

    A frame is accepted only when its ``__name__`` is a real package —
    i.e., its ``__package__`` is a non-empty string, the module is
    importable, and ``__name__`` is consistent with ``__package__``.
    This skips test modules (which are not real packages) and test
    runner internals (pytest, unittest, ...).

    Falls back to this module's own ``__package__`` (or its ``__name__``
    if unset) when no qualifying caller frame is available — for
    example, a REPL, an unscoped script, or a test invocation.
    """
    try:
        frame = inspect.currentframe()
    except AttributeError:
        return sys.modules[__name__].__package__ or __name__

    if frame is None:
        return sys.modules[__name__].__package__ or __name__

    internal_names = {__name__, f"{__name__}.get", f"{__name__}.check", f"{__name__}.run"}
    internal_names.update({"get", "check", "run", "get_op", "check_func"})

    test_runner_prefixes = ("_pytest", "pytest", "unittest", "_io", "codeop")
    caller = frame.f_back
    while caller is not None:
        mod = caller.f_globals.get("__name__", "")
        if any(mod.startswith(p) for p in test_runner_prefixes):
            break
        if mod and mod not in internal_names and not mod.startswith(f"{__name__}."):
            caller_pkg = caller.f_globals.get("__package__")
            if (
                caller_pkg
                and caller_pkg != ""
                and mod in sys.modules
                and (mod == caller_pkg or mod.startswith(caller_pkg + "."))
            ):
                return caller_pkg
        caller = caller.f_back

    return sys.modules[__name__].__package__ or __name__


# @since 20230510 copied from bbsengine5
def load(args: object, modulepath: str, package: Optional[str] = None) -> ModuleType:
    """
    Loads a module from a string path.
    Preserves BC and handles conditional reloading in debug mode.

    If ``package`` is provided:
      - a bare (non-dotted) ``modulepath`` like ``"checkfunctions"`` is
        resolved as ``"{package}.{modulepath}"``. If ``package`` is
        absolute (no leading dot), the result is the absolute dotted name
        (equivalent to ``from {package} import {modulepath}``). If
        ``package`` is relative (leading dot, e.g. ``".backend"`` from a
        caller in ``bbsengine6.backend``), the leading-dot form is
        resolved against the calling frame's ``__package__`` to produce
        the absolute anchor before the import.
      - a leading-dot relative ``modulepath`` like ``".backend.checkfunctions"``
        is forwarded to ``importlib.import_module`` with ``package=`` so
        it resolves relative to ``package``. As above, a relative
        ``package=`` is first resolved to its absolute form.

    Dotted ``modulepath`` values without a leading dot are always treated
    as absolute imports, and any ``package`` argument is ignored for them.
    """
    debug = getattr(args, "debug", False) if args else False

    if modulepath in sys.modules and debug:
        io.echo(f"{modulepath=} is in sys.modules. reloading.", level="debug")
        importlib.reload(sys.modules[modulepath])

    try:
        if package is not None and "." not in modulepath:
            # Bare modulepath: qualify with the package anchor. If the
            # anchor is relative (e.g., ".backend" from a caller in
            # bbsengine6.backend), convert it to an absolute package by
            # walking up the calling frame's __package__.
            if package.startswith("."):
                caller_pkg = _caller_package()
                anchor = _absolute_package_from_relative(caller_pkg, package)
                m = importlib.import_module(f"{anchor}.{modulepath}")
            else:
                m = importlib.import_module(f"{package}.{modulepath}")
        elif package is not None and modulepath.startswith("."):
            # Relative dotted form (e.g. ".backend.checkfunctions"):
            # importlib needs the package anchor to resolve a leading-dot
            # name. If the anchor is itself relative, resolve it to an
            # absolute package first; otherwise importlib will refuse.
            if package.startswith("."):
                caller_pkg = _caller_package()
                anchor = _absolute_package_from_relative(caller_pkg, package)
                m = importlib.import_module(modulepath, package=anchor)
            else:
                m = importlib.import_module(modulepath, package=package)
        else:
            # Dotted absolute modulepath: package= is ignored.
            m = importlib.import_module(modulepath)
        return m
    except Exception:
        io.echo_traceback(f"module {modulepath=} not importable")
        raise


# @since 20260428
def is_importable(modulepath: str) -> bool:
    """
    Check if a module is importable.

    Args:
        modulepath: Full module path (e.g., "console.member")

    Returns:
        True if the module can be imported, False otherwise
    """
    try:
        _ = importlib.import_module(modulepath)
        return True
    except Exception:
        return False


# --- Module Registry (Pure Functional) ---
#
# Design principles:
# - State encapsulated in a closure, not global variables
# - All registry functions are pure-ish (same inputs -> same outputs, except logging)
# - Thread-safety via a single lock object
# - No classes - just functions and dataclasses for data

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ModuleAPI:
    """Immutable API container - registered module's version and callable functions."""

    version: str
    apis: dict[str, Callable]
    module_path: str


@dataclass
class RegistryState:
    """Mutable state for the registry - wrapped in a closure for encapsulation."""

    modules: dict[str, ModuleAPI] = field(default_factory=dict)
    require_registration: bool = False


def _create_registry() -> tuple[
    Callable[[str, str, str, dict], None],
    Callable[[str], None],
    Callable[[str], bool],
    Callable[[str], Optional[ModuleAPI]],
    Callable[[str, str], Optional[Callable]],
    Callable[[bool], None],
    Callable[[], bool],
    Callable[[], list[str]],
]:
    """Create a thread-safe registry closure with all operations.

    Returns 8 operation functions in order:
    (register, unregister, is_registered, get_module, get_module_api,
     set_require, get_require, get_all_names)
    """
    state = RegistryState()
    lock = threading.RLock()

    def register(
        name: str, module_path: str, version: str, apis: dict[str, Callable]
    ) -> None:
        with lock:
            state.modules[name] = ModuleAPI(
                version=version,
                apis=apis,
                module_path=module_path,
            )
        io.echo(f"registered module: {name} v{version}", level="debug")

    def unregister(name: str) -> None:
        with lock:
            state.modules.pop(name, None)

    def is_registered(name: str) -> bool:
        with lock:
            return name in state.modules

    def get_module(name: str) -> Optional[ModuleAPI]:
        with lock:
            return state.modules.get(name)

    def get_module_api(name: str, api_name: str) -> Optional[Callable]:
        with lock:
            module = state.modules.get(name)
            if module:
                return module.apis.get(api_name)
            return None

    def set_require_registration(required: bool) -> None:
        with lock:
            state.require_registration = required

    def get_require_registration() -> bool:
        with lock:
            return state.require_registration

    def get_all_names() -> list[str]:
        with lock:
            return list(state.modules.keys())

    return (
        register,
        unregister,
        is_registered,
        get_module,
        get_module_api,
        set_require_registration,
        get_require_registration,
        get_all_names,
    )


# Default registry instance - used throughout bbsengine6
(
    _register_module,
    _unregister_module,
    _is_module_registered,
    _get_module,
    _get_module_api,
    _set_require_registration,
    _get_require_registration,
    _get_all_module_names,
) = _create_registry()


# Convenience aliases matching the old function names
def register_module(
    name: str, module_path: str, version: str, apis: dict[str, Callable]
) -> None:
    """Register a module with its API. Thread-safe."""
    _register_module(name, module_path, version, apis)


def unregister_module(name: str) -> None:
    """Remove module registration. Thread-safe."""
    _unregister_module(name)


def is_module_registered(name: str) -> bool:
    """Check if module is registered. Thread-safe."""
    return _is_module_registered(name)


def get_module(name: str) -> Optional[ModuleAPI]:
    """Get registered module API. Thread-safe."""
    return _get_module(name)


def get_module_api(name: str, api_name: str) -> Optional[Callable]:
    """Get a specific API function from a registered module. Thread-safe."""
    return _get_module_api(name, api_name)


def set_require_registration(required: bool) -> None:
    """Set flag to require module registration in module.check()."""
    _set_require_registration(required)


def get_require_registration() -> bool:
    """Get the current require_registration flag."""
    return _get_require_registration()


def get_all_modules() -> list[str]:
    """Get names of all registered modules."""
    return _get_all_module_names()


# --- Signature Validation ---


def _check_func_return(func_ann, stub_ann):
    """Check return type compatibility with Optional[T] == Union[T, None] support."""
    # DEBUG using _echo like the rest of the game
    # try:
    #     io.echo(f"DEBUG _check_func_return: func_ann={func_ann!r} type={type(func_ann)} id={id(func_ann)}")
    #     io.echo(f"DEBUG _check_func_return: stub_ann={stub_ann!r} type={type(stub_ann)} id={id(stub_ann)}")
    #     io.echo(f"DEBUG _check_func_return: == result: {func_ann == stub_ann}")
    #     io.echo(f"DEBUG _check_func_return: is result: {func_ann is stub_ann}")
    # except Exception:
    #     pass

    if stub_ann is inspect._empty:
        return True

    if func_ann is inspect._empty:
        # Unannotated function: structurally compatible (treat as Any).
        return True

    if func_ann == stub_ann:
        return True

    # Try identity check as fallback for basic types like bool, int, str
    if func_ann is stub_ann:
        return True

    # Handle string annotations (PEP 563) - both must be strings to compare
    if isinstance(stub_ann, str) and isinstance(func_ann, str):
        if stub_ann == func_ann:
            return True

    from typing import get_args, get_origin

    def _args(ann):
        origin = get_origin(ann)
        if origin is not None:
            return set(get_args(ann)) | {origin}
        return {ann}

    stub_args = _args(stub_ann)
    func_args = _args(func_ann)

    # Stub is a Union (e.g. bool | None): func must be in the union or a
    # member of it. Accepts narrower return types like `bool` against
    # `bool | None`.
    if len(stub_args - func_args) != len(stub_args):
        return True

    # Otherwise the two annotations must agree exactly.
    return func_args == stub_args


def _kind_compatible(func_kind, stub_kind):
    """Check parameter kind compatibility with positional-only enforcement."""
    if stub_kind is inspect.Parameter.POSITIONAL_ONLY:
        return func_kind is inspect.Parameter.POSITIONAL_ONLY

    if stub_kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        return func_kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )

    return func_kind == stub_kind


def _check_func_signature(
    func, stub, *, name=None, allow_extra=True, enforce_return=True
):
    """Advanced signature validation with return type checking."""
    sig_func = inspect.signature(func)
    sig_stub = inspect.signature(stub)

    f_params = list(sig_func.parameters.values())
    s_params = list(sig_stub.parameters.values())

    f_name = name or func.__name__

    def fail(reason=None):
        io.echo(
            f"{f_name}() signature mismatch\n"
            f"  expected: {f_name}{sig_stub}\n"
            f"  found:    {f_name}{sig_func}"
            + (f"\n  reason:   {reason}" if reason else ""),
            level="debug",
        )
        return False

    if len(f_params) < len(s_params):
        return False

    for i, s in enumerate(s_params):
        f = f_params[i]

        if f.name != s.name and s.kind is not inspect.Parameter.VAR_KEYWORD:
            return fail(f"parameter {i + 1} should be '{s.name}'")

        if not _kind_compatible(f.kind, s.kind):
            return fail(f"'{s.name}' must be positional-only")

        if s.default is inspect._empty and f.default is not inspect._empty:
            return fail(f"'{s.name}' must not have a default")

    if not allow_extra and len(f_params) != len(s_params):
        return fail("too many parameters")

    if enforce_return:
        if not _check_func_return(
            sig_func.return_annotation, sig_stub.return_annotation
        ):
            return fail("return type mismatch")

    return True


# --- Stub Functions ---


def _stub_access(args: argparse.Namespace, op: str, **kwargs: dict) -> bool | None:
    pass


def _stub_init(args: argparse.Namespace, **kwargs: dict) -> bool | None:
    pass


def _stub_buildargs(
    args: argparse.Namespace, **kwargs: dict
) -> argparse.ArgumentParser | None:
    pass


def _stub_main(args: argparse.Namespace, **kwargs: dict) -> bool | None:
    pass


def _stub_version(args: argparse.Namespace, **kwargs: dict) -> str | None:
    return None


OP_TO_STUB = {
    "run": _stub_main,
    "init": _stub_init,
    "buildargs": _stub_buildargs,
    "access": _stub_access,
    "version": _stub_version,
}


# @since 20260415
def get_op(
    module_ref: Union[str, ModuleType], op: str, args: Any = None
) -> Callable | None:
    """
    Get an optional operation function if present and matches expected signature.
    Returns None if op not in map or function missing/invalid.

    Args:
        module_ref: Module name (str) or module object
        op: Operation name (e.g., "run", "init", "turn")
        args: argparse.Namespace or None

    Returns:
        Callable or None
    """
    m = get(module_ref, args)
    stub = OP_TO_STUB.get(op)
    if stub is None:
        return None
    if check_func(m, op, stub, silent=True):
        return getattr(m, op)
    return None


# --- Logic and Validation ---


# @since 20251128
def _check_params(
    func_name: str, params: dict, required: list, optional_kwargs: bool = False
):
    """
    Helper to check for required parameters by name (e.g., 'args', 'op')
    and the presence of a keyword argument catcher ('kw' or 'kwargs').
    Returns True on success, False on failure.
    """
    for p in required:
        if p not in params:
            io.echo(f"missing '{p}' from {func_name}()", level="error")
            return False

    if not optional_kwargs and "kw" not in params and "kwargs" not in params:
        io.echo(f"missing 'keyword args' in {func_name}()", level="error")
        return False
    return True


# @since 20220826
def check(args, modulename, op="run", *, package: Optional[str] = None, **kwargs):
    debug = args.debug if args is not None and args.debug is True else False
    silent = kwargs.get("silent", True)

    # Look up module_path from registry if module is registered
    module_info = get_module(modulename)
    if module_info is not None:
        actual_modpath = module_info.module_path
    else:
        actual_modpath = modulename

    # --- Registration Check ---
    if get_require_registration() is True:
        if not is_module_registered(modulename):
            io.echo(
                f"module {modulename} is not registered (required by config)",
                level="error",
            )
            return False
        io.echo(f"module.check: {modulename} is registered", level="debug")

    m = get(actual_modpath, args, package=package)

    if debug is True:
        io.echo(f"bbsengine6.module.check.100: {modulename=}", level="debug")

    # -----------------------------------------------
    # --- 1. Check Existence and Callability (REQUIRED FUNCTIONS) ---
    # -----------------------------------------------

    # --- Check init() ---
    if hasattr(m, "init") is False:
        if debug is True:
            io.echo("no init function", level="warn")
        return False
    if callable(m.init) is False:
        io.echo("init function is not callable", level="error")
        return False

    # --- Check access() ---
    if hasattr(m, "access") is False:
        if debug is True:
            io.echo("no access function", level="error")
        return False
    if (callable(m.access)) is False:
        io.echo("no callable access function", level="error")
        return False

    try:
        if m.access(args, op, **kwargs) is True:
            if silent is False:
                io.echo("access check passed", level="debug")
        else:
            if silent is False:
                io.echo("access check failed", level="error")
            return False
    except Exception as e:
        io.echo_traceback(f"module.check error: {e}")
        return None

    # --- Check buildargs() (REQUIRED) ---
    if hasattr(m, "buildargs") is False:
        io.echo("no buildargs function found (required)", level="error")
        return False
    if callable(m.buildargs) is False:
        io.echo("buildargs function is not callable", level="error")
        return False

    # --- Check main() ---
    if hasattr(m, "main") is False:
        io.echo("main function not found", level="error")
        return False
    if callable(m.main) is False:
        io.echo("main function not callable", level="error")
        return False

    if debug is True:
        io.echo("checking signatures", level="debug")

    # -----------------------------------------------
    # --- 2. Signature Verification (with stubs) ---
    # -----------------------------------------------

    # Using _check_func_signature from asimov for validation
    if not _check_func_signature(m.init, _stub_init):
        io.echo("init() signature invalid", level="error")
        return False

    if not _check_func_signature(m.buildargs, _stub_buildargs):
        io.echo("buildargs() signature invalid", level="error")
        return False

    if not _check_func_signature(m.main, _stub_main):
        io.echo("main() signature invalid", level="error")
        return False

    sig_access = inspect.signature(m.access)
    if not _check_func_signature(m.access, _stub_access):
        io.echo(
            f"access() signature mismatch\n"
            f"Expected:\n  access{inspect.signature(_stub_access)}\n"
            f"Found:\n  access{sig_access}",
            level="error",
        )
        return False

    # Check for optional version()
    if hasattr(m, "version"):
        if callable(m.version) is False:
            io.echo("version function is not callable", level="error")
            return False

        if not _check_func_signature(m.version, _stub_version):
            io.echo("version() signature invalid", level="error")
            return False

    if debug is True:
        io.echo("bbsengine6.module.check.200: check passed", level="debug")

    return True


# @since 20230510 copied from bbsengine5
def runcallback(
    args: object, callback: Union[Callable, str], optional: bool = False, **kwargs
):
    debug = getattr(args, "debug", False) if args is not None else True

    if callback is None:
        if debug is True:
            io.echo("runcallback.140: callback is None", level="debug")
        return None

    if callable(callback) is True:
        if debug is True:
            io.echo("runcallback.160: callback is callable", level="debug")
        cb: Callable = callback  # type: ignore[assignment]
        return cb(args, **kwargs)

    if not isinstance(callback, str):
        io.echo(
            f"runcallback.150: callback is not str or callable: {type(callback)=}",
            level="error",
        )
        return None

    parts = callback.split(".")
    modpath = ".".join(parts[:-1]) if len(parts) > 1 else parts[0]
    fname = parts[-1] if len(parts) > 1 else "main"

    if debug is True:
        io.echo(
            f"runcallback.160: modulepath={modpath!r} funcname={fname!r}",
            level="debug",
        )

    if modpath is None or modpath == "":
        # Bare-name callback (e.g. "main"): look up *fname* in the immediate
        # caller's globals rather than eval()-ing arbitrary expressions.
        func = None
        try:
            caller_frame = inspect.stack()[1].frame
            func = caller_frame.f_globals.get(fname)
        except (IndexError, AttributeError):
            func = None
        if func is None:
            io.echo(
                f"runcallback.340: {fname!r} not found in caller globals.",
                level="error",
            )
            return None

        if callable(func) is True:
            if debug is True:
                io.echo("runcallback.260: callable", level="debug")
            return func(args, **kwargs)
        else:
            if debug is True:
                io.echo("runcallback.280: not callable", level="debug")
            return None

    m = get(modpath, args)
    if debug is True:
        io.echo(f"runcallback.200: {m=} {fname=}", level="debug")

    try:
        func = getattr(m, fname)
    except AttributeError:
        io.echo(f"runcallback.240: function {fname}() not found", level="error")
        return None

    if debug is True:
        io.echo(f"runcallback.220: func={func!r}", level="debug")

    if callable(func) is True:
        return func(args, **kwargs)

    return None


# @since 20220727
# @since 20230508 added to bbsengine6
def run(args, modulename, **kwargs):
    debug = args.debug if hasattr(args, "debug") and args.debug else False
    buildargs = True

    # Pop package= so it isn't forwarded to callbacks (e.g. main(), init()).
    # It is used to resolve bare submodule names against a parent package.
    package = kwargs.pop("package", None)

    # Look up module_path from registry if module is registered
    module_info = get_module(modulename)
    if module_info is not None:
        actual_modpath = module_info.module_path
    else:
        actual_modpath = modulename

    # Use get() to resolve module
    m = get(actual_modpath, args, package=package)

    if check(args, modulename, package=package, **kwargs) is False:
        io.echo(f"check of {modulename=} failed. module not run.", level="error")
        return False

    if debug is True:
        io.echo(f"bbsengine6.module.run.100: {args=}", level="debug")

    res = runcallback(args, m.init, **kwargs)
    if debug is True:
        io.echo(f"{modulename}.init() {res=}", level="debug")

    if buildargs is True:
        argv = kwargs.get("argv", [])
        if debug is True:
            io.echo(f"bbsengine6.module.run.120: {argv=}", level="debug")

        # Check for help request BEFORE calling buildargs
        if _is_help_request(argv):
            prgargparser = runcallback(args, m.buildargs, **kwargs)

            if prgargparser is not None:
                prgargparser.print_help()
            else:
                # Auto-generate help from module docstring
                fallback_parser = _create_help_from_docstring(m)
                if fallback_parser:
                    fallback_parser.print_help()  # type: ignore
                else:
                    io.echo(
                        f"Help for {modulename}: No documentation available",
                        level="info",
                    )

            return True  # Help is success, not error

        prgargparser = runcallback(args, m.buildargs, **kwargs)

        if debug is True:
            io.echo(f"bbsengine6.module.run.130: {prgargparser=}", level="debug")

        if prgargparser is not None:
            try:
                argv = [a.strip() for a in argv] if argv else []

                # If argv is empty but args already has subparser info from parent
                # parser, use args directly to preserve that info
                if not argv and _has_subparser_info(args):
                    prgargs = args
                    if debug is True:
                        io.echo(
                            "bbsengine6.module.run.135: using existing args "
                            "(argv empty, subparser info present)",
                            level="debug",
                        )
                elif argv and _has_subparser_info(args):
                    # Caller passed both pre-parsed args and a non-empty
                    # argv. The two may disagree (the parent already
                    # consumed some flags; the child will see them again
                    # and may reject them). Surface this rather than
                    # silently producing a different Namespace.
                    io.echo(
                        f"bbsengine6.module.run.140: WARNING: caller passed "
                        f"both pre-parsed args and argv={argv!r}; the child "
                        f"parser will re-parse argv and may reject flags "
                        f"already consumed by the parent. Prefer passing "
                        f"args only (no argv=) for child invocations.",
                        level="warn",
                    )
                    prgargs = prgargparser.parse_args(argv)
                else:
                    prgargs = prgargparser.parse_args(argv)
                if debug is True:
                    io.echo(
                        f"bbsengine6.module.run.140: {prgargs=} {argv=}", level="debug"
                    )
            except SystemExit as e:
                return e.code == 0 if hasattr(e, "code") else False
            except argparse.ArgumentError:
                io.echo("argument error", level="error")
                return False

            if debug is True:
                io.echo(f"bbsengine6.module.run.220: {prgargs=}", level="debug")

            return runcallback(prgargs, m.main, **kwargs)

    res = runcallback(args, m.main, **kwargs)

    if debug is True:
        io.echo(f"{modulename}.main() {res=}", level="debug")
    return res


# @since 20240709
# @project:9332
runmodule = run


# @since 20250316 (from asimov)
def check_func(
    mod_ref: Union[str, ModuleType],
    func_name: str,
    required_signature: Callable,
    *,
    allow_extra: bool = True,
    enforce_return: bool = True,
    silent: bool = False,
) -> bool:
    """
    Validate that a module function matches a required signature.

    This uses the same compatibility rules as module.check():
    - positional-only enforcement
    - default value rules
    - optional extra parameters
    - Optional[T] / Union[T, None] return compatibility

    Returns True on success, False on failure.
    """
    try:
        module = get(mod_ref)
    except Exception:
        if not silent:
            io.echo_traceback("validate_function: failed to resolve module")
        return False

    if not hasattr(module, func_name):
        if not silent:
            io.echo(f"validate_function: '{func_name}' not found", level="error")
        return False

    func = getattr(module, func_name)
    if not callable(func):
        if not silent:
            io.echo(f"validate_function: '{func_name}' is not callable", level="error")
        return False

    result = _check_func_signature(
        func,
        required_signature,
        name=func_name,
        allow_extra=allow_extra,
        enforce_return=enforce_return,
    )

    if result is not True:
        if not silent:
            io.echo(str(result), level="error")
        return False

    return True


# @since 20250316
def validate_function(*args, **kwargs) -> bool:
    """
    Backward-compatible alias for check_func().
    Prefer check_func() for new code.
    """
    return check_func(*args, **kwargs)
