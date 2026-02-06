"""Invoice tools: read-only invoice queries."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from sap_mcp.bapi.return_handler import parse_return
from sap_mcp.connection.manager import pool


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_invoices(
        company_code: str = "",
        date_from: str = "",
        date_to: str = "",
        reference_document: str = "",
    ) -> dict:
        """Search for invoices by company code, date range, or reference document.

        Args:
            company_code: Company code (e.g. '1000')
            date_from: Start date YYYYMMDD (optional)
            date_to: End date YYYYMMDD (optional)
            reference_document: Reference sales order number (optional)

        Returns:
            List of matching invoices.
        """
        params: dict[str, Any] = {}
        if company_code:
            params["COMP_CODE"] = company_code
        if date_from:
            params["DOC_DATE_FROM"] = date_from
        if date_to:
            params["DOC_DATE_TO"] = date_to
        if reference_document:
            params["REF_DOC"] = reference_document

        with pool.acquire() as conn:
            result = conn.call("BAPI_INCOMINGINVOICE_GETLIST", **params)
        bapi = parse_return(result.get("RETURN"))
        invoices = result.get("INVOICELIST", [])
        return {"invoices": invoices, "count": len(invoices)}
