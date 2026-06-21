"""Sales order tools: get, search, create, change."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from sap_mcp.bapi.return_handler import parse_return
from sap_mcp.bapi.table import query_table
from sap_mcp.bapi.transaction import execute_bapi_with_commit
from sap_mcp.connection.manager import pool as default_pool
from sap_mcp.connection.manager import ConnectionManager
from sap_mcp.tools.master_data import _pad_material


def _pad_doc(number: str) -> str:
    return number.zfill(10)


def register(mcp: FastMCP, pool: ConnectionManager = default_pool) -> None:

    @mcp.tool()
    def get_sales_order(sales_order_number: str) -> dict:
        """Read a sales order header (VBAK) and items (VBAP)."""
        vbeln = sales_order_number.zfill(10)
        with pool.acquire() as conn:
            header = query_table(
                conn, "VBAK",
                ["VBELN", "AUART", "ERDAT", "KUNNR", "NETWR", "WAERK",
                 "VKORG", "VTWEG", "SPART", "BSTNK"],
                [f"VBELN = '{vbeln}'"],
            )
            items = query_table(
                conn, "VBAP",
                ["VBELN", "POSNR", "MATNR", "ARKTX", "KWMENG", "VRKME",
                 "NETWR", "WERKS", "PSTYV", "ABGRU"],
                [f"VBELN = '{vbeln}'"], max_rows=200,
            )
        if not header:
            return {"error": f"Sales order {vbeln} not found in VBAK"}
        return {"header": header[0], "items": items}

    @mcp.tool()
    def search_sales_orders(
        customer_number: str = "",
        date_from: str = "",
        date_to: str = "",
    ) -> dict:
        """Search sales orders by customer and/or date range.

        Args:
            customer_number: SAP customer number (optional)
            date_from: Start date YYYYMMDD (optional)
            date_to: End date YYYYMMDD (optional)

        Returns:
            List of matching sales orders.
        """
        params: dict[str, Any] = {}
        if customer_number:
            params["CUSTOMER_NUMBER"] = customer_number.zfill(10)
        if date_from:
            params["DOCUMENT_DATE"] = date_from
        if date_to:
            params["DOCUMENT_DATE_TO"] = date_to

        with pool.acquire() as conn:
            result = conn.call("BAPI_SALESORDER_GETLIST", **params)
        orders = result.get("SALES_ORDERS", [])
        return {"sales_orders": orders, "count": len(orders)}

    @mcp.tool()
    def create_sales_order(
        order_type: str,
        sales_org: str,
        distribution_channel: str,
        division: str,
        sold_to_party: str,
        purchase_order: str,
        items: list[dict[str, Any]],
    ) -> dict:
        """Create a new sales order in SAP.

        Args:
            order_type: Sales document type (e.g. 'TA' for standard)
            sales_org: Sales organization (e.g. '1000')
            distribution_channel: Distribution channel (e.g. '10')
            division: Division (e.g. '00')
            sold_to_party: Customer number of the buyer
            purchase_order: Customer's PO reference
            items: List of line items, each with keys:
                - material: Material number
                - quantity: Order quantity
                - plant: Delivering plant (optional)

        Returns:
            Created sales order number or error details.
        """
        header = {
            "DOC_TYPE": order_type,
            "SALES_ORG": sales_org,
            "DISTR_CHAN": distribution_channel,
            "DIVISION": division,
            "PURCH_NO_C": purchase_order,
        }
        partners = [
            {"PARTN_ROLE": "AG", "PARTN_NUMB": sold_to_party.zfill(10)},
        ]
        order_items = []
        for i, item in enumerate(items):
            itm = {
                "ITM_NUMBER": str((i + 1) * 10).zfill(6),
                "MATERIAL": _pad_material(item["material"]),
                "TARGET_QTY": str(item["quantity"]),
            }
            if "plant" in item:
                itm["PLANT"] = item["plant"]
            order_items.append(itm)

        with pool.acquire() as conn:
            result, bapi = execute_bapi_with_commit(
                conn,
                "BAPI_SALESORDER_CREATEFROMDAT2",
                ORDER_HEADER_IN=header,
                ORDER_PARTNERS=partners,
                ORDER_ITEMS_IN=order_items,
            )

        if not bapi.success:
            return {"error": bapi.summary, "messages": bapi.messages}

        return {
            "sales_order": result.get("SALESDOCUMENT", ""),
            "message": bapi.summary,
        }

    @mcp.tool()
    def change_sales_order(
        sales_order_number: str,
        items: list[dict[str, Any]] | None = None,
        header_changes: dict[str, Any] | None = None,
    ) -> dict:
        """Change an existing sales order.

        Args:
            sales_order_number: Sales document number to change
            items: List of item changes, each with keys:
                - item_number: Item number (e.g. '000010')
                - quantity: New quantity (optional)
                - material: New material (optional)
            header_changes: Dict of header fields to change (optional)

        Returns:
            Success or error message.
        """
        padded = _pad_doc(sales_order_number)
        params: dict[str, Any] = {"SALESDOCUMENT": padded}

        if header_changes:
            params["ORDER_HEADER_IN"] = header_changes
            params["ORDER_HEADER_INX"] = {
                k: "X" for k in header_changes
            }

        if items:
            order_items = []
            order_items_x = []
            for item in items:
                itm: dict[str, Any] = {"ITM_NUMBER": item["item_number"]}
                itm_x: dict[str, str] = {"ITM_NUMBER": item["item_number"]}
                if "quantity" in item:
                    itm["TARGET_QTY"] = str(item["quantity"])
                    itm_x["TARGET_QTY"] = "X"
                if "material" in item:
                    itm["MATERIAL"] = _pad_material(item["material"])
                    itm_x["MATERIAL"] = "X"
                order_items.append(itm)
                order_items_x.append(itm_x)
            params["ORDER_ITEM_IN"] = order_items
            params["ORDER_ITEM_INX"] = order_items_x

        with pool.acquire() as conn:
            result, bapi = execute_bapi_with_commit(
                conn,
                "BAPI_SALESORDER_CHANGE",
                **params,
            )

        if not bapi.success:
            return {"error": bapi.summary, "messages": bapi.messages}
        return {"message": bapi.summary}
