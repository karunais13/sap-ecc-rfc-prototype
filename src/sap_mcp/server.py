"""FastMCP server entry point.

Two transports:
  - "stdio" (default): one SAP system from the SAP_ env vars, for local clients.
  - "streamable-http": one FastMCP instance per country, each with its own SAP
    connection pool, mounted at /mcp/{country_code} in a single ASGI app so a
    reverse proxy can forward /mcp/* to this container.
"""

from __future__ import annotations

import contextlib
import os
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from sap_mcp.config import load_countries
from sap_mcp.connection.manager import ConnectionManager
from sap_mcp.tools import generic_rfc, invoices, master_data, purchasing, sales

TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8000"))
PATH = os.getenv("MCP_PATH", "/mcp")

_INSTRUCTIONS = (
    "This server provides tools to interact with SAP ECC via RFC. "
    "Use master data tools to look up materials, customers, and vendors. "
    "Use sales/purchasing tools to read or create orders. "
    "Use read_table to query any SAP table, and call_rfc for any function module. "
    "Numbers are automatically padded with leading zeros where needed."
)


def _build_mcp(name: str, pool: ConnectionManager, streamable_http_path: str) -> FastMCP:
    """Create a FastMCP instance with all SAP tools bound to one connection pool."""
    mcp = FastMCP(
        name,
        instructions=_INSTRUCTIONS,
        host=HOST,
        port=PORT,
        streamable_http_path=streamable_http_path,
    )
    generic_rfc.register(mcp, pool)
    master_data.register(mcp, pool)
    sales.register(mcp, pool)
    purchasing.register(mcp, pool)
    invoices.register(mcp, pool)
    return mcp


# Default single-system server (stdio mode / Claude Desktop). Uses env settings.
mcp = _build_mcp("SAP ECC RFC Server", ConnectionManager(), PATH)


def _build_http_app():
    """Build a Starlette app mounting one FastMCP per country at /mcp/{code}."""
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    countries = load_countries()

    routes = []
    session_managers = []
    for code, cfg in countries.items():
        pool = ConnectionManager(config=cfg)
        path = f"{PATH}/{code}"
        country_mcp = _build_mcp(f"SAP ECC RFC Server [{code.upper()}]", pool, path)
        sub_app = country_mcp.streamable_http_app()  # creates the session manager
        # Pull the country's route(s) into the parent app at the exact path.
        routes.extend(sub_app.routes)
        session_managers.append(country_mcp.session_manager)

    served = sorted(countries.keys())

    async def healthz(_request):
        return JSONResponse({"status": "ok", "countries": served})

    routes.append(Route("/healthz", healthz, methods=["GET"]))

    @asynccontextmanager
    async def lifespan(_app):
        async with contextlib.AsyncExitStack() as stack:
            for manager in session_managers:
                await stack.enter_async_context(manager.run())
            yield

    return Starlette(routes=routes, lifespan=lifespan)


def main() -> None:
    if TRANSPORT == "streamable-http":
        import uvicorn

        uvicorn.run(_build_http_app(), host=HOST, port=PORT)
    else:
        mcp.run(transport=TRANSPORT)


if __name__ == "__main__":
    main()
