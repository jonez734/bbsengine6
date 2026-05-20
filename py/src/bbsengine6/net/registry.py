# internet/registry.py
# Machine registry for managing remote machine configurations.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import psycopg
from psycopg import sql

from bbsengine6 import database

logger = None  # Lazy import to avoid circular dependencies


def get_logger():
    """Get logger lazily."""
    global logger
    if logger is None:
        import logging

        logger = logging.getLogger(__name__)
    return logger


@dataclass
class MachineConfig:
    """Configuration for a remote machine."""

    machine_name: str
    host: str
    port: int
    auth_token: Optional[str] = None
    tls_enabled: bool = False
    verify_cert: bool = True

    def ws_url(self) -> str:
        """Generate WebSocket URL for this machine."""
        protocol = "wss" if self.tls_enabled else "ws"
        return f"{protocol}://{self.host}:{self.port}/notify"


class MachineRegistry:
    """Registry for managing remote machine configurations."""

    def __init__(self, dbname: str = "bbsengine6"):
        """
        Initialize registry.

        Args:
            dbname: Database name for machine configs
        """
        self.dbname = dbname
        self._cache: Dict[str, MachineConfig] = {}
        self._cache_valid = False

    def _get_connection(self) -> Any:
        """Get database connection."""
        return psycopg.connect(f"dbname={self.dbname}")

    def _ensure_table(self, conn: Any) -> None:
        """Ensure machine_registry table exists."""
        with database.cursor(conn) as cur:
            cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS postoffice.machine_registry (
                        machine_name TEXT PRIMARY KEY,
                        host TEXT NOT NULL,
                        port INTEGER NOT NULL DEFAULT 8765,
                        auth_token TEXT,
                        tls_enabled BOOLEAN DEFAULT FALSE,
                        verify_cert BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
            )
        conn.commit()

    def register(
        self,
        machine_name: str,
        host: str,
        port: int = 8765,
        auth_token: Optional[str] = None,
        tls_enabled: bool = False,
        verify_cert: bool = True,
        conn: Optional[Any] = None,
    ) -> bool:
        """
        Register a remote machine.

        Args:
            machine_name: Machine identifier
            host: Hostname or IP address
            port: WebSocket port (default 8765)
            auth_token: Authentication token (optional)
            tls_enabled: Whether to use WSS (default False)
            verify_cert: Whether to verify TLS certificate (default True)
            conn: Database connection (creates new if None)

        Returns:
            True on success, False on error
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            self._ensure_table(conn)

            with database.cursor(conn) as cur:
                cur.execute(
                    sql.SQL(
                        """
                        INSERT INTO postoffice.machine_registry
                        (machine_name, host, port, auth_token, tls_enabled, verify_cert)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (machine_name) DO UPDATE SET
                            host = EXCLUDED.host,
                            port = EXCLUDED.port,
                            auth_token = EXCLUDED.auth_token,
                            tls_enabled = EXCLUDED.tls_enabled,
                            verify_cert = EXCLUDED.verify_cert,
                            updated_at = NOW()
                        """
                    ),
                    (machine_name, host, port, auth_token, tls_enabled, verify_cert),
                )
            conn.commit()

            # Invalidate cache
            self._cache_valid = False

            get_logger().info(f"Registered machine: {machine_name} @ {host}:{port}")
            return True

        except Exception as e:
            get_logger().error(f"Failed to register machine {machine_name}: {e}")
            return False
        finally:
            if should_close:
                try:
                    conn.close()
                except Exception:
                    pass

    def get(
        self, machine_name: str, conn: Optional[Any] = None
    ) -> Optional[MachineConfig]:
        """
        Get machine configuration.

        Args:
            machine_name: Machine identifier
            conn: Database connection (creates new if None)

        Returns:
            MachineConfig if found, None otherwise
        """
        # Check cache first
        if self._cache_valid and machine_name in self._cache:
            return self._cache[machine_name]

        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            self._ensure_table(conn)

            with database.cursor(conn) as cur:
                cur.execute(
                    sql.SQL(
                        """
                        SELECT machine_name, host, port, auth_token, tls_enabled, verify_cert
                        FROM postoffice.machine_registry
                        WHERE machine_name = %s
                        """
                    ),
                    (machine_name,),
                )

                row = cur.fetchone()
                if not row:
                    return None

                config = MachineConfig(
                    machine_name=row[0],
                    host=row[1],
                    port=row[2],
                    auth_token=row[3],
                    tls_enabled=row[4],
                    verify_cert=row[5],
                )

                # Cache it
                self._cache[machine_name] = config
                return config

        except Exception as e:
            get_logger().error(f"Failed to get machine config for {machine_name}: {e}")
            return None
        finally:
            if should_close:
                try:
                    conn.close()
                except Exception:
                    pass

    def list_all(self, conn: Optional[Any] = None) -> List[MachineConfig]:
        """
        List all registered machines.

        Args:
            conn: Database connection (creates new if None)

        Returns:
            List of MachineConfig objects
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            self._ensure_table(conn)

            with database.cursor(conn) as cur:
                cur.execute(
                    sql.SQL(
                        """
                        SELECT machine_name, host, port, auth_token, tls_enabled, verify_cert
                        FROM postoffice.machine_registry
                        ORDER BY machine_name
                        """
                    )
                )

                configs = []
                for row in cur.fetchall():
                    config = MachineConfig(
                        machine_name=row[0],
                        host=row[1],
                        port=row[2],
                        auth_token=row[3],
                        tls_enabled=row[4],
                        verify_cert=row[5],
                    )
                    configs.append(config)

                return configs

        except Exception as e:
            get_logger().error(f"Failed to list machines: {e}")
            return []
        finally:
            if should_close:
                try:
                    conn.close()
                except Exception:
                    pass

    def unregister(self, machine_name: str, conn: Optional[Any] = None) -> bool:
        """
        Unregister a machine.

        Args:
            machine_name: Machine identifier
            conn: Database connection (creates new if None)

        Returns:
            True on success, False on error
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            self._ensure_table(conn)

            with database.cursor(conn) as cur:
                cur.execute(
                    sql.SQL(
                        """
                        DELETE FROM postoffice.machine_registry
                        WHERE machine_name = %s
                        """
                    ),
                    (machine_name,),
                )
            conn.commit()

            # Invalidate cache
            self._cache_valid = False
            self._cache.pop(machine_name, None)

            get_logger().info(f"Unregistered machine: {machine_name}")
            return True

        except Exception as e:
            get_logger().error(f"Failed to unregister machine {machine_name}: {e}")
            return False
        finally:
            if should_close:
                try:
                    conn.close()
                except Exception:
                    pass

    def refresh_cache(self, conn: Optional[Any] = None) -> None:
        """Refresh cache from database."""
        self._cache = {}
        machines = self.list_all(conn)
        for machine in machines:
            self._cache[machine.machine_name] = machine
        self._cache_valid = True


# Module-level instance
_default_registry: Optional[MachineRegistry] = None


def get_registry(dbname: str = "bbsengine6") -> MachineRegistry:
    """Get or create default machine registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = MachineRegistry(dbname)
    return _default_registry
