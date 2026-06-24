# notify/daemon/cli.py
# Command-line interface for bbsengine6 notify daemon

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from . import config as config_module
from . import credentials as credentials_module
from . import daemon as daemon_module
from . import imap_monitor
from . import notification as notification_module


def setup_logging(level: str, logfile: Optional[str] = None) -> None:
    """
    Setup logging for CLI.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        logfile: Optional log file path
    """
    log_format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

    # File handler if specified
    if logfile:
        try:
            file_handler = logging.FileHandler(logfile)
            file_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(file_handler)
        except Exception as e:
            logging.error(f"Failed to open log file {logfile}: {e}")


def cmd_start(args: argparse.Namespace) -> int:
    """
    Start the daemon.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        cfg = config_module.load_config(args.config)
        daemon_module.start_daemon(cfg)
        return 0
    except Exception as e:
        logging.error(f"Failed to start daemon: {e}", exc_info=args.debug)
        return 1


def cmd_stop(args: argparse.Namespace) -> int:
    """
    Stop the daemon.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        daemon_module.stop_daemon()
        logging.info("Daemon stopped")
        return 0
    except Exception as e:
        logging.error(f"Failed to stop daemon: {e}", exc_info=args.debug)
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """
    Check daemon status.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 if running, 1 if not)
    """
    running = daemon_module.is_running()
    if running:
        print("Daemon is running")
        return 0
    else:
        print("Daemon is not running")
        return 1


def cmd_test_imap(args: argparse.Namespace) -> int:
    """
    Test IMAP connections.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        cfg = config_module.load_config(args.config)
        imap_servers = cfg.get("imap_servers", [])

        if not imap_servers:
            print("No IMAP servers configured")
            return 1

        success = True
        for server in imap_servers:
            try:
                host = server.get("host")
                port = server.get("port", 993)
                username = server.get("username")

                # Get password
                password = credentials_module.get_password(
                    server.get("name"),
                    username,
                    server.get("name"),
                    cfg.get("credentials", {}),
                )

                # Try to connect
                imap_conn = imap_monitor.connect_imap(host, port, username, password)
                imap_conn.logout()
                print(f"✓ {server.get('name')}: Connected successfully")

            except Exception as e:
                print(f"✗ {server.get('name')}: Failed - {e}")
                success = False

        return 0 if success else 1

    except Exception as e:
        logging.error(f"Test IMAP failed: {e}", exc_info=args.debug)
        return 1


def cmd_test_notify(args: argparse.Namespace) -> int:
    """
    Test notification sending.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        # Create a mock storage object for testing
        class MockStorage:
            _pool = None

            def record_notification(self, *args, **kwargs):
                pass

        dispatcher = notification_module.NotificationDispatcher(MockStorage())

        # Try to send a test notification
        result = dispatcher.send_custom_notification(
            event_type="test.notification",
            recipients=[args.recipient or "admin"],
            template="test-notification",
            urgency="ROUTINE",
            template_vars={"test": "true"},
        )

        if result is not None:
            print(f"✓ Notification sent: {result}")
            return 0
        else:
            print("✗ Notification failed to send")
            return 1

    except Exception as e:
        logging.error(f"Test notify failed: {e}", exc_info=args.debug)
        return 1


def main() -> int:
    """
    Main CLI entry point.

    Returns:
        Exit code
    """
    parser = argparse.ArgumentParser(
        prog="bbsengine6-notify-daemon",
        description="IMAP/Event notification daemon for bbsengine6",
    )

    parser.add_argument(
        "--config", help="Path to config.json (overrides defaults)", default=None
    )

    parser.add_argument("--logfile", help="Log file location", default=None)

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Start command
    subparsers.add_parser("start", help="Start the daemon")

    # Stop command
    subparsers.add_parser("stop", help="Stop the daemon")

    # Status command
    subparsers.add_parser("status", help="Check daemon status")

    # Test IMAP command
    subparsers.add_parser("test-imap", help="Test IMAP connections")

    # Test notify command
    test_notify_parser = subparsers.add_parser(
        "test-notify", help="Test notification sending"
    )
    test_notify_parser.add_argument(
        "--recipient", help="Recipient moniker for test notification", default=None
    )

    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(log_level, args.logfile)

    # Route to command handler
    if args.command == "start":
        return cmd_start(args)
    elif args.command == "stop":
        return cmd_stop(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "test-imap":
        return cmd_test_imap(args)
    elif args.command == "test-notify":
        return cmd_test_notify(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
