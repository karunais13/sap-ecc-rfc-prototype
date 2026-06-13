"""Thread-safe SAP RFC connection pool."""

from __future__ import annotations

import threading
from collections import deque
from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator

from sap_mcp.config import settings
from sap_mcp.connection.mock import MockConnection

if TYPE_CHECKING:
    pass

# Union type for real or mock connections
Connection = object


class ConnectionManager:
    """Thread-safe connection pool for SAP RFC connections.

    Each manager is bound to one SAP system config (a country). The config only
    needs `mock_mode`, `connection_params()` and `connection_pool_size` — both
    SAPSettings and SAPConfig satisfy this. Defaults to the env `settings`
    singleton for backward compatibility (stdio mode / tests).
    """

    def __init__(self, config=None, pool_size: int | None = None) -> None:
        self._config = config or settings
        self._pool_size = pool_size or self._config.connection_pool_size
        self._pool: deque[Connection] = deque()
        self._lock = threading.Lock()
        self._created = 0

    def _create_connection(self) -> Connection:
        if self._config.mock_mode:
            return MockConnection(**self._config.connection_params())
        try:
            from pyrfc import Connection as RealConnection
            return RealConnection(**self._config.connection_params())
        except ImportError as exc:
            raise RuntimeError(
                "pyrfc is not installed. Install with: uv pip install 'sap-mcp[sap]' "
                "or set SAP_MOCK_MODE=true"
            ) from exc

    @contextmanager
    def acquire(self) -> Generator[Connection, None, None]:
        conn = self._checkout()
        try:
            yield conn
            self._checkin(conn)
        except Exception:
            self._discard(conn)
            raise

    def _checkout(self) -> Connection:
        with self._lock:
            while self._pool:
                conn = self._pool.popleft()
                if self._is_alive(conn):
                    return conn
                self._created -= 1

            if self._created < self._pool_size:
                self._created += 1
                return self._create_connection()

        # Pool exhausted — block until one is returned (simple spin)
        import time
        while True:
            with self._lock:
                if self._pool:
                    conn = self._pool.popleft()
                    if self._is_alive(conn):
                        return conn
                    self._created -= 1
                if self._created < self._pool_size:
                    self._created += 1
                    return self._create_connection()
            time.sleep(0.05)

    def _checkin(self, conn: Connection) -> None:
        with self._lock:
            self._pool.append(conn)

    def _discard(self, conn: Connection) -> None:
        try:
            if hasattr(conn, "close"):
                conn.close()
        except Exception:
            pass
        with self._lock:
            self._created -= 1

    def _is_alive(self, conn: Connection) -> bool:
        if hasattr(conn, "alive"):
            return bool(conn.alive)
        return True

    def close_all(self) -> None:
        with self._lock:
            while self._pool:
                conn = self._pool.popleft()
                try:
                    if hasattr(conn, "close"):
                        conn.close()
                except Exception:
                    pass
            self._created = 0


# Module-level singleton
pool = ConnectionManager()
