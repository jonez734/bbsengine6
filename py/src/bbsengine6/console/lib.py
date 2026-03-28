import argparse
import importlib
import os

from bbsengine6 import io, database, screen, module

SQLDIR = "$HOME/projects/bbsengine6/sql/"

# Module cache for dynamic discovery
_discovered_modules_cache = None


def discover_console_modules(args=None, force_refresh=False):
    """
    Dynamically discover console modules that meet criteria:
    - Module has main() function
    - Module has docstring
    - Module can be imported successfully

    Args:
        args: Optional args object (for debug flag)
        force_refresh: Force rediscovery even if cached

    Returns:
        dict: {module_name: help_text}
    """
    global _discovered_modules_cache

    # Determine if we should use cache
    debug_mode = getattr(args, "debug", False) if args else False

    use_cache = (
        not force_refresh and not debug_mode and _discovered_modules_cache is not None
    )

    if use_cache:
        return _discovered_modules_cache

    # Perform discovery
    modules = {}
    console_package = "bbsengine6.console"

    try:
        # Get the directory where this module (lib.py) is located
        # That's the console package directory
        console_path = os.path.dirname(os.path.abspath(__file__))

        if os.path.isdir(console_path):
            for filename in os.listdir(console_path):
                if filename.endswith(".py") and not filename.startswith("_"):
                    module_name = filename[:-3]  # Remove .py extension

                    # Skip special modules
                    if module_name in ["lib", "__init__", "__main__", "main"]:
                        continue

                    # Try to validate the module
                    is_valid, help_text = validate_module_for_discovery(
                        f"{console_package}.{module_name}"
                    )

                    if is_valid:
                        modules[module_name] = help_text

    except Exception as e:
        if debug_mode:
            io.echo(f"Error discovering modules: {e}", level="debug")

    # Cache the result (unless in debug mode)
    if not debug_mode:
        _discovered_modules_cache = modules

    return modules


def validate_module_for_discovery(module_fullname):
    """
    Check if module meets discovery criteria.

    Args:
        module_fullname: Full module name (e.g., 'bbsengine6.console.member')

    Returns:
        tuple: (is_valid: bool, help_text: str or None)
    """
    try:
        # Try to import the module
        m = importlib.import_module(module_fullname)

        # Check for main() function
        if not hasattr(m, "main") or not callable(getattr(m, "main", None)):
            return (False, None)

        # Check for docstring
        doc = getattr(m, "__doc__", None)
        if not doc or not isinstance(doc, str):
            return (False, None)

        # Extract first line of docstring as help text
        help_text = doc.strip().split("\n")[0].strip()

        return (True, help_text)

    except Exception:
        io.echo_traceback("bbsengine6.console.lib.104:")
        return (False, None)


def clear_module_cache():
    """Clear the module discovery cache"""
    global _discovered_modules_cache
    _discovered_modules_cache = None


# @since 20230518 copied from teos
def buildargs(args=None, **kwargs):
    parser = argparse.ArgumentParser("con")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {
        "databasename": "zoid6",
        "databasehost": "localhost",
        "databaseuser": None,
        "databaseport": 5432,
        "databasepassword": None,
    }
    database.buildargs(parser, defaults)

    return parser


# @since 20230523
def runmodule(args, submodule, **kwargs):
    #  io.echo(f"con.lib.runmodule.100: {kwargs=}", level="debug")
    return module.runmodule(args, f"bbsengine6.console.{submodule}", **kwargs)


# @since 20230523 copied from teos
def setbottombar(args, left, **kwargs):
    def right():
        help = " | F1: Help" if "help" in kwargs and kwargs["help"] is True else ""
        debug = " | debug" if args.debug is True else ""
        return f"con{debug}{help}"

    screen.setbottombar(left, right, **kwargs)
    return


def checkroles(args, **kwargs):
    return runmodule(args, "checkroles", **kwargs)


def checkextensions(args, **kwargs):
    return runmodule(args, "checkextensions", **kwargs)


def checkdatabase(args, **kwargs):
    return runmodule(args, "checkdatabase", **kwargs)


def checksuperuser(args, **kwargs):
    return runmodule(args, "checksuperuser", **kwargs)


def createdatabase(args, **kwargs):
    return runmodule(args, "createdatabase", **kwargs)


def checkfunctions(args, **kwargs):
    return runmodule(args, "checkfunctions", **kwargs)


def checkclasses(args, **kwargs):
    return runmodule(args, "checkclasses", **kwargs)


def checkschema(args, **kwargs):
    return runmodule(args, "checkschema", **kwargs)


def checkflag(args, **kwargs):
    return runmodule(args, "checkflag", **kwargs)


def checkwebserverrole(args, **kwargs):
    return runmodule(args, "checkwebserverrole", **kwargs)


# @since 20260223 - Argparse subcommand support
# @since 20260223 - Updated to use dynamic module discovery
def build_subcommand_parser(parser=None, **kwargs):
    """
    Create or extend parser with subcommands for console modules.
    Uses argparse subparsers to add dynamically discovered modules as subcommands.

    Args:
        parser: Optional existing parser to extend
        kwargs: Additional arguments (including 'args' for debug mode)

    Returns:
        tuple: (parser, subparsers)
    """
    # Get args from kwargs if available (for debug mode detection)
    args = kwargs.get("args")

    if parser is None:
        parser = argparse.ArgumentParser(
            prog="zoidoffice",
            description="BBS Engine 6 Console - Manage your BBS system",
            add_help=True,
        )
        parser.add_argument("--verbose", action="store_true", dest="verbose")
        parser.add_argument("--debug", action="store_true", dest="debug")

        defaults = {
            "databasename": "zoid6",
            "databasehost": "localhost",
            "databaseuser": None,
            "databaseport": 5432,
            "databasepassword": None,
        }
        database.buildargs(parser, defaults)

    # Create subparsers for module commands
    subparsers = parser.add_subparsers(dest="subcommand", help="Available modules")

    # Dynamically discover modules (uses cache in normal mode, refreshes in debug mode)
    subcommands = discover_console_modules(args=args) or {}

    for cmd_name, cmd_help in subcommands.items():
        subparsers.add_parser(cmd_name, help=cmd_help, add_help=True)

    return parser, subparsers


# ============================================================================
# Module-Specific Arguments Pattern
# ============================================================================
"""
To add custom arguments to a module, define buildargs() that returns
an ArgumentParser with your custom arguments.

Example module (bbsengine6/console/mytest.py):

    import argparse
    
    def init(args, **kwargs):
        return True
    
    def buildargs(args, **kwargs):
        '''My test module - does something useful'''
        parser = argparse.ArgumentParser(description=__doc__)
        
        # Add module-specific arguments
        parser.add_argument('--filter', choices=['all', 'active', 'sysop'],
                          help='Filter results by type')
        parser.add_argument('--verbose', action='store_true',
                          help='Show detailed output')
        
        return parser
    
    def access(args, op, **kwargs):
        return True
    
    def main(args, **kwargs):
        # Access custom arguments via args.filter, args.verbose
        filter_type = getattr(args, 'filter', 'all')
        verbose = getattr(args, 'verbose', False)
        
        if verbose:
            print(f"Running with filter: {filter_type}")
        
        # ... module logic
    
    # Usage:
    # zoidoffice mytest --filter sysop --verbose
    # zoidoffice mytest --help  # Shows custom --filter and --verbose args

Modules that don't define custom arguments will work as before.
"""


def handle_subcommand(args, subcommand, **kwargs):
    """
    Route to appropriate module based on subcommand.

    Args:
        args: Parsed arguments namespace
        subcommand: Name of subcommand (module) to run
        argv: Optional list of arguments to pass to the module's buildargs()
              These are the arguments that come AFTER the subcommand name.
              Example: "zoidoffice member --filter sysop"
              → subcommand="member", argv=["--filter", "sysop"]

    Returns:
        bool: True if successful, False on error
    """
    if subcommand == "member":
        return runmodule(args, "member", **kwargs)
    elif subcommand == "session":
        return runmodule(args, "session", **kwargs)
    elif subcommand == "memberapproval":
        return runmodule(args, "memberapproval", **kwargs)
    else:
        io.echo(f"Unknown subcommand: {subcommand}", level="error")
        return False
