"""FastMCP server entry point — registers all SAP tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from sap_mcp.tools import generic_rfc, invoices, master_data, purchasing, sales

mcp = FastMCP(
    "SAP ECC RFC Server",
    instructions=(
        "This server provides tools to interact with SAP ECC via RFC. "
        "Use master data tools to look up materials, customers, and vendors. "
        "Use sales/purchasing tools to read or create orders. "
        "Use read_table to query any SAP table, and call_rfc for any function module. "
        "Numbers are automatically padded with leading zeros where needed."
    ),
)

# Register all tool modules
generic_rfc.register(mcp)
master_data.register(mcp)
sales.register(mcp)
purchasing.register(mcp)
invoices.register(mcp)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
