"""Master data tools: materials, customers, vendors."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from sap_mcp.bapi.return_handler import parse_return
from sap_mcp.bapi.table import query_table
from sap_mcp.connection.manager import pool as default_pool
from sap_mcp.connection.manager import ConnectionManager


def _pad_material(number: str) -> str:
    """Format a material number for SAP internal use.

    Numeric material numbers are stored zero-padded to 18 chars; alphanumeric
    (lexical) numbers are stored left-justified, UPPERCASE, with NO padding.
    Blindly zfill-ing corrupts alphanumeric matnr (e.g. CC132 -> 0000000000000CC132).
    """
    n = number.strip().upper()
    return n.zfill(18) if n.isdigit() else n


def _pad_partner(number: str) -> str:
    return number.zfill(10)


def register(mcp: FastMCP, pool: ConnectionManager = default_pool) -> None:

    @mcp.tool()
    def get_material(material_number: str) -> dict:
        """Read material master data by material number.

        Args:
            material_number: SAP material number (will be padded with leading zeros)

        Returns:
            Material general data including description, type, unit of measure, weights.
        """
        n = material_number.strip().upper()
        if len(n) > 18:                       # S/4 long material number
            kwargs = {"MATERIAL_LONG": n}
        else:
            kwargs = {"MATERIAL": _pad_material(n)}
        with pool.acquire() as conn:
            result = conn.call("BAPI_MATERIAL_GET_DETAIL", **kwargs)
        bapi = parse_return(result.get("RETURN"))
        if not bapi.success:
            return {"error": bapi.summary}
        return {"material": result.get("MATERIAL_GENERAL_DATA", {})}

    @mcp.tool()
    def search_materials(description: str = "", material_type: str = "") -> dict:
        """Search materials by description (MAKT) and/or material type (MARA)."""
        with pool.acquire() as conn:
            if description:
                rows = query_table(
                    conn, "MAKT",
                    ["MATNR", "MAKTX", "SPRAS"],
                    [f"MAKTX LIKE '%{description.upper()}%' AND SPRAS = 'E'"],
                    max_rows=50,
                )
            else:
                rows = []
            if material_type:
                mat = query_table(
                    conn, "MARA", ["MATNR", "MTART", "MEINS"],
                    [f"MTART = '{material_type.upper()}'"], max_rows=50,
                )
                if description:                       # intersect by MATNR
                    keep = {r["MATNR"] for r in mat}
                    rows = [r for r in rows if r["MATNR"] in keep]
                else:
                    rows = mat
        return {"materials": rows, "count": len(rows)}

    @mcp.tool()
    def get_customer(customer_number: str) -> dict:
        """Read customer master data by customer number.

        Args:
            customer_number: SAP customer number (will be padded with leading zeros)

        Returns:
            Customer general data including name, address, country.
        """
        padded = _pad_partner(customer_number)
        with pool.acquire() as conn:
            result = conn.call("BAPI_CUSTOMER_GETDETAIL2", CUSTOMERNO=padded)
        bapi = parse_return(result.get("RETURN"))
        if not bapi.success:
            return {"error": bapi.summary}
        return {"customer": result.get("CUSTOMERGENERALDETAIL", {})}

    @mcp.tool()
    def search_customers(name: str = "", city: str = "") -> dict:
        """Search customers by name and/or city (KNA1; descriptions stored UPPERCASE)."""
        where = []
        if name:
            where.append(f"NAME1 LIKE '%{name.upper()}%'")
        if city:
            where.append(f"ORT01 LIKE '%{city.upper()}%'")
        with pool.acquire() as conn:
            rows = query_table(
                conn, "KNA1",
                ["KUNNR", "NAME1", "ORT01", "LAND1", "STCD1"],
                [" AND ".join(where)] if where else None,
                max_rows=50,
            )
        return {"customers": rows, "count": len(rows)}

    @mcp.tool()
    def get_vendor(vendor_number: str) -> dict:
        """Read vendor master data by vendor number.

        Args:
            vendor_number: SAP vendor number (will be padded with leading zeros)

        Returns:
            Vendor general data including name, address, country.
        """
        padded = _pad_partner(vendor_number)
        with pool.acquire() as conn:
            result = conn.call("BAPI_VENDOR_GETDETAIL", VENDORNO=padded)
        bapi = parse_return(result.get("RETURN"))
        if not bapi.success:
            return {"error": bapi.summary}
        return {"vendor": result.get("GENERALDETAIL", {})}

    @mcp.tool()
    def search_vendors(name: str = "") -> dict:
        """Search vendors by name (LFA1; descriptions stored UPPERCASE)."""
        where = [f"NAME1 LIKE '%{name.upper()}%'"] if name else None
        with pool.acquire() as conn:
            rows = query_table(
                conn, "LFA1",
                ["LIFNR", "NAME1", "ORT01", "LAND1", "STCD1"],
                where, max_rows=50,
            )
        return {"vendors": rows, "count": len(rows)}
