"""Invoice tools: read-only invoice queries."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from sap_mcp.bapi.table import query_table
from sap_mcp.connection.manager import pool as default_pool
from sap_mcp.connection.manager import ConnectionManager


def register(mcp: FastMCP, pool: ConnectionManager = default_pool) -> None:

    @mcp.tool()
    def get_invoices(
        company_code: str = "",
        date_from: str = "",
        date_to: str = "",
        reference_document: str = "",
    ) -> dict:
        """Search SD billing documents (invoices) by company code, date, or source order."""
        with pool.acquire() as conn:
            # reference_document = the originating sales order -> resolve via VBRP-AUBEL
            if reference_document:
                items = query_table(
                    conn, "VBRP",
                    ["VBELN", "POSNR", "AUBEL", "MATNR", "ARKTX", "FKIMG", "NETWR"],
                    [f"AUBEL = '{reference_document.zfill(10)}'"],
                )
                return {"invoices": items, "count": len(items)}

            where = []
            if company_code:
                where.append(f"BUKRS = '{company_code}'")
            if date_from and date_to:
                where.append(f"FKDAT >= '{date_from}' AND FKDAT <= '{date_to}'")
            elif date_from:
                where.append(f"FKDAT >= '{date_from}'")
            headers = query_table(
                conn, "VBRK",
                ["VBELN", "FKART", "FKDAT", "KUNAG", "NETWR", "MWSBK", "WAERK", "VBTYP"],
                [" AND ".join(where)] if where else None,
                max_rows=200,
            )
        return {"invoices": headers, "count": len(headers)}
