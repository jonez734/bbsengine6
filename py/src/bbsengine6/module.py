import sys
import argparse
import importlib
import inspect
from typing import get_type_hints, Callable

from . import io

# @since 20260223 - Help handling support
def _is_help_request(argv: list) -> bool:
    """Check if argv contains --help or -h"""
    return "--help" in argv or "-h" in argv

def _create_help_from_docstring(module) -> object:
    """Create argparse parser from module docstring for help display"""
    if not hasattr(module, '__doc__') or not module.__doc__:
        return None
    
    parser = argparse.ArgumentParser(
        description=module.__doc__.strip(),
        add_help=True
    )
    return parser

# @since 20251128
def _check_params(func_name: str, params: dict, required: list, optional_kwargs: bool = False):
    """
    Helper to check for required parameters by name (e.g., 'args', 'op')
    and the presence of a keyword argument catcher ('kw' or 'kwargs').
    Returns True on success, False on failure.
    """
    for p in required:
        if p not in params:
            io.echo(f"missing '{p}' from {func_name}()", level="error")
            return False

    # Check for keyword arguments catcher ('kw' or 'kwargs') unless optional_kwargs is True
    if not optional_kwargs and "kw" not in params and "kwargs" not in params:
        io.echo(f"missing 'keyword args' in {func_name}()", level="error")
        return False
    return True

# @since 20220826
def check(args, modulename, op="run", **kwargs):
  debug = args.debug if args is not None and args.debug is True else False
  silent = kwargs.get("silent", True)

  # --- Module Import and Reload (Reloading is now conditional on debug) ---
  if modulename in sys.modules:
    if debug is True:
      io.echo(f"{modulename=} is in sys.modules. reloading.", level="debug")
      importlib.reload(sys.modules[modulename])

  if debug is True:
    io.echo(f"bbsengine.module.check.120: {modulename=}", level="debug")

  try:
    m = importlib.import_module(modulename)
  except ModuleNotFoundError:
    if silent is False:
      io.echo(f"module {modulename=} not importable", level="error")
    return False
  except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stdout)
    return False

  if debug is True:
    io.echo(f"bbsengine6.module.check.100: {type(m)=} {m=}", level="debug")

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
    # Use **kwargs here instead of **kw
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
    io.echo("no working main function", level="error")
    return False
  if callable(m.main) is False:
    io.echo("no working main function", level="error")
    return False

  if debug is True:
    io.echo("checking signatures", level="debug")

  # -----------------------------------------------
  # --- 2. Setup and Check Signatures ---
  # -----------------------------------------------

  # All core functions are required and verified as callable.
  functions_to_check = ["init", "access", "buildargs", "main"]

  # Check for optional version()
  if hasattr(m, "version"):
    if callable(m.version) is False:
      io.echo("version function is not callable", level="error")
      return False
    functions_to_check.append("version")

  # --- Parameter Signature Check Loop ---
  for f in functions_to_check:
    sig = inspect.signature(eval(f"m.{f}"))
    params = sig.parameters

    if args.debug is True:
      io.echo(f"{sig=} {params=}", level="debug")

    # Define required parameters for the helper
    required_params = ["args"]
    if f == "access":
      required_params.append("op")

    # All checked functions must have 'args' and **kwargs
    if not _check_params(f, params, required_params):
      return False

  return True

#@since 20230510 copied from bbsengine5
def load(args:object, modulepath:str):
  try:
      m = importlib.import_module(modulepath)
  except ModuleNotFoundError:
      io.echo(f"bbsengine6.module.load.180: module {modulepath} not found", level="error")
      raise
  return m
  
# @since 20230510 copied from bbsengine5
def runcallback(args:object, callback:callable, optional:bool=False, **kwargs): # s:argparse.Namespace, callback, argparser=None, **kwargs):
  debug = args.debug if args is not None else True
  if debug is True:
    io.echo(f"bbsengine6.runcallback.100: {args=} {kwargs=}", level="debug")
#  if argparser is not None:
#    args = argparser.parse_args()

  if callback is None:
    if debug is True:
      io.echo("runcallback.140: callback is None", level="debug")
    return None

  if callable(callback) is True:
    if debug is True:
      io.echo("runcallback.160: callback is callable", level="debug")
    return callback(args, **kwargs)

  s = callback.split(".")
  if len(s) > 1:
    modulepath = ".".join(s[:-1])
    funcname = s[len(s)-1:][0]
  else:
    modulepath = s[0] # None
    funcname = "main" # s[0]

  if debug is True:
    io.echo("runcallback.160: modulepath=%r funcname=%r" % (modulepath, funcname), level="debug")

  if modulepath is None:
    try:
      func = eval(funcname)
      io.echo("runcallback.320: func=%r" % (func))
    except NameError:
      io.echo("runcallback.340: %r not found." % (funcname), level="error")
      return None

    if callable(func) is True:
      if debug is True:
        io.echo("runcallback.260: callable", level="debug")
      return func(args, **kwargs)
    else:
      if debug is True:
        io.echo("runcallback.280: not callable", level="debug")
      return None

  m = load(args, modulepath)
  if debug is True:
    io.echo(f"runcallback.200: {m=} {funcname=}", level="debug")

  try:
    func = getattr(m, funcname)
  except AttributeError:
#    ttyio.echo("runcallback.240: function %s.%s() not found" % (modulepath, funcname))
    return None
  else:
    if debug is True:
      io.echo("runcallback.220: func=%r" % (func), level="debug")
    if callable(func) is True:
      return func(args, **kwargs)

  return None

# @since 20220727
# @since 20230508 added to bbsengine6
def run(args, modulename, **kwargs):
  debug = args.debug if "debug" in args else False
  buildargs = True

  if check(args, modulename, **kwargs) is False:
    io.echo(f"check of {modulename=} failed. module not run.", level="error")
    return False

  if debug is True:
    io.echo(f"bbsengine6.module.run.100: {args=}", level="debug")

  res = runcallback(args, f"{modulename}.init", **kwargs)
  if debug is True:
    io.echo(f"{modulename}.init() {res=}", level="debug")

  if buildargs is True:
    argv = kwargs["argv"] if "argv" in kwargs else []
    if debug is True:
      io.echo(f"bbsengine6.module.run.120: {argv=}", level="debug")
    
    # Check for help request BEFORE calling buildargs
    if _is_help_request(argv):
      prgargparser = runcallback(args, f"{modulename}.buildargs", **kwargs)
      
      if prgargparser is not None:
        prgargparser.print_help()
      else:
        # Auto-generate help from module docstring
        m = load(args, modulename)
        fallback_parser = _create_help_from_docstring(m)
        if fallback_parser:
          fallback_parser.print_help()
        else:
          io.echo(f"Help for {modulename}: No documentation available", level="info")
      
      return True  # Help is success, not error
    
    prgargparser = runcallback(args, f"{modulename}.buildargs", **kwargs)

    if debug is True:
      io.echo(f"bbsengine6.module.run.130: {prgargparser=}", level="debug")

    if prgargparser is not None:
      try:
        # argv already doesn't include subcommand name (extracted by console/__main__.py)
        # Just clean up whitespace
        argv = [a.strip() for a in argv] if argv else []
        prgargs = prgargparser.parse_args(argv)
        if debug is True:
          io.echo(f"bbsengine6.module.run.140: {prgargs=} {argv=}", level="debug")
#        prgargs = [s.strip() for s in prgargs]
      except SystemExit as e:
        # Exit code 0 = help or success, non-zero = error
        return e.code == 0 if hasattr(e, 'code') else False
      except argparse.ArgumentError:
        io.echo("argument error", level="error")
        return False

      if debug is True:
        io.echo(f"bbsengine6.module.run.220: {prgargs=}", level="debug")

      # return runcallback(prgargs, f"{modulename}.main", **kwargs)

  res = runcallback(args, f"{modulename}.main", **kwargs)

  if debug is True:
    io.echo(f"{modulename}.main() {res=}", level="debug")
  return res

# @since 20240709
# @project:9332
runmodule = run

# @since 20220828
#def runsubmodule(args, module, **kw):
#  if args.debug is True:
#    io.echo("bbsengine6.module.runsubmodule.100: trace", level="debug")
#  return runmodule(args, module, **kw)

# @since 20250316
def validate_function(module_name: str, func_name: str, required_signature: Callable):
    module = importlib.import_module(module_name)

    # Check if function exists
    if not hasattr(module, func_name):
        raise ValueError(f"Function '{func_name}' not found in module '{module_name}'")

    func = getattr(module, func_name)

    if not callable(func):
        raise ValueError(f"'{func_name}' in module '{module_name}' is not callable")

    # Inspect signature
    sig = inspect.signature(func)
    required_sig = inspect.signature(required_signature)

    # Compare parameters
    if sig.parameters.keys() != required_sig.parameters.keys():
        raise ValueError(f"'{func_name}' has wrong parameters: {sig.parameters.keys()}")

    # Compare types
    func_hints = get_type_hints(func)
    required_hints = get_type_hints(required_signature)

    for param, required_type in required_hints.items():
        if param == 'return':
            continue
        if param not in func_hints:
            raise ValueError(f"Missing type annotation for '{param}' in '{func_name}'")
        if func_hints[param] != required_type:
            raise ValueError(f"Wrong type for '{param}': expected {required_type}, got {func_hints[param]}")

    # Compare return type
    if func_hints.get('return', None) != required_hints.get('return', None):
        raise ValueError(f"Wrong return type for '{func_name}': expected {required_hints.get('return')}, got {func_hints.get('return')}")

    io.echo(f"'{func_name}' in '{module_name}' is valid!", level="debug")
    return True


# Example usage:
#def required_init(config: dict, verbose: bool) -> None:
#    pass

#validate_function('my_module', 'init', required_init)

#def init(args: argparse.Namespace, **kwargs) -> bool: pass

