# notifyd/daemon.py
# Main daemon process and lifecycle management

from __future__ import annotations

import logging
import signal
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Global daemon instance
_global_daemon: Optional[NotifyDaemon] = None


class DaemonError(Exception):
    """Raised when daemon operation fails"""

    pass


def start_daemon(config: Dict[str, Any]) -> NotifyDaemon:
    """
    Start notification daemon with given configuration.

    Args:
        config: Configuration dictionary from load_config()

    Returns:
        NotifyDaemon instance

    Raises:
        DaemonError: If daemon fails to start
    """
    global _global_daemon

    try:
        daemon = NotifyDaemon(config)
        daemon.start()
        _global_daemon = daemon
        return daemon
    except Exception as e:
        raise DaemonError(f"Failed to start daemon: {e}") from e


def stop_daemon(daemon: Optional[NotifyDaemon] = None) -> None:
    """
    Stop notification daemon gracefully.

    Args:
        daemon: NotifyDaemon instance (if None, uses global)
    """
    global _global_daemon

    target = daemon or _global_daemon
    if target is not None:
        target.stop()
        if target is _global_daemon:
            _global_daemon = None


def is_running(daemon: Optional[NotifyDaemon] = None) -> bool:
    """
    Check if daemon is running.

    Args:
        daemon: NotifyDaemon instance (if None, uses global)

    Returns:
        True if daemon running
    """
    target = daemon or _global_daemon
    return target is not None and target.running


class NotifyDaemon:
    """
    Main daemon process.

    Responsibilities:
        1. Load configuration
        2. Initialize components (storage, monitor, listener, dispatcher)
        3. Spawn background threads
        4. Handle signals (SIGTERM, SIGINT)
        5. Graceful shutdown with thread cleanup
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize daemon.

        Args:
            config: Configuration dictionary from load_config()
        """
        self.config = config
        self.running = False
        self._threads: list[threading.Thread] = []
        self._lock = threading.RLock()
        self._stop_event = threading.Event()

    def start(self) -> None:
        """
        Start daemon.

        Spawns background threads and enters main loop.
        """
        with self._lock:
            if self.running:
                logger.warning("Daemon already running")
                return

            self.running = True
            self._stop_event.clear()

        try:
            # Setup signal handlers
            signal.signal(signal.SIGTERM, self._handle_signal)
            signal.signal(signal.SIGINT, self._handle_signal)

            # Spawn monitor thread
            monitor_thread = threading.Thread(
                target=self._monitor_loop, name="notifyd-monitor", daemon=False
            )
            monitor_thread.start()
            self._threads.append(monitor_thread)

            logger.info("Daemon started")

            # Wait for stop signal
            self._stop_event.wait()

        except Exception as e:
            logger.error(f"Error starting daemon: {e}", exc_info=True)
            with self._lock:
                self.running = False
            raise
        finally:
            self._cleanup()

    def stop(self) -> None:
        """
        Stop daemon gracefully.

        Sets stop event and joins threads.
        """
        with self._lock:
            if not self.running:
                logger.warning("Daemon not running")
                return

            self.running = False

        logger.info("Stopping daemon")
        self._stop_event.set()

        # Join threads with timeout
        self._join_threads(timeout=5.0)

    def _handle_signal(self, signum: int, frame: Any) -> None:
        """
        Handle SIGTERM/SIGINT signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, stopping")
        self.stop()

    def _monitor_loop(self) -> None:
        """
        IMAP polling background thread.

        Periodically polls IMAP servers for new emails.
        Runs until _stop_event is set.
        """
        logger.debug("Monitor loop started")

        try:
            while self.running and not self._stop_event.is_set():
                try:
                    # Sleep for configured interval
                    poll_interval = (
                        self.config.get("imap_servers", [{}])[0].get(
                            "poll_interval", 30
                        )
                        if self.config.get("imap_servers")
                        else 30
                    )

                    if self._stop_event.wait(timeout=poll_interval):
                        # Stop event was set, exit
                        break

                    # Poll IMAP servers
                    logger.debug("Polling IMAP servers")
                    # TODO: Integrate with imap_monitor.poll_imap_all_mailboxes()

                except Exception as e:
                    logger.error(f"Error in monitor loop: {e}", exc_info=True)
                    # Continue on error
                    continue

        finally:
            logger.debug("Monitor loop stopped")

    def _cleanup(self) -> None:
        """Clean up resources and join threads."""
        self._join_threads(timeout=5.0)
        logger.info("Daemon stopped")

    def _join_threads(self, timeout: float = 5.0) -> None:
        """
        Join all spawned threads.

        Args:
            timeout: Maximum time to wait per thread
        """
        for thread in self._threads:
            if thread.is_alive():
                logger.debug(f"Waiting for thread {thread.name}")
                thread.join(timeout=timeout)

                if thread.is_alive():
                    logger.warning(f"Thread {thread.name} did not stop within timeout")
