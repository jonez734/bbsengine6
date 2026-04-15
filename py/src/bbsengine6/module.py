import sys
import argparse
import importlib
import inspect
from typing import Callable, Union, Any
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
def get(module_input: Union[str, ModuleType], args: Any = None) -> ModuleType:
    """
    Utility to resolve a module reference.
    If input is a string, it loads the module via load().
    If it's already a module object, it returns it.
    """
    if isinstance(module_input, ModuleType):
        return module_input

    if isinstance(module_input, str):
        return load(args, module_input)

    raise ValueError(
        f"Expected module name (str) or module object, got {type(module_input)=}"
    )


# @since 20230510 copied from bbsengine5
def load(args: object, modulepath: str) -> ModuleType:
    """
    Loads a module from a string path.
    Preserves BC and handles conditional reloading in debug mode.
    """
    debug = getattr(args, "debug", False) if args else False

    if modulepath in sys.modules and debug:
        io.echo(f"{modulepath=} is in sys.modules. reloading.", level="debug")
        importlib.reload(sys.modules[modulepath])

    try:
        m = importlib.import_module(modulepath)
        return m
    except Exception:
        io.echo_traceback(f"module {modulepath=} not importable")
        raise


# --- Signature Validation ---


def _check_func_return(func_ann, stub_ann):
    """Check return type compatibility with Optional[T] == Union[T, None] support."""
    if stub_ann is inspect._empty:
        return True

    if func_ann is inspect._empty:
        return False

    if func_ann == stub_ann:
        return True

    from typing import get_origin, get_args, Union

    def normalize(ann):
        origin = get_origin(ann)
        if origin is Union:
            return set(get_args(ann))
        return {ann}

    return normalize(func_ann) == normalize(stub_ann)


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
        return SignatureError(
            func_name=f_name,
            expected=f"{f_name}{sig_stub}",
            found=f"{f_name}{sig_func}",
            reason=reason,
        )

    if len(f_params) < len(s_params):
        return False

    for i, s in enumerate(s_params):
        f = f_params[i]

        if f.name != s.name:
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


def _stub_access(args: argparse.Namespace, op: str, /, **kwargs: dict) -> bool | None:
    pass


def _stub_init(args: argparse.Namespace, /, **kwargs: dict) -> bool | None:
    pass


def _stub_buildargs(
    args: argparse.Namespace, **kwargs: dict
) -> argparse.ArgumentParser | None:
    pass


def _stub_main(args: argparse.Namespace, /, **kwargs: dict) -> bool | None:
    pass


def _stub_version(args: argparse.Namespace, /, **kwargs: dict) -> str:
    pass


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
def check(args, modulename, op="run", **kwargs):
    debug = args.debug if args is not None and args.debug is True else False
    silent = kwargs.get("silent", True)

    m = get(modulename, args)

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
    debug = args.debug if args is not None else True

    if callback is None:
        if debug is True:
            io.echo("runcallback.140: callback is None", level="debug")
        return None

    if callable(callback) is True:
        if debug is True:
            io.echo("runcallback.160: callback is callable", level="debug")
        return callback(args, **kwargs)

    parts = callback.split(".")
    modpath = ".".join(parts[:-1]) if len(parts) > 1 else parts[0]
    fname = parts[-1] if len(parts) > 1 else "main"

    if debug is True:
        io.echo(
            f"runcallback.160: modulepath={modpath!r} funcname={fname!r}",
            level="debug",
        )

    if modpath is None or modpath == "":
        try:
            func = eval(fname)
            io.echo(f"runcallback.320: func={func!r}")
        except NameError:
            io.echo(f"runcallback.340: {fname!r} not found.", level="error")
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

    # Use get() to resolve module
    m = get(modulename, args)

    if check(args, modulename, **kwargs) is False:
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
                    fallback_parser.print_help()
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