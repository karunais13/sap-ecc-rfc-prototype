"""Shared fixtures for tests."""

from __future__ import annotations

import os

import pytest

# Force mock mode for all tests
os.environ["SAP_MOCK_MODE"] = "true"


@pytest.fixture()
def mock_connection():
    from sap_mcp.connection.mock import MockConnection
    return MockConnection(ashost="test", sysnr="00", client="100")
