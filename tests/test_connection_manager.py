"""Tests for connection manager."""

from __future__ import annotations

import threading

from sap_mcp.connection.manager import ConnectionManager
from sap_mcp.connection.mock import MockConnection


class TestConnectionManager:

    def test_acquire_returns_mock_connection(self):
        mgr = ConnectionManager(pool_size=2)
        with mgr.acquire() as conn:
            assert isinstance(conn, MockConnection)
            assert conn.alive

    def test_connection_reuse(self):
        mgr = ConnectionManager(pool_size=2)
        with mgr.acquire() as conn1:
            id1 = id(conn1)
        with mgr.acquire() as conn2:
            id2 = id(conn2)
        assert id1 == id2, "Connection should be reused from pool"

    def test_connection_discarded_on_error(self):
        mgr = ConnectionManager(pool_size=2)
        try:
            with mgr.acquire() as conn:
                id1 = id(conn)
                raise ValueError("boom")
        except ValueError:
            pass
        with mgr.acquire() as conn2:
            assert id(conn2) != id1, "Should get a new connection after error"

    def test_pool_limit(self):
        mgr = ConnectionManager(pool_size=1)
        results = []
        barrier = threading.Barrier(2, timeout=2)

        def use_conn():
            with mgr.acquire() as conn:
                results.append(id(conn))
                try:
                    barrier.wait()
                except threading.BrokenBarrierError:
                    pass

        t1 = threading.Thread(target=use_conn)
        t2 = threading.Thread(target=use_conn)
        t1.start()
        t2.start()
        t1.join(timeout=3)
        t2.join(timeout=3)
        # Both threads should complete (second waits for first to return connection)
        assert len(results) == 2

    def test_close_all(self):
        mgr = ConnectionManager(pool_size=2)
        with mgr.acquire() as conn:
            pass
        mgr.close_all()
        # After close_all, new acquire should create fresh connection
        with mgr.acquire() as conn:
            assert isinstance(conn, MockConnection)

    def test_call_through_connection(self):
        mgr = ConnectionManager(pool_size=1)
        with mgr.acquire() as conn:
            result = conn.call("BAPI_MATERIAL_GET_DETAIL", MATERIAL="000000000000000100")
            assert "MATERIAL_GENERAL_DATA" in result
