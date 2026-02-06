"""Tests for MCP tools using mock connection."""

from __future__ import annotations

import json

import pytest

from sap_mcp.connection.manager import pool
from sap_mcp.connection.mock import MockConnection


class TestGenericRFCTools:

    def test_read_table_mara(self):
        from sap_mcp.tools.generic_rfc import register
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)

        # Access registered tool function
        with pool.acquire() as conn:
            result = conn.call(
                "RFC_READ_TABLE",
                QUERY_TABLE="MARA",
                DELIMITER="|",
                ROWCOUNT=10,
            )
        assert "DATA" in result
        assert "FIELDS" in result
        assert len(result["DATA"]) == 3

    def test_read_table_with_fields(self):
        with pool.acquire() as conn:
            result = conn.call(
                "RFC_READ_TABLE",
                QUERY_TABLE="MARA",
                DELIMITER="|",
                FIELDS=[{"FIELDNAME": "MATNR"}, {"FIELDNAME": "MTART"}],
                ROWCOUNT=10,
            )
        fields = result["FIELDS"]
        assert len(fields) == 2
        assert fields[0]["FIELDNAME"] == "MATNR"

    def test_read_table_unknown_table(self):
        with pool.acquire() as conn:
            result = conn.call("RFC_READ_TABLE", QUERY_TABLE="ZZZZZ", DELIMITER="|")
        assert result["DATA"] == []

    def test_describe_rfc(self):
        with pool.acquire() as conn:
            desc = conn.get_function_description("BAPI_MATERIAL_GET_DETAIL")
        assert desc.name == "BAPI_MATERIAL_GET_DETAIL"
        assert len(desc.parameters) > 0
        param_names = [p["name"] for p in desc.parameters]
        assert "MATERIAL" in param_names

    def test_call_rfc_unknown_function(self):
        with pool.acquire() as conn:
            result = conn.call("Z_CUSTOM_FUNC", PARAM1="test")
        assert "RETURN" in result


class TestMasterDataTools:

    def test_get_material_found(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_MATERIAL_GET_DETAIL", MATERIAL="000000000000000100")
        assert result["MATERIAL_GENERAL_DATA"]["MATL_DESC"] == "Steel Rod 10mm"

    def test_get_material_not_found(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_MATERIAL_GET_DETAIL", MATERIAL="999999999999999999")
        assert result["RETURN"]["TYPE"] == "E"

    def test_search_materials(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_MATERIAL_GETLIST", MATNR_RA=[], MATERIAL_DESCRIPTION="")
        assert len(result["MATNRLIST"]) == 3

    def test_get_customer_found(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_CUSTOMER_GETDETAIL2", CUSTOMERNO="0000001000")
        assert result["CUSTOMERGENERALDETAIL"]["NAME"] == "Acme Corporation"

    def test_get_customer_not_found(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_CUSTOMER_GETDETAIL2", CUSTOMERNO="9999999999")
        assert result["RETURN"]["TYPE"] == "E"

    def test_search_customers(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_CUSTOMER_GETLIST", NAME="", CITY="")
        assert len(result["ADDRESSDATA"]) == 2

    def test_get_vendor_found(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_VENDOR_GETDETAIL", VENDORNO="0000003000")
        assert result["GENERALDETAIL"]["NAME"] == "Steel Supplies AG"

    def test_search_vendors(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_VENDOR_GETLIST", NAME="")
        assert len(result["VENDORS"]) == 2


class TestSalesTools:

    def test_search_sales_orders(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_SALESORDER_GETLIST")
        assert len(result["SALES_ORDERS"]) == 2

    def test_search_by_customer(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_SALESORDER_GETLIST", CUSTOMER_NUMBER="0000001000")
        assert len(result["SALES_ORDERS"]) == 1
        assert result["SALES_ORDERS"][0]["SOLD_TO"] == "0000001000"

    def test_create_sales_order(self):
        with pool.acquire() as conn:
            result = conn.call(
                "BAPI_SALESORDER_CREATEFROMDAT2",
                ORDER_HEADER_IN={"DOC_TYPE": "TA"},
                ORDER_PARTNERS=[],
                ORDER_ITEMS_IN=[],
            )
        assert result["SALESDOCUMENT"] != ""
        assert result["RETURN"][0]["TYPE"] == "S"

    def test_change_sales_order(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_SALESORDER_CHANGE", SALESDOCUMENT="0000010001")
        assert result["RETURN"][0]["TYPE"] == "S"


class TestPurchasingTools:

    def test_get_purchase_order(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_PO_GETDETAIL1", PURCHASEORDER="4500000001")
        assert result["PO_HEADER"]["VENDOR"] == "0000003000"
        assert len(result["PO_ITEMS"]) == 1

    def test_get_purchase_order_not_found(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_PO_GETDETAIL1", PURCHASEORDER="9999999999")
        assert result["RETURN"][0]["TYPE"] == "E"

    def test_search_purchase_orders(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_PO_GETITEMS")
        assert len(result["PO_ITEMS"]) > 0

    def test_create_purchase_order(self):
        with pool.acquire() as conn:
            result = conn.call(
                "BAPI_PO_CREATE1",
                PO_HEADER={"DOC_TYPE": "NB", "VENDOR": "0000003000"},
                PO_ITEMS=[],
            )
        assert result["PURCHASEORDER"] != ""


class TestInvoiceTools:

    def test_get_invoices(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_INCOMINGINVOICE_GETLIST")
        assert len(result["INVOICELIST"]) == 1
        assert result["INVOICELIST"][0]["NET_VALUE"] == "15000.00"


class TestTransactionHandling:

    def test_commit(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_TRANSACTION_COMMIT", WAIT="X")
        assert result["RETURN"]["TYPE"] == "S"

    def test_rollback(self):
        with pool.acquire() as conn:
            result = conn.call("BAPI_TRANSACTION_ROLLBACK")
        assert result["RETURN"]["TYPE"] == "S"

    def test_execute_bapi_with_commit_success(self):
        from sap_mcp.bapi.transaction import execute_bapi_with_commit

        with pool.acquire() as conn:
            result, bapi = execute_bapi_with_commit(
                conn,
                "BAPI_SALESORDER_CREATEFROMDAT2",
                ORDER_HEADER_IN={},
                ORDER_PARTNERS=[],
                ORDER_ITEMS_IN=[],
            )
        assert bapi.success
        assert result["SALESDOCUMENT"] != ""
