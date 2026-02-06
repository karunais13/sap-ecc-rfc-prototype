"""Integration test: check stock levels and auto-reorder when low.

Simulates what an AI agent would do:
1. Read stock from MARD table
2. Identify materials below a reorder threshold
3. Look up the preferred vendor
4. Create a purchase order for low-stock materials
"""

from __future__ import annotations

from sap_mcp.bapi.return_handler import parse_return
from sap_mcp.bapi.transaction import execute_bapi_with_commit
from sap_mcp.connection.manager import pool


REORDER_THRESHOLD = 100  # units — anything below this triggers reorder
REORDER_QUANTITY = 500   # how much to order


def _read_table_as_dicts(conn, table: str, fields: list[str], where: list[str] | None = None) -> list[dict]:
    """Helper: call RFC_READ_TABLE and parse into list of dicts."""
    params = {
        "QUERY_TABLE": table,
        "DELIMITER": "|",
        "ROWCOUNT": 100,
        "FIELDS": [{"FIELDNAME": f} for f in fields],
    }
    if where:
        params["OPTIONS"] = [{"TEXT": w} for w in where]
    result = conn.call("RFC_READ_TABLE", **params)
    field_info = result.get("FIELDS", [])
    field_names = [f["FIELDNAME"] for f in field_info]
    rows = []
    for row in result.get("DATA", []):
        vals = [v.strip() for v in row["WA"].split("|")]
        rows.append(dict(zip(field_names, vals)))
    return rows


class TestStockReorderFlow:

    def test_full_reorder_flow(self):
        """End-to-end: check stock → find low items → get vendor → create PO."""

        # Step 1: Check stock levels in plant 1000
        with pool.acquire() as conn:
            stock_rows = _read_table_as_dicts(
                conn, "MARD",
                fields=["MATNR", "WERKS", "LGORT", "LABST"],
            )

        assert len(stock_rows) == 3
        print(f"\n--- Stock Levels ---")
        for row in stock_rows:
            print(f"  Material {row['MATNR']}: {row['LABST']} in plant {row['WERKS']}")

        # Step 2: Identify materials below reorder threshold
        low_stock = [
            row for row in stock_rows
            if float(row["LABST"]) < REORDER_THRESHOLD
        ]

        assert len(low_stock) == 2  # material 100 (50 KG) and 1000 (3 EA)
        print(f"\n--- Low Stock ({len(low_stock)} materials below {REORDER_THRESHOLD}) ---")
        for row in low_stock:
            print(f"  Material {row['MATNR']}: {row['LABST']} (REORDER NEEDED)")

        # Step 3: Get material details for each low-stock item
        materials_to_order = []
        for row in low_stock:
            with pool.acquire() as conn:
                detail = conn.call("BAPI_MATERIAL_GET_DETAIL", MATERIAL=row["MATNR"])
            bapi = parse_return(detail.get("RETURN"))
            assert bapi.success
            mat_data = detail["MATERIAL_GENERAL_DATA"]
            materials_to_order.append({
                "material": row["MATNR"],
                "description": mat_data.get("MATL_DESC", ""),
                "current_stock": float(row["LABST"]),
                "plant": row["WERKS"],
            })

        print(f"\n--- Materials to Reorder ---")
        for m in materials_to_order:
            print(f"  {m['material']} - {m['description']}: "
                  f"current={m['current_stock']}, will order {REORDER_QUANTITY}")

        # Step 4: Search for a vendor (pick first available)
        with pool.acquire() as conn:
            vendor_result = conn.call("BAPI_VENDOR_GETLIST", NAME="")
        vendors = vendor_result["VENDORS"]
        assert len(vendors) > 0
        chosen_vendor = vendors[0]["VENDOR"]
        print(f"\n--- Selected Vendor: {chosen_vendor} ({vendors[0]['NAME']}) ---")

        # Step 5: Create a purchase order
        po_items = []
        for i, m in enumerate(materials_to_order):
            po_items.append({
                "PO_ITEM": str((i + 1) * 10).zfill(5),
                "MATERIAL": m["material"],
                "QUANTITY": str(REORDER_QUANTITY),
                "PLANT": m["plant"],
            })

        with pool.acquire() as conn:
            result, bapi = execute_bapi_with_commit(
                conn,
                "BAPI_PO_CREATE1",
                PO_HEADER={
                    "DOC_TYPE": "NB",
                    "VENDOR": chosen_vendor,
                    "PURCH_ORG": "1000",
                    "PUR_GROUP": "001",
                    "COMP_CODE": "1000",
                },
                PO_ITEMS=po_items,
            )

        assert bapi.success, f"PO creation failed: {bapi.summary}"
        po_number = result["PURCHASEORDER"]
        assert po_number != ""
        print(f"\n--- Purchase Order Created: {po_number} ---")
        print(f"  Vendor: {chosen_vendor}")
        print(f"  Items: {len(po_items)}")
        for item in po_items:
            print(f"    - Material {item['MATERIAL']}: qty {item['QUANTITY']}")
        print(f"  Status: COMMITTED")

    def test_no_reorder_when_stock_sufficient(self):
        """If all stock is above threshold, no PO should be created."""

        high_threshold = 1  # very low threshold — everything is above

        with pool.acquire() as conn:
            stock_rows = _read_table_as_dicts(
                conn, "MARD",
                fields=["MATNR", "LABST"],
            )

        low_stock = [
            row for row in stock_rows
            if float(row["LABST"]) < high_threshold
        ]

        assert len(low_stock) == 0, "No materials should be below threshold=1"

    def test_reorder_only_specific_plant(self):
        """Filter stock check to a specific plant."""

        with pool.acquire() as conn:
            stock_rows = _read_table_as_dicts(
                conn, "MARD",
                fields=["MATNR", "WERKS", "LABST"],
            )

        # All our mock data is plant 1000
        plant_stock = [r for r in stock_rows if r["WERKS"] == "1000"]
        assert len(plant_stock) == 3

        # Non-existent plant should return nothing useful
        other_plant = [r for r in stock_rows if r["WERKS"] == "2000"]
        assert len(other_plant) == 0
