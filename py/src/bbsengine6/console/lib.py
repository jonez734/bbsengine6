import argparse

from bbsengine6 import io, database, session, screen, module

SQLDIR = "$HOME/projects/bbsengine6/sql/"

# @since 20230518 copied from teos
def buildargs(args=None, **kwargs):
    parser = argparse.ArgumentParser("con")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {"databasename": "zoid6", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None}
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
def build_subcommand_parser(parser=None, **kwargs):
    """
    Create or extend parser with subcommands for console modules.
    Uses argparse subparsers to add member, session, etc. as subcommands.
    
    Args:
        parser: Optional existing parser to extend
        
    Returns:
        tuple: (parser, subparsers)
    """
    if parser is None:
        parser = argparse.ArgumentParser(
            prog="zoidoffice",
            description="BBS Engine 6 Console - Manage your BBS system",
            add_help=True
        )
        parser.add_argument("--verbose", action="store_true", dest="verbose")
        parser.add_argument("--debug", action="store_true", dest="debug")
        
        defaults = {
            "databasename": "zoid6",
            "databasehost": "localhost",
            "databaseuser": None,
            "databaseport": 5432,
            "databasepassword": None
        }
        database.buildargs(parser, defaults)
    
    # Create subparsers for module commands
    subparsers = parser.add_subparsers(
        dest='subcommand',
        help='Available modules'
    )
    
    # Define subcommands explicitly
    subcommands = {
        'member': 'Manage BBS members',
        'session': 'Manage active sessions',
        'memberapproval': 'Approve new member applications'
    }
    
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
    if subcommand == 'member':
        return runmodule(args, 'member', **kwargs)
    elif subcommand == 'session':
        return runmodule(args, 'session', **kwargs)
    elif subcommand == 'memberapproval':
        return runmodule(args, 'memberapproval', **kwargs)
    else:
        io.echo(f"Unknown subcommand: {subcommand}", level="error")
        return False
