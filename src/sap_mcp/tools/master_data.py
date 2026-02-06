"""Master data tools: materials, customers, vendors."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from sap_mcp.bapi.return_handler import parse_return
from sap_mcp.connection.manager import pool


def _pad_material(number: str) -> str:
    return number.zfill(18)


def _pad_partner(number: str) -> str:
    return number.zfill(10)


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_material(material_number: str) -> dict:
        """Read material master data by material number.

        Args:
            material_number: SAP material number (will be padded with leading zeros)

        Returns:
            Material general data including description, type, unit of measure, weights.
        """
        padded = _pad_material(material_number)
        with pool.acquire() as conn:
            result = conn.call("BAPI_MATERIAL_GET_DETAIL", MATERIAL=padded)
        bapi = parse_return(result.get("RETURN"))
        if not bapi.success:
            return {"error": bapi.summary}
        return {"material": result.get("MATERIAL_GENERAL_DATA", {})}

    @mcp.tool()
    def search_materials(description: str = "", material_type: str = "") -> dict:
        """Search for materials by description or type.

        Args:
            description: Material description search term
            material_type: Material type (e.g. 'ROH' for raw, 'FERT' for finished)

        Returns:
            List of matching materials with number and description.
        """
        selection = []
        if description:
            selection.append({"SIGN": "I", "OPTION": "CP", "LOW": f"*{description}*"})
        with pool.acquire() as conn:
            result = conn.call(
                "BAPI_MATERIAL_GETLIST",
                MATNR_RA=selection if selection else [],
                MATERIAL_DESCRIPTION=description,
            )
        bapi = parse_return(result.get("RETURN"))
        materials = result.get("MATNRLIST", [])
        return {"materials": materials, "count": len(materials)}

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
        """Search for customers by name or city.

        Args:
            name: Customer name search term
            city: City search term

        Returns:
            List of matching customers with number, name, city, country.
        """
        with pool.acquire() as conn:
            result = conn.call("BAPI_CUSTOMER_GETLIST", NAME=name, CITY=city)
        customers = result.get("ADDRESSDATA", [])
        return {"customers": customers, "count": len(customers)}

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
        """Search for vendors by name.

        Args:
            name: Vendor name search term

        Returns:
            List of matching vendors with number, name, city, country.
        """
        with pool.acquire() as conn:
            result = conn.call("BAPI_VENDOR_GETLIST", NAME=name)
        vendors = result.get("VENDORS", [])
        return {"vendors": vendors, "count": len(vendors)}
