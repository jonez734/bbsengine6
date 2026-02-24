from bbsengine6 import io, screen, session, database
import sys
import argparse

from . import lib

if __name__ == "__main__":
    # Build parser with subcommands
    parser, subparsers = lib.build_subcommand_parser()
    
    # Parse arguments
    args = parser.parse_args()
    
    screen.init()
    lib.setbottombar(args, "con")
    
    try:
        # Route based on subcommand
        if args.subcommand:
            # Subcommand specified: run that module
            if lib.handle_subcommand(args, args.subcommand) is False:
                io.echo(f"error running module {args.subcommand}", level="error")
                # Return to menu instead of exit
        else:
            # No subcommand: show interactive menu (current behavior)
            if lib.runmodule(args, "main") is False:
                io.echo(f"error running module main", level="error")
                # Return to menu instead of exit
                
    except EOFError:
        io.echo("**EOF**")
    except KeyboardInterrupt:
        io.echo("**INTR**")
    finally:
        io.echo(f"{{decsc}}{{curpos:{io.terminal.height()},0}}{{el}}{{reset}}{{decrc}}")
