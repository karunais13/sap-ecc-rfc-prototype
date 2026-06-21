"""Purchasing tools: get, search, create purchase orders."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from sap_mcp.bapi.return_handler import parse_return
from sap_mcp.bapi.transaction import execute_bapi_with_commit
from sap_mcp.connection.manager import pool as default_pool
from sap_mcp.connection.manager import ConnectionManager
from sap_mcp.tools.master_data import _pad_material


def _pad_po(number: str) -> str:
    return number.zfill(10)


def register(mcp: FastMCP, pool: ConnectionManager = default_pool) -> None:

    @mcp.tool()
    def get_purchase_order(purchase_order_number: str) -> dict:
        """Read a purchase order header and line items.

        Args:
            purchase_order_number: SAP purchase order number

        Returns:
            PO header and items.
        """
        padded = _pad_po(purchase_order_number)
        with pool.acquire() as conn:
            result = conn.call("BAPI_PO_GETDETAIL1", PURCHASEORDER=padded)
        bapi = parse_return(result.get("RETURN"))
        if not bapi.success:
            return {"error": bapi.summary}
        return {
            "header": result.get("POHEADER", {}),
            "items": result.get("POITEM", []),
        }

    @mcp.tool()
    def search_purchase_orders(
        vendor_number: str = "",
        date_from: str = "",
        date_to: str = "",
    ) -> dict:
        """Search purchase orders by vendor and/or date range.

        Args:
            vendor_number: SAP vendor number (optional)
            date_from: Start date YYYYMMDD (optional)
            date_to: End date YYYYMMDD (optional)

        Returns:
            List of matching purchase order items.
        """
        params: dict[str, Any] = {}
        if vendor_number:
            params["VENDOR"] = vendor_number.zfill(10)
        if date_from:
            params["DOC_DATE"] = date_from     # BAPI supports an exact date only
        with pool.acquire() as conn:
            result = conn.call("BAPI_PO_GETITEMS", **params)
        items = result.get("PO_ITEMS", [])
        return {"purchase_order_items": items, "count": len(items)}

    @mcp.tool()
    def create_purchase_order(
        vendor_number: str,
        purchasing_org: str,
        purchasing_group: str,
        company_code: str,
        items: list[dict[str, Any]],
        doc_type: str = "NB",
    ) -> dict:
        """Create a new purchase order in SAP.

        Args:
            vendor_number: Vendor number
            purchasing_org: Purchasing organization (e.g. '1000')
            purchasing_group: Purchasing group (e.g. '001')
            company_code: Company code (e.g. '1000')
            items: List of line items, each with keys:
                - material: Material number
                - quantity: Order quantity
                - plant: Receiving plant
                - net_price: Net price per unit (optional)
            doc_type: PO document type (default 'NB' for standard)

        Returns:
            Created PO number or error details.
        """
        header = {
            "DOC_TYPE": doc_type,
            "VENDOR": vendor_number.zfill(10),
            "PURCH_ORG": purchasing_org,
            "PUR_GROUP": purchasing_group,
            "COMP_CODE": company_code,
        }

        po_items = []
        for i, item in enumerate(items):
            itm: dict[str, Any] = {
                "PO_ITEM": str((i + 1) * 10).zfill(5),
                "MATERIAL": _pad_material(item["material"]),
                "QUANTITY": str(item["quantity"]),
                "PLANT": item["plant"],
            }
            if "net_price" in item:
                itm["NET_PRICE"] = str(item["net_price"])
            po_items.append(itm)

        with pool.acquire() as conn:
            result, bapi = execute_bapi_with_commit(
                conn,
                "BAPI_PO_CREATE1",
                PO_HEADER=header,
                PO_ITEMS=po_items,
            )

        if not bapi.success:
            return {"error": bapi.summary, "messages": bapi.messages}

        return {
            "purchase_order": result.get("PURCHASEORDER", ""),
            "message": bapi.summary,
        }
