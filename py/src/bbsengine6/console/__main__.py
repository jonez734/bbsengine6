from bbsengine6 import io, screen

# Import argcomplete for shell completion (optional - continues if not installed)
try:
    import argcomplete

    ARGCOMPLETE_AVAILABLE = True
except ImportError:
    ARGCOMPLETE_AVAILABLE = False

from . import lib

if __name__ == "__main__":
    # Build parser with subcommands
    parser, subparsers = lib.build_subcommand_parser()

    # Enable argcomplete for shell completion (if available)
    if ARGCOMPLETE_AVAILABLE:
        argcomplete.autocomplete(parser)

    # Parse arguments - use parse_known_args to separate subcommand from its args
    # This allows modules to receive their own arguments after the subcommand name
    args, remaining_argv = parser.parse_known_args()

    screen.init()
    lib.setbottombar(args, "con")

    try:
        # Route based on subcommand
        if args.subcommand:
            # Subcommand specified: run that module with remaining args
            if (
                lib.handle_subcommand(args, args.subcommand, argv=remaining_argv)
                is False
            ):
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
